import asyncio
from typing import Any
from functools import lru_cache
from explorecourses import CourseConnection
import mcp.types as types

from tools.registry import register_tool
# from tools.registry import register_tool 

ACADEMIC_YEAR = "2025-2026"


# Lazy, module-level singleton for ExploreCourses CourseConnection
@lru_cache(maxsize=1)
def get_course_connection() -> CourseConnection:
    """Return a process-wide CourseConnection instance.

    This is created on first use and cached for the lifetime of the process.
    The import is done lazily to avoid import-time failures when optional
    dependencies are missing in environments like docs or lint-only runs.
    """

    return CourseConnection()


def reset_course_connection_cache() -> None:
    """Clear the cached CourseConnection (useful in tests)."""
    get_course_connection.cache_clear()

# List schools
list_schools_spec = types.Tool(
    name="list-schools",
    title="Schools at Stanford",
    description="Return all schools available in ExploreCourses, optionally with department counts.",
    inputSchema={
        "type": "object",
        "required": ["include_department_count"],
        "properties": {
            "include_department_count": {
                "type": "boolean",
                "description": "If true, the tool will return the number of department per school.",
            },
        },
    },
)

async def list_schools_handler(arguments: dict[str, Any], ctx: Any) -> list[types.ContentBlock]:
    include_count = arguments.get("include_department_count")
    api = get_course_connection()
    
    schools = api.get_schools(ACADEMIC_YEAR)
    
    out = "Schools:"
    
    for school in schools:
        deps = school.departments
        out += f"\n - {school.name}"
        
        if include_count:
            plural = "s" if len(deps) > 1 else ""
            out += f" ({len(deps)} department{plural})"
    
    return [types.TextContent(type="text", text=out)]
    
def register_all() -> None:
    register_tool(list_schools_spec, list_schools_handler)

# async def test():
#     res = await list_schools_handler({
#         "include_department_count": True
#     }, "")
    
#     print(res)

# if __name__ == "__main__":
#     asyncio.run(test())
