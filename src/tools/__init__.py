from .course_catalog.course_catalog import register_all as register_course_catalog


def register_all_tools() -> None:
    """Register all tool groups with the registry.

    Add additional registrations here as you create new tool modules.
    """
    register_course_catalog()


