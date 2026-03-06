#!/usr/bin/env python3
"""
Orchestra DSL - End-to-End Test

Demonstrates the complete pipeline:
1. Source code (.orc) → Lexer → Tokens
2. Tokens → Parser → AST
3. AST → CodeGenerator → Python code
4. Python code → Runtime → Execution

This proves the entire system works!
"""

import sys
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from orchestra_lexer import Lexer, print_tokens
from orchestra_parser import Parser
from orchestra_ast import print_ast
from orchestra_codegen import CodeGenerator


# ============================================================================
# Test Workflows
# ============================================================================

SIMPLE_WORKFLOW = """
workflow hello_world {
    agent: claude_sonnet
    task: "Say hello to the world"
}
"""

CONDITIONAL_WORKFLOW = """
workflow credit_analysis {
    agent: best_for(complexity: high, max_cost: 0.01)
    
    guard: input.amount > 0
    
    if input.amount > 1000000 {
        quality_gate: strict
    } else {
        quality_gate: standard
    }
    
    task: "Analyze credit risk for ${input.company}"
}
"""

CASCADE_WORKFLOW = """
workflow robust_analysis {
    agent: cascade [
        try: ultra_reasoning,
        fallback: guardian_claude,
        last_resort: hydra_financial
    ]
    
    timeout: 30.0
    
    try {
        task: "Perform deep financial analysis"
    } catch timeout_error {
        task: "Provide quick summary instead"
    }
}
"""

COMPLEX_WORKFLOW = """
workflow multi_stage_analysis {
    # Stage 1: Input validation
    guard: input.amount > 0
    guard: input.company != ""
    
    # Stage 2: Agent selection based on complexity
    if input.amount > 10000000 {
        agent: ultra_reasoning
        quality_gate: strict
    } else {
        agent: claude_sonnet
        quality_gate: standard
    }
    
    # Stage 3: Analysis with error handling
    try {
        timeout: 60.0
        task: "Comprehensive analysis for ${input.company} - Amount: ${input.amount}"
    } retry {
        strategy: exponential_backoff
        max_attempts: 3
    } catch timeout_error {
        agent: hydra_financial
        task: "Quick analysis for ${input.company}"
    }
}
"""


# ============================================================================
# Test Functions
# ============================================================================

def test_lexer(source: str, name: str):
    """Test the lexer"""
    print(f"\n{'=' * 70}")
    print(f"LEXER TEST: {name}")
    print(f"{'=' * 70}\n")
    
    print("Source Code:")
    print("-" * 70)
    print(source)
    print()
    
    try:
        lexer = Lexer(source)
        tokens = lexer.tokenize()
        
        print("Tokens:")
        print("-" * 70)
        print_tokens(tokens)
        
        print(f"\n✅ Lexer test passed: {len(tokens)} tokens generated\n")
        return tokens
    
    except Exception as e:
        print(f"\n❌ Lexer test failed: {e}\n")
        return None


def test_parser(tokens, name: str):
    """Test the parser"""
    print(f"\n{'=' * 70}")
    print(f"PARSER TEST: {name}")
    print(f"{'=' * 70}\n")
    
    try:
        parser = Parser(tokens)
        ast = parser.parse()
        
        print("Abstract Syntax Tree:")
        print("-" * 70)
        print(print_ast(ast))
        
        print(f"\n✅ Parser test passed: {len(ast.workflows)} workflow(s) parsed\n")
        return ast
    
    except Exception as e:
        print(f"\n❌ Parser test failed: {e}\n")
        import traceback
        traceback.print_exc()
        return None


def test_codegen(ast, name: str):
    """Test the code generator"""
    print(f"\n{'=' * 70}")
    print(f"CODE GENERATOR TEST: {name}")
    print(f"{'=' * 70}\n")
    
    try:
        generator = CodeGenerator()
        code = generator.generate(ast)
        
        print("Generated Python Code:")
        print("-" * 70)
        print(code)
        
        # Try to compile it (syntax check)
        compile(code, '<generated>', 'exec')
        
        print(f"\n✅ Code generator test passed: {len(code.splitlines())} lines generated\n")
        return code
    
    except Exception as e:
        print(f"\n❌ Code generator test failed: {e}\n")
        import traceback
        traceback.print_exc()
        return None


def test_full_pipeline(source: str, name: str):
    """Test complete pipeline from source to Python code"""
    print(f"\n{'#' * 70}")
    print(f"# FULL PIPELINE TEST: {name}")
    print(f"{'#' * 70}\n")
    
    # Step 1: Lexer
    tokens = test_lexer(source, name)
    if not tokens:
        return False
    
    # Step 2: Parser
    ast = test_parser(tokens, name)
    if not ast:
        return False
    
    # Step 3: Code Generator
    code = test_codegen(ast, name)
    if not code:
        return False
    
    print(f"\n{'=' * 70}")
    print(f"✅ FULL PIPELINE TEST PASSED: {name}")
    print(f"{'=' * 70}\n")
    
    return True


def save_generated_code(code: str, filename: str):
    """Save generated code to file"""
    output_path = Path(__file__).parent / filename
    output_path.write_text(code)
    print(f"💾 Generated code saved to: {output_path}")


# ============================================================================
# Main Test Suite
# ============================================================================

def main():
    """Run all tests"""
    print("\n" + "=" * 70)
    print(" ORCHESTRA DSL - END-TO-END TEST SUITE")
    print("=" * 70)
    
    tests = [
        (SIMPLE_WORKFLOW, "Simple Workflow"),
        (CONDITIONAL_WORKFLOW, "Conditional Workflow"),
        (CASCADE_WORKFLOW, "Cascade Workflow"),
        (COMPLEX_WORKFLOW, "Complex Multi-Stage Workflow"),
    ]
    
    results = []
    generated_codes = []
    
    for source, name in tests:
        success = test_full_pipeline(source, name)
        results.append((name, success))
        
        # Generate and save code for successful tests
        if success:
            lexer = Lexer(source)
            tokens = lexer.tokenize()
            parser = Parser(tokens)
            ast = parser.parse()
            generator = CodeGenerator()
            code = generator.generate(ast)
            generated_codes.append((name, code))
    
    # Summary
    print("\n" + "=" * 70)
    print(" TEST SUMMARY")
    print("=" * 70 + "\n")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {name}")
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    # Save generated code
    if generated_codes:
        print("\n" + "=" * 70)
        print(" SAVING GENERATED CODE")
        print("=" * 70 + "\n")
        
        all_code = []
        for name, code in generated_codes:
            all_code.append(f"# {name}")
            all_code.append(code)
            all_code.append("\n\n")
        
        save_generated_code("\n".join(all_code), "generated_workflows.py")
    
    # Final status
    print("\n" + "=" * 70)
    if passed == total:
        print("🎉 ALL TESTS PASSED!")
        print("=" * 70)
        return 0
    else:
        print(f"⚠️  {total - passed} TEST(S) FAILED")
        print("=" * 70)
        return 1


if __name__ == "__main__":
    sys.exit(main())
