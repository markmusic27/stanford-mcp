from typing import Any, Awaitable, Callable, Dict, List

import mcp.types as types

ToolHandler = Callable[[Dict[str, Any], Any], Awaitable[List[types.ContentBlock]]]

_TOOL_SPECS: Dict[str, types.Tool] = {}
_TOOL_HANDLERS: Dict[str, ToolHandler] = {}


def register_tool(spec: types.Tool, handler: ToolHandler) -> None:
    _TOOL_SPECS[spec.name] = spec
    _TOOL_HANDLERS[spec.name] = handler


def list_all_tools() -> List[types.Tool]:
    return list(_TOOL_SPECS.values())


async def dispatch(name: str, arguments: Dict[str, Any], ctx: Any) -> List[types.ContentBlock]:
    if name not in _TOOL_HANDLERS:
        raise ValueError(f"Unknown tool: {name}")
    handler = _TOOL_HANDLERS[name]
    return await handler(arguments, ctx)


