"""
Orchestra DSL - Abstract Syntax Tree (AST) Node Definitions

Defines all AST node types for the Orchestra language.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Any, Union
from enum import Enum


# ============================================================================
# Base Classes
# ============================================================================

@dataclass
class ASTNode:
    """Base class for all AST nodes"""
    line: int
    column: int


# ============================================================================
# Program Structure
# ============================================================================

@dataclass
class Program(ASTNode):
    """Root node containing all workflows"""
    workflows: List["Workflow"]


@dataclass
class Workflow(ASTNode):
    """A workflow definition"""
    name: str
    statements: List["Statement"]
    
    def __repr__(self):
        return f"Workflow({self.name}, {len(self.statements)} statements)"


# ============================================================================
# Statements
# ============================================================================

@dataclass
class Statement(ASTNode):
    """Base class for all statements"""
    pass


@dataclass
class AgentStatement(Statement):
    """Agent selection statement"""
    agent_spec: "AgentSpec"


@dataclass
class TaskStatement(Statement):
    """Task execution statement"""
    task: str  # Can contain ${variable} interpolations


@dataclass
class GuardStatement(Statement):
    """Guard clause for validation"""
    condition: "Expression"


@dataclass
class QualityGateStatement(Statement):
    """Quality gate specification"""
    level: str  # "strict", "standard", "relaxed"


@dataclass
class TimeoutStatement(Statement):
    """Timeout specification"""
    seconds: float


@dataclass
class ConditionalStatement(Statement):
    """If-else conditional"""
    condition: "Expression"
    then_branch: List[Statement]
    else_branch: Optional[List[Statement]] = None


@dataclass
class MatchStatement(Statement):
    """Match-case pattern matching"""
    value: "Expression"
    cases: List["CaseClause"]
    default: Optional[List[Statement]] = None


@dataclass
class CaseClause(ASTNode):
    """Single case in a match statement"""
    pattern: Any  # The value to match
    statements: List[Statement]


@dataclass
class TryStatement(Statement):
    """Try-catch-retry error handling"""
    try_block: List[Statement]
    retry_config: Optional["RetryConfig"] = None
    catch_blocks: List["CatchBlock"] = field(default_factory=list)


@dataclass
class CatchBlock(ASTNode):
    """Catch block for error handling"""
    error_type: str  # "timeout_error", "api_error", etc.
    statements: List[Statement]


@dataclass
class RetryConfig(ASTNode):
    """Retry configuration"""
    strategy: str = "exponential_backoff"  # "fixed", "linear", "exponential_backoff"
    max_attempts: int = 3
    backoff_factor: float = 2.0
    initial_delay: float = 1.0


@dataclass
class Assignment(Statement):
    """Variable assignment"""
    target: str
    value: "Expression"


# ============================================================================
# Agent Specifications
# ============================================================================

@dataclass
class AgentSpec(ASTNode):
    """Base class for agent specifications"""
    pass


@dataclass
class SimpleAgent(AgentSpec):
    """Direct agent reference"""
    name: str
    
    def __repr__(self):
        return f"SimpleAgent({self.name})"


@dataclass
class BestForRouting(AgentSpec):
    """best_for() routing strategy"""
    criteria: dict[str, Any]
    
    def __repr__(self):
        return f"BestForRouting({self.criteria})"


@dataclass
class CascadeRouting(AgentSpec):
    """cascade[] routing with fallback chain"""
    agents: List["AgentRef"]
    
    def __repr__(self):
        return f"CascadeRouting({len(self.agents)} agents)"


@dataclass
class RoundRobinRouting(AgentSpec):
    """round_robin[] load distribution"""
    agents: List[str]


@dataclass
class LoadBalanceRouting(AgentSpec):
    """load_balance[] with weighted distribution"""
    agents: List[str]
    weights: Optional[List[float]] = None


@dataclass
class CheapestAboveRouting(AgentSpec):
    """cheapest_above() with quality threshold"""
    quality_threshold: float
    candidates: List[str]


@dataclass
class DynamicSelectRouting(AgentSpec):
    """dynamic_select() with custom selection function"""
    selector_function: str


@dataclass
class AgentRef(ASTNode):
    """Reference to an agent in cascade/fallback chains"""
    role: str  # "try", "fallback", "last_resort"
    name: str


# ============================================================================
# Expressions
# ============================================================================

@dataclass
class Expression(ASTNode):
    """Base class for expressions"""
    pass


@dataclass
class BinaryOp(Expression):
    """Binary operation (e.g., a + b, x > 5)"""
    left: Expression
    operator: str  # "+", "-", "*", "/", ">", "<", ">=", "<=", "==", "!=", "and", "or"
    right: Expression


@dataclass
class UnaryOp(Expression):
    """Unary operation (e.g., -x, not y)"""
    operator: str  # "-", "not"
    operand: Expression


@dataclass
class Literal(Expression):
    """Literal value (number, string, boolean)"""
    value: Any  # int, float, str, bool
    
    def __repr__(self):
        return f"Literal({self.value})"


@dataclass
class Identifier(Expression):
    """Variable or attribute reference"""
    name: str
    attributes: List[str] = field(default_factory=list)
    
    def full_name(self) -> str:
        """Get fully qualified name (e.g., 'input.amount')"""
        if self.attributes:
            return f"{self.name}.{'.'.join(self.attributes)}"
        return self.name
    
    def __repr__(self):
        return f"Identifier({self.full_name()})"


@dataclass
class StringInterpolation(Expression):
    """String with ${variable} interpolations"""
    template: str  # Original template string
    parts: List[Union[str, Expression]]  # Parsed parts


@dataclass
class FunctionCall(Expression):
    """Function call expression"""
    name: str
    arguments: List[Expression]


# ============================================================================
# Type System
# ============================================================================

class OrchestraType(Enum):
    """Orchestra type system"""
    NUMBER = "number"
    STRING = "string"
    BOOLEAN = "boolean"
    AGENT = "agent"
    WORKFLOW = "workflow"
    OBJECT = "object"
    ANY = "any"


@dataclass
class TypeAnnotation(ASTNode):
    """Type annotation for variables"""
    type: OrchestraType
    nullable: bool = False


# ============================================================================
# Utility Classes
# ============================================================================

@dataclass
class SourceLocation:
    """Location in source file"""
    line: int
    column: int
    filename: Optional[str] = None
    
    def __str__(self):
        if self.filename:
            return f"{self.filename}:{self.line}:{self.column}"
        return f"{self.line}:{self.column}"


# ============================================================================
# AST Visitor Pattern
# ============================================================================

class ASTVisitor:
    """Base class for AST visitors"""
    
    def visit(self, node: ASTNode) -> Any:
        """Visit a node and dispatch to appropriate method"""
        method_name = f"visit_{node.__class__.__name__}"
        visitor = getattr(self, method_name, self.generic_visit)
        return visitor(node)
    
    def generic_visit(self, node: ASTNode) -> Any:
        """Called if no explicit visitor method exists"""
        raise NotImplementedError(f"No visit method for {node.__class__.__name__}")
    
    def visit_Program(self, node: Program):
        for workflow in node.workflows:
            self.visit(workflow)
    
    def visit_Workflow(self, node: Workflow):
        for statement in node.statements:
            self.visit(statement)
    
    def visit_AgentStatement(self, node: AgentStatement):
        self.visit(node.agent_spec)
    
    def visit_TaskStatement(self, node: TaskStatement):
        pass
    
    def visit_ConditionalStatement(self, node: ConditionalStatement):
        self.visit(node.condition)
        for stmt in node.then_branch:
            self.visit(stmt)
        if node.else_branch:
            for stmt in node.else_branch:
                self.visit(stmt)
    
    def visit_BinaryOp(self, node: BinaryOp):
        self.visit(node.left)
        self.visit(node.right)
    
    def visit_Literal(self, node: Literal):
        pass
    
    def visit_Identifier(self, node: Identifier):
        pass


# ============================================================================
# AST Pretty Printer
# ============================================================================

class ASTPrettyPrinter(ASTVisitor):
    """Pretty print AST for debugging"""
    
    def __init__(self):
        self.indent_level = 0
        self.output = []
    
    def indent(self):
        return "  " * self.indent_level
    
    def print_node(self, name: str, *args):
        self.output.append(f"{self.indent()}{name}({', '.join(str(a) for a in args)})")
    
    def visit_Workflow(self, node: Workflow):
        self.print_node("Workflow", node.name)
        self.indent_level += 1
        for stmt in node.statements:
            self.visit(stmt)
        self.indent_level -= 1
    
    def visit_AgentStatement(self, node: AgentStatement):
        self.print_node("AgentStatement")
        self.indent_level += 1
        self.visit(node.agent_spec)
        self.indent_level -= 1
    
    def visit_SimpleAgent(self, node: SimpleAgent):
        self.print_node("SimpleAgent", node.name)
    
    def visit_BestForRouting(self, node: BestForRouting):
        self.print_node("BestForRouting", node.criteria)
    
    def visit_TaskStatement(self, node: TaskStatement):
        self.print_node("TaskStatement", repr(node.task))
    
    def visit_GuardStatement(self, node: GuardStatement):
        self.print_node("GuardStatement")
        self.indent_level += 1
        self.visit(node.condition)
        self.indent_level -= 1
    
    def visit_QualityGateStatement(self, node: QualityGateStatement):
        self.print_node("QualityGateStatement", node.level)
    
    def visit_TimeoutStatement(self, node: TimeoutStatement):
        self.print_node("TimeoutStatement", node.seconds)
    
    def visit_TryStatement(self, node: TryStatement):
        self.print_node("TryStatement")
        self.indent_level += 1
        self.print_node("Try Block")
        self.indent_level += 1
        for stmt in node.try_block:
            self.visit(stmt)
        self.indent_level -= 1
        if node.retry_config:
            self.print_node("Retry", node.retry_config.strategy)
        for catch in node.catch_blocks:
            self.print_node("Catch", catch.error_type)
            self.indent_level += 1
            for stmt in catch.statements:
                self.visit(stmt)
            self.indent_level -= 1
        self.indent_level -= 1
    
    def visit_CascadeRouting(self, node: CascadeRouting):
        self.print_node("CascadeRouting")
        self.indent_level += 1
        for agent_ref in node.agents:
            self.print_node(f"{agent_ref.role}: {agent_ref.name}")
        self.indent_level -= 1
    
    def visit_ConditionalStatement(self, node: ConditionalStatement):
        self.print_node("ConditionalStatement")
        self.indent_level += 1
        self.print_node("Condition")
        self.indent_level += 1
        self.visit(node.condition)
        self.indent_level -= 1
        self.print_node("Then")
        self.indent_level += 1
        for stmt in node.then_branch:
            self.visit(stmt)
        self.indent_level -= 1
        if node.else_branch:
            self.print_node("Else")
            self.indent_level += 1
            for stmt in node.else_branch:
                self.visit(stmt)
            self.indent_level -= 1
        self.indent_level -= 1
    
    def visit_BinaryOp(self, node: BinaryOp):
        self.print_node("BinaryOp", node.operator)
        self.indent_level += 1
        self.visit(node.left)
        self.visit(node.right)
        self.indent_level -= 1
    
    def visit_Literal(self, node: Literal):
        self.print_node("Literal", repr(node.value))
    
    def visit_Identifier(self, node: Identifier):
        self.print_node("Identifier", node.full_name())
    
    def get_output(self) -> str:
        return "\n".join(self.output)


def print_ast(node: ASTNode) -> str:
    """Pretty print an AST node"""
    printer = ASTPrettyPrinter()
    printer.visit(node)
    return printer.get_output()
