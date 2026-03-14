# Task 1: Call an LLM from Code - Implementation Plan

## 1. Provider and Model Selection

- **Provider**: Qwen Code API (recommended in the task)
- **Model**: `qwen3-coder-plus` (from `.env.agent.example`)
- **Base URL**: from `LLM_API_BASE` in `.env.agent.secret`
- **API Key**: from `LLM_API_KEY` in `.env.agent.secret`

## 2. Code Structure (`agent.py`)

### 2.1. Imports

- `os`, `sys`, `json`, `argparse`ыыыыыы
- `requests` for HTTP
- `dotenv` for loading `.env.agent.secret`

### 2.2. Functions

1. `load_config()` - reads `.env.agent.secret`, returns API settings dict
2. `call_llm(question, config)` - sends POST request to API, returns response
3. `parse_response(response_json)` - extracts answer text from JSON
4. `main()` - parses args, calls chain, outputs JSON

### 2.3. Output Format

Always JSON with fields:

- `answer`: string with the answer
- `tool_calls`: empty list `[]`

Debug output (logs, errors) - only to `stderr`

### 2.4. System Prompt

Minimal: "You are a helpful assistant. Answer the user's question concisely."

## 3. Qwen API Request Format

OpenAI-compatible:

```json
{
  "model": "qwen3-coder-plus",
  "messages": [
    {"role": "system", "content": "..."},
    {"role": "user", "content": "question"}
  ],
  "temperature": 0.7
}
