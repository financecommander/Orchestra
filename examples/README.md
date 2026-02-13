# Orchestra DSL Examples

This directory contains example scripts demonstrating how to use Orchestra DSL.

## test_agents.py

Tests that both Anthropic and OpenAI providers are working correctly.

### Prerequisites

1. Install Orchestra DSL dependencies:
   ```bash
   pip install -r ../requirements.txt
   ```

2. Set up API keys as environment variables:
   ```bash
   export ANTHROPIC_API_KEY="your_anthropic_key_here"
   export OPENAI_API_KEY="your_openai_key_here"
   ```

   Alternatively, create a `.env` file in the project root:
   ```bash
   ANTHROPIC_API_KEY=your_anthropic_key_here
   OPENAI_API_KEY=your_openai_key_here
   ```

### Usage

Run the test script:
```bash
python examples/test_agents.py
```

The script will:
- Test the Claude/Anthropic provider if `ANTHROPIC_API_KEY` is set
- Test the OpenAI provider if `OPENAI_API_KEY` is set
- Skip any provider whose API key is not configured
- Exit with an error if no API keys are configured

### Expected Output

```
Testing Claude...
✅ Claude: Orchestra DSL is a domain-specific language for coordinating multiple AI agents...

Testing OpenAI...
✅ OpenAI: Orchestra DSL is a framework for orchestrating AI agent workflows...

🎉 All configured agents working!
```

## plaid_integration_workflow.py

A multi-agent workflow demonstrating fintech feature development with Orchestra DSL. Uses Claude for architecture design and OpenAI for code generation to build a Plaid bank verification integration with BSA/AML compliance.

### Usage

```bash
python examples/plaid_integration_workflow.py
```

This example requires both `ANTHROPIC_API_KEY` and `OPENAI_API_KEY` to be set.

### What It Demonstrates

- Multi-agent orchestration (Claude + OpenAI)
- Task dependencies (implementation depends on design)
- Workflow execution with sequential stages
- Fintech compliance considerations (BSA/AML)

---

## Troubleshooting

**Issue**: `ModuleNotFoundError: No module named 'orchestra'`
- **Solution**: Make sure you've installed the requirements and are running from the project root, or install Orchestra DSL in development mode:
  ```bash
  pip install -e .
  ```

**Issue**: API key errors
- **Solution**: Verify your API keys are set correctly:
  ```bash
  echo $ANTHROPIC_API_KEY
  echo $OPENAI_API_KEY
  ```
