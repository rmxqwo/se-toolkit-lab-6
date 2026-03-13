# Task 2: The Documentation Agent - Implementation Plan

## Overview

Создание агента с инструментами для навигации по wiki проекта. Агент сможет читать файлы и листать директории.

## Tool Schemas

### read_file

- **Parameters**: `path` (string) - относительный путь от корня проекта
- **Returns**: содержимое файла или сообщение об ошибке
- **Security**: проверка на directory traversal attacks

### list_files

- **Parameters**: `path` (string) - относительный путь к директории
- **Returns**: список файлов и директорий (newline-separated)
- **Security**: проверка на выход за пределы проекта

## Agentic Loop Implementation

1. Отправляем вопрос пользователя + определения инструментов в LLM
2. Проверяем ответ:
   - Если есть `tool_calls` → выполняем каждый инструмент, добавляем результаты как сообщения с ролью `tool`, переходим к шагу 1
   - Если текстовый ответ (нет tool_calls) → это финальный ответ, парсим JSON
3. Счетчик вызовов инструментов (максимум 10)
4. Извлечение source из ответа LLM

## System Prompt Strategy

Инструктируем LLM:

1. Сначала использовать `list_files` для изучения структуры wiki
2. Затем `read_file` для поиска ответа в конкретных файлах
3. Включать source reference в формате `file.md#section`
4. Отвечать в JSON формате с полями `answer` и `source`

## Security Measures

- Использование `os.path.abspath` и `os.path.realpath`
- Проверка, что запрашиваемый путь начинается с корня проекта
- Запрет на `../` и симлинки вне проекта

## Testing Strategy

Добавить 2 теста:

1. "How do you resolve a merge conflict?" → проверка использования read_file
2. "What files are in the wiki?" → проверка использования list_files
