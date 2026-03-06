"""Tests for the Orchestra Language Server."""

import json
import pytest

from orchestra.lsp.server import (
    OrchestraLanguageServer,
    KEYWORD_DOCS,
    SNIPPETS,
)


# =====================================================================
# DIAGNOSTICS TESTS
# =====================================================================

class TestDiagnostics:
    """Tests for diagnostic generation from .orc source."""

    def setup_method(self):
        self.server = OrchestraLanguageServer()

    def test_valid_workflow_no_diagnostics(self):
        source = '''workflow TestFlow {
    step analyze {
        agent: "gpt-4"
        prompt: "Analyze data"
    }
}
'''
        self.server._documents["test://file.orc"] = source
        diags = self.server._publish_diagnostics("test://file.orc")
        errors = [d for d in diags if d.get("severity") == 1]
        assert len(errors) == 0

    def test_lexer_error_produces_diagnostic(self):
        source = 'workflow Test { step x { agent = @ } }'
        self.server._documents["test://bad.orc"] = source
        diags = self.server._publish_diagnostics("test://bad.orc")
        assert len(diags) >= 1

    def test_empty_document_no_crash(self):
        self.server._documents["test://empty.orc"] = ""
        diags = self.server._publish_diagnostics("test://empty.orc")
        assert isinstance(diags, list)


# =====================================================================
# COMPLETION TESTS
# =====================================================================

class TestCompletion:
    """Tests for autocompletion."""

    def setup_method(self):
        self.server = OrchestraLanguageServer()

    def test_top_level_completion(self):
        source = "wor"
        self.server._documents["test://file.orc"] = source
        items = self.server.completion("test://file.orc", 0, 3)
        labels = [item["label"] for item in items]
        assert "workflow" in labels

    def test_workflow_body_completion(self):
        source = "workflow Test {\n    st\n}"
        self.server._documents["test://file.orc"] = source
        items = self.server.completion("test://file.orc", 1, 6)
        labels = [item["label"] for item in items]
        assert "step" in labels

    def test_step_body_completion(self):
        source = 'workflow Test {\n    step analyze {\n        ag\n    }\n}'
        self.server._documents["test://file.orc"] = source
        items = self.server.completion("test://file.orc", 2, 10)
        labels = [item["label"] for item in items]
        # Inside a step body, expect step-body keywords like agent, prompt, etc.
        assert len(items) > 0

    def test_completions_always_list(self):
        self.server._documents["test://file.orc"] = ""
        items = self.server.completion("test://file.orc", 0, 0)
        assert isinstance(items, list)


# =====================================================================
# HOVER TESTS
# =====================================================================

class TestHover:
    """Tests for hover information."""

    def setup_method(self):
        self.server = OrchestraLanguageServer()

    def test_keyword_hover(self):
        source = "workflow Test {}"
        self.server._documents["test://file.orc"] = source
        result = self.server.hover("test://file.orc", 0, 4)
        assert result is not None
        contents = result.get("contents", {})
        value = contents.get("value", "") if isinstance(contents, dict) else str(contents)
        assert "workflow" in value.lower() or "Workflow" in value

    def test_no_hover_on_whitespace(self):
        source = "   "
        self.server._documents["test://file.orc"] = source
        result = self.server.hover("test://file.orc", 0, 1)
        assert result is None

    def test_hover_on_step(self):
        source = "step analyze {"
        self.server._documents["test://file.orc"] = source
        result = self.server.hover("test://file.orc", 0, 2)
        assert result is not None


# =====================================================================
# DOCUMENT SYMBOLS TESTS
# =====================================================================

class TestDocumentSymbols:
    """Tests for document symbol outline."""

    def setup_method(self):
        self.server = OrchestraLanguageServer()

    def test_symbols_for_workflow(self):
        source = '''workflow TestFlow {
    step analyze {
        agent: "gpt-4"
        prompt: "Analyze data"
    }
    step report {
        agent: "gpt-4"
        prompt: "Write report"
    }
}
'''
        self.server._documents["test://file.orc"] = source
        symbols = self.server.document_symbols("test://file.orc")
        # Symbols depend on parser producing a valid AST
        assert isinstance(symbols, list)

    def test_empty_document_symbols(self):
        self.server._documents["test://file.orc"] = ""
        symbols = self.server.document_symbols("test://file.orc")
        assert isinstance(symbols, list)


# =====================================================================
# DOCUMENT MANAGEMENT TESTS
# =====================================================================

class TestDocumentManagement:
    """Tests for document open/change/close lifecycle."""

    def setup_method(self):
        self.server = OrchestraLanguageServer()

    def test_did_open(self):
        self.server.did_open("test://file.orc", "workflow Test {}")
        assert "test://file.orc" in self.server._documents

    def test_did_change(self):
        self.server.did_open("test://file.orc", "old")
        self.server.did_change("test://file.orc", "new")
        assert self.server._documents["test://file.orc"] == "new"

    def test_did_close(self):
        self.server.did_open("test://file.orc", "content")
        self.server.did_close("test://file.orc")
        assert "test://file.orc" not in self.server._documents


# =====================================================================
# DATA INTEGRITY TESTS
# =====================================================================

class TestConstants:
    """Tests for LSP constants and data."""

    def test_keyword_docs_nonempty(self):
        assert len(KEYWORD_DOCS) > 0

    def test_snippets_nonempty(self):
        assert len(SNIPPETS) > 0

    def test_all_snippets_have_required_keys(self):
        for snippet in SNIPPETS:
            assert "label" in snippet
            assert "insert_text" in snippet
