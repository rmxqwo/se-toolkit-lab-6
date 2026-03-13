# System Agent CLI

## Overview

The System Agent is an AI assistant that can answer questions about the system using three sources:

- **Documentation** (wiki files)
- **Source code** (backend files)
- **Live API data** (backend endpoints)

## Architecture

### Tools

#### `read_file`

Reads documentation or source code files.

- **Parameters**: `path` (string)
- **Security**: Prevents directory traversal
- **Use cases**: Wiki questions, system facts, debugging

#### `list_files`

Explores project structure.

- **Parameters**: `path` (string)
- **Use cases**: Discovering available documentation or code

#### `query_api`

Queries the live backend API with authentication.

- **Parameters**: `method` (string), `path` (string), `body` (optional)
- **Authentication**: `X-API-Key` header with `LMS_API_KEY`
- **Returns**: JSON with `status_code` and `body`
- **Use cases**: Item counts, completion rates, live data

### Agentic Loop

1. User question → LLM with tool definitions
2. LLM decides which tool(s) to use
3. Tools executed, results fed back
4. Repeat until answer or max 10 calls
5. Output JSON with answer, source (optional), and tool_calls

## Environment Configuration

All configuration comes from environment variables (no hardcoding):

| Variable | Purpose | Required |
|----------|---------|----------|
| `LLM_API_KEY` | LLM provider API key | Yes |
| `LLM_API_BASE` | LLM endpoint URL | No (has default) |
| `LLM_MODEL` | Model name | No (has default) |
| `LMS_API_KEY` | Backend API key | Yes |
| `AGENT_API_BASE_URL` | Backend base URL | No (default: localhost:42002) |

## Decision Strategy

The system prompt guides the LLM to choose tools based on question type:

1. **Wiki questions** (e.g., "How to resolve merge conflict?")
   → `list_files("wiki")` + `read_file("wiki/*.md")`

2. **System facts** (e.g., "What framework?")
   → `read_file("backend/*.py")` - look for imports, configs

3. **Live data** (e.g., "How many items?")
   → `query_api("GET", "/items/")` or `/items/count`

4. **Debugging** (e.g., "Why is completion-rate failing?")
   → First `query_api` to see error, then `read_file` to find bug

## Benchmark Results

After implementing `query_api` and iterating on system prompt:
