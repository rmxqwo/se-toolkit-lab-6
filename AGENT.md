# Documentation Agent CLI

## Overview

The Documentation Agent is an AI assistant that can navigate and read documentation files to answer questions. Unlike a simple chatbot, it has **tools** that allow it to interact with the file system.

## Setup

1. Get API key from [OpenRouter.ai](https://openrouter.ai)
2. Copy `.env.agent.example` to `.env.agent.secret`
3. Add your key to `.env.agent.secret`

## Usage

```bash
uv run agent.py "How do you resolve a merge conflict?"
