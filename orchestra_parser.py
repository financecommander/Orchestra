"""
Orchestra DSL - Parser

Converts token stream into Abstract Syntax Tree (AST).
Uses recursive descent parsing strategy.
"""

from typing import List, Optional
from orchestra_lexer import Token, TokenType, Lexer
from orchestra_ast import *


# ============================================================================
# Parser
# ============================================================================

class Parser:
    """Parse Orchestra token stream into AST"""
    
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.position = 0
        self.current_token = tokens[0] if tokens else None
    
    # ------------------------------------------------------------------------
    # Token Navigation
    # ------------------------------------------------------------------------
    
    def advance(self) -> Token:
        """Move to next token"""
        if self.position < len(self.tokens) - 1:
            self.position += 1
            self.current_token = self.tokens[self.position]
        return self.current_token
    
    def peek(self, offset: int = 1) -> Optional[Token]:
        """Look ahead at token"""
        pos = self.position + offset
        if pos < len(self.tokens):
            return self.tokens[pos]
        return None
    
    def at_end(self) -> bool:
        """Check if at end of token stream"""
        return self.current_token.type == TokenType.EOF
    
    def match(self, *token_types: TokenType) -> bool:
        """Check if current token matches any type"""
        return self.current_token.type in token_types
    
    def consume(self, token_type: TokenType, message: str = None) -> Token:
        """Consume expected token or raise error"""
        if not self.match(token_type):
            if message:
                raise SyntaxError(
                    f"{message} at {self.current_token.line}:{self.current_token.column}"
                )
            else:
                raise SyntaxError(
                    f"Expected {token_type.name}, got {self.current_token.type.name} "
                    f"at {self.current_token.line}:{self.current_token.column}"
                )
        
        token = self.current_token
        self.advance()
        return token
    
    # ------------------------------------------------------------------------
    # Main Entry Points
    # ------------------------------------------------------------------------
    
    def parse(self) -> Program:
        """Parse entire program"""
        workflows = []
        
        while not self.at_end():
            workflows.append(self.parse_workflow())
        
        return Program(workflows=workflows, line=1, column=1)
    
    def parse_workflow(self) -> Workflow:
        """Parse a workflow definition"""
        # workflow IDENTIFIER {
        workflow_token = self.consume(TokenType.WORKFLOW)
        name_token = self.consume(TokenType.IDENTIFIER, "Expected workflow name")
        name = name_token.value
        
        self.consume(TokenType.LBRACE, "Expected '{' after workflow name")
        
        # Parse statements until }
        statements = []
        while not self.match(TokenType.RBRACE) and not self.at_end():
            statements.append(self.parse_statement())
        
        self.consume(TokenType.RBRACE, "Expected '}' at end of workflow")
        
        return Workflow(
            name=name,
            statements=statements,
            line=workflow_token.line,
            column=workflow_token.column
        )
    
    # ------------------------------------------------------------------------
    # Statement Parsing
    # ------------------------------------------------------------------------
    
    def parse_statement(self) -> Statement:
        """Parse a single statement"""
        
        # Agent statement
        if self.match(TokenType.AGENT):
            return self.parse_agent_statement()
        
        # Task statement
        if self.match(TokenType.TASK):
            return self.parse_task_statement()
        
        # Guard statement
        if self.match(TokenType.GUARD):
            return self.parse_guard_statement()
        
        # Quality gate statement
        if self.match(TokenType.QUALITY_GATE):
            return self.parse_quality_gate_statement()
        
        # Timeout statement
        if self.match(TokenType.TIMEOUT):
            return self.parse_timeout_statement()
        
        # Conditional statement
        if self.match(TokenType.IF):
            return self.parse_conditional_statement()
        
        # Match statement
        if self.match(TokenType.MATCH):
            return self.parse_match_statement()
        
        # Try statement
        if self.match(TokenType.TRY):
            return self.parse_try_statement()
        
        # Assignment (variable = expression)
        if self.match(TokenType.IDENTIFIER) and self.peek() and self.peek().type == TokenType.EQUALS:
            return self.parse_assignment()
        
        raise SyntaxError(
            f"Unexpected token {self.current_token.type.name} "
            f"at {self.current_token.line}:{self.current_token.column}"
        )
    
    def parse_agent_statement(self) -> AgentStatement:
        """Parse: agent: <agent_spec>"""
        agent_token = self.consume(TokenType.AGENT)
        self.consume(TokenType.COLON)
        
        agent_spec = self.parse_agent_spec()
        
        return AgentStatement(
            agent_spec=agent_spec,
            line=agent_token.line,
            column=agent_token.column
        )
    
    def parse_agent_spec(self) -> AgentSpec:
        """Parse agent specification"""
        
        # best_for(...)
        if self.match(TokenType.BEST_FOR):
            return self.parse_best_for_routing()
        
        # cascade [...]
        if self.match(TokenType.CASCADE):
            return self.parse_cascade_routing()
        
        # round_robin [...]
        if self.match(TokenType.ROUND_ROBIN):
            return self.parse_round_robin_routing()
        
        # load_balance [...]
        if self.match(TokenType.LOAD_BALANCE):
            return self.parse_load_balance_routing()
        
        # cheapest_above(...)
        if self.match(TokenType.CHEAPEST_ABOVE):
            return self.parse_cheapest_above_routing()
        
        # dynamic_select(...)
        if self.match(TokenType.DYNAMIC_SELECT):
            return self.parse_dynamic_select_routing()
        
        # Simple agent name
        if self.match(TokenType.IDENTIFIER):
            token = self.current_token
            name = token.value
            self.advance()
            return SimpleAgent(name=name, line=token.line, column=token.column)
        
        raise SyntaxError(
            f"Expected agent specification at {self.current_token.line}:{self.current_token.column}"
        )
    
    def parse_best_for_routing(self) -> BestForRouting:
        """Parse: best_for(complexity: high, max_cost: 0.01)"""
        token = self.consume(TokenType.BEST_FOR)
        self.consume(TokenType.LPAREN)
        
        criteria = {}
        while not self.match(TokenType.RPAREN):
            # criterion_name: value
            name = self.consume(TokenType.IDENTIFIER).value
            self.consume(TokenType.COLON)
            
            # Value can be identifier, number, or string
            if self.match(TokenType.IDENTIFIER):
                value = self.current_token.value
                self.advance()
            elif self.match(TokenType.NUMBER):
                value = self.current_token.value
                self.advance()
            elif self.match(TokenType.STRING):
                value = self.current_token.value
                self.advance()
            else:
                raise SyntaxError(f"Expected value at {self.current_token.line}:{self.current_token.column}")
            
            criteria[name] = value
            
            # Optional comma
            if self.match(TokenType.COMMA):
                self.advance()
        
        self.consume(TokenType.RPAREN)
        
        return BestForRouting(criteria=criteria, line=token.line, column=token.column)
    
    def parse_cascade_routing(self) -> CascadeRouting:
        """Parse: cascade [try: agent1, fallback: agent2, last_resort: agent3]"""
        token = self.consume(TokenType.CASCADE)
        self.consume(TokenType.LBRACKET)
        
        agents = []
        while not self.match(TokenType.RBRACKET):
            # Role: agent_name
            # TRY can be either TRY_KW or TRY token type depending on context
            if self.match(TokenType.TRY_KW, TokenType.TRY, TokenType.FALLBACK, TokenType.LAST_RESORT):
                role_token = self.current_token
                role = role_token.value if role_token.value else "try"
                self.advance()
                self.consume(TokenType.COLON)
                name = self.consume(TokenType.IDENTIFIER).value
                agents.append(AgentRef(role=role, name=name, line=role_token.line, column=role_token.column))
            elif self.match(TokenType.IDENTIFIER):
                # Just agent name (implied role)
                name_token = self.current_token
                name = name_token.value
                self.advance()
                agents.append(AgentRef(role="agent", name=name, line=name_token.line, column=name_token.column))
            else:
                raise SyntaxError(f"Expected agent reference at {self.current_token.line}:{self.current_token.column}")
            
            # Optional comma
            if self.match(TokenType.COMMA):
                self.advance()
        
        self.consume(TokenType.RBRACKET)
        
        return CascadeRouting(agents=agents, line=token.line, column=token.column)
    
    def parse_round_robin_routing(self) -> RoundRobinRouting:
        """Parse: round_robin [agent1, agent2, agent3]"""
        token = self.consume(TokenType.ROUND_ROBIN)
        self.consume(TokenType.LBRACKET)
        
        agents = []
        while not self.match(TokenType.RBRACKET):
            name = self.consume(TokenType.IDENTIFIER).value
            agents.append(name)
            
            if self.match(TokenType.COMMA):
                self.advance()
        
        self.consume(TokenType.RBRACKET)
        
        return RoundRobinRouting(agents=agents, line=token.line, column=token.column)
    
    def parse_load_balance_routing(self) -> LoadBalanceRouting:
        """Parse: load_balance [agent1, agent2, agent3]"""
        token = self.consume(TokenType.LOAD_BALANCE)
        self.consume(TokenType.LBRACKET)
        
        agents = []
        while not self.match(TokenType.RBRACKET):
            name = self.consume(TokenType.IDENTIFIER).value
            agents.append(name)
            
            if self.match(TokenType.COMMA):
                self.advance()
        
        self.consume(TokenType.RBRACKET)
        
        return LoadBalanceRouting(agents=agents, line=token.line, column=token.column)
    
    def parse_cheapest_above_routing(self) -> CheapestAboveRouting:
        """Parse: cheapest_above(0.8, [agent1, agent2])"""
        token = self.consume(TokenType.CHEAPEST_ABOVE)
        self.consume(TokenType.LPAREN)
        
        threshold = self.consume(TokenType.NUMBER).value
        self.consume(TokenType.COMMA)
        
        self.consume(TokenType.LBRACKET)
        candidates = []
        while not self.match(TokenType.RBRACKET):
            name = self.consume(TokenType.IDENTIFIER).value
            candidates.append(name)
            
            if self.match(TokenType.COMMA):
                self.advance()
        
        self.consume(TokenType.RBRACKET)
        self.consume(TokenType.RPAREN)
        
        return CheapestAboveRouting(
            quality_threshold=threshold,
            candidates=candidates,
            line=token.line,
            column=token.column
        )
    
    def parse_dynamic_select_routing(self) -> DynamicSelectRouting:
        """Parse: dynamic_select(selector_function)"""
        token = self.consume(TokenType.DYNAMIC_SELECT)
        self.consume(TokenType.LPAREN)
        
        selector = self.consume(TokenType.IDENTIFIER).value
        
        self.consume(TokenType.RPAREN)
        
        return DynamicSelectRouting(
            selector_function=selector,
            line=token.line,
            column=token.column
        )
    
    def parse_task_statement(self) -> TaskStatement:
        """Parse: task: "description" """
        token = self.consume(TokenType.TASK)
        self.consume(TokenType.COLON)
        
        task = self.consume(TokenType.STRING).value
        
        return TaskStatement(task=task, line=token.line, column=token.column)
    
    def parse_guard_statement(self) -> GuardStatement:
        """Parse: guard: condition"""
        token = self.consume(TokenType.GUARD)
        self.consume(TokenType.COLON)
        
        condition = self.parse_expression()
        
        return GuardStatement(condition=condition, line=token.line, column=token.column)
    
    def parse_quality_gate_statement(self) -> QualityGateStatement:
        """Parse: quality_gate: strict"""
        token = self.consume(TokenType.QUALITY_GATE)
        self.consume(TokenType.COLON)
        
        level = self.consume(TokenType.IDENTIFIER).value
        
        return QualityGateStatement(level=level, line=token.line, column=token.column)
    
    def parse_timeout_statement(self) -> TimeoutStatement:
        """Parse: timeout: 30.0"""
        token = self.consume(TokenType.TIMEOUT)
        self.consume(TokenType.COLON)
        
        seconds = self.consume(TokenType.NUMBER).value
        
        return TimeoutStatement(seconds=seconds, line=token.line, column=token.column)
    
    def parse_conditional_statement(self) -> ConditionalStatement:
        """Parse: if condition { ... } else { ... }"""
        token = self.consume(TokenType.IF)
        
        condition = self.parse_expression()
        
        self.consume(TokenType.LBRACE)
        then_branch = []
        while not self.match(TokenType.RBRACE) and not self.at_end():
            then_branch.append(self.parse_statement())
        self.consume(TokenType.RBRACE)
        
        else_branch = None
        if self.match(TokenType.ELSE):
            self.advance()
            self.consume(TokenType.LBRACE)
            else_branch = []
            while not self.match(TokenType.RBRACE) and not self.at_end():
                else_branch.append(self.parse_statement())
            self.consume(TokenType.RBRACE)
        
        return ConditionalStatement(
            condition=condition,
            then_branch=then_branch,
            else_branch=else_branch,
            line=token.line,
            column=token.column
        )
    
    def parse_match_statement(self) -> MatchStatement:
        """Parse: match value { case ... }"""
        token = self.consume(TokenType.MATCH)
        
        value = self.parse_expression()
        
        self.consume(TokenType.LBRACE)
        
        cases = []
        default = None
        
        while not self.match(TokenType.RBRACE) and not self.at_end():
            if self.match(TokenType.CASE):
                case_token = self.consume(TokenType.CASE)
                pattern = self.parse_expression()
                self.consume(TokenType.COLON)
                self.consume(TokenType.LBRACE)
                
                statements = []
                while not self.match(TokenType.RBRACE) and not self.at_end():
                    statements.append(self.parse_statement())
                self.consume(TokenType.RBRACE)
                
                cases.append(CaseClause(pattern=pattern, statements=statements, line=case_token.line, column=case_token.column))
        
        self.consume(TokenType.RBRACE)
        
        return MatchStatement(value=value, cases=cases, default=default, line=token.line, column=token.column)
    
    def parse_try_statement(self) -> TryStatement:
        """Parse: try { ... } retry { ... } catch error { ... }"""
        token = self.consume(TokenType.TRY)
        
        self.consume(TokenType.LBRACE)
        try_block = []
        while not self.match(TokenType.RBRACE) and not self.at_end():
            try_block.append(self.parse_statement())
        self.consume(TokenType.RBRACE)
        
        retry_config = None
        if self.match(TokenType.RETRY):
            retry_config = self.parse_retry_config()
        
        catch_blocks = []
        while self.match(TokenType.CATCH):
            catch_blocks.append(self.parse_catch_block())
        
        return TryStatement(
            try_block=try_block,
            retry_config=retry_config,
            catch_blocks=catch_blocks,
            line=token.line,
            column=token.column
        )
    
    def parse_retry_config(self) -> RetryConfig:
        """Parse: retry { strategy: exponential_backoff, max_attempts: 3 }"""
        token = self.consume(TokenType.RETRY)
        self.consume(TokenType.LBRACE)
        
        config = {}
        while not self.match(TokenType.RBRACE):
            # Key can be IDENTIFIER or specific retry keywords
            if self.match(TokenType.IDENTIFIER, TokenType.STRATEGY, TokenType.MAX_ATTEMPTS, 
                         TokenType.BACKOFF_FACTOR, TokenType.INITIAL_DELAY):
                key = self.current_token.value
                self.advance()
            else:
                raise SyntaxError(f"Expected config key at {self.current_token.line}:{self.current_token.column}")
            
            self.consume(TokenType.COLON)
            
            if self.match(TokenType.IDENTIFIER):
                value = self.current_token.value
                self.advance()
            elif self.match(TokenType.NUMBER):
                value = self.current_token.value
                self.advance()
            else:
                raise SyntaxError(f"Expected value at {self.current_token.line}:{self.current_token.column}")
            
            config[key] = value
            
            if self.match(TokenType.COMMA):
                self.advance()
        
        self.consume(TokenType.RBRACE)
        
        return RetryConfig(
            strategy=config.get('strategy', 'exponential_backoff'),
            max_attempts=config.get('max_attempts', 3),
            backoff_factor=config.get('backoff_factor', 2.0),
            initial_delay=config.get('initial_delay', 1.0),
            line=token.line,
            column=token.column
        )
    
    def parse_catch_block(self) -> CatchBlock:
        """Parse: catch error_type { ... }"""
        token = self.consume(TokenType.CATCH)
        
        error_type = self.consume(TokenType.IDENTIFIER).value
        
        self.consume(TokenType.LBRACE)
        statements = []
        while not self.match(TokenType.RBRACE) and not self.at_end():
            statements.append(self.parse_statement())
        self.consume(TokenType.RBRACE)
        
        return CatchBlock(
            error_type=error_type,
            statements=statements,
            line=token.line,
            column=token.column
        )
    
    def parse_assignment(self) -> Assignment:
        """Parse: variable = expression"""
        token = self.current_token
        target = self.consume(TokenType.IDENTIFIER).value
        self.consume(TokenType.EQUALS)
        value = self.parse_expression()
        
        return Assignment(target=target, value=value, line=token.line, column=token.column)
    
    # ------------------------------------------------------------------------
    # Expression Parsing (Precedence Climbing)
    # ------------------------------------------------------------------------
    
    def parse_expression(self) -> Expression:
        """Parse an expression"""
        return self.parse_logical_or()
    
    def parse_logical_or(self) -> Expression:
        """Parse: expr or expr"""
        left = self.parse_logical_and()
        
        while self.match(TokenType.OR):
            op_token = self.current_token
            self.advance()
            right = self.parse_logical_and()
            left = BinaryOp(left=left, operator='or', right=right, line=op_token.line, column=op_token.column)
        
        return left
    
    def parse_logical_and(self) -> Expression:
        """Parse: expr and expr"""
        left = self.parse_comparison()
        
        while self.match(TokenType.AND):
            op_token = self.current_token
            self.advance()
            right = self.parse_comparison()
            left = BinaryOp(left=left, operator='and', right=right, line=op_token.line, column=op_token.column)
        
        return left
    
    def parse_comparison(self) -> Expression:
        """Parse: expr > expr, expr == expr, etc."""
        left = self.parse_additive()
        
        while self.match(TokenType.GT, TokenType.LT, TokenType.GTE, TokenType.LTE, TokenType.EQ, TokenType.NEQ):
            op_token = self.current_token
            op = op_token.value
            self.advance()
            right = self.parse_additive()
            left = BinaryOp(left=left, operator=op, right=right, line=op_token.line, column=op_token.column)
        
        return left
    
    def parse_additive(self) -> Expression:
        """Parse: expr + expr, expr - expr"""
        left = self.parse_multiplicative()
        
        while self.match(TokenType.PLUS, TokenType.MINUS):
            op_token = self.current_token
            op = op_token.value
            self.advance()
            right = self.parse_multiplicative()
            left = BinaryOp(left=left, operator=op, right=right, line=op_token.line, column=op_token.column)
        
        return left
    
    def parse_multiplicative(self) -> Expression:
        """Parse: expr * expr, expr / expr"""
        left = self.parse_unary()
        
        while self.match(TokenType.STAR, TokenType.SLASH, TokenType.PERCENT):
            op_token = self.current_token
            op = op_token.value
            self.advance()
            right = self.parse_unary()
            left = BinaryOp(left=left, operator=op, right=right, line=op_token.line, column=op_token.column)
        
        return left
    
    def parse_unary(self) -> Expression:
        """Parse: -expr, not expr"""
        if self.match(TokenType.MINUS, TokenType.NOT):
            op_token = self.current_token
            op = op_token.value
            self.advance()
            operand = self.parse_unary()
            return UnaryOp(operator=op, operand=operand, line=op_token.line, column=op_token.column)
        
        return self.parse_primary()
    
    def parse_primary(self) -> Expression:
        """Parse primary expressions (literals, identifiers, parentheses)"""
        
        # Numbers
        if self.match(TokenType.NUMBER):
            token = self.current_token
            value = token.value
            self.advance()
            return Literal(value=value, line=token.line, column=token.column)
        
        # Strings
        if self.match(TokenType.STRING):
            token = self.current_token
            value = token.value
            self.advance()
            return Literal(value=value, line=token.line, column=token.column)
        
        # Booleans
        if self.match(TokenType.TRUE):
            token = self.current_token
            self.advance()
            return Literal(value=True, line=token.line, column=token.column)
        
        if self.match(TokenType.FALSE):
            token = self.current_token
            self.advance()
            return Literal(value=False, line=token.line, column=token.column)
        
        # Identifiers (with attribute access)
        # INPUT is a keyword but can be used like an identifier in expressions
        if self.match(TokenType.IDENTIFIER, TokenType.INPUT, TokenType.OUTPUT):
            token = self.current_token
            name = token.value
            self.advance()
            
            # Attribute access (e.g., input.amount)
            attributes = []
            while self.match(TokenType.DOT):
                self.advance()
                attr = self.consume(TokenType.IDENTIFIER).value
                attributes.append(attr)
            
            return Identifier(name=name, attributes=attributes, line=token.line, column=token.column)
        
        # Parentheses
        if self.match(TokenType.LPAREN):
            self.advance()
            expr = self.parse_expression()
            self.consume(TokenType.RPAREN)
            return expr
        
        raise SyntaxError(
            f"Unexpected token {self.current_token.type.name} in expression "
            f"at {self.current_token.line}:{self.current_token.column}"
        )


# ============================================================================
# Testing & Debugging
# ============================================================================

def parse_file(filepath: str) -> Program:
    """Parse a .orc file"""
    with open(filepath, 'r') as f:
        source = f.read()
    
    lexer = Lexer(source)
    tokens = lexer.tokenize()
    
    parser = Parser(tokens)
    return parser.parse()


if __name__ == "__main__":
    # Test the parser
    test_source = """
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
    
    lexer = Lexer(test_source)
    tokens = lexer.tokenize()
    
    parser = Parser(tokens)
    ast = parser.parse()
    
    print("=" * 60)
    print("PARSER TEST")
    print("=" * 60)
    print(print_ast(ast))
