# Agent CLI - Task 1

## Overview
Simple CLI agent that calls LLM (Qwen) and returns JSON response.

## Provider
- **Qwen Code API** running locally via Docker
- Model: `qwen3-coder-plus`
- Port: 42005

## Usage
```bash
uv run agent.py "Your question here"
