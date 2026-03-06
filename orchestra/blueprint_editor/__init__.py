"""Orchestra Visual Blueprint Editor.

Provides a web-based drag-and-drop workflow designer that generates
valid .orc syntax. The editor serves a single-page application with
a visual workflow canvas and bidirectional .orc code synchronization.

Features:
- Drag-and-drop workflow building blocks (steps, gates, routing)
- Live .orc syntax preview with two-way sync
- Export to .orc files
- Import existing .orc files
- Visual representation of parallel blocks, conditional branches, and cascades
"""

from orchestra.blueprint_editor.editor import BlueprintEditor

__all__ = ["BlueprintEditor"]
