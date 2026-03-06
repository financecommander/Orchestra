"""
Orchestra DSL - Lexer (Tokenizer)

Converts Orchestra source code into a stream of tokens.
"""

from dataclasses import dataclass
from enum import Enum, auto
from typing import List, Optional, Any


# ============================================================================
# Token Types
# ============================================================================

class TokenType(Enum):
    """All token types in Orchestra language"""
    
    # Keywords
    WORKFLOW = auto()
    AGENT = auto()
    TASK = auto()
    IF = auto()
    ELSE = auto()
    MATCH = auto()
    CASE = auto()
    TRY = auto()
    RETRY = auto()
    CATCH = auto()
    GUARD = auto()
    QUALITY_GATE = auto()
    TIMEOUT = auto()
    INPUT = auto()
    OUTPUT = auto()
    
    # Routing strategies
    BEST_FOR = auto()
    CASCADE = auto()
    ROUND_ROBIN = auto()
    LOAD_BALANCE = auto()
    CHEAPEST_ABOVE = auto()
    DYNAMIC_SELECT = auto()
    
    # Routing modifiers
    TRY_KW = auto()  # 'try' in agent list context
    FALLBACK = auto()
    LAST_RESORT = auto()
    
    # Retry strategies
    STRATEGY = auto()
    MAX_ATTEMPTS = auto()
    BACKOFF_FACTOR = auto()
    INITIAL_DELAY = auto()
    
    # Literals
    IDENTIFIER = auto()
    STRING = auto()
    NUMBER = auto()
    TRUE = auto()
    FALSE = auto()
    
    # Operators
    COLON = auto()          # :
    COMMA = auto()          # ,
    DOT = auto()            # .
    ARROW = auto()          # ->
    EQUALS = auto()         # =
    GT = auto()             # >
    LT = auto()             # <
    GTE = auto()            # >=
    LTE = auto()            # <=
    EQ = auto()             # ==
    NEQ = auto()            # !=
    PLUS = auto()           # +
    MINUS = auto()          # -
    STAR = auto()           # *
    SLASH = auto()          # /
    PERCENT = auto()        # %
    
    # Logical operators
    AND = auto()
    OR = auto()
    NOT = auto()
    
    # Delimiters
    LBRACE = auto()         # {
    RBRACE = auto()         # }
    LPAREN = auto()         # (
    RPAREN = auto()         # )
    LBRACKET = auto()       # [
    RBRACKET = auto()       # ]
    
    # Special
    NEWLINE = auto()
    EOF = auto()
    COMMENT = auto()


# ============================================================================
# Token Class
# ============================================================================

@dataclass
class Token:
    """A single token from the source"""
    type: TokenType
    value: Any
    line: int
    column: int
    
    def __repr__(self):
        return f"Token({self.type.name}, {repr(self.value)}, {self.line}:{self.column})"


# ============================================================================
# Lexer
# ============================================================================

