# Orchestra DSL - Technical Architecture Specification

**Version:** 2.0  
**Status:** Design Complete, Implementation In Progress  
**Author:** Calculus Holdings LLC  
**Date:** March 2026

---

## 1. System Overview

### 1.1 Purpose

Orchestra is a declarative domain-specific language (DSL) for multi-agent AI orchestration. It enables developers to define complex AI workflows using simple, readable syntax that compiles to efficient Python code.

### 1.2 Design Goals

1. **Declarative Syntax** - Express intent, not implementation
2. **Cost Optimization** - Automatic routing to cheapest capable agent
3. **Reliability** - Built-in error handling and retry logic
4. **Composability** - Workflows as reusable building blocks
5. **Type Safety** - Catch errors at compile time
6. **Performance** - Compile to efficient Python bytecode

### 1.3 Architecture Layers

```
┌─────────────────────────────────────┐
│     .orc Source Files               │ ← User writes workflows
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│     Lexer (Tokenization)            │ ← Convert text to tokens
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│     Parser (Syntax Analysis)        │ ← Build Abstract Syntax Tree
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│     Semantic Analyzer               │ ← Type checking, validation
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│     Compiler (Code Generation)      │ ← Generate Python code
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│     Runtime (Execution Engine)      │ ← Execute workflows
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│     Swarm (Agent Coordination)      │ ← AI Portal integration
└─────────────────────────────────────┘
```

---

## 2. Component Specifications

### 2.1 Lexer (Tokenizer)

**Purpose:** Convert .orc source text into stream of tokens

**Input:** Raw .orc file text
**Output:** List of Token objects

**Token Types:**
```python
class TokenType(Enum):
    # Keywords
    WORKFLOW = "workflow"
    AGENT = "agent"
    TASK = "task"
    IF = "if"
    ELSE = "else"
    MATCH = "match"
    CASE = "case"
    TRY = "try"
    RETRY = "retry"
    CATCH = "catch"
    GUARD = "guard"
    QUALITY_GATE = "quality_gate"
    TIMEOUT = "timeout"
    
    # Routing strategies
    BEST_FOR = "best_for"
    CASCADE = "cascade"
    ROUND_ROBIN = "round_robin"
    LOAD_BALANCE = "load_balance"
    CHEAPEST_ABOVE = "cheapest_above"
    DYNAMIC_SELECT = "dynamic_select"
    
    # Literals
    IDENTIFIER = "identifier"
    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    
    # Operators
    COLON = ":"
    COMMA = ","
    DOT = "."
    ARROW = "->"
    EQUALS = "="
    GT = ">"
    LT = "<"
    GTE = ">="
    LTE = "<="
    EQ = "=="
    NEQ = "!="
    
    # Delimiters
    LBRACE = "{"
    RBRACE = "}"
    LPAREN = "("
    RPAREN = ")"
    LBRACKET = "["
    RBRACKET = "]"
    
    # Special
    NEWLINE = "newline"
    EOF = "eof"
    COMMENT = "comment"
```

**Implementation:**
```python
class Token:
    def __init__(self, type: TokenType, value: Any, line: int, column: int):
        self.type = type
        self.value = value
        self.line = line
        self.column = column

class Lexer:
    def __init__(self, source: str):
        self.source = source
        self.position = 0
        self.line = 1
        self.column = 1
        self.tokens: List[Token] = []
    
    def tokenize(self) -> List[Token]:
        """Convert source text to token stream"""
        pass
    
    def next_token(self) -> Token:
        """Read next token from source"""
        pass
    
    def peek(self, offset: int = 0) -> str:
        """Look ahead in source without consuming"""
        pass
```

**Error Handling:**
- Illegal character detection
- Unclosed string literals
- Invalid number formats
- Line/column tracking for error messages

---

### 2.2 Parser (Syntax Analysis)

**Purpose:** Convert token stream into Abstract Syntax Tree (AST)

**Input:** List of Token objects
**Output:** AST root node

