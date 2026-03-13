#!/usr/bin/env python3
"""
Documentation Agent CLI with tools for reading files and listing directories.
Usage: uv run agent.py "Your question here"
"""

import os
import sys
import json
import time
from dotenv import load_dotenv
from openai import OpenAI
import argparse
from typing import Dict, Any, List, Optional

# Load environment variables from .env.agent.secret
load_dotenv('.env.agent.secret')


class DocumentationAgent:
    """Agent that can read files and list directories to answer questions about documentation."""
    
    def __init__(self):
        """Initialize agent with configuration from environment."""
        self.api_key = os.getenv('LLM_API_KEY')
        self.api_base = os.getenv('LLM_API_BASE', 'https://openrouter.ai/api/v1')
        self.model = os.getenv('LLM_MODEL', 'meta-llama/llama-4-scout:free')
        self.project_root = os.path.abspath('.')  # Current directory as project root
        self.tool_calls_log: List[Dict[str, Any]] = []
        self.max_tool_calls = 10
        
        # Validate required configuration
        if not self.api_key:
            raise ValueError("LLM_API_KEY not found in environment. Please set it in .env.agent.secret")
        
        # Initialize OpenAI-compatible client
        self.client = OpenAI(
            base_url=self.api_base,
            api_key=self.api_key,
            default_headers={
                "HTTP-Referer": "http://localhost:42002",
                "X-Title": "SE Toolkit Lab Agent"
            }
        )
        
        # Define available tools for function calling
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "read_file",
                    "description": "Read a file from the project repository. Use this to read documentation files.",
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
                    "description": "List files and directories at a given path. Use this to explore the wiki structure.",
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
        
        self.system_prompt = """You are a documentation assistant with access to a project wiki.
You have two tools to help you find information:

1. list_files(path): List contents of a directory to explore the wiki structure
2. read_file(path): Read contents of a file to find specific information

IMPORTANT: Your final response MUST be in valid JSON format with two fields:
- "answer": your answer to the user's question
- "source": the wiki section where you found the information (e.g., "wiki/git-workflow.md#resolving-merge-conflicts")

Strategy to follow:
1. First, use list_files("wiki") to see what documentation files are available
2. Then, read relevant files with read_file("wiki/filename.md")
3. Find the answer and identify the specific section (look for markdown headings)
4. Respond with JSON containing the answer and source reference

Example response format:
{"answer": "To resolve a merge conflict, edit the conflicting file...", "source": "wiki/git-workflow.md#resolving-merge-conflicts"}

Always include the source reference where you found the information.
If you can't find the answer, respond with {"answer": "I couldn't find information about this in the wiki.", "source": "unknown"}"""

    def read_file(self, path: str) -> str:
        """
        Read a file safely, preventing directory traversal.
        
        Args:
            path: Relative path from project root
            
        Returns:
            File contents or error message
        """
        try:
            # Security: prevent directory traversal
            full_path = os.path.abspath(os.path.join(self.project_root, path))
            
            # Check if path is within project root
            if not full_path.startswith(self.project_root):
                return f"Error: Access denied - path '{path}' is outside project directory"
            
            # Check if file exists and is a file
            if not os.path.exists(full_path):
                return f"Error: File '{path}' does not exist"
            if not os.path.isfile(full_path):
                return f"Error: '{path}' is not a file"
            
            # Read file
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
                return content
                
        except Exception as e:
            return f"Error reading file '{path}': {str(e)}"

    def list_files(self, path: str) -> str:
        """
        List files and directories safely, preventing directory traversal.
        
        Args:
            path: Relative directory path from project root
            
        Returns:
            Newline-separated list of entries or error message
        """
        try:
            # Security: prevent directory traversal
            full_path = os.path.abspath(os.path.join(self.project_root, path))
            
            # Check if path is within project root
            if not full_path.startswith(self.project_root):
                return f"Error: Access denied - path '{path}' is outside project directory"
            
            # Check if directory exists
            if not os.path.exists(full_path):
                return f"Error: Path '{path}' does not exist"
            if not os.path.isdir(full_path):
                return f"Error: '{path}' is not a directory"
            
            # List contents
            entries = os.listdir(full_path)
            return "\n".join(sorted(entries))
            
        except Exception as e:
            return f"Error listing directory '{path}': {str(e)}"

    def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """
        Execute a tool and return its result.
        
        Args:
            tool_name: Name of the tool to execute
            arguments: Tool arguments
            
        Returns:
            Tool execution result
        """
        if tool_name == "read_file":
            return self.read_file(arguments.get("path", ""))
        elif tool_name == "list_files":
            return self.list_files(arguments.get("path", ""))
        else:
            return f"Error: Unknown tool '{tool_name}'"

    def extract_json_from_response(self, text: str) -> Optional[Dict[str, str]]:
        """
        Extract JSON from LLM response text.
        
        Args:
            text: Response text that might contain JSON
            
        Returns:
            Parsed JSON or None if not found
        """
        try:
            # Try to find JSON in the response
            # Look for content between curly braces
            start_idx = text.find('{')
            end_idx = text.rfind('}')
            
            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                json_str = text[start_idx:end_idx + 1]
                return json.loads(json_str)
        except:
            pass
        return None

    def process_question(self, question: str) -> Dict[str, Any]:
        """
        Main agentic loop to process a question.
        
        Args:
            question: User's question
            
        Returns:
            Dictionary with answer, source, and tool_calls
        """
        self.tool_calls_log = []
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": question}
        ]
        
        tool_call_count = 0
        
        while tool_call_count < self.max_tool_calls:
            try:
                # Get response from LLM
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=self.tools,
                    tool_choice="auto",
                    temperature=0.7,
                    max_tokens=1000
                )
                
                message = response.choices[0].message
                
                # Check for tool calls
                if message.tool_calls:
                    # Process each tool call
                    for tool_call in message.tool_calls:
                        tool_call_count += 1
                        if tool_call_count > self.max_tool_calls:
                            break
                        
                        function_name = tool_call.function.name
                        try:
                            arguments = json.loads(tool_call.function.arguments)
                        except:
                            arguments = {}
                        
                        # Execute tool
                        result = self.execute_tool(function_name, arguments)
                        
                        # Log the tool call
                        self.tool_calls_log.append({
                            "tool": function_name,
                            "args": arguments,
                            "result": result
                        })
                        
                        # Add tool response to messages
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": result
                        })
                    
                    continue  # Go back to LLM with tool results
                
                # If no tool calls, try to extract JSON from response
                if message.content:
                    # Try to parse JSON from the response
                    parsed_json = self.extract_json_from_response(message.content)
                    
                    if parsed_json and "answer" in parsed_json:
                        return {
                            "answer": parsed_json["answer"],
                            "source": parsed_json.get("source", "unknown"),
                            "tool_calls": self.tool_calls_log
                        }
                    elif parsed_json:
                        # Has JSON but missing required fields
                        return {
                            "answer": str(parsed_json),
                            "source": "unknown",
                            "tool_calls": self.tool_calls_log
                        }
                    else:
                        # No JSON found, use text as answer
                        return {
                            "answer": message.content.strip(),
                            "source": "unknown",
                            "tool_calls": self.tool_calls_log
                        }
                
            except Exception as e:
                print(f"Error in agentic loop: {str(e)}", file=sys.stderr)
                # Return whatever we have
                return {
                    "answer": f"Error processing question: {str(e)}",
                    "source": "unknown",
                    "tool_calls": self.tool_calls_log
                }
        
        # If we hit max tool calls
        return {
            "answer": "I've reached the maximum number of tool calls. Here's what I found so far.",
            "source": "unknown",
            "tool_calls": self.tool_calls_log
        }
    
    def run(self, question: str) -> None:
        """Main execution flow."""
        start_time = time.time()
        
        try:
            print(f"Processing question: {question}", file=sys.stderr)
            print(f"Using model: {self.model}", file=sys.stderr)
            
            result = self.process_question(question)
            
            elapsed = time.time() - start_time
            if elapsed > 60:
                raise TimeoutError(f"Execution time {elapsed:.2f}s exceeded 60s limit")
            
            # Output JSON
            print(json.dumps(result, ensure_ascii=False, indent=2))
            
        except TimeoutError as e:
            print(f"Timeout error: {e}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Documentation Agent - answers questions using wiki files")
    parser.add_argument('question', help='Question to ask about the documentation')
    args = parser.parse_args()
    
    try:
        agent = DocumentationAgent()
        agent.run(args.question)
    except ValueError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()