class Lexer:
    """Tokenize Orchestra source code"""
    
    # Keywords mapping
    KEYWORDS = {
        'workflow': TokenType.WORKFLOW,
        'agent': TokenType.AGENT,
        'task': TokenType.TASK,
        'if': TokenType.IF,
        'else': TokenType.ELSE,
        'match': TokenType.MATCH,
        'case': TokenType.CASE,
        'try': TokenType.TRY,
        'retry': TokenType.RETRY,
        'catch': TokenType.CATCH,
        'guard': TokenType.GUARD,
        'quality_gate': TokenType.QUALITY_GATE,
        'timeout': TokenType.TIMEOUT,
        'input': TokenType.INPUT,
        'output': TokenType.OUTPUT,
        
        # Routing strategies
        'best_for': TokenType.BEST_FOR,
        'cascade': TokenType.CASCADE,
        'round_robin': TokenType.ROUND_ROBIN,
        'load_balance': TokenType.LOAD_BALANCE,
        'cheapest_above': TokenType.CHEAPEST_ABOVE,
        'dynamic_select': TokenType.DYNAMIC_SELECT,
        
        # Routing modifiers
        'fallback': TokenType.FALLBACK,
        'last_resort': TokenType.LAST_RESORT,
        
        # Retry config
        'strategy': TokenType.STRATEGY,
        'max_attempts': TokenType.MAX_ATTEMPTS,
        'backoff_factor': TokenType.BACKOFF_FACTOR,
        'initial_delay': TokenType.INITIAL_DELAY,
        
        # Boolean literals
        'true': TokenType.TRUE,
        'false': TokenType.FALSE,
        
        # Logical operators
        'and': TokenType.AND,
        'or': TokenType.OR,
        'not': TokenType.NOT,
    }
    
    def __init__(self, source: str):
        self.source = source
        self.position = 0
        self.line = 1
        self.column = 1
        self.tokens: List[Token] = []
    
    def current_char(self) -> Optional[str]:
        """Get current character without advancing"""
        if self.position >= len(self.source):
            return None
        return self.source[self.position]
    
    def peek(self, offset: int = 1) -> Optional[str]:
        """Look ahead in source"""
        pos = self.position + offset
        if pos >= len(self.source):
            return None
        return self.source[pos]
    
    def advance(self) -> Optional[str]:
        """Move to next character"""
        if self.position >= len(self.source):
            return None
        
        char = self.source[self.position]
        self.position += 1
        
        if char == '\n':
            self.line += 1
            self.column = 1
        else:
            self.column += 1
        
        return char
    
    def skip_whitespace(self):
        """Skip whitespace except newlines"""
        while self.current_char() in ' \t\r':
            self.advance()
    
    def skip_comment(self):
        """Skip single-line comment"""
        # Skip '#' character
        self.advance()
        
        # Skip until end of line
        while self.current_char() and self.current_char() != '\n':
            self.advance()
    
    def read_string(self) -> str:
        """Read a string literal"""
        quote_char = self.current_char()  # ' or "
        self.advance()  # Skip opening quote
        
        value = []
        while True:
            char = self.current_char()
            
            if char is None:
                raise SyntaxError(f"Unclosed string at {self.line}:{self.column}")
            
            if char == quote_char:
                self.advance()  # Skip closing quote
                break
            
            if char == '\\':
                # Escape sequence
                self.advance()
                next_char = self.current_char()
                if next_char == 'n':
                    value.append('\n')
                elif next_char == 't':
                    value.append('\t')
                elif next_char == 'r':
                    value.append('\r')
                elif next_char == '\\':
                    value.append('\\')
                elif next_char == quote_char:
                    value.append(quote_char)
                else:
                    value.append(next_char)
                self.advance()
            else:
                value.append(char)
                self.advance()
        
        return ''.join(value)
    
    def read_number(self) -> float | int:
        """Read a number (integer or float)"""
        value = []
        has_dot = False
        
        while True:
            char = self.current_char()
            
            if char is None:
                break
            
            if char == '.':
                if has_dot:
                    break  # Second dot, stop
                has_dot = True
                value.append(char)
                self.advance()
            elif char.isdigit():
                value.append(char)
                self.advance()
            elif char == '_':
                # Allow underscores in numbers (e.g., 1_000_000)
                self.advance()
            else:
                break
        
        number_str = ''.join(value)
        return float(number_str) if has_dot else int(number_str)
    
    def read_identifier(self) -> str:
        """Read an identifier or keyword"""
        value = []
        
        while True:
            char = self.current_char()
            
            if char is None:
                break
            
            if char.isalnum() or char == '_':
                value.append(char)
                self.advance()
            else:
                break
        
        return ''.join(value)
    
    def tokenize(self) -> List[Token]:
        """Tokenize the entire source"""
        self.tokens = []
        
        while self.position < len(self.source):
            self.skip_whitespace()
            
            char = self.current_char()
            
            if char is None:
                break
            
            # Track position for token
            token_line = self.line
            token_column = self.column
            
            # Comments
            if char == '#':
                self.skip_comment()
                continue
            
            # Newlines
            if char == '\n':
                self.advance()
                # Skip multiple newlines (treat as one)
                continue
            
            # Strings
            if char in '"\'':
                value = self.read_string()
                self.tokens.append(Token(TokenType.STRING, value, token_line, token_column))
                continue
            
            # Numbers
            if char.isdigit():
                value = self.read_number()
                self.tokens.append(Token(TokenType.NUMBER, value, token_line, token_column))
                continue
            
            # Identifiers and keywords
            if char.isalpha() or char == '_':
                value = self.read_identifier()
                token_type = self.KEYWORDS.get(value, TokenType.IDENTIFIER)
                
                # Special handling for 'try' - context-dependent
                if value == 'try' and self.peek() == ':':
                    token_type = TokenType.TRY_KW
                
                self.tokens.append(Token(token_type, value, token_line, token_column))
                continue
            
            # Two-character operators
            if char == '=' and self.peek() == '=':
                self.advance()
                self.advance()
                self.tokens.append(Token(TokenType.EQ, '==', token_line, token_column))
                continue
            
            if char == '!' and self.peek() == '=':
                self.advance()
                self.advance()
                self.tokens.append(Token(TokenType.NEQ, '!=', token_line, token_column))
                continue
            
            if char == '>' and self.peek() == '=':
                self.advance()
                self.advance()
                self.tokens.append(Token(TokenType.GTE, '>=', token_line, token_column))
                continue
            
            if char == '<' and self.peek() == '=':
                self.advance()
                self.advance()
                self.tokens.append(Token(TokenType.LTE, '<=', token_line, token_column))
                continue
            
            if char == '-' and self.peek() == '>':
                self.advance()
                self.advance()
                self.tokens.append(Token(TokenType.ARROW, '->', token_line, token_column))
                continue
            
            # Single-character tokens
            single_char_tokens = {
                ':': TokenType.COLON,
                ',': TokenType.COMMA,
                '.': TokenType.DOT,
                '=': TokenType.EQUALS,
                '>': TokenType.GT,
                '<': TokenType.LT,
                '+': TokenType.PLUS,
                '-': TokenType.MINUS,
                '*': TokenType.STAR,
                '/': TokenType.SLASH,
                '%': TokenType.PERCENT,
                '{': TokenType.LBRACE,
                '}': TokenType.RBRACE,
                '(': TokenType.LPAREN,
                ')': TokenType.RPAREN,
                '[': TokenType.LBRACKET,
                ']': TokenType.RBRACKET,
            }
            
            if char in single_char_tokens:
                self.advance()
                self.tokens.append(Token(single_char_tokens[char], char, token_line, token_column))
                continue
            
            # Unknown character
            raise SyntaxError(f"Unexpected character '{char}' at {token_line}:{token_column}")
        
        # Add EOF token
        self.tokens.append(Token(TokenType.EOF, None, self.line, self.column))
        
        return self.tokens


# ============================================================================
# Testing & Debugging
# ============================================================================

def tokenize_file(filepath: str) -> List[Token]:
    """Tokenize a .orc file"""
    with open(filepath, 'r') as f:
        source = f.read()
    lexer = Lexer(source)
    return lexer.tokenize()


def print_tokens(tokens: List[Token]):
    """Pretty print tokens for debugging"""
    for token in tokens:
        print(f"{token.line:3d}:{token.column:3d} {token.type.name:15s} {repr(token.value)}")


if __name__ == "__main__":
    # Test the lexer
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
    
    print("=" * 60)
    print("LEXER TEST")
    print("=" * 60)
    print_tokens(tokens)
