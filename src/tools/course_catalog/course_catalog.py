import asyncio
from typing import Any
from functools import lru_cache
from explorecourses import CourseConnection
import mcp.types as types
import explorecourses.filters as filters

from tools.registry import register_tool
from .formatting import format_course_no_sections, format_course_sections
from .filtering import build_filters_from_arguments
from types import SimpleNamespace
from datetime import datetime

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



check_time_conflicts_spec = types.Tool(
    name="check-time-conflicts",
    title="Check Section Time Conflicts",
    description=(
        "Given a list of {course_id, section_id} pairs, validate IDs and report any day/time overlaps."
    ),
    inputSchema={
        "type": "object",
        "required": ["selections"],
        "properties": {
            "selections": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["course_id", "section_id"],
                    "properties": {
                        "course_id": {"type": "number"},
                        "section_id": {"type": "number"}
                    },
                },
                "description": "List of pairs to evaluate for conflicts."
            }
        }
    }
)

def _parse_time_to_minutes(value: str | None) -> int | None:
    if value is None:
        return None
    s = value.strip()
    if not s:
        return None
    # Try several common formats
    time_formats = [
        "%I:%M %p", "%I:%M%p", "%I:%M:%S %p", "%H:%M", "%H:%M:%S"
    ]
    for fmt in time_formats:
        try:
            t = datetime.strptime(s, fmt)
            return t.hour * 60 + t.minute
        except Exception:
            pass
    return None

def _format_conflict_line(day: str, a: dict, b: dict) -> str:
    return (
        f"- {day}: {a['course_id']}[{a['section_id']}] {a['start_str']}–{a['end_str']} "
        f"conflicts with {b['course_id']}[{b['section_id']}] {b['start_str']}–{b['end_str']}"
    )

async def check_time_conflicts_handler(arguments: dict[str, Any], ctx: Any) -> list[types.ContentBlock]:
    selections = arguments.get("selections")
    if not isinstance(selections, list) or not selections:
        raise ValueError("'selections' must be a non-empty array of {course_id, section_id}.")

    api = get_course_connection()

    # Fetch all terms so we can find sections regardless of quarter
    term_filters = [filters.AUTUMN, filters.WINTER, filters.SPRING, filters.SUMMER]

    # Validate and collect schedules by day
    day_to_intervals: dict[str, list[dict]] = {}
    messages: list[str] = []

    for item in selections:
        if not isinstance(item, dict):
            raise TypeError("Each selection must be an object with course_id and section_id.")
        course_id = item.get("course_id")
        section_id = item.get("section_id")
        if not isinstance(course_id, (int, float)):
            raise TypeError("course_id must be a number.")
        if not isinstance(section_id, (int, float)):
            raise TypeError("section_id must be a number.")

        candidates = api.get_courses_by_query(course_id, *term_filters, year=ACADEMIC_YEAR)
        course = None
        for c in candidates:
            if c.course_id == course_id:
                course = c
                break
        if course is None:
            raise ValueError(f"Invalid course_id: {course_id}")

        target_section = None
        for sec in getattr(course, "sections", ()) or ():
            if getattr(sec, "class_id", None) == section_id:
                target_section = sec
                break
        if target_section is None:
            raise ValueError(f"Invalid section_id: {section_id} for course_id {course_id}")

        schedules = getattr(target_section, "schedules", ()) or ()
        if not schedules:
            messages.append(f"Note: course {course_id} section {section_id} has no schedules.")
            continue

        for sched in schedules:
            start_min = _parse_time_to_minutes(getattr(sched, "start_time", None))
            end_min = _parse_time_to_minutes(getattr(sched, "end_time", None))
            start_str = str(getattr(sched, "start_time", None))
            end_str = str(getattr(sched, "end_time", None))
            if start_min is None or end_min is None:
                messages.append(
                    f"Warning: course {course_id} section {section_id} has unparseable time window {start_str}–{end_str}. Skipping this schedule for conflict checks."
                )
                continue
            days = list(getattr(sched, "days", ()) or ())
            if not days:
                messages.append(
                    f"Warning: course {course_id} section {section_id} schedule has no days. Skipping."
                )
                continue
            for day in days:
                bucket = day_to_intervals.setdefault(day, [])
                bucket.append({
                    "course_id": course_id,
                    "section_id": section_id,
                    "start": start_min,
                    "end": end_min,
                    "start_str": start_str,
                    "end_str": end_str,
                })

    # Detect conflicts
    conflicts: list[str] = []
    for day, intervals in day_to_intervals.items():
        intervals.sort(key=lambda x: (x["start"], x["end"]))
        prev = None
        for cur in intervals:
            if prev is not None:
                # Overlap if current starts before previous ends
                if cur["start"] < prev["end"]:
                    conflicts.append(_format_conflict_line(day, prev, cur))
            prev = cur

    header = "Time Conflict Check"
    out_lines = [header]
    if messages:
        out_lines.append("\nNotes:")
        out_lines.extend(f"- {m}" for m in messages)
    if conflicts:
        out_lines.append("\nConflicts:")
        out_lines.extend(conflicts)
    else:
        out_lines.append("\nNo conflicts detected.")

    return [types.TextContent(type="text", text="\n".join(out_lines))]



search_courses_spec = types.Tool(
    name="search-courses",
    title="Search Courses",
    description=(
        "Search courses by keyword and term filters (Autumn, Winter, Spring, Summer)."
    ),
    inputSchema={
        "type": "object",
        "required": ["keyword", "terms"],
        "properties": {
            "keyword": {
                "type": "string",
                "description": "Free-text keyword to search course titles, descriptions, etc.",
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
    keyword = arguments.get("keyword", "")
    if not isinstance(keyword, str):
        raise TypeError("'keyword' must be a string.")

    fs = build_filters_from_arguments(arguments, term_field="terms", require_terms=True)

    api = get_course_connection()
    courses = api.get_courses_by_query(keyword, *fs, year=ACADEMIC_YEAR)  # IMPLEMENT FROM HERE (MARK)

    raise NotImplementedError("IMPLEMENT FROM HERE (MARK)")

def register_all() -> None:
    register_tool(list_schools_spec, list_schools_handler)
    register_tool(list_departments_spec, list_departments_handler)
    register_tool(get_course_spec, get_course_handler)
    register_tool(get_schedule_spec, get_schedule_handler)
    register_tool(check_time_conflicts_spec, check_time_conflicts_handler)
    register_tool(search_courses_spec, search_courses_handler)