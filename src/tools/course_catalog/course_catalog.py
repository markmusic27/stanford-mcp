import asyncio
from typing import Any
from functools import lru_cache
from explorecourses import CourseConnection
import mcp.types as types

from tools.registry import register_tool

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
    if include_count is None:
        raise ValueError("Missing required argument 'include_department_count' (boolean).")
    if not isinstance(include_count, bool):
        raise TypeError(
            f"Invalid type for 'include_department_count': expected boolean, got {type(include_count).__name__}"
        )
    api = get_course_connection()

    
    schools = api.get_schools(ACADEMIC_YEAR)
    
    out = "Schools:"
    
    for school in schools:
        deps = school.departments
        out += f"\n - {school.name}"
        
        if include_count is True:
            plural = "s" if len(deps) > 1 else ""
            out += f" ({len(deps)} department{plural})"
    
    return [types.TextContent(type="text", text=out)]

list_departments_spec = types.Tool(
    name="list-departments",
    title="Departments in a School",
    description="List departments (name and code) within a given school. If school is omitted, tool returns all departments across schools.",
    inputSchema={
        "type": "object",
        "required": [],
        "properties": {
            "school": {
                "type": "string",
                "description": "Name of the school (schools can be fetched with list-schools tool). E.g. 'School of Engineering'",
            },
        },
    },
)

async def list_departments_handler(arguments: dict[str, Any], ctx: Any) -> list[types.ContentBlock]:
    school = arguments.get("school", "all")
    api = get_course_connection()
    formatted = ""
    
    schools = api.get_schools(ACADEMIC_YEAR)
    
    if school == "all" or school == "":
        for s in schools:
            deps = s.departments
            formatted+=f"\n\n{s.name}"
            for d in deps:
                formatted+=f"\n - {d.name} ({d.code})"
                
        return [types.TextContent(type="text", text=formatted)]
    
    for sch in schools:
        if (sch.name == school):
            deps = sch.departments
            formatted+=f"\n{sch.name}"
            for d in deps:
                formatted+=f"\n - {d.name} ({d.code})"
                
            return [types.TextContent(type="text", text=formatted)]
 
    
    raise ValueError(f"Unknown school: {school!r}")

def register_all() -> None:
    register_tool(list_schools_spec, list_schools_handler)
    register_tool(list_departments_spec, list_departments_handler)


# async def test():
#     res = await list_departments_handler({
#         "school": "School of Medicine"
#     }, "")
    
#     print(res)

# if __name__ == "__main__":
#     asyncio.run(test())
