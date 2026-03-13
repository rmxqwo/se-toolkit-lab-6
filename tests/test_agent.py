#!/usr/bin/env python3
"""
Tests for the Documentation Agent (Task 2)
"""

import os
import sys
import json
from pathlib import Path

# Добавляем путь к проекту
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Импортируем агента
from agent import DocumentationAgent


def test_merge_conflict_question():
    """Test that agent uses read_file to answer about merge conflicts."""
    agent = DocumentationAgent()
    result = agent.process_question("How do you resolve a merge conflict?")
    
    # Проверяем структуру ответа
    assert "answer" in result, "Answer field missing"
    assert "source" in result, "Source field missing"
    assert "tool_calls" in result, "Tool_calls field missing"
    
    # Проверяем, что использовался read_file
    read_file_calls = [call for call in result["tool_calls"] 
                      if call["tool"] == "read_file"]
    assert len(read_file_calls) > 0, "Agent should use read_file tool"
    
    # Проверяем, что source указывает на git-workflow.md
    assert "git-workflow.md" in result["source"].lower(), "Source should reference git-workflow.md"


def test_list_files_question():
    """Test that agent uses list_files to discover wiki contents."""
    agent = DocumentationAgent()
    result = agent.process_question("What files are in the wiki?")
    
    # Проверяем структуру ответа
    assert "answer" in result, "Answer field missing"
    assert "source" in result, "Source field missing"
    assert "tool_calls" in result, "Tool_calls field missing"
    
    # Проверяем, что использовался list_files
    list_files_calls = [call for call in result["tool_calls"] 
                       if call["tool"] == "list_files"]
    assert len(list_files_calls) > 0, "Agent should use list_files tool"
    
    # Проверяем, что листали wiki директорию
    wiki_calls = [call for call in list_files_calls 
                 if call["args"].get("path") == "wiki"]
    assert len(wiki_calls) > 0, "Agent should list wiki directory"


def test_security_directory_traversal():
    """Test that directory traversal is prevented."""
    agent = DocumentationAgent()
    
    # Попытка прочитать файл вне проекта
    result = agent.read_file("../../../etc/passwd")
    assert "Access denied" in result or "Error" in result, "Should block directory traversal"
    
    # Попытка через wiki
    result = agent.read_file("wiki/../.env.agent.secret")
    assert "Access denied" in result or "Error" in result, "Should block encoded traversal"


def test_max_tool_calls():
    """Test that agent respects max tool calls limit."""
    agent = DocumentationAgent()
    agent.max_tool_calls = 2
    
    # Вопрос, который требует много инструментов
    result = agent.process_question("Tell me about everything in the wiki")
    
    # Проверяем, что не превысили лимит
    assert len(result["tool_calls"]) <= 2, f"Too many tool calls: {len(result['tool_calls'])}"


if __name__ == "__main__":
    # Для ручного тестирования
    print("Running tests...")
    
    test_merge_conflict_question()
    print("✅ test_merge_conflict_question passed")
    
    test_list_files_question()
    print("✅ test_list_files_question passed")
    
    test_security_directory_traversal()
    print("✅ test_security_directory_traversal passed")
    
    test_max_tool_calls()
    print("✅ test_max_tool_calls passed")
    
    print("\n🎉 All tests passed!")