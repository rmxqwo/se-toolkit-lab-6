# Task 1: Call an LLM from Code - Implementation Plan

## LLM Provider Choice
**Provider:** OpenRouter.ai
**Model:** meta-llama/llama-4-scout:free
**Reasoning:** 
- Free tier available
- Supports tool calling (needed for Tasks 2-3)
- Reliable performance
- 50 requests/day limit - sufficient for development

## Architecture

### Project Structure


### Components

1. **Environment Configuration**
   - Use `python-dotenv` to load `.env.agent.secret`
   - Variables: `LLM_API_KEY`, `LLM_API_BASE`, `LLM_MODEL`

2. **Agent Class**
   - `__init__`: Load config, setup OpenAI-compatible client
   - `call_llm(question)`: Make API request to OpenRouter
   - `run()`: Main execution flow

3. **CLI Interface**
   - Parse command line argument
   - Handle errors gracefully
   - Output JSON to stdout, debug to stderr

### Implementation Steps

1. Set up environment file structure
2. Implement agent with OpenAI client
3. Add error handling and timeout (60s)
4. Create regression test
5. Write documentation

### Error Handling
- Network errors → exit code 1, error message to stderr
- API errors → exit code 1, error message to stderr
- Timeout (>60s) → exit code 1
- Missing API key → exit code 1