**Grammar (EBNF):**
```ebnf
program         ::= workflow+

workflow        ::= "workflow" IDENTIFIER "{" statement* "}"

statement       ::= agent_stmt
                  | task_stmt
                  | guard_stmt
                  | quality_gate_stmt
                  | timeout_stmt
                  | conditional_stmt
                  | try_stmt
                  | assignment_stmt

agent_stmt      ::= "agent" ":" agent_spec

agent_spec      ::= IDENTIFIER                          # Simple agent
                  | routing_strategy                     # Advanced routing

routing_strategy ::= "best_for" "(" criteria_list ")"
                   | "cascade" "[" agent_list "]"
                   | "round_robin" "[" agent_list "]"
                   | "load_balance" "[" agent_list "]"
                   | "cheapest_above" "(" quality "," agent_list ")"
                   | "dynamic_select" "(" selector_func ")"

criteria_list   ::= criterion ("," criterion)*
criterion       ::= IDENTIFIER ":" value

agent_list      ::= agent_ref ("," agent_ref)*
agent_ref       ::= "try" ":" IDENTIFIER
                  | "fallback" ":" IDENTIFIER
                  | "last_resort" ":" IDENTIFIER
                  | IDENTIFIER

task_stmt       ::= "task" ":" STRING

guard_stmt      ::= "guard" ":" expression

quality_gate_stmt ::= "quality_gate" ":" IDENTIFIER

timeout_stmt    ::= "timeout" ":" NUMBER

conditional_stmt ::= if_stmt ("else" if_stmt)* ("else" "{" statement* "}")?

if_stmt         ::= "if" expression "{" statement* "}"

try_stmt        ::= "try" "{" statement* "}"
                   ("retry" "{" retry_config "}")?
                   ("catch" IDENTIFIER "{" statement* "}")?

retry_config    ::= retry_option ("," retry_option)*
retry_option    ::= "strategy" ":" IDENTIFIER
                  | "max_attempts" ":" NUMBER
                  | "backoff_factor" ":" NUMBER

expression      ::= comparison
comparison      ::= term ((">" | "<" | ">=" | "<=" | "==" | "!=") term)*
term            ::= factor (("+" | "-") factor)*
factor          ::= primary (("*" | "/") primary)*
primary         ::= NUMBER
                  | STRING
                  | BOOLEAN
                  | IDENTIFIER ("." IDENTIFIER)*
                  | "(" expression ")"

assignment_stmt ::= IDENTIFIER "=" expression

value           ::= NUMBER | STRING | BOOLEAN | IDENTIFIER
```

**AST Node Classes:**
```python
from dataclasses import dataclass
from typing import List, Optional, Any

@dataclass
class ASTNode:
    """Base class for all AST nodes"""
    line: int
    column: int

@dataclass
class Workflow(ASTNode):
    name: str
    statements: List[ASTNode]

@dataclass
class AgentStatement(ASTNode):
    agent_spec: "AgentSpec"

@dataclass
class AgentSpec(ASTNode):
    pass  # Base class

@dataclass
class SimpleAgent(AgentSpec):
    name: str

@dataclass
class BestForRouting(AgentSpec):
    criteria: dict[str, Any]

@dataclass
class CascadeRouting(AgentSpec):
    agents: List[str]
    fallback_chain: bool = True

@dataclass
class TaskStatement(ASTNode):
    task: str

@dataclass
class GuardStatement(ASTNode):
    condition: "Expression"

@dataclass
class QualityGateStatement(ASTNode):
    level: str

@dataclass
class TimeoutStatement(ASTNode):
    seconds: float

@dataclass
class ConditionalStatement(ASTNode):
    condition: "Expression"
    then_branch: List[ASTNode]
    else_branch: Optional[List[ASTNode]] = None

@dataclass
class TryStatement(ASTNode):
    try_block: List[ASTNode]
    retry_config: Optional[dict] = None
    catch_blocks: Optional[List["CatchBlock"]] = None

@dataclass
class CatchBlock(ASTNode):
    error_type: str
    statements: List[ASTNode]

@dataclass
class Expression(ASTNode):
    pass  # Base class

@dataclass
class BinaryOp(Expression):
    left: Expression
    operator: str
    right: Expression

@dataclass
class Literal(Expression):
    value: Any

@dataclass
class Identifier(Expression):
    name: str
    attributes: List[str] = None

@dataclass
class Assignment(ASTNode):
    target: str
    value: Expression
```

