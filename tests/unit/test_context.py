"""Tests for Context module."""

from orchestra.core.context import Context


class TestContext:
    """Test cases for Context class."""

    def test_context_creation(self):
        """Test basic context creation."""
        context = Context()
        assert context.variables == {}
        assert context.execution_id is not None
        assert context.start_time is not None

    def test_context_set_get(self):
        """Test setting and getting variables."""
        context = Context()

        context.set("key1", "value1")
        assert context.get("key1") == "value1"

        context.set("key2", 42)
        assert context.get("key2") == 42

    def test_context_get_default(self):
        """Test getting variable with default value."""
        context = Context()

        assert context.get("nonexistent") is None
        assert context.get("nonexistent", "default") == "default"

    def test_context_has(self):
        """Test checking variable existence."""
        context = Context()

        assert not context.has("key1")

        context.set("key1", "value1")
        assert context.has("key1")

    def test_context_update(self):
        """Test updating multiple variables."""
        context = Context()

        updates = {"key1": "value1", "key2": "value2", "key3": 42}
        context.update(updates)

        assert context.get("key1") == "value1"
        assert context.get("key2") == "value2"
        assert context.get("key3") == 42

    def test_context_clear(self):
        """Test clearing all variables."""
        context = Context()

        context.set("key1", "value1")
        context.set("key2", "value2")
        assert len(context.variables) == 2

        context.clear()
        assert len(context.variables) == 0

    def test_context_method_chaining(self):
        """Test method chaining for context."""
        context = Context()

        result = context.set("key1", "value1").set("key2", "value2")
        assert result == context
        assert context.get("key1") == "value1"
        assert context.get("key2") == "value2"

    def test_context_execution_id(self):
        """Test execution ID generation."""
        context1 = Context()
        context2 = Context()

        assert context1.execution_id is not None
        assert context2.execution_id is not None
        # IDs might be the same if created in same second
        assert "exec_" in context1.execution_id

    def test_context_custom_execution_id(self):
        """Test context with custom execution ID."""
        context = Context(execution_id="custom_id")
        assert context.execution_id == "custom_id"

    def test_context_repr(self):
        """Test context string representation."""
        context = Context()
        context.set("key1", "value1")

        repr_str = repr(context)
        assert "Context" in repr_str
        assert "variables=1" in repr_str
