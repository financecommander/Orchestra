"""Orchestra Language Server Protocol (LSP) implementation.

Provides IDE support for .orc files:
- Syntax highlighting via semantic tokens
- Real-time diagnostics (errors and warnings)
- Autocompletion for keywords, agents, and workflow constructs
- Hover information for keywords and constructs
- Go-to-definition for workflow and step references
"""

from orchestra.lsp.server import OrchestraLanguageServer

__all__ = ["OrchestraLanguageServer"]