**Parser Implementation:**
```python
class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.position = 0
        self.current_token = tokens[0] if tokens else None
    
    def parse(self) -> List[Workflow]:
        """Parse token stream into AST"""
        workflows = []
        while not self.at_end():
            workflows.append(self.parse_workflow())
        return workflows
    
    def parse_workflow(self) -> Workflow:
        """Parse a workflow definition"""
        pass
    
    def parse_statement(self) -> ASTNode:
        """Parse a single statement"""
        pass
    
    def parse_agent_spec(self) -> AgentSpec:
        """Parse agent specification"""
        pass
    
    def parse_expression(self) -> Expression:
        """Parse an expression"""
        pass
    
    def consume(self, token_type: TokenType) -> Token:
        """Consume expected token or raise error"""
        pass
    
    def match(self, *token_types: TokenType) -> bool:
        """Check if current token matches any type"""
        pass
    
    def advance(self) -> Token:
        """Move to next token"""
        pass
    
    def at_end(self) -> bool:
        """Check if at end of token stream"""
        pass
```

**Error Handling:**
- Syntax error detection with line/column
- Unexpected token reporting
- Missing closing braces/brackets
- Invalid expressions
- Helpful error messages

---

### 2.3 Semantic Analyzer

**Purpose:** Validate AST for semantic correctness

**Responsibilities:**
1. Type checking
2. Variable scope validation
3. Agent availability verification
4. Circular dependency detection
5. Resource constraint validation

**Implementation:**
```python
class SemanticAnalyzer:
    def __init__(self, swarm: "Swarm"):
        self.swarm = swarm
        self.symbol_table = {}
        self.errors = []
    
    def analyze(self, workflows: List[Workflow]) -> bool:
        """Validate workflows for semantic correctness"""
        for workflow in workflows:
            self.analyze_workflow(workflow)
        return len(self.errors) == 0
    
    def analyze_workflow(self, workflow: Workflow):
        """Validate a single workflow"""
        pass
    
    def check_types(self, expression: Expression) -> str:
        """Infer and validate expression types"""
        pass
    
    def validate_agent_exists(self, agent_name: str) -> bool:
        """Check if agent is available in swarm"""
        pass
    
    def validate_routing_criteria(self, criteria: dict) -> bool:
        """Validate routing criteria are valid"""
        pass
```

**Validation Rules:**

1. **Agent Validation:**
   - Agent must exist in swarm configuration
   - Routing criteria must be valid
   - Cost constraints must be positive

2. **Type Checking:**
   - Numeric operations on numbers only
   - String concatenation on strings only
   - Boolean operations on booleans only
   - Attribute access on objects with those attributes

3. **Scope Validation:**
   - Variables must be defined before use
   - No shadowing of reserved keywords
   - Input variables must be declared

4. **Resource Constraints:**
   - Timeout values must be positive
   - Max attempts must be positive integers
   - Budget constraints must be achievable

---

### 2.4 Compiler (Code Generation)

**Purpose:** Convert validated AST into executable Python code

**Input:** Validated AST
**Output:** Python code (as string or bytecode)

**Code Generation Strategy:**

