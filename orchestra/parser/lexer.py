"""Lexer/Tokenizer for the Orchestra .orc DSL."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum, auto
from typing import Iterator, List


class TokenType(Enum):
    """Token types for the Orchestra DSL."""

    # Structural
    LBRACE = auto()
    RBRACE = auto()
    LBRACKET = auto()
    RBRACKET = auto()
    LPAREN = auto()
    RPAREN = auto()
    COLON = auto()
    COMMA = auto()
    DOT = auto()
    ARROW = auto()       # =>
    HASH = auto()        # # (comments handled by lexer, but needed for parsing)

    # Operators
    GT = auto()          # >
    LT = auto()          # <
    GTE = auto()         # >=
    LTE = auto()         # <=
    EQ = auto()          # ==
    NEQ = auto()         # !=
    BANG = auto()        # !

    # Keywords
    WORKFLOW = auto()
    STEP = auto()
    PARALLEL = auto()
    IF = auto()
    ELSE = auto()
    MATCH = auto()
    CASE = auto()
    DEFAULT = auto()
    GUARD = auto()
    BUDGET = auto()
    CIRCUIT_BREAKER = auto()
    QUALITY_GATE = auto()
    TRY = auto()
    RETRY = auto()
    CATCH = auto()
    FINALLY = auto()
    FOR = auto()
    EACH = auto()
    IN = auto()
    THEN = auto()
    ON_PARTIAL_FAILURE = auto()
    ON_FAILURE = auto()
    ON_ERROR = auto()
    ON_VIOLATION = auto()
    ON_OPEN = auto()
    ON_TIMEOUT = auto()
    ON_SOFT_TIMEOUT = auto()
    ON_HARD_TIMEOUT = auto()
    ON_BELOW_THRESHOLD = auto()
    ON_VALIDATION_FAILURE = auto()
    REQUIRE = auto()
    ASSERT = auto()
    VALIDATE_OUTPUT = auto()
    TIMEOUT = auto()
    AGENT = auto()
    MODEL = auto()
    TASK = auto()
    ACTION = auto()
    CASCADE = auto()
    BALANCE = auto()
    ROUTE = auto()
    SELECT = auto()
    TRITON_TERNARY = auto()
    BEST_FOR = auto()
    CHEAPEST_ABOVE = auto()
    VERSION = auto()
    OWNER = auto()
    PROTECTED_BY = auto()
    CRITICALITY = auto()
    PRIORITY = auto()
    NOTIFY = auto()
    ALERT = auto()
    LOG = auto()
    DATA = auto()
    STRATEGY = auto()
    POOL = auto()
    MAX_CONCURRENT = auto()
    FALLBACK = auto()
    LAST_RESORT = auto()
    DEGRADE_TO = auto()
    RETURN = auto()
    CONTINUE = auto()
    ABORT_WORKFLOW = auto()
    MARK_FOR_RETRY = auto()
    SKIP_TO = auto()
    SOFT = auto()
    HARD = auto()
    METRICS = auto()
    CANDIDATES = auto()
    WEIGHTS = auto()
    OPTIMIZE_FOR = auto()
    TIMEFRAME = auto()
    METRIC = auto()
    MAX_ATTEMPTS = auto()
    INITIAL_DELAY = auto()
    MAX_DELAY = auto()
    PER_TASK = auto()
    HOURLY_LIMIT = auto()
    ALERT_AT = auto()
    FAILURE_THRESHOLD = auto()
    HALF_OPEN_AFTER = auto()
    MIN_SUCCESS_RATE = auto()
    CONTEXT = auto()
    CAPTURE = auto()
    LEVEL = auto()
    MESSAGE = auto()
    NULL = auto()

    # Literals
    STRING = auto()
    NUMBER = auto()
    IDENTIFIER = auto()
    BOOL_TRUE = auto()
    BOOL_FALSE = auto()

    # Special
    NEWLINE = auto()
    EOF = auto()


# Map keyword strings to token types
KEYWORDS: dict[str, TokenType] = {
    "workflow": TokenType.WORKFLOW,
    "step": TokenType.STEP,
    "parallel": TokenType.PARALLEL,
    "if": TokenType.IF,
    "else": TokenType.ELSE,
    "match": TokenType.MATCH,
    "case": TokenType.CASE,
    "default": TokenType.DEFAULT,
    "guard": TokenType.GUARD,
    "budget": TokenType.BUDGET,
    "circuit_breaker": TokenType.CIRCUIT_BREAKER,
    "quality_gate": TokenType.QUALITY_GATE,
    "try": TokenType.TRY,
    "retry": TokenType.RETRY,
    "catch": TokenType.CATCH,
    "finally": TokenType.FINALLY,
    "for": TokenType.FOR,
    "each": TokenType.EACH,
    "in": TokenType.IN,
    "then": TokenType.THEN,
    "on_partial_failure": TokenType.ON_PARTIAL_FAILURE,
    "on_failure": TokenType.ON_FAILURE,
    "on_error": TokenType.ON_ERROR,
    "on_violation": TokenType.ON_VIOLATION,
    "on_open": TokenType.ON_OPEN,
    "on_timeout": TokenType.ON_TIMEOUT,
    "on_soft_timeout": TokenType.ON_SOFT_TIMEOUT,
    "on_hard_timeout": TokenType.ON_HARD_TIMEOUT,
    "on_below_threshold": TokenType.ON_BELOW_THRESHOLD,
    "on_validation_failure": TokenType.ON_VALIDATION_FAILURE,
    "require": TokenType.REQUIRE,
    "assert": TokenType.ASSERT,
    "validate_output": TokenType.VALIDATE_OUTPUT,
    "timeout": TokenType.TIMEOUT,
    "agent": TokenType.AGENT,
    "model": TokenType.MODEL,
    "task": TokenType.TASK,
    "action": TokenType.ACTION,
    "cascade": TokenType.CASCADE,
    "balance": TokenType.BALANCE,
    "route": TokenType.ROUTE,
    "select": TokenType.SELECT,
    "triton_ternary": TokenType.TRITON_TERNARY,
    "best_for": TokenType.BEST_FOR,
    "cheapest_above": TokenType.CHEAPEST_ABOVE,
    "version": TokenType.VERSION,
    "owner": TokenType.OWNER,
    "protected_by": TokenType.PROTECTED_BY,
    "criticality": TokenType.CRITICALITY,
    "priority": TokenType.PRIORITY,
    "notify": TokenType.NOTIFY,
    "alert": TokenType.ALERT,
    "log": TokenType.LOG,
    "data": TokenType.DATA,
    "strategy": TokenType.STRATEGY,
    "pool": TokenType.POOL,
    "max_concurrent": TokenType.MAX_CONCURRENT,
    "fallback": TokenType.FALLBACK,
    "last_resort": TokenType.LAST_RESORT,
    "degrade_to": TokenType.DEGRADE_TO,
    "return": TokenType.RETURN,
    "continue": TokenType.CONTINUE,
    "abort_workflow": TokenType.ABORT_WORKFLOW,
    "mark_for_retry": TokenType.MARK_FOR_RETRY,
    "soft": TokenType.SOFT,
    "hard": TokenType.HARD,
    "metrics": TokenType.METRICS,
    "candidates": TokenType.CANDIDATES,
    "weights": TokenType.WEIGHTS,
    "optimize_for": TokenType.OPTIMIZE_FOR,
    "timeframe": TokenType.TIMEFRAME,
    "metric": TokenType.METRIC,
    "max_attempts": TokenType.MAX_ATTEMPTS,
    "initial_delay": TokenType.INITIAL_DELAY,
    "max_delay": TokenType.MAX_DELAY,
    "per_task": TokenType.PER_TASK,
    "hourly_limit": TokenType.HOURLY_LIMIT,
    "alert_at": TokenType.ALERT_AT,
    "failure_threshold": TokenType.FAILURE_THRESHOLD,
    "half_open_after": TokenType.HALF_OPEN_AFTER,
    "min_success_rate": TokenType.MIN_SUCCESS_RATE,
    "context": TokenType.CONTEXT,
    "capture": TokenType.CAPTURE,
    "level": TokenType.LEVEL,
    "message": TokenType.MESSAGE,
    "null": TokenType.NULL,
    "true": TokenType.BOOL_TRUE,
    "false": TokenType.BOOL_FALSE,
}


@dataclass(frozen=True)
class Token:
    """A single lexical token."""

    type: TokenType
    value: str
    line: int
    column: int

    def __repr__(self) -> str:
        if self.type in (TokenType.STRING, TokenType.NUMBER, TokenType.IDENTIFIER):
            return f"Token({self.type.name}, {self.value!r}, L{self.line}:{self.column})"
        return f"Token({self.type.name}, L{self.line}:{self.column})"


class LexerError(Exception):
    """Raised when the lexer encounters invalid input."""

    def __init__(self, message: str, line: int, column: int):
        self.line = line
        self.column = column
        super().__init__(f"Lexer error at line {line}, column {column}: {message}")


class Lexer:
    """Tokenizer for Orchestra .orc files.

    Converts raw source text into a stream of Token objects.
    Handles comments (# ...), strings, numbers, identifiers/keywords,
    and all structural/operator characters.
    """

    def __init__(self, source: str):
        self.source = source
        self.pos = 0
        self.line = 1
        self.column = 1
        self._tokens: list[Token] | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def tokenize(self) -> List[Token]:
        """Tokenize the entire source and return a list of tokens.

        The list always ends with an EOF token.
        """
        if self._tokens is not None:
            return list(self._tokens)

        tokens: list[Token] = []
        for tok in self._iter_tokens():
            tokens.append(tok)
        tokens.append(Token(TokenType.EOF, "", self.line, self.column))
        self._tokens = tokens
        return list(tokens)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _peek(self) -> str:
        if self.pos >= len(self.source):
            return ""
        return self.source[self.pos]

    def _peek_next(self) -> str:
        nxt = self.pos + 1
        if nxt >= len(self.source):
            return ""
        return self.source[nxt]

    def _advance(self) -> str:
        ch = self.source[self.pos]
        self.pos += 1
        if ch == "\n":
            self.line += 1
            self.column = 1
        else:
            self.column += 1
        return ch

    def _skip_whitespace(self):
        """Skip spaces/tabs (NOT newlines — those are significant)."""
        while self.pos < len(self.source) and self.source[self.pos] in (" ", "\t", "\r"):
            self._advance()

    def _skip_comment(self):
        """Skip from # to end of line."""
        while self.pos < len(self.source) and self.source[self.pos] != "\n":
            self._advance()

    def _read_string(self) -> str:
        """Read a quoted string (double-quote). Supports basic escapes."""
        quote = self._advance()  # consume opening quote
        buf: list[str] = []
        while self.pos < len(self.source):
            ch = self._advance()
            if ch == "\\":
                nxt = self._advance() if self.pos < len(self.source) else ""
                escape_map = {"n": "\n", "t": "\t", "\\": "\\", '"': '"'}
                buf.append(escape_map.get(nxt, nxt))
            elif ch == quote:
                return "".join(buf)
            else:
                buf.append(ch)
        raise LexerError("Unterminated string", self.line, self.column)

    def _read_number(self) -> str:
        """Read an integer or decimal number."""
        start = self.pos
        has_dot = False
        while self.pos < len(self.source):
            ch = self.source[self.pos]
            if ch == "." and not has_dot:
                has_dot = True
                self._advance()
            elif ch.isdigit():
                self._advance()
            else:
                break
        return self.source[start : self.pos]

    def _read_identifier(self) -> str:
        """Read an identifier: [a-zA-Z_][a-zA-Z0-9_]*"""
        start = self.pos
        while self.pos < len(self.source):
            ch = self.source[self.pos]
            if ch.isalnum() or ch == "_":
                self._advance()
            else:
                break
        return self.source[start : self.pos]

    def _make(self, ttype: TokenType, value: str, line: int, col: int) -> Token:
        return Token(ttype, value, line, col)

    # ------------------------------------------------------------------
    # Main iteration
    # ------------------------------------------------------------------

    def _iter_tokens(self) -> Iterator[Token]:
        """Yield tokens one-at-a-time."""
        while self.pos < len(self.source):
            self._skip_whitespace()
            if self.pos >= len(self.source):
                break

            line, col = self.line, self.column
            ch = self._peek()

            # Newlines
            if ch == "\n":
                self._advance()
                yield self._make(TokenType.NEWLINE, "\\n", line, col)
                continue

            # Comments
            if ch == "#":
                self._skip_comment()
                continue

            # Markdown-style headers (## ...) — treat entire line as comment
            if ch == "#":
                self._skip_comment()
                continue

            # Strings
            if ch == '"':
                val = self._read_string()
                yield self._make(TokenType.STRING, val, line, col)
                continue

            # Numbers
            if ch.isdigit():
                val = self._read_number()
                yield self._make(TokenType.NUMBER, val, line, col)
                continue

            # Identifiers / keywords
            if ch.isalpha() or ch == "_":
                val = self._read_identifier()
                ttype = KEYWORDS.get(val, TokenType.IDENTIFIER)
                yield self._make(ttype, val, line, col)
                continue

            # Two-character operators
            nxt = self._peek_next()
            if ch == "=" and nxt == ">":
                self._advance(); self._advance()
                yield self._make(TokenType.ARROW, "=>", line, col)
                continue
            if ch == ">" and nxt == "=":
                self._advance(); self._advance()
                yield self._make(TokenType.GTE, ">=", line, col)
                continue
            if ch == "<" and nxt == "=":
                self._advance(); self._advance()
                yield self._make(TokenType.LTE, "<=", line, col)
                continue
            if ch == "!" and nxt == "=":
                self._advance(); self._advance()
                yield self._make(TokenType.NEQ, "!=", line, col)
                continue
            if ch == "=" and nxt == "=":
                self._advance(); self._advance()
                yield self._make(TokenType.EQ, "==", line, col)
                continue

            # Single-character tokens
            single_map = {
                "{": TokenType.LBRACE,
                "}": TokenType.RBRACE,
                "[": TokenType.LBRACKET,
                "]": TokenType.RBRACKET,
                "(": TokenType.LPAREN,
                ")": TokenType.RPAREN,
                ":": TokenType.COLON,
                ",": TokenType.COMMA,
                ".": TokenType.DOT,
                ">": TokenType.GT,
                "<": TokenType.LT,
                "!": TokenType.BANG,
            }
            if ch in single_map:
                self._advance()
                yield self._make(single_map[ch], ch, line, col)
                continue

            # Dollar-sign interpolation ${...} — treat as identifier
            if ch == "$" and nxt == "{":
                self._advance()  # $
                self._advance()  # {
                buf: list[str] = []
                while self.pos < len(self.source) and self._peek() != "}":
                    buf.append(self._advance())
                if self.pos < len(self.source):
                    self._advance()  # closing }
                yield self._make(TokenType.IDENTIFIER, "${" + "".join(buf) + "}", line, col)
                continue

            raise LexerError(f"Unexpected character: {ch!r}", line, col)
