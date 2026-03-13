# Task 3: The System Agent - Implementation Plan

## Overview

Добавление нового инструмента `query_api` для взаимодействия с deployed backend. Агент должен уметь отвечать на вопросы о системе (framework, порты, статус коды) и данные из базы (количество предметов, скоринг).

## Текущее состояние (Task 2)

- ✅ Инструменты: `read_file`, `list_files`
- ✅ Agentic loop с максимум 10 вызовами
- ✅ Безопасность от directory traversal
- ✅ Выходной JSON с answer, source, tool_calls

## Новый инструмент: `query_api`

### Схема function calling

```json
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
          "description": "HTTP method"
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
