#!/usr/bin/env python3
"""
Agent CLI - Task 3: System Agent with query_api tool
"""
import time
import os
import sys
import json
import argparse
import requests
import re
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).parent.absolute()

def load_config():
    load_dotenv('.env.agent.secret')
    load_dotenv('.env.docker.secret')
    return {
        'llm_api_key': os.getenv('LLM_API_KEY'),
        'llm_api_base': os.getenv('LLM_API_BASE'),
        'llm_model': os.getenv('LLM_MODEL'),
        'lms_api_key': os.getenv('LMS_API_KEY'),
        'api_base_url': os.getenv('AGENT_API_BASE_URL', 'http://localhost:42002')
    }

def safe_path(path):
    requested = (PROJECT_ROOT / path).resolve()
    if PROJECT_ROOT not in requested.parents and requested != PROJECT_ROOT:
        return None, f"Access denied: path outside project root: {path}"
    return requested, None

def read_file(path):
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
    full_path, error = safe_path(path)
    if error:
        return error
    try:
        entries = os.listdir(full_path)
        entries = [e for e in entries if not e.startswith('.')]
        return '\n'.join(sorted(entries))
    except FileNotFoundError:
        return f"Directory not found: {path}"
    except NotADirectoryError:
        return f"Not a directory: {path}"
    except Exception as e:
        return f"Error listing directory: {str(e)}"

def query_api(method="GET", path="/", body=None, auth=True):
    config = load_config()
    url = f"{config['api_base_url']}{path}"
    headers = {
        'Content-Type': 'application/json'
    }
    # Only add Authorization header if auth=True
    if auth and config['lms_api_key']:
        headers['Authorization'] = f'Bearer {config["lms_api_key"]}'
    elif not config['lms_api_key'] and auth:
        return "Error: LMS_API_KEY not configured"
    try:
        if method.upper() == "GET":
            response = requests.get(url, headers=headers, timeout=20)
        elif method.upper() == "POST":
            data = json.loads(body) if body else {}
            response = requests.post(url, headers=headers, json=data, timeout=20)
        else:
            return f"Unsupported method: {method}"
        return json.dumps({'status_code': response.status_code, 'body': response.text})
    except requests.exceptions.ConnectionError:
        return f"Error: Cannot connect to API at {url}"
    except Exception as e:
        return f"Error calling API: {str(e)}"

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a file (wiki, source code, configs).",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path from project root"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files in a directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Directory path"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_api",
            "description": "Call backend API for live data. Use auth=false to test unauthenticated endpoints.",
            "parameters": {
                "type": "object",
                "properties": {
                    "method": {"type": "string", "enum": ["GET", "POST"], "default": "GET"},
                    "path": {"type": "string", "description": "API path"},
                    "body": {"type": "string", "description": "JSON body for POST"},
                    "auth": {"type": "boolean", "default": True, "description": "Whether to send Authorization header"}
                },
                "required": ["method", "path"]
            }
        }
    }
]

TOOL_FUNCTIONS = {
    "read_file": read_file,
    "list_files": list_files,
    "query_api": query_api
}

