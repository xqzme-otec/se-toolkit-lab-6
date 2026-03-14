# Agent CLI - Task 2: Documentation Agent

## Overview

CLI agent that answers questions by reading wiki files using tools and an agentic loop.

## Provider

- **Qwen Code API** running locally via Docker
- Model: `qwen3-coder-plus`
- Port: 42005

## Tools

The agent has two tools:

1. **`list_files(path)`** - lists contents of a directory (used to explore wiki/)
2. **`read_file(path)`** - reads file content (used to find answers in wiki files)

## Agentic Loop

1. Send question + tool definitions to LLM
2. If LLM requests tool calls → execute tools → append results → repeat (max 10 iterations)
3. If LLM responds with text → that's final answer
4. Output JSON with answer, source, and all tool calls made

## System Prompt

The agent is instructed to:

- First explore wiki/ with `list_files`
- Then read relevant files with `read_file`
- Include source reference (wiki/file.md#section) in answer

## Usage

```bash
uv run agent.py "How do you resolve a merge conflict?"
