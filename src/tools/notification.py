from typing import Any

import anyio
import mcp.types as types
from .registry import register_tool


spec = types.Tool(
    name="start-notification-stream",
    description=("Sends a stream of notifications with configurable count and interval"),
    inputSchema={
        "type": "object",
        "required": ["interval", "count", "caller"],
        "properties": {
            "interval": {
                "type": "number",
                "description": "Interval between notifications in seconds",
            },
            "count": {
                "type": "number",
                "description": "Number of notifications to send",
            },
            "caller": {
                "type": "string",
                "description": ("Identifier of the caller to include in notifications"),
            },
        },
    },
)


async def start(arguments: dict[str, Any], ctx: Any) -> list[types.ContentBlock]:
    interval = arguments.get("interval", 1.0)
    count = arguments.get("count", 5)
    caller = arguments.get("caller", "unknown")

    # Send the specified number of notifications with the given interval
    for i in range(count):
        await ctx.session.send_log_message(
            level="info",
            data=f"Notification {i + 1}/{count} from caller: {caller}",
            logger="notification_stream",
            related_request_id=ctx.request_id,
        )
        if i < count - 1:  # Don't wait after the last notification
            await anyio.sleep(interval)

    return [
        types.TextContent(
            type="text",
            text=(f"Sent {count} notifications with {interval}s interval for caller: {caller}"),
        )
    ]


def register_all() -> None:
    register_tool(spec, start)


