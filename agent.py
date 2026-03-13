#!/usr/bin/env python3
"""
Agent CLI for calling LLM with questions.
Usage: uv run agent.py "Your question here"
"""

import os
import sys
import json
import time
from dotenv import load_dotenv
from openai import OpenAI
import argparse
from typing import Dict, Any

# Load environment variables from .env.agent.secret
load_dotenv('.env.agent.secret')


class Agent:
    """Simple agent that calls LLM and returns structured response."""
    
    def __init__(self):
        """Initialize agent with configuration from environment."""
        self.api_key = os.getenv('LLM_API_KEY')
        self.api_base = os.getenv('LLM_API_BASE', 'https://openrouter.ai/api/v1')
        self.model = os.getenv('LLM_MODEL', 'meta-llama/llama-4-scout:free')
        
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
        
        # System prompt (minimal for now)
        self.system_prompt = "You are a helpful assistant that answers questions concisely and accurately."
    
    def call_llm(self, question: str) -> Dict[str, Any]:
        """
        Call LLM with question and return structured response.
        """
        try:
            # Make API call
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": question}
                ],
                temperature=0.7,
                max_tokens=500,
                timeout=55
            )
            
            # Extract answer
            answer = response.choices[0].message.content
            
            return {
                "answer": answer.strip() if answer else "",
                "tool_calls": []
            }
            
        except Exception as e:
            print(f"Error calling LLM: {str(e)}", file=sys.stderr)
            raise
    
    def run(self, question: str) -> None:
        """Main execution flow."""
        start_time = time.time()
        
        try:
            print(f"Processing question: {question}", file=sys.stderr)
            print(f"Using model: {self.model}", file=sys.stderr)
            
            result = self.call_llm(question)
            
            elapsed = time.time() - start_time
            if elapsed > 60:
                raise TimeoutError(f"Execution time {elapsed:.2f}s exceeded 60s limit")
            
            print(json.dumps(result, ensure_ascii=False))
            
        except TimeoutError as e:
            print(f"Timeout error: {e}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Call LLM with a question")
    parser.add_argument('question', help='Question to ask the LLM')
    args = parser.parse_args()
    
    try:
        agent = Agent()
        agent.run(args.question)
    except ValueError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()