**Template-based approach:**
```python
class CodeGenerator:
    def __init__(self):
        self.indent_level = 0
        self.generated_code = []
    
    def generate(self, workflows: List[Workflow]) -> str:
        """Generate Python code from AST"""
        self.emit_imports()
        for workflow in workflows:
            self.generate_workflow(workflow)
        return "\n".join(self.generated_code)
    
    def generate_workflow(self, workflow: Workflow):
        """Generate code for a workflow"""
        # Generate function definition
        self.emit(f"async def {workflow.name}(input, swarm):")
        self.indent()
        
        # Generate workflow body
        for stmt in workflow.statements:
            self.generate_statement(stmt)
        
        self.dedent()
    
    def generate_statement(self, stmt: ASTNode):
        """Generate code for a statement"""
        if isinstance(stmt, AgentStatement):
            self.generate_agent_statement(stmt)
        elif isinstance(stmt, TaskStatement):
            self.generate_task_statement(stmt)
        elif isinstance(stmt, ConditionalStatement):
            self.generate_conditional(stmt)
        # ... etc
    
    def generate_agent_statement(self, stmt: AgentStatement):
        """Generate agent selection code"""
        if isinstance(stmt.agent_spec, SimpleAgent):
            self.emit(f"agent = swarm.get_agent('{stmt.agent_spec.name}')")
        elif isinstance(stmt.agent_spec, BestForRouting):
            criteria = self.format_criteria(stmt.agent_spec.criteria)
            self.emit(f"router = AgentRouter(swarm)")
            self.emit(f"agent = router.best_for({criteria})")
        # ... etc
    
    def emit(self, code: str):
        """Emit a line of code with proper indentation"""
        indent = "    " * self.indent_level
        self.generated_code.append(f"{indent}{code}")
    
    def indent(self):
        self.indent_level += 1
    
    def dedent(self):
        self.indent_level -= 1
```

**Code Generation Examples:**

**Input Orchestra:**
```orchestra
workflow credit_analysis {
    agent: best_for(complexity: high, max_cost: 0.01)
    
    guard: input.amount > 0
    
    if input.amount > 1000000 {
        quality_gate: strict
    }
    
    task: "Analyze credit risk for ${input.company}"
}
```

**Generated Python:**
```python
from orchestra.advanced import AgentRouter, ConditionalExecutor, ErrorHandler
from orchestra.runtime import WorkflowContext

async def credit_analysis(input, swarm):
    """Generated workflow: credit_analysis"""
    
    # Guard clause validation
    if not (input.amount > 0):
        raise GuardViolationError("Guard failed: input.amount > 0")
    
    # Agent selection
    router = AgentRouter(swarm)
    agent = router.best_for(complexity="high", max_cost=0.01)
    
    # Conditional execution
    if input.amount > 1000000:
        quality_gate = "strict"
    else:
        quality_gate = "standard"
    
    # Task execution
    task = f"Analyze credit risk for {input.company}"
    result = await agent.execute(task, quality_gate=quality_gate)
    
    return result
```

**Optimization Passes:**

1. **Dead Code Elimination** - Remove unreachable code
2. **Constant Folding** - Evaluate constants at compile time
3. **Common Subexpression Elimination** - Cache repeated expressions
4. **Inline Simple Functions** - Reduce function call overhead

---

### 2.5 Runtime (Execution Engine)

**Purpose:** Execute compiled workflows with proper context and error handling

**Components:**

**WorkflowContext:**
```python
class WorkflowContext:
    """Runtime context for workflow execution"""
    
    def __init__(self, input: dict, swarm: "Swarm"):
        self.input = input
        self.swarm = swarm
        self.variables = {}
        self.metrics = WorkflowMetrics()
        self.error_handler = ErrorHandler()
    
    def get_variable(self, name: str) -> Any:
        """Get variable from context"""
        if name in self.variables:
            return self.variables[name]
        elif hasattr(self.input, name):
            return getattr(self.input, name)
        else:
            raise NameError(f"Variable '{name}' not found")
    
    def set_variable(self, name: str, value: Any):
        """Set variable in context"""
        self.variables[name] = value
```

**WorkflowMetrics:**
```python
@dataclass
class WorkflowMetrics:
    """Track workflow execution metrics"""
    
    start_time: float = 0
    end_time: float = 0
    total_cost: float = 0
    agent_calls: int = 0
    retries: int = 0
    errors: List[str] = None
    
    def duration(self) -> float:
        return self.end_time - self.start_time
    
    def to_dict(self) -> dict:
        return {
            "duration_seconds": self.duration(),
            "total_cost_usd": self.total_cost,
            "agent_calls": self.agent_calls,
            "retries": self.retries,
            "errors": self.errors or []
        }
```

