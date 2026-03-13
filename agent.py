
## 2. Обновленный `agent.py` с query_api

```python
#!/usr/bin/env python3
"""
System Agent CLI with tools for reading files and querying API.
Usage: uv run agent.py "Your question here"
"""

import os
import sys
import json
import time
import requests
from dotenv import load_dotenv
from openai import OpenAI
import argparse
from typing import Dict, Any, List, Optional
from urllib.parse import urljoin

# Load environment variables
load_dotenv('.env.agent.secret')
load_dotenv('.env.docker.secret')  # For LMS_API_KEY


class SystemAgent:
    """Agent that can read files, list directories, and query the backend API."""
    
    def __init__(self):
        """Initialize agent with configuration from environment."""
        # LLM Configuration (must come from env)
        self.llm_api_key = os.getenv('LLM_API_KEY')
        self.llm_api_base = os.getenv('LLM_API_BASE', 'https://openrouter.ai/api/v1')
        self.llm_model = os.getenv('LLM_MODEL', 'meta-llama/llama-4-scout:free')
        
        # Backend API Configuration
        self.lms_api_key = os.getenv('LMS_API_KEY')
        self.api_base_url = os.getenv('AGENT_API_BASE_URL', 'http://localhost:42002')
        
        # Validate required configuration
        if not self.llm_api_key:
            raise ValueError("LLM_API_KEY not found in environment")
        if not self.lms_api_key:
            raise ValueError("LMS_API_KEY not found in environment")
        
        self.project_root = os.path.abspath('.')
        self.tool_calls_log: List[Dict[str, Any]] = []
        self.max_tool_calls = 10
        
        # Initialize OpenAI-compatible client
        self.client = OpenAI(
            base_url=self.llm_api_base,
            api_key=self.llm_api_key,
            default_headers={
                "HTTP-Referer": "http://localhost:42002",
                "X-Title": "SE Toolkit System Agent"
            }
        )
        
        # Define available tools
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "read_file",
                    "description": "Read a file from the project repository. Use this to read documentation or source code.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "Relative path from project root (e.g., 'wiki/git-workflow.md' or 'backend/main.py')"
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
                    "description": "List files and directories at a given path. Use this to explore the project structure.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "Relative directory path from project root (e.g., 'wiki' or 'backend')"
                            }
                        },
                        "required": ["path"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "query_api",
                    "description": "Send HTTP requests to the backend API. Use this to get live data from the system.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "method": {
                                "type": "string",
                                "enum": ["GET", "POST", "PUT", "DELETE"],
                                "description": "HTTP method (GET for retrieving data, POST for creating, etc.)"
                            },
                            "path": {
                                "type": "string",
                                "description": "API path (e.g., '/items/', '/analytics/completion-rate?lab=lab-99')"
                            },
                            "body": {
                                "type": "string",
                                "description": "Optional JSON request body for POST/PUT requests"
                            }
                        },
                        "required": ["method", "path"]
                    }
                }
            }
        ]
        
        self.system_prompt = """You are a system assistant with access to both documentation and live API data.

You have three tools:

1. **read_file(path)** - Read documentation or source code files
2. **list_files(path)** - Explore project structure
3. **query_api(method, path, body)** - Query the live backend API

## How to choose the right tool:

**For documentation questions** (wiki, guides):
- First use list_files("wiki") to see what's available
- Then read_file("wiki/filename.md") to find answers
- Include source reference in format "wiki/file.md#section"

**For system facts** (framework, ports, status codes):
- Read source code: read_file("backend/main.py") or read_file("backend/app.py")
- Look for framework imports, port configurations

**For live data** (item count, scores, completion rates):
- Use query_api with appropriate endpoint
- GET /items/ - list all items
- GET /items/count - get total count
- GET /analytics/completion-rate?lab=XXX - get completion rates

**For debugging**:
- First query_api to see the error
- Then read_file to find the buggy line in source code

Your final response MUST be in JSON format:
{"answer": "your answer", "source": "source reference (optional)"}

If you use API, source can be "api:/path" or omitted.
Always explain your reasoning in the answer if needed."""

    def read_file(self, path: str) -> str:
        """Read a file safely, preventing directory traversal."""
        try:
            full_path = os.path.abspath(os.path.join(self.project_root, path))
            
            if not full_path.startswith(self.project_root):
                return f"Error: Access denied - path '{path}' is outside project directory"
            
            if not os.path.exists(full_path):
                return f"Error: File '{path}' does not exist"
            if not os.path.isfile(full_path):
                return f"Error: '{path}' is not a file"
            
            with open(full_path, 'r', encoding='utf-8') as f:
                return f.read()
                
        except Exception as e:
            return f"Error reading file '{path}': {str(e)}"

    def list_files(self, path: str) -> str:
        """List files and directories safely."""
        try:
            full_path = os.path.abspath(os.path.join(self.project_root, path))
            
            if not full_path.startswith(self.project_root):
                return f"Error: Access denied - path '{path}' is outside project directory"
            
            if not os.path.exists(full_path):
                return f"Error: Path '{path}' does not exist"
            if not os.path.isdir(full_path):
                return f"Error: '{path}' is not a directory"
            
            entries = os.listdir(full_path)
            return "\n".join(sorted(entries))
            
        except Exception as e:
            return f"Error listing directory '{path}': {str(e)}"

    def query_api(self, method: str, path: str, body: Optional[str] = None) -> str:
        """
        Query the backend API with authentication.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            path: API path (e.g., '/items/')
            body: Optional JSON body for POST/PUT
            
        Returns:
            JSON string with status_code and body
        """
        try:
            # Construct full URL
            url = urljoin(self.api_base_url, path.lstrip('/'))
            
            # Prepare headers
            headers = {
                "X-API-Key": self.lms_api_key,
                "Content-Type": "application/json"
            }
            
            # Prepare request data
            data = None
            if body and method.upper() in ["POST", "PUT"]:
                try:
                    data = json.loads(body)
                except json.JSONDecodeError:
                    return json.dumps({
                        "status_code": 400,
                        "body": {"error": "Invalid JSON in request body"}
                    })
            
            # Make request
            response = requests.request(
                method=method.upper(),
                url=url,
                headers=headers,
                json=data,
                timeout=10
            )
            
            # Parse response
            try:
                response_body = response.json()
            except:
                response_body = response.text
            
            return json.dumps({
                "status_code": response.status_code,
                "body": response_body
            })
            
        except requests.Timeout:
            return json.dumps({
                "status_code": 504,
                "body": {"error": "Request timeout"}
            })
        except requests.ConnectionError:
            return json.dumps({
                "status_code": 503,
                "body": {"error": f"Could not connect to {self.api_base_url}"}
            })
        except Exception as e:
            return json.dumps({
                "status_code": 500,
                "body": {"error": str(e)}
            })

    def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Execute a tool and return its result."""
        if tool_name == "read_file":
            return self.read_file(arguments.get("path", ""))
        elif tool_name == "list_files":
            return self.list_files(arguments.get("path", ""))
        elif tool_name == "query_api":
            return self.query_api(
                arguments.get("method", "GET"),
                arguments.get("path", ""),
                arguments.get("body")
            )
        else:
            return f"Error: Unknown tool '{tool_name}'"

    def extract_json_from_response(self, text: str) -> Optional[Dict[str, str]]:
        """Extract JSON from LLM response text."""
        try:
            start_idx = text.find('{')
            end_idx = text.rfind('}')
            
            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                json_str = text[start_idx:end_idx + 1]
                return json.loads(json_str)
        except:
            pass
        return None

    def process_question(self, question: str) -> Dict[str, Any]:
        """Main agentic loop to process a question."""
        self.tool_calls_log = []
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": question}
        ]
        
        tool_call_count = 0
        
        while tool_call_count < self.max_tool_calls:
            try:
                response = self.client.chat.completions.create(
                    model=self.llm_model,
                    messages=messages,
                    tools=self.tools,
                    tool_choice="auto",
                    temperature=0.7,
                    max_tokens=1000
                )
                
                message = response.choices[0].message
                
                if message.tool_calls:
                    for tool_call in message.tool_calls:
                        tool_call_count += 1
                        if tool_call_count > self.max_tool_calls:
                            break
                        
                        function_name = tool_call.function.name
                        try:
                            arguments = json.loads(tool_call.function.arguments)
                        except:
                            arguments = {}
                        
                        result = self.execute_tool(function_name, arguments)
                        
                        self.tool_calls_log.append({
                            "tool": function_name,
                            "args": arguments,
                            "result": result
                        })
                        
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": result
                        })
                    
                    continue
                
                if message.content:
                    parsed_json = self.extract_json_from_response(message.content)
                    
                    if parsed_json and "answer" in parsed_json:
                        return {
                            "answer": parsed_json["answer"],
                            "source": parsed_json.get("source", "unknown"),
                            "tool_calls": self.tool_calls_log
                        }
                    else:
                        return {
                            "answer": message.content.strip(),
                            "source": "unknown",
                            "tool_calls": self.tool_calls_log
                        }
                
            except Exception as e:
                return {
                    "answer": f"Error processing question: {str(e)}",
                    "source": "unknown",
                    "tool_calls": self.tool_calls_log
                }
        
        return {
            "answer": "Maximum tool calls reached. Here's what I found so far.",
            "source": "unknown",
            "tool_calls": self.tool_calls_log
        }
    
    def run(self, question: str) -> None:
        """Main execution flow."""
        start_time = time.time()
        
        try:
            print(f"Processing question: {question}", file=sys.stderr)
            print(f"Using model: {self.llm_model}", file=sys.stderr)
            print(f"API Base URL: {self.api_base_url}", file=sys.stderr)
            
            result = self.process_question(question)
            
            elapsed = time.time() - start_time
            if elapsed > 60:
                raise TimeoutError(f"Execution time {elapsed:.2f}s exceeded 60s limit")
            
            print(json.dumps(result, ensure_ascii=False, indent=2))
            
        except TimeoutError as e:
            print(f"Timeout error: {e}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="System Agent - answers questions using wiki, code, and live API")
    parser.add_argument('question', help='Question about the system')
    args = parser.parse_args()
    
    try:
        agent = SystemAgent()
        agent.run(args.question)
    except ValueError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()