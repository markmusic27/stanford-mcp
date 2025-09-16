import asyncio
from typing import Any, Iterable
from functools import lru_cache
from explorecourses import Course, CourseConnection
import mcp.types as types
import explorecourses.filters as filters

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


# Course formatting
IND = "    "  # 4-space indent

def _none_guard(x: Any, fallback: str = "None") -> str:
    return fallback if x is None else str(x)

def _join(seq: Iterable[Any], sep: str = ", ") -> str:
    if not seq:
        return ""
    return sep.join(str(s) for s in seq)

def fmt_objectives(objs: Iterable[Any], indent: str = IND) -> str:
    if not objs:
        return f"{indent}- (none)"
    lines = []
    for o in objs:
        code = getattr(o, "code", None)
        desc = getattr(o, "description", None)
        if code or desc:
            lines.append(f"{indent}- {code}: {desc}")
        else:
            lines.append(f"{indent}- {o}")
    return "\n".join(lines)

def fmt_tags(tags: Iterable[Any], indent: str = IND) -> str:
    if not tags:
        return f"{indent}- (none)"
    return "\n".join(
        f"{indent}- {getattr(t, 'organization', '')}::{getattr(t, 'name', '')}"
        for t in tags
    )

def fmt_attributes(attrs: Iterable[Any], indent: str = IND) -> str:
    if not attrs:
        return f"{indent}- (none)"
    out = []
    for a in attrs:
        name = getattr(a, "name", "")
        val = getattr(a, "value", "")
        desc = getattr(a, "description", "")
        cat = getattr(a, "catalog_print", None)
        sch = getattr(a, "schedule_print", None)
        tail = f" — {desc}" if desc else ""
        flags = []
        if cat is not None:
            flags.append(f"catalog_print={cat}")
        if sch is not None:
            flags.append(f"schedule_print={sch}")
        flag_text = f" [{', '.join(flags)}]" if flags else ""
        out.append(f"{indent}- {name}::{val}{tail}{flag_text}")
    return "\n".join(out)

def fmt_instructors(instrs: Iterable[Any], indent: str = IND) -> str:
    if not instrs:
        return f"{indent}- (none)"
    lines = []
    for i in instrs:
        first = getattr(i, "first_name", "") or ""
        last = getattr(i, "last_name", "") or ""
        sunet = getattr(i, "sunet_id", "") or ""
        pi = getattr(i, "is_primary_instructor", None)
        pi_tag = " (PI)" if pi else ""
        name_part = f"{first} {last}".strip() or getattr(i, "name", "(unknown)")
        # Keep SUNet if present
        sunet_part = f" [{sunet}]" if sunet else ""
        lines.append(f"{indent}- {name_part}{sunet_part}{pi_tag}")
    return "\n".join(lines)

def fmt_schedules(schedules: Iterable[Any], base_indent: str = IND) -> str:
    if not schedules:
        return f"{base_indent}(none)"
    lines = []
    for idx, s in enumerate(schedules, 1):
        i1 = base_indent
        i2 = base_indent + IND
        i3 = base_indent + IND * 2
        days = _join(getattr(s, "days", ()), sep=", ")
        lines.append(f"{i1}- Schedule #{idx}:")
        lines.append(f"{i2}dates: {getattr(s, 'start_date', None)} → {getattr(s, 'end_date', None)}")
        lines.append(f"{i2}time: {getattr(s, 'start_time', None)} – {getattr(s, 'end_time', None)}")
        lines.append(f"{i2}location: {getattr(s, 'location', None)}")
        lines.append(f"{i2}days: {days}")
        lines.append(f"{i2}instructors:")
        lines.append(fmt_instructors(getattr(s, "instructors", ()), indent=i3))
    return "\n".join(lines)

def fmt_sections(sections: Iterable[Any], base_indent: str = IND) -> str:
    if not sections:
        return f"{base_indent}- (none)"
    out = []
    for idx, sec in enumerate(sections, 1):
        i1 = base_indent
        i2 = base_indent + IND
        i3 = base_indent + IND * 2
        out.append(f"{i1}- Section #{idx}: {getattr(sec, 'component', None)} {getattr(sec, 'section_num', None)} (class_id: {getattr(sec, 'class_id', None)})")
        out.append(f"{i2}term: {getattr(sec, 'term', None)}")
        out.append(f"{i2}units: {getattr(sec, 'units', None)}")
        out.append(f"{i2}enrollment: {getattr(sec, 'curr_class_size', None)}/{getattr(sec, 'max_class_size', None)}")
        out.append(f"{i2}waitlist: {getattr(sec, 'curr_waitlist_size', None)}/{getattr(sec, 'max_waitlist_size', None)}")
        notes = getattr(sec, "notes", None)
        if notes:
            out.append(f"{i2}notes: {notes}")
        out.append(f"{i2}schedules:")
        out.append(fmt_schedules(getattr(sec, "schedules", ()), base_indent=i3))
        out.append(f"{i2}attributes:")
        out.append(fmt_attributes(getattr(sec, "attributes", ()), indent=i3))
    return "\n".join(out)

def format_course(course: Course) -> str:
    return f"""# Course
course_id: {getattr(course, 'course_id', None)}
year: {getattr(course, 'year', None)}
subject: {getattr(course, 'subject', None)}
code: {getattr(course, 'code', None)}
title: {getattr(course, 'title', None)}
description: {getattr(course, 'description', None)}
gers: {_join(getattr(course, 'gers', ()) or ())}
repeatable: {getattr(course, 'repeatable', None)}
grading_basis: {getattr(course, 'grading_basis', None)}
units_min: {getattr(course, 'units_min', None)}
units_max: {getattr(course, 'units_max', None)}
final_exam: {getattr(course, 'final_exam', None)}
active: {getattr(course, 'active', None)}
offer_num: {getattr(course, 'offer_num', None)}
academic_group: {getattr(course, 'academic_group', None)}
academic_org: {getattr(course, 'academic_org', None)}
academic_career: {getattr(course, 'academic_career', None)}
max_units_repeat: {getattr(course, 'max_units_repeat', None)}
max_times_repeat: {getattr(course, 'max_times_repeat', None)}

learning_objectives:
{fmt_objectives(getattr(course, 'objectives', ()))}

tags:
{fmt_tags(getattr(course, 'tags', ()))}

course_attributes:
{fmt_attributes(getattr(course, 'attributes', ()))}

sections:
{fmt_sections(getattr(course, 'sections', ()))}
"""

# End of course formatting

get_course_spec = types.Tool(
    name="get-course",
    title="Course Details",
    description="Fetch a full course record by course_id, including title, description, GERS, attributes, tags, repeatability, sections, schedules, and exam flags.",
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
    
    return [types.TextContent(type="text", text=format_course(course))]

# def register_all() -> None:
#     register_tool(list_schools_spec, list_schools_handler)
#     register_tool(list_departments_spec, list_departments_handler)
#     register_tool(get_course_spec, get_course_handler)


async def test():
    res = await get_course_handler({
        "course_id": 225453
    }, "")
    
    print(res)

if __name__ == "__main__":
    asyncio.run(test())