**RuntimeEngine:**
```python
class RuntimeEngine:
    """Execute compiled workflows"""
    
    def __init__(self, swarm: "Swarm"):
        self.swarm = swarm
        self.compiled_workflows = {}
    
    async def execute_workflow(
        self, 
        workflow_name: str, 
        input: dict,
        timeout: Optional[float] = None
    ) -> WorkflowResult:
        """Execute a compiled workflow"""
        
        # Get compiled workflow function
        if workflow_name not in self.compiled_workflows:
            raise ValueError(f"Workflow '{workflow_name}' not found")
        
        workflow_func = self.compiled_workflows[workflow_name]
        
        # Create execution context
        context = WorkflowContext(input, self.swarm)
        context.metrics.start_time = time.time()
        
        try:
            # Execute with timeout
            if timeout:
                result = await asyncio.wait_for(
                    workflow_func(input, self.swarm),
                    timeout=timeout
                )
            else:
                result = await workflow_func(input, self.swarm)
            
            context.metrics.end_time = time.time()
            
            return WorkflowResult(
                success=True,
                result=result,
                metrics=context.metrics
            )
            
        except Exception as e:
            context.metrics.end_time = time.time()
            context.metrics.errors.append(str(e))
            
            return WorkflowResult(
                success=False,
                error=str(e),
                metrics=context.metrics
            )
    
    def load_workflow(self, workflow_name: str, code: str):
        """Load compiled workflow into runtime"""
        # Execute generated code to get function
        local_scope = {}
        exec(code, globals(), local_scope)
        self.compiled_workflows[workflow_name] = local_scope[workflow_name]
```

**WorkflowResult:**
```python
@dataclass
class WorkflowResult:
    """Result of workflow execution"""
    
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    metrics: Optional[WorkflowMetrics] = None
    
    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "result": self.result,
            "error": self.error,
            "metrics": self.metrics.to_dict() if self.metrics else None
        }
```

---

### 2.6 CLI Tool

**Purpose:** Command-line interface for Orchestra DSL

**Commands:**

```bash
# Run a workflow
orchestra run workflow.orc --input '{"amount": 2000000, "company": "TechCorp"}'
orchestra run workflow.orc -i input.json

# Validate syntax
orchestra validate workflow.orc
orchestra validate *.orc

# Compile to Python (for debugging)
orchestra compile workflow.orc --output workflow.py

# List workflows in a file
orchestra list workflow.orc

# Test a workflow
orchestra test workflow.orc --test-input test_cases.json

# Interactive REPL
orchestra repl

# Show workflow info
orchestra info workflow.orc

# Format/lint workflows
orchestra format workflow.orc
```

**Implementation:**
```python
import click
from pathlib import Path
from orchestra import Lexer, Parser, SemanticAnalyzer, CodeGenerator, RuntimeEngine

@click.group()
def cli():
    """Orchestra DSL - Declarative Multi-Agent Orchestration"""
    pass

@cli.command()
@click.argument('workflow_file', type=click.Path(exists=True))
@click.option('--input', '-i', help='Input JSON file or inline JSON')
@click.option('--timeout', '-t', type=float, help='Execution timeout in seconds')
def run(workflow_file, input, timeout):
    """Run a workflow"""
    
    # Load workflow
    source = Path(workflow_file).read_text()
    
    # Compile
    lexer = Lexer(source)
    tokens = lexer.tokenize()
    
    parser = Parser(tokens)
    ast = parser.parse()
    
    analyzer = SemanticAnalyzer(swarm)
    if not analyzer.analyze(ast):
        for error in analyzer.errors:
            click.echo(f"Error: {error}", err=True)
        return
    
    generator = CodeGenerator()
    code = generator.generate(ast)
    
    # Execute
    runtime = RuntimeEngine(swarm)
    runtime.load_workflow(ast[0].name, code)
    
    # Parse input
    if input.startswith('{'):
        input_data = json.loads(input)
    else:
        input_data = json.loads(Path(input).read_text())
    
    # Run
    result = await runtime.execute_workflow(ast[0].name, input_data, timeout)
    
    if result.success:
        click.echo(json.dumps(result.to_dict(), indent=2))
    else:
        click.echo(f"Error: {result.error}", err=True)

@cli.command()
@click.argument('workflow_file', type=click.Path(exists=True))
def validate(workflow_file):
    """Validate workflow syntax"""
    
    source = Path(workflow_file).read_text()
    
    try:
        lexer = Lexer(source)
        tokens = lexer.tokenize()
        
        parser = Parser(tokens)
        ast = parser.parse()
        
        analyzer = SemanticAnalyzer(swarm)
        if analyzer.analyze(ast):
            click.echo(f"✅ {workflow_file} is valid")
        else:
            for error in analyzer.errors:
                click.echo(f"❌ {error}", err=True)
    
    except Exception as e:
        click.echo(f"❌ Syntax error: {e}", err=True)

if __name__ == '__main__':
    cli()
```

