# Task 2: The Documentation Agent - Implementation Plan

## 1. Tool Definitions

### 1.1 read_file(path)
- **Purpose:** Read file content from project
- **Security:** Prevent path traversal (block `..`, enforce absolute path check)
- **Returns:** File content or error message

### 1.2 list_files(path)
- **Purpose:** List directory contents
- **Security:** Same as read_file
- **Returns:** Newline-separated list

## 2. Tool Schemas (OpenAI format)
```json
{
  "type": "function",
  "function": {
    "name": "read_file",
    "description": "Read a file from the project",
    "parameters": {
      "type": "object",
      "properties": {
        "path": {"type": "string", "description": "Relative path from project root"}
      },
      "required": ["path"]
    }
  }
}
