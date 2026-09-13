"""Tests for androguard.agent.protocol — ToolRegistry, _annotation_schema, jsonable."""

from __future__ import annotations

import pytest
from typing import Dict, List, Optional, Union

from androguard.agent.protocol import (
    AgentError,
    ToolRegistry,
    ToolSpec,
    _annotation_schema,
    jsonable,
    tool_from_callable,
)


# ---------------------------------------------------------------------------
# _annotation_schema
# ---------------------------------------------------------------------------

class TestAnnotationSchema:
    def test_empty(self):
        import inspect
        assert _annotation_schema(inspect.Parameter.empty) == {}

    def test_str(self):
        assert _annotation_schema(str) == {"type": "string"}

    def test_int(self):
        assert _annotation_schema(int) == {"type": "integer"}

    def test_float(self):
        assert _annotation_schema(float) == {"type": "number"}

    def test_bool(self):
        assert _annotation_schema(bool) == {"type": "boolean"}

    def test_bytes(self):
        schema = _annotation_schema(bytes)
        assert schema["type"] == "string"

    def test_dict(self):
        assert _annotation_schema(dict) == {"type": "object"}

    def test_list(self):
        assert _annotation_schema(list) == {"type": "array"}

    def test_none_type(self):
        assert _annotation_schema(None) == {"type": "null"}
        assert _annotation_schema(type(None)) == {"type": "null"}

    def test_list_of_str(self):
        schema = _annotation_schema(List[str])
        assert schema["type"] == "array"
        assert schema["items"] == {"type": "string"}

    def test_dict_str_int(self):
        schema = _annotation_schema(Dict[str, int])
        assert schema["type"] == "object"
        assert schema["additionalProperties"] == {"type": "integer"}

    def test_optional_str(self):
        schema = _annotation_schema(Optional[str])
        assert schema["type"] == "string"
        assert schema.get("nullable") is True

    def test_union_str_int(self):
        schema = _annotation_schema(Union[str, int])
        assert "anyOf" in schema
        types = {s["type"] for s in schema["anyOf"]}
        assert types == {"string", "integer"}


# ---------------------------------------------------------------------------
# jsonable
# ---------------------------------------------------------------------------

class TestJsonable:
    def test_primitives(self):
        assert jsonable(1) == 1
        assert jsonable("x") == "x"
        assert jsonable(True) is True
        assert jsonable(None) is None

    def test_bytes(self):
        result = jsonable(b"\xde\xad")
        assert result == {"bytes_hex": "dead"}

    def test_set_sorted(self):
        result = jsonable({3, 1, 2})
        assert result == [1, 2, 3]

    def test_frozenset(self):
        result = jsonable(frozenset(["b", "a"]))
        assert result == ["a", "b"]

    def test_generator(self):
        result = jsonable(x * 2 for x in range(3))
        assert result == [0, 2, 4]

    def test_mapping(self):
        result = jsonable({"b": 2, "a": 1})
        assert result == {"b": 2, "a": 1}

    def test_nested(self):
        result = jsonable({"items": {3, 1, 2}})
        assert result == {"items": [1, 2, 3]}

    def test_non_serializable_fallback(self):
        class Opaque:
            def __str__(self):
                return "opaque"
        result = jsonable(Opaque())
        assert result == "opaque"


# ---------------------------------------------------------------------------
# tool_from_callable — type hints resolve correctly (PEP 563 strings)
# ---------------------------------------------------------------------------

class TestToolFromCallable:
    def test_no_params(self):
        def fn() -> dict:
            """Do nothing."""
        spec = tool_from_callable("fn", fn)
        assert spec.name == "fn"
        assert spec.input_schema["properties"] == {}
        assert spec.input_schema["required"] == []

    def test_str_param(self):
        def fn(name: str) -> dict:
            """Greet."""
        spec = tool_from_callable("fn", fn)
        assert spec.input_schema["properties"]["name"] == {"type": "string"}
        assert "name" in spec.input_schema["required"]

    def test_optional_param(self):
        def fn(limit: Optional[int] = None) -> dict:
            """Limit."""
        spec = tool_from_callable("fn", fn)
        schema = spec.input_schema["properties"]["limit"]
        assert schema["type"] == "integer"
        assert schema.get("nullable") is True
        assert schema["default"] is None
        assert "limit" not in spec.input_schema["required"]

    def test_var_keyword_allows_additional(self):
        def fn(action: str, **kwargs) -> dict:
            """Action."""
        spec = tool_from_callable("fn", fn)
        # **kwargs → additionalProperties must allow extras
        assert spec.input_schema["additionalProperties"] is True
        assert "action" in spec.input_schema["properties"]
        assert "kwargs" not in spec.input_schema["properties"]

    def test_description_from_docstring(self):
        def fn() -> dict:
            """First line summary.

            More detail.
            """
        spec = tool_from_callable("fn", fn)
        assert spec.description.startswith("First line summary.")
        assert "More detail." in spec.description


# ---------------------------------------------------------------------------
# ToolRegistry
# ---------------------------------------------------------------------------

class TestToolRegistry:
    def _make(self):
        reg = ToolRegistry()
        def greet(name: str) -> dict:
            """Say hello."""
            return {"hello": name}
        reg.add("greet", greet)
        return reg

    def test_list_contains_tool(self):
        reg = self._make()
        names = [t["name"] for t in reg.list()]
        assert "greet" in names

    def test_list_sorted(self):
        reg = ToolRegistry()
        reg.add("b", lambda: None)
        reg.add("a", lambda: None)
        names = [t["name"] for t in reg.list()]
        assert names == ["a", "b"]

    def test_call_success(self):
        reg = self._make()
        result = reg.call("greet", {"name": "world"})
        assert result == {"hello": "world"}

    def test_call_unknown_tool(self):
        reg = self._make()
        with pytest.raises(AgentError) as exc_info:
            reg.call("no_such_tool", {})
        assert exc_info.value.code == "tool_not_found"

    def test_call_invalid_arguments(self):
        reg = self._make()
        with pytest.raises(AgentError) as exc_info:
            reg.call("greet", {})  # missing required 'name'
        assert exc_info.value.code == "invalid_arguments"

    def test_call_tool_raises(self):
        reg = ToolRegistry()
        def bad() -> dict:
            raise ValueError("boom")
        reg.add("bad", bad)
        with pytest.raises(AgentError) as exc_info:
            reg.call("bad", {})
        assert exc_info.value.code == "tool_failed"

    def test_add_object(self):
        class Obj:
            def public(self) -> dict:
                """Public."""
                return {}
            def _private(self):
                pass
        reg = ToolRegistry()
        reg.add_object(Obj(), prefix="obj")
        names = [t["name"] for t in reg.list()]
        assert "obj.public" in names
        assert "obj._private" not in names

    def test_private_name_rejected(self):
        reg = ToolRegistry()
        with pytest.raises(ValueError):
            reg.add("_hidden", lambda: None)
