#!/usr/bin/env python3
"""
Tests for the System Agent (Task 3)
"""

import os
import sys
import json
import pytest
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from agent import SystemAgent


class TestSystemAgent:
    """Test suite for System Agent."""
    
    def test_merge_conflict_question(self):
        """Test wiki question (from Task 2)."""
        agent = SystemAgent()
        result = agent.process_question("How do you resolve a merge conflict?")
        
        assert "answer" in result
        assert "source" in result
        assert "tool_calls" in result
        
        read_file_calls = [c for c in result["tool_calls"] if c["tool"] == "read_file"]
        assert len(read_file_calls) > 0
        assert "git-workflow.md" in result["source"].lower()
    
    def test_list_files_question(self):
        """Test listing files question (from Task 2)."""
        agent = SystemAgent()
        result = agent.process_question("What files are in the wiki?")
        
        assert "answer" in result
        assert "tool_calls" in result
        
        list_files_calls = [c for c in result["tool_calls"] if c["tool"] == "list_files"]
        assert len(list_files_calls) > 0
    
    def test_framework_question(self):
        """Test system fact question - should use read_file on backend code."""
        agent = SystemAgent()
        result = agent.process_question("What Python web framework does this project use?")
        
        assert "answer" in result
        assert "tool_calls" in result
        
        # Should read backend files
        read_calls = [c for c in result["tool_calls"] if c["tool"] == "read_file"]
        assert len(read_calls) > 0
        
        # Should look at Python files
        py_files = [c for c in read_calls if "backend/" in c["args"].get("path", "")]
        assert len(py_files) > 0 or "framework" in result["answer"].lower()
    
    def test_items_count_question(self):
        """Test data question - should use query_api."""
        agent = SystemAgent()
        result = agent.process_question("How many items are in the database?")
        
        assert "answer" in result
        assert "tool_calls" in result
        
        # Should use query_api
        api_calls = [c for c in result["tool_calls"] if c["tool"] == "query_api"]
        assert len(api_calls) > 0, "Should use query_api for data question"
        
        # Should query items endpoint
        items_calls = [c for c in api_calls if "items" in c["args"].get("path", "")]
        assert len(items_calls) > 0, "Should query /items/ endpoint"
    
    def test_query_api_method(self):
        """Test query_api implementation."""
        agent = SystemAgent()
        
        # Test with invalid URL (should handle gracefully)
        agent.api_base_url = "http://nonexistent.local"
        result = agent.query_api("GET", "/items/")
        result_dict = json.loads(result)
        
        assert "status_code" in result_dict
        assert result_dict["status_code"] in [503, 500]  # Connection error or timeout
    
    def test_security_directory_traversal(self):
        """Test directory traversal prevention."""
        agent = SystemAgent()
        
        result = agent.read_file("../../../etc/passwd")
        assert "Access denied" in result
        
        result = agent.read_file("wiki/../.env.agent.secret")
        assert "Access denied" in result
    
    def test_max_tool_calls(self):
        """Test max tool calls limit."""
        agent = SystemAgent()
        agent.max_tool_calls = 2
        result = agent.process_question("Tell me about everything in the system")
        assert len(result["tool_calls"]) <= 2


@pytest.mark.skipif(not os.getenv('LMS_API_KEY'), reason="No LMS API key")
class TestLiveAPI:
    """Tests that require live backend API."""
    
    def test_query_api_live(self):
        """Test query_api against real backend."""
        agent = SystemAgent()
        result = agent.query_api("GET", "/health")
        result_dict = json.loads(result)
        
        assert result_dict["status_code"] == 200
        assert "body" in result_dict


if __name__ == "__main__":
    pytest.main([__file__, "-v"])