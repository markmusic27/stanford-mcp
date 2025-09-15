from .weather import register_all as register_weather


def register_all_tools() -> None:
    """Register all tool groups with the registry.

    Add additional registrations here as you create new tool modules.
    """
    register_weather()


