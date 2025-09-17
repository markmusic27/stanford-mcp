from typing import Any, Iterable

from explorecourses import Course

# Formatting utilities and course pretty-printer

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


def format_course(course: Any) -> str:
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
{fmt_objectives(getattr(course, 'objectives', ())) }

tags:
{fmt_tags(getattr(course, 'tags', ())) }

course_attributes:
{fmt_attributes(getattr(course, 'attributes', ())) }

sections:
{fmt_sections(getattr(course, 'sections', ())) }
"""


def format_course_no_sections(course: Any) -> str:
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
{fmt_objectives(getattr(course, 'objectives', ())) }

tags:
{fmt_tags(getattr(course, 'tags', ())) }

course_attributes:
{fmt_attributes(getattr(course, 'attributes', ())) }
"""


def format_course_sections(course: Any) -> str:
    return f"""sections:
{fmt_sections(getattr(course, 'sections', ())) }
"""

def format_course_summary(course: Course) -> str:
    desc = course.description
    if len(desc) > 700:
        desc = desc[:697] + "..." + " (description clipped, fetch with get-course tool for full details)"
    units = str(course.units_max) if course.units_max == course.units_min else f"{course.units_min} - {course.units_max}"
    header = f"{course.subject + course.code} | id: {course.course_id} | {units} units"
    return header + f"\n{course.title}" + f"\n\n{desc}\n"
