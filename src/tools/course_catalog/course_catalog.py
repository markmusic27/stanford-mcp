import asyncio
from typing import Any
from functools import lru_cache
from explorecourses import CourseConnection
from explorecourses.classes import Course
import mcp.types as types
import explorecourses.filters as filters

from tools.registry import register_tool
from .formatting import format_course, format_course_summary
from .filtering import build_filters_from_arguments

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
        "required": ["course_id", "terms"],
        "properties": {
            "course_id": {
                "type": "number",
                "description": "Identifier of the course (e.g. 105645, NOT CS 106B). Use search-courses to find valid IDs.",
            },
            "terms": {
                "type": "array",
                "minItems": 1,
                "items": {"type": "string"},
                "description": "List of terms to search in: Autumn | Winter | Spring | Summer (at least one).",
            },
            "ug_reqs": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional UG requirements: LANGUAGE, WRITING1, WRITING2, WRITINGSLE, WAY_AII, WAY_AQR, WAY_CE, WAY_ED, WAY_ER, WAY_FR, WAY_SI, WAY_SMA.",
            },
            "units": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional units filters: 1, 2, 3, 4, 5, GT5.",
            },
            "times": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional time of day: early_morning, morning, lunchtime, afternoon, evening.",
            },
            "days": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional meeting days: sunday, monday, tuesday, wednesday, thursday, friday, saturday.",
            },
            "careers": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional careers: UG, GR, GSB, LAW, MED.",
            },
        },
    },
)

async def get_course_handler(arguments: dict[str, Any], ctx: Any) -> list[types.ContentBlock]:
    course_id = arguments.get("course_id")
    api = get_course_connection()
    
    # Build filters: keep term behavior defaulting to Autumn if not provided
    fs = build_filters_from_arguments(
        {**arguments, "terms": arguments.get("terms") or ["Autumn"]},
        term_field="terms",
        require_terms=True,
    )
    candidates = api.get_courses_by_query(course_id, *fs, year=ACADEMIC_YEAR)
    course = None
    
    # Validate course_id and extract course
    for c in candidates:
        if (c.course_id == course_id):
            course = c
    
    if course == None:
        raise ValueError(f"No matches found with course_id '{course_id}'")
    
    return [types.TextContent(type="text", text=format_course(course))]

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



search_courses_spec = types.Tool(
    name="search-courses",
    title="Search Courses",
    description=(
        "Search courses by query and term filters (Autumn, Winter, Spring, Summer). Returns basic information."
    ),
    inputSchema={
        "type": "object",
        "required": ["query", "terms"],
        "properties": {
            "query": {
                "type": "string",
                "description": "Free-text query to search course titles, descriptions, etc.",
            },
            "terms": {
                "type": "array",
                "minItems": 1,
                "items": {"type": "string"},
                "description": "List of terms to search in: Autumn | Winter | Spring | Summer (at least one).",
            },
            "ug_reqs": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional UG requirements: LANGUAGE, WRITING1, WRITING2, WRITINGSLE, WAY_AII, WAY_AQR, WAY_CE, WAY_ED, WAY_ER, WAY_FR, WAY_SI, WAY_SMA.",
            },
            "units": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional units filters: 1, 2, 3, 4, 5, GT5.",
            },
            "times": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional time of day: early_morning, morning, lunchtime, afternoon, evening.",
            },
            "days": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional meeting days: sunday, monday, tuesday, wednesday, thursday, friday, saturday.",
            },
            "careers": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional careers: UG, GR, GSB, LAW, MED.",
            },
        },
    },
)

async def search_courses_handler(arguments: dict[str, Any], ctx: Any) -> list[types.ContentBlock]:
    query = arguments.get("query", "")
    if not isinstance(query, str):
        raise TypeError("'query' must be a string.")

    fs = build_filters_from_arguments(arguments, term_field="terms", require_terms=True)

    api = get_course_connection()
    courses = api.get_courses_by_query(query, *fs, year=ACADEMIC_YEAR) 
    
    out = "Note: search-courses is for exploring and finding courses. It returns only summary fields (name, description, units). To retrieve all details about a course (instructors, schedule, requirements, etc.), use the get-course tool.\n\nResults:"
    
    for c in courses:
        out += "\n\n" + format_course_summary(c)
        
    return [types.TextContent(type="text", text=out)]


def register_all() -> None:
    register_tool(list_schools_spec, list_schools_handler)
    register_tool(list_departments_spec, list_departments_handler)
    register_tool(get_course_spec, get_course_handler)
    register_tool(search_courses_spec, search_courses_handler)