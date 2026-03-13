#!/usr/bin/env python3
import subprocess
import json
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_agent_basic_question():
    result = subprocess.run(
        ["uv", "run", "agent.py", "What is the capital of France?"],
        capture_output=True,
        text=True,
        cwd=project_root
    )
    
    assert result.returncode == 0, f"Agent failed: {result.stderr}"
    
    try:
        output = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        assert False, f"Invalid JSON: {result.stdout}"
    
    assert "answer" in output
    assert "tool_calls" in output
    assert isinstance(output["tool_calls"], list)
    assert "Paris" in output["answer"]
    
    print("✅ Test passed!")

if __name__ == "__main__":
    test_agent_basic_question()