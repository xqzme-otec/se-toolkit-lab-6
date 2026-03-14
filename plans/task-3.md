# Task 3: The System Agent - Implementation Plan

## 1. New Tool: query_api
- **Purpose:** Call backend API endpoints
- **Parameters:** method (GET/POST), path, body (optional)
- **Authentication:** Bearer token with LMS_API_KEY from env
- **Base URL:** AGENT_API_BASE_URL from env (default: http://localhost:42002)

## 2. Tool Schema
{
  "type": "function",
  "function": {
    "name": "query_api",
    "description": "Call the backend API. Use for checking data, status codes, etc.",
    "parameters": {
      "type": "object",
      "properties": {
        "method": {"type": "string", "enum": ["GET", "POST"], "default": "GET"},
        "path": {"type": "string", "description": "API path like /items/"},
        "body": {"type": "string", "description": "JSON body for POST requests"}
      },
      "required": ["method", "path"]
    }
  }
}

## 3. System Prompt Update
Add instructions for when to use:
- list_files/read_file → wiki and code questions
- query_api → data queries, status codes, API behavior

## 4. Environment Variables
- LLM_API_KEY, LLM_API_BASE, LLM_MODEL (from .env.agent.secret)
- LMS_API_KEY (from .env.docker.secret)
- AGENT_API_BASE_URL (optional, default localhost:42002)

## 5. Benchmark Strategy
1. Run `uv run run_eval.py` to see failures
2. Fix one by one:
   - Question 4-5: query_api basic
   - Question 6-7: error diagnosis (query_api + read_file)
   - Question 8-9: LLM judge (complex reasoning)
3. Iterate until all 10 pass

## 6. Initial Score (to be filled after first run)
- [ ] Run 1: __/10
- [ ] Run 2: __/10
- [ ] Final: 10/10