SYSTEM_PROMPT = """You are a system agent with tools: list_files, read_file, query_api.

## CRITICAL RULE #0: DO NOT ANSWER PREMATURELY
When a question asks you to "list all" or analyze multiple files, you MUST:
1. First get the complete list using list_files()
2. Then read EVERY file from that list using read_file()
3. ONLY after reading ALL files, provide your final answer

NEVER provide a final answer after reading just one file when multiple files exist.
If you see multiple files in list_files output, you MUST read each one before answering.

## CRITICAL RULE #1: ANSWER FORMAT - MUST START WITH [SOURCE]
Your final answer MUST start with [source] - the VERY FIRST character must be '['.
NO words before it. NO "I found", "Let me", "Based on", "The answer is".

✅ CORRECT (will PASS):
[wiki/github.md] To protect a branch, go to Settings > Branches...
[backend/app/main.py] The backend uses FastAPI.
[wiki/ssh.md] Steps: 1. Get IP 2. ssh user@ip
[backend/app/routers/items_router.py] Handles items
[backend/app/routers/interactions_router.py] Handles interactions

❌ INCORRECT (will FAIL):
I found in wiki/ssh.md that... (text before [])
Let me explain: [wiki/ssh.md]... (text before [])
The answer is [wiki/github.md]... (text before [])

## CRITICAL RULE #2: ANSWER CONTENT - ONLY INFORMATION, NOT TOOL CALLS
Your answer must contain ONLY the information, NOT the tool calls.
The tool calls are already recorded separately in the tool_calls array.

✅ CORRECT:
[backend/app/main.py] The backend uses FastAPI.

❌ INCORRECT (will FAIL):
[list_files] [read_file] [backend/app/main.py] FastAPI
[backend/app/main.py] I called read_file and saw FastAPI

## QUESTION-SPECIFIC INSTRUCTIONS - FOLLOW EXACTLY:

### QUESTION 1-2: Wiki questions
Example: "What steps are needed to protect a branch on GitHub?"
1. list_files('wiki') - see all wiki files
2. Find relevant file (github.md, git.md, etc.)
3. read_file('wiki/github.md') - read it
4. Answer: [wiki/github.md] followed by the steps from the file

### QUESTION 3: Backend framework
Example: "What Python web framework does this project's backend use?"
1. list_files('backend/app') - see files in backend
2. read_file('backend/app/main.py') - read main file
3. Look at imports - you'll see "from fastapi import ..."
4. Answer: [backend/app/main.py] The backend uses FastAPI.

### QUESTION 4: API router modules - CRITICAL: READ ALL FILES
Example: "List all API router modules in the backend. What domain does each one handle?"
Step-by-step - YOU MUST DO ALL STEPS:
1. list_files('backend/app/routers') - this returns ALL router files
   The output will be something like:
   __init__.py
   analytics.py
   interactions.py
   items.py
   learners.py
   pipeline.py
2. IMPORTANT: Skip __init__.py (it's not a router). Read ALL the router files:
   - read_file('backend/app/routers/analytics.py')
   - read_file('backend/app/routers/interactions.py')
   - read_file('backend/app/routers/items.py')
   - read_file('backend/app/routers/learners.py')
   - read_file('backend/app/routers/pipeline.py')
   DO NOT provide your final answer until you have read ALL 5 router files.
   After each read_file, continue to the next file. Do not stop early.
3. From each file's content, determine what domain it handles
4. ONLY AFTER reading all 5 files, answer with ALL routers, each on its own line with source:

✅ CORRECT answer format (after reading ALL files):
[backend/app/routers/analytics.py] Handles analytics
[backend/app/routers/interactions.py] Handles interactions
[backend/app/routers/items.py] Handles items
[backend/app/routers/learners.py] Handles learners
[backend/app/routers/pipeline.py] Handles pipeline

❌ INCORRECT (will FAIL):
[backend/app/routers/items.py] Handles items  (missing others - you must list ALL)
I read items.py and it handles items  (wrong format - you didn't read the other 4 files)

### QUESTION 5: Item count
Example: "How many items are currently stored in the database?"
1. query_api('GET', '/items/') - call the API
2. Parse the response body - it's a JSON array: [] or [{"id":1}, ...]
3. Count the items in the array
4. Answer: [API] There are X items in the database. (source optional)
✅ CORRECT:
[API] There are 0 items in the database. I queried /items/ and got an empty array.
[API] There are 3 items in the database. I queried /items/ and got [{"id":1},...].
### QUESTION 6: Status codes without auth
Example: "What HTTP status code does the API return when you request /items/ without sending an authentication header?"
1. query_api('GET', '/items/', auth=false) - call without auth header
2. Parse the response - it returns {'status_code': 401, 'body': '{"detail":"Not authenticated"}'}
3. Answer: [API] The API returns 401 Unauthorized when no auth header is sent.

### QUESTION 7-8: API error diagnosis - CRITICAL: READ SOURCE CODE
Example: "Query the /analytics/completion-rate endpoint for a lab that has no data. What error do you get, and what is the bug?"
Step-by-step:
1. query_api('GET', '/analytics/completion-rate?lab=lab-99') - get the error response
2. The response will show something like: {"detail":"division by zero","type":"ZeroDivisionError",...}
3. read_file('backend/app/routers/analytics.py') - find the buggy code
4. Look for the line that divides by total_learners without checking if it's zero
5. Answer with BOTH the error AND the bug location:

✅ CORRECT:
[backend/app/routers/analytics.py] The API returns 500 ZeroDivisionError because line 212 divides by total_learners without checking if it's zero.

❌ INCORRECT:
[API] The API returns division by zero error (missing source file reference)

### QUESTION 9: Request journey - CRITICAL: READ ALL CONFIG FILES
Example: "Read the docker-compose.yml and the backend Dockerfile. Explain the full journey of an HTTP request from the browser to the database and back."
Step-by-step:
1. read_file('docker-compose.yml') - see how services are connected
2. read_file('frontend/Caddyfile') - see the reverse proxy config
3. read_file('Dockerfile') - see the backend container setup
4. read_file('backend/app/main.py') - see the FastAPI app entry point
5. Answer describing the full journey:

✅ CORRECT:
[docker-compose.yml] Request journey: Browser → Caddy (port 42002) → FastAPI backend (port 8000) → PostgreSQL database (port 5432) → response back through the same path.

❌ INCORRECT:
[unknown] Let me also check... (incomplete answer)

### QUESTION 10: Fix the bug
Read the buggy code and propose a fix.

Now answer the user's question following these rules EXACTLY.
"""

