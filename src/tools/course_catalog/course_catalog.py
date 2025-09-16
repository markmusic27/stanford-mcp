import asyncio
from typing import Any
from functools import lru_cache
from explorecourses import CourseConnection
import mcp.types as types
import explorecourses.filters as filters

from tools.registry import register_tool
from .formatting import format_course_no_sections, format_course_sections
from types import SimpleNamespace

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
                "description": "Name of the school (schools can be fetched with list-schools tool). E.g. 'School of Engineering'.",
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

get_course_spec = types.Tool(
    name="get-course",
    title="Course Details",
    description="Fetch a full course record by course_id, including title, description, GERS, attributes, tags, repeatability, and exam flags. (for section/schedules, use get-schedule tool)",
    inputSchema={
        "type": "object",
        "required": ["course_id"],
        "properties": {
            "course_id": {
                "type": "number",
                "description": "Identifier of the course (e.g. 105645, NOT CS 106B). Use search-courses to find valid IDs.",
            },
        },
    },
)

async def get_course_handler(arguments: dict[str, Any], ctx: Any) -> list[types.ContentBlock]:
    course_id = arguments.get("course_id")
    api = get_course_connection()
    
    # TODO: ADD FILTER
    fs = [filters.AUTUMN]
    candidates = api.get_courses_by_query(course_id, *fs, year=ACADEMIC_YEAR)
    course = None
    
    # Validate course_id and extract course
    for c in candidates:
        if (c.course_id == course_id):
            course = c
    
    if course == None:
        raise ValueError(f"No matches found with course_id '{course_id}'")
    
    return [types.TextContent(type="text", text=format_course_no_sections(course))]

get_schedule_spec = types.Tool(
    name="get-schedule",
    title="Course Sections and Schedules",
    description="Fetch sections and schedules for a course by course_id. Optionally filter by term.",
    inputSchema={
        "type": "object",
        "required": ["course_id"],
        "properties": {
            "course_id": {
                "type": "number",
                "description": "Identifier of the course (e.g. 105645, NOT CS 106B). Use search-courses to find valid IDs.",
            },
            "term": {
                "type": "string",
                "description": "Optional term to filter sections: Autumn | Winter | Spring | Summer. If omitted/empty, returns all terms.",
            },
        },
    },
)

async def get_schedule_handler(arguments: dict[str, Any], ctx: Any) -> list[types.ContentBlock]:
    course_id = arguments.get("course_id")
    api = get_course_connection()

    term_arg = (arguments.get("term") or "").strip().lower()
    term_to_filter = {
        "autumn": filters.AUTUMN,
        "winter": filters.WINTER,
        "spring": filters.SPRING,
        "summer": filters.SUMMER,
    }

    if term_arg == "":
        fs = [filters.AUTUMN, filters.WINTER, filters.SPRING, filters.SUMMER]
    else:
        if term_arg not in term_to_filter:
            valid = ", ".join(["Autumn", "Winter", "Spring", "Summer"])
            raise ValueError(f"Invalid term '{arguments.get('term')}'. Valid options: {valid}")
        fs = [term_to_filter[term_arg]]
    candidates = api.get_courses_by_query(course_id, *fs, year=ACADEMIC_YEAR)
    course = None
    
    for c in candidates:
        if (c.course_id == course_id):
            course = c
    
    if course == None:
        raise ValueError(f"No matches found with course_id '{course_id}'")

    # Optionally filter sections by term label present in the section's term string
    sections = list(getattr(course, "sections", ()) or ())
    if term_arg != "":
        sections = [
            s for s in sections
            if (str(getattr(s, "term", "")).lower().find(term_arg) != -1)
        ]

    ns = SimpleNamespace(sections=sections)
    return [types.TextContent(type="text", text=format_course_sections(ns))]

def register_all() -> None:
    register_tool(list_schools_spec, list_schools_handler)
    register_tool(list_departments_spec, list_departments_handler)
    register_tool(get_course_spec, get_course_handler)
    register_tool(get_schedule_spec, get_schedule_handler)