---

## 3. Data Flow

### 3.1 Compilation Pipeline

```
.orc file
    │
    ▼
┌─────────────┐
│   Lexer     │ → Token stream
└─────────────┘
    │
    ▼
┌─────────────┐
│   Parser    │ → Abstract Syntax Tree (AST)
└─────────────┘
    │
    ▼
┌─────────────┐
│  Analyzer   │ → Validated AST + Symbol Table
└─────────────┘
    │
    ▼
┌─────────────┐
│  Compiler   │ → Python code (string)
└─────────────┘
    │
    ▼
┌─────────────┐
│  Runtime    │ → Callable function
└─────────────┘
```

### 3.2 Execution Pipeline

```
Input data
    │
    ▼
┌──────────────────┐
│ Workflow Context │
└──────────────────┘
    │
    ▼
┌──────────────────┐
│ Agent Selection  │ → AgentRouter.best_for()
└──────────────────┘
    │
    ▼
┌──────────────────┐
│ Task Execution   │ → agent.execute(task)
└──────────────────┘
    │
    ▼
┌──────────────────┐
│ Quality Gates    │ → Validate output
└──────────────────┘
    │
    ▼
┌──────────────────┐
│ Error Handling   │ → Retry if needed
└──────────────────┘
    │
    ▼
Result + Metrics
```

---

## 4. Integration Points

### 4.1 Swarm Integration

Orchestra workflows use the Swarm orchestrator for agent coordination:

```python
from swarm import Swarm

# Initialize swarm
swarm = Swarm(ai_portal_url="http://localhost:8000")

# Workflows can access swarm agents
agent = swarm.get_agent("claude_sonnet")
result = await agent.execute("Analyze this data")
```

### 4.2 AI Portal Integration

Through Swarm, workflows access the AI Portal for model inference:

```
Orchestra Workflow
    ↓
Swarm Orchestrator
    ↓
AI Portal Client
    ↓
AI Portal (/chat/send)
    ↓
Model (Claude, Grok, etc.)
```

### 4.3 External Systems

Workflows can integrate with external systems:

```orchestra
workflow data_pipeline {
    # Load data from database
    agent: data_specialist
    task: "Load customer data from PostgreSQL"
    
    # Process with AI
    agent: claude_sonnet
    task: "Analyze customer behavior patterns"
    
    # Save results to S3
    agent: data_specialist
    task: "Save analysis to S3 bucket"
}
```

---

## 5. Error Handling Strategy

### 5.1 Compile-Time Errors

**Lexical Errors:**
- Illegal characters
- Unclosed strings
- Invalid numbers

**Syntax Errors:**
- Unexpected tokens
- Missing delimiters
- Invalid expressions

**Semantic Errors:**
- Type mismatches
- Undefined variables
- Invalid agent names
- Resource constraint violations

### 5.2 Runtime Errors

**Execution Errors:**
- Agent unavailable
- Timeout exceeded
- Quality gate failure
- Network errors

**Handling Strategy:**
```orchestra
try {
    agent: ultra_reasoning
    task: "Complex analysis"
    timeout: 30.0
} retry {
    strategy: exponential_backoff
    max_attempts: 3
} catch timeout_error {
    agent: claude_sonnet  # Fallback
}
```

---

## 6. Performance Considerations

### 6.1 Compilation Performance

