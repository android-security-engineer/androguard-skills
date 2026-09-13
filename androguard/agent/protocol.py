"""Common tool discovery, invocation, and JSON conversion primitives.

This is intentionally MCP-shaped rather than tied to a particular transport.
The stdio server in :mod:`androguard.agent.server` uses the same primitives as
an embedding application, HTTP adapter, or an MCP server implementation.
"""

from __future__ import annotations

import inspect
import json
import typing
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, Iterable, Mapping, Union, get_args, get_origin


class AgentError(Exception):
    """An expected, structured error returned to an Agent caller."""

    def __init__(self, message: str, code: str = "agent_error"):
        super().__init__(message)
        self.code = code
        self.message = message


def jsonable(value: Any) -> Any:
    """Convert AndroGuard values into deterministic JSON-compatible values."""

    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (bytes, bytearray)):
        return {"bytes_hex": bytes(value).hex()}
    if isinstance(value, (set, frozenset)):
        return [jsonable(item) for item in sorted(value, key=str)]
    if isinstance(value, Mapping):
        return {str(key): jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsonable(item) for item in value]
    if isinstance(value, (filter, map, zip, range)):
        return [jsonable(item) for item in value]
    if hasattr(value, "__next__"):
        return [jsonable(item) for item in value]
    try:
        json.dumps(value)
        return value
    except (TypeError, ValueError):
        return str(value)


def _annotation_schema(annotation: Any) -> Dict[str, Any]:
    """Translate the useful subset of Python annotations to JSON Schema."""

    if annotation is inspect.Parameter.empty or annotation is Any:
        return {}
    if annotation is None or annotation is type(None):
        return {"type": "null"}
    if annotation in (str, int, float, bool):
        return {"type": {str: "string", int: "integer", float: "number", bool: "boolean"}[annotation]}
    if annotation is bytes or annotation is bytearray:
        return {"type": "string", "description": "hex-encoded bytes"}
    if annotation is dict:
        return {"type": "object"}
    if annotation is list:
        return {"type": "array"}

    origin = get_origin(annotation)
    args = get_args(annotation)
    if origin in (list, tuple, set, frozenset, Iterable):
        item_schema = _annotation_schema(args[0]) if args else {}
        return {"type": "array", "items": item_schema}
    if origin in (dict, Mapping):
        return {"type": "object", "additionalProperties": _annotation_schema(args[1]) if len(args) > 1 else {}}
    if origin is Union:
        non_null = [arg for arg in args if arg is not type(None)]
        if len(non_null) == 1 and len(non_null) != len(args):
            schema = _annotation_schema(non_null[0])
            schema["nullable"] = True
            return schema
        return {"anyOf": [_annotation_schema(arg) for arg in args]}
    if isinstance(annotation, type) and issubclass(annotation, Enum):
        return {"type": "string", "enum": [item.value for item in annotation]}
    return {}


@dataclass(frozen=True)
class ToolSpec:
    """A discoverable Agent tool and its JSON Schema input contract."""

    name: str
    description: str
    input_schema: Dict[str, Any]
    handler: Callable[..., Any]

    def public(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
        }


def tool_from_callable(name: str, handler: Callable[..., Any], description: str = "") -> ToolSpec:
    """Build a tool description from a normal Python callable."""

    signature = inspect.signature(handler)
    # get_type_hints resolves PEP-563 stringified annotations (from __future__ import annotations)
    try:
        hints = typing.get_type_hints(handler)
    except Exception:
        hints = {}

    properties: Dict[str, Any] = {}
    required = []
    has_var_keyword = False
    for parameter in signature.parameters.values():
        if parameter.kind is parameter.VAR_POSITIONAL:
            continue
        if parameter.kind is parameter.VAR_KEYWORD:
            has_var_keyword = True
            continue
        annotation = hints.get(parameter.name, parameter.annotation)
        schema = _annotation_schema(annotation)
        if parameter.default is not parameter.empty:
            schema["default"] = jsonable(parameter.default)
        properties[parameter.name] = schema
        if parameter.default is parameter.empty:
            required.append(parameter.name)

    doc = inspect.getdoc(handler) or description or f"Call {name}."
    return ToolSpec(
        name=name,
        description=doc,
        input_schema={
            "type": "object",
            "properties": properties,
            "required": required,
            # allow extra kwargs when the handler accepts **kwargs
            "additionalProperties": has_var_keyword,
        },
        handler=handler,
    )


class ToolRegistry:
    """Registry used by both the headless API and MCP transports."""

    def __init__(self):
        self._tools: Dict[str, ToolSpec] = {}

    def add(self, name: str, handler: Callable[..., Any], description: str = "") -> ToolSpec:
        if not name or name.startswith("_"):
            raise ValueError("Tool names must be non-empty and public")
        spec = tool_from_callable(name, handler, description)
        self._tools[name] = spec
        return spec

    def add_object(self, obj: Any, prefix: str = "") -> None:
        for name, handler in inspect.getmembers(obj, predicate=callable):
            if name.startswith("_"):
                continue
            tool_name = f"{prefix}.{name}" if prefix else name
            self.add(tool_name, handler)

    def list(self) -> list[Dict[str, Any]]:
        return [self._tools[name].public() for name in sorted(self._tools)]

    def get(self, name: str) -> ToolSpec:
        try:
            return self._tools[name]
        except KeyError as exc:
            raise AgentError(f"Unknown tool: {name}", "tool_not_found") from exc

    def call(self, name: str, arguments: Mapping[str, Any] | None = None) -> Any:
        spec = self.get(name)
        arguments = dict(arguments or {})
        try:
            bound = inspect.signature(spec.handler).bind(**arguments)
        except TypeError as exc:
            raise AgentError(f"Invalid arguments for {name}: {exc}", "invalid_arguments") from exc
        try:
            return jsonable(spec.handler(*bound.args, **bound.kwargs))
        except AgentError:
            raise
        except Exception as exc:
            raise AgentError(f"Tool {name} failed: {exc}", "tool_failed") from exc