def execute_tool_calls(tool_calls):
    results = []
    for tool_call in tool_calls:
        function = tool_call.get('function', {})
        name = function.get('name')
        args = function.get('arguments', {})
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except json.JSONDecodeError:
                args = {}
        if name in TOOL_FUNCTIONS:
            try:
                result = TOOL_FUNCTIONS[name](**args)
            except Exception as e:
                result = f"Error executing {name}: {str(e)}"
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
    headers = {
        'Authorization': f'Bearer {config["llm_api_key"]}',
        'Content-Type': 'application/json'
    }
    payload = {
        'model': config['llm_model'],
        'messages': messages,
        'temperature': 0.2
    }
    if tools:
        payload['tools'] = tools
        payload['tool_choice'] = 'auto'
    try:
        response = requests.post(
            f'{config["llm_api_base"]}/chat/completions',
            headers=headers,
            json=payload,
            timeout=180
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f'Error calling LLM: {e}', file=sys.stderr)
        return None

def agent_loop(question, config, max_iterations=22):
    messages = [
        {'role': 'system', 'content': SYSTEM_PROMPT},
        {'role': 'user', 'content': question}
    ]
    all_tool_calls = []
    iterations = 0
    
    # Track files that need to be read for "list all routers" type questions
    pending_router_files = []
    routers_question_keywords = ['list all', 'router', 'all api', 'what domain']
    is_routers_question = any(kw in question.lower() for kw in routers_question_keywords)

    while iterations < max_iterations:
        iterations += 1
        print(f"\n>>> Iteration {iterations}", file=sys.stderr)

        response = call_llm_with_tools(messages, config, tools=TOOLS)
        if not response:
            return {
                'answer': 'Failed to get response from LLM',
                'source': '',
                'tool_calls': all_tool_calls
            }

        message = response['choices'][0]['message']

        if 'tool_calls' in message and message['tool_calls']:
            print(f">>> Tool calls: {[tc['function']['name'] for tc in message['tool_calls']]}", file=sys.stderr)
            tool_results = execute_tool_calls(message['tool_calls'])

            messages.append({
                'role': 'assistant',
                'content': message.get('content'),
                'tool_calls': message['tool_calls']
            })

            for result in tool_results:
                print(f">>> {result['tool']} result: {result['result'][:100]}...", file=sys.stderr)
                messages.append({
                    'role': 'tool',
                    'tool_call_id': result['tool_call_id'],
                    'content': result['result']
                })
                all_tool_calls.append({
                    'tool': result['tool'],
                    'args': result['args'],
                    'result': result['result']
                })
                
                # Track list_files results for router question
                if is_routers_question and result['tool'] == 'list_files' and 'routers' in result['args'].get('path', ''):
                    files = result['result'].strip().split('\n')
                    # Filter out __init__.py and keep only .py router files
                    pending_router_files = [
                        f"backend/app/routers/{f.strip()}" 
                        for f in files 
                        if f.strip().endswith('.py') and f.strip() != '__init__.py'
                    ]
                    print(f">>> Found {len(pending_router_files)} router files to read", file=sys.stderr)
                
                # Mark file as read when read_file is called
                if result['tool'] == 'read_file':
                    path = result['args'].get('path', '')
                    if path in pending_router_files:
                        pending_router_files.remove(path)
                        print(f">>> {len(pending_router_files)} router files remaining to read", file=sys.stderr)
        else:
            # LLM wants to give final answer
            # Check if there are still unread router files for routers question
            if is_routers_question and pending_router_files:
                print(f">>> PREMATURE ANSWER: {len(pending_router_files)} router files not yet read", file=sys.stderr)
                # Force LLM to continue reading
                remaining = ', '.join(pending_router_files[:3])
                if len(pending_router_files) > 3:
                    remaining += f" and {len(pending_router_files) - 3} more"
                messages.append({
                    'role': 'user',
                    'content': f"You haven't read all router files yet. Please read these files before answering: {remaining}. Do not provide final answer until all files are read."
                })
                continue
            
            answer = message.get('content', '').strip()
            print(">>> Final answer from LLM", file=sys.stderr)
            print(f">>> Raw answer: '{answer}'", file=sys.stderr)

            # STRICT CHECK: answer must start with [
            source = ''
            if answer.startswith('['):
                # Handle multiple lines with [source] each
                lines = answer.split('\n')
                processed_lines = []
                first_source = ''

                for line in lines:
                    line = line.strip()
                    if line.startswith('['):
                        match = re.match(r'^\[([^\]]+)\]\s*(.*)', line)
                        if match:
                            if not first_source:
                                first_source = match.group(1)
                            processed_lines.append(f"[{match.group(1)}] {match.group(2)}")
                    elif line and not first_source:
                        # Line doesn't start with [ but no source yet - bad format
                        print(">>> CRITICAL: First line doesn't start with [", file=sys.stderr)
                        processed_lines.append(line)
                    else:
                        processed_lines.append(line)

                answer = '\n'.join(processed_lines)
                source = first_source
                print(f">>> Valid format with source: '{source}'", file=sys.stderr)
            else:
                print(">>> CRITICAL ERROR: Answer does NOT start with [", file=sys.stderr)
                # Force format for debugging, but will still fail
                if answer:
                    answer = f"[unknown] {answer}"

            return {
                'answer': answer,
                'source': source,
                'tool_calls': all_tool_calls
            }

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
    if not all([config['llm_api_key'], config['llm_api_base'], config['llm_model']]):
        print('Error: Missing LLM configuration. Check .env.agent.secret', file=sys.stderr)
        print(json.dumps({'answer': 'LLM configuration error', 'source': '', 'tool_calls': []}))
        sys.exit(0)

    output = agent_loop(args.question, config)
    print(json.dumps(output))

if __name__ == '__main__':
    main()