- **Caching:** Cache compiled workflows to avoid recompilation
- **Lazy Loading:** Load workflows only when needed
- **Parallel Compilation:** Compile multiple workflows in parallel

### 6.2 Runtime Performance

- **Connection Pooling:** Reuse HTTP connections to AI Portal
- **Batch Processing:** Group similar tasks together
- **Async Execution:** Use asyncio for concurrent agent calls

### 6.3 Memory Management

- **Streaming Results:** Stream large responses instead of buffering
- **Context Cleanup:** Clear workflow context after execution
- **Resource Limits:** Set memory limits on long-running workflows

---

## 7. Security Considerations

### 7.1 Code Injection Prevention

- **No eval() of user input:** Always parse and validate
- **Sandboxed execution:** Limit what workflows can do
- **Input sanitization:** Validate all input data

### 7.2 Resource Protection

- **Timeout enforcement:** Prevent infinite loops
- **Cost limits:** Prevent budget overruns
- **Rate limiting:** Prevent API abuse

### 7.3 Data Privacy

- **Sean Christopher Grady protected:** Safety protocol active
- **Encrypted storage:** Sensitive data encrypted at rest
- **Audit logging:** Track all workflow executions

---

## 8. Testing Strategy

### 8.1 Unit Tests

- Lexer: Token generation
- Parser: AST construction
- Analyzer: Semantic validation
- Compiler: Code generation
- Runtime: Execution correctness

### 8.2 Integration Tests

- End-to-end workflow execution
- Swarm integration
- Error handling
- Performance benchmarks

### 8.3 Test Workflows

```orchestra
# Test case: Simple workflow
workflow test_simple {
    agent: claude_sonnet
    task: "Hello world"
}

# Test case: Error handling
workflow test_errors {
    try {
        agent: ultra_reasoning
        timeout: 0.001  # Intentionally short
    } catch timeout_error {
        agent: claude_sonnet
    }
}
```

---

## 9. Future Enhancements

### 9.1 Planned Features

- **Parallel Execution:** Run multiple agents concurrently
- **State Management:** Persist workflow state
- **Debugging Tools:** Step-through debugger for workflows
- **Visual Designer:** GUI for building workflows
- **Import System:** Reusable workflow modules

### 9.2 Advanced Routing

- **Machine Learning:** Learn optimal routing from history
- **A/B Testing:** Compare agent performance
- **Dynamic Pricing:** Adjust routing based on current costs

### 9.3 Observability

- **Distributed Tracing:** OpenTelemetry integration
- **Metrics Dashboard:** Real-time workflow monitoring
- **Alerting:** Automated issue detection

---

## 10. Implementation Roadmap

### Phase 1: Foundation (Week 1-2)
- ✅ Lexer implementation
- ✅ Basic parser (workflow, agent, task)
- ✅ Simple AST nodes
- ✅ Basic code generation
- ✅ Minimal runtime

### Phase 2: Advanced Features (Week 3-4)
- ✅ Advanced routing integration
- ✅ Conditionals (if/else)
- ✅ Error handling (try/catch/retry)
- ✅ Quality gates
- ✅ Timeouts

### Phase 3: Tooling (Week 5-6)
- CLI implementation
- Validation tools
- Testing framework
- Documentation generator

### Phase 4: Production (Week 7-8)
- Performance optimization
- Security hardening
- Integration testing
- Documentation completion

---

## 11. Appendix

### 11.1 Keywords Reference

```
workflow, agent, task, if, else, match, case, try, retry, catch,
guard, quality_gate, timeout, best_for, cascade, round_robin,
load_balance, cheapest_above, dynamic_select
```

### 11.2 Operator Precedence

```
Highest → Lowest:
1. Attribute access (.)
2. Unary (-, not)
3. Multiplicative (*, /)
4. Additive (+, -)
5. Comparison (>, <, >=, <=, ==, !=)
6. Logical AND (and)
7. Logical OR (or)
```

### 11.3 Type System

```
Types:
- number (int, float)
- string
- boolean
- object (with attributes)
- agent (special type)
- workflow (special type)
```

---

**End of Architecture Specification**
