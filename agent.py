#!/usr/bin/env python3
"""
Agent CLI - Task 2: Documentation Agent with tools
"""

import os
import sys
import json
import argparse
import requests
from pathlib import Path
from dotenv import load_dotenv

# Get project root directory
PROJECT_ROOT = Path(__file__).parent.absolute()

def load_config():
    """Load config from .env.agent.secret"""
    load_dotenv('.env.agent.secret')
    return {
        'api_key': os.getenv('LLM_API_KEY'),
        'api_base': os.getenv('LLM_API_BASE'),
        'model': os.getenv('LLM_MODEL')
    }

def safe_path(path):
    """Prevent path traversal attacks"""
    requested = (PROJECT_ROOT / path).resolve()
    if PROJECT_ROOT not in requested.parents and requested != PROJECT_ROOT:
        return None, f"Access denied: path outside project root: {path}"
    return requested, None

def read_file(path):
    """Read file from project"""
    full_path, error = safe_path(path)
    if error:
        return error
    
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return f"File not found: {path}"
    except Exception as e:
        return f"Error reading file: {str(e)}"

def list_files(path):
    """List directory contents"""
    full_path, error = safe_path(path)
    if error:
        return error
    
    try:
        entries = os.listdir(full_path)
        # Filter out hidden files/dirs and sort
        entries = [e for e in entries if not e.startswith('.')]
        return '\n'.join(sorted(entries))
    except FileNotFoundError:
        return f"Directory not found: {path}"
    except NotADirectoryError:
        return f"Not a directory: {path}"
    except Exception as e:
        return f"Error listing directory: {str(e)}"

# Tool definitions for OpenAI format
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a file from the project. Use this to read wiki files, source code, etc.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string", 
                        "description": "Relative path from project root (e.g., 'wiki/git-workflow.md')"
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files and directories at a given path. Use this to explore wiki/ directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative directory path from project root (e.g., 'wiki')"
                    }
                },
                "required": ["path"]
            }
        }
    }
]

# Map tool names to functions
TOOL_FUNCTIONS = {
    "read_file": read_file,
    "list_files": list_files
}

SYSTEM_PROMPT = """You are a documentation agent for a software engineering toolkit project.
Your goal is to answer questions by reading the wiki files.

Available tools:
- list_files(path): Explore directories, especially wiki/
- read_file(path): Read file contents

Strategy:
1. First use list_files('wiki') to see available documentation
2. Then use read_file on relevant wiki files to find answers
3. When you find the answer, include the source file path with anchor like wiki/file.md#section

Answer concisely but completely. Always include the source reference."""

def execute_tool_calls(tool_calls):
    """Execute tool calls and return results"""
    results = []
    for tool_call in tool_calls:
        function = tool_call.get('function', {})
        name = function.get('name')
        args = function.get('arguments', {})
        
        # Parse arguments if they're string
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except json.JSONDecodeError:
                args = {}
        
        if name in TOOL_FUNCTIONS:
            result = TOOL_FUNCTIONS[name](**args)
        else:
            result = f"Unknown tool: {name}"
        
        results.append({
            "tool": name,
            "args": args,
            "result": result,
            "tool_call_id": tool_call.get('id', '')
        })
    
    return results

def call_llm_with_tools(messages, config, tools=None):
    """Call LLM API with optional tools"""
    headers = {
        'Authorization': f'Bearer {config["api_key"]}',
        'Content-Type': 'application/json'
    }
    
    payload = {
        'model': config['model'],
        'messages': messages,
        'temperature': 0.7
    }
    
    if tools:
        payload['tools'] = tools
        payload['tool_choice'] = 'auto'
    
    try:
        response = requests.post(
            f'{config["api_base"]}/chat/completions',
            headers=headers,
            json=payload,
            timeout=60
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f'Error calling LLM: {e}', file=sys.stderr)
        return None

def agent_loop(question, config, max_iterations=10):
    """Main agent loop with tool execution"""
    messages = [
        {'role': 'system', 'content': SYSTEM_PROMPT},
        {'role': 'user', 'content': question}
    ]
    
    all_tool_calls = []
    iterations = 0
    
    while iterations < max_iterations:
        iterations += 1
        
        # Call LLM with tools
        response = call_llm_with_tools(messages, config, tools=TOOLS)
        if not response:
            return {
                'answer': 'Failed to get response from LLM',
                'source': '',
                'tool_calls': all_tool_calls
            }
        
        message = response['choices'][0]['message']
        
        # Check if there are tool calls
        if 'tool_calls' in message and message['tool_calls']:
            # Execute tools
            tool_results = execute_tool_calls(message['tool_calls'])
            
            # Add assistant message with tool calls to history
            messages.append({
                'role': 'assistant',
                'content': message.get('content'),
                'tool_calls': message['tool_calls']
            })
            
            # Add tool results
            for result in tool_results:
                messages.append({
                    'role': 'tool',
                    'tool_call_id': result['tool_call_id'],
                    'content': result['result']
                })
                # Store in all_tool_calls for output
                all_tool_calls.append({
                    'tool': result['tool'],
                    'args': result['args'],
                    'result': result['result']
                })
        else:
            # No tool calls - this is the final answer
            answer = message.get('content', '')
            
            # Try to extract source from answer (look for wiki/...md#... pattern)
            source = ''
            import re
            match = re.search(r'(wiki/[a-zA-Z0-9\-\./]+\.md#[a-zA-Z0-9\-]+)', answer)
            if match:
                source = match.group(1)
            
            return {
                'answer': answer,
                'source': source,
                'tool_calls': all_tool_calls
            }
    
    # Max iterations reached
    return {
        'answer': 'Maximum iterations reached without final answer',
        'source': '',
        'tool_calls': all_tool_calls
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('question', help='Question to ask the agent')
    args = parser.parse_args()
    
    config = load_config()
    
    # Validate config
    if not all([config['api_key'], config['api_base'], config['model']]):
        print('Error: Missing LLM configuration. Check .env.agent.secret', file=sys.stderr)
        print(json.dumps({'answer': 'Configuration error', 'source': '', 'tool_calls': []}))
        sys.exit(0)
    
    # Run agent loop
    output = agent_loop(args.question, config)
    
    # Output JSON
    print(json.dumps(output))

if __name__ == '__main__':
    main()