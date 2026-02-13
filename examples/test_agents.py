"""
Test that all AI agents work correctly
"""

import os
from orchestra.providers.agents.anthropic import AnthropicProvider
from orchestra.providers.agents.openai import OpenAIProvider

def test_claude():
    """Test Claude/Anthropic provider"""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("⚠️  Skipping Claude test: ANTHROPIC_API_KEY not set")
        return False

    print("Testing Claude...")
    claude = AnthropicProvider(api_key=api_key)
    result = claude.execute(
        prompt="Explain Orchestra DSL in one sentence",
        model="claude-sonnet-4-5"
    )
    print(f"✅ Claude: {result}\n")
    return True

def test_openai():
    """Test OpenAI provider"""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("⚠️  Skipping OpenAI test: OPENAI_API_KEY not set")
        return False

    print("Testing OpenAI...")
    openai = OpenAIProvider(api_key=api_key)
    result = openai.execute(
        prompt="Explain Orchestra DSL in one sentence",
        model="gpt-4-turbo"
    )
    print(f"✅ OpenAI: {result}\n")
    return True

if __name__ == "__main__":
    claude_ok = test_claude()
    openai_ok = test_openai()

    if claude_ok or openai_ok:
        print("🎉 All configured agents working!")
    else:
        print("❌ No API keys configured. Set ANTHROPIC_API_KEY and/or OPENAI_API_KEY")
        exit(1)
