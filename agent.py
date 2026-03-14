#!/usr/bin/env python3
"""
Agent CLI - Task 1: Call LLM without tools
"""

import os
import sys
import json
import argparse
import requests
from dotenv import load_dotenv

def load_config():
    """Load config from .env.agent.secret"""
    load_dotenv('.env.agent.secret')
    return {
        'api_key': os.getenv('LLM_API_KEY'),
        'api_base': os.getenv('LLM_API_BASE'),
        'model': os.getenv('LLM_MODEL')
    }

def call_llm(question, config):
    """Call LLM API and return response JSON"""
    headers = {
        'Authorization': f'Bearer {config["api_key"]}',
        'Content-Type': 'application/json'
    }
    
    payload = {
        'model': config['model'],
        'messages': [
            {'role': 'system', 'content': 'You are a helpful assistant. Answer concisely.'},
            {'role': 'user', 'content': question}
        ],
        'temperature': 0.7
    }
    
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

def parse_response(response_json):
    """Extract answer from API response"""
    if not response_json:
        return 'Failed to get response from LLM'
    
    try:
        return response_json['choices'][0]['message']['content']
    except (KeyError, IndexError):
        return 'Error parsing LLM response'

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('question', help='Question to ask the LLM')
    args = parser.parse_args()
    
    config = load_config()
    
    # Validate config
    if not all([config['api_key'], config['api_base'], config['model']]):
        print('Error: Missing LLM configuration. Check .env.agent.secret', file=sys.stderr)
        print(json.dumps({'answer': 'Configuration error', 'tool_calls': []}))
        sys.exit(0)
    
    # Call LLM
    response_json = call_llm(args.question, config)
    answer = parse_response(response_json)
    
    # Output JSON
    output = {
        'answer': answer,
        'tool_calls': []
    }
    print(json.dumps(output))

if __name__ == '__main__':
    main()
