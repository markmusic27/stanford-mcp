import importlib
import importlib.util
import logging
from pathlib import Path
from types import ModuleType
from typing import Callable, Optional
import sys


logger = logging.getLogger(__name__)


def _call_register_if_present(module: ModuleType) -> bool:
    """Call register_all() if present on the given module.

    Returns True if a callable register_all was found and invoked, else False.
    """
    register_func: Optional[Callable[[], None]] = getattr(module, "register_all", None)
    if callable(register_func):
        register_func()
        logger.debug("Registered tools via %s.register_all()", module.__name__)
        return True
    return False


def register_all_tools() -> None:
    """Auto-discover and register tools under tools/*/.

    Supported conventions inside each subdirectory (e.g., tools/weather):
    - __init__.py defines register_all()
    - <name>.py defines register_all()  (e.g., weather/weather.py)
    - tool.py defines register_all()    (e.g., weather/tool.py)
    """
    tools_pkg_name = __name__  # "tools"
    tools_dir = Path(__file__).parent

    for entry in tools_dir.iterdir():
        if not entry.is_dir():
            continue

        name = entry.name
        full_pkg_name = f"{tools_pkg_name}.{name}"

        # 1) Try importing the package itself (works for packages and namespace packages)
        try:
            pkg = importlib.import_module(full_pkg_name)
        except Exception as exc:
            logger.warning("Failed to import %s: %s", full_pkg_name, exc)
        else:
            if _call_register_if_present(pkg):
                continue

        # 2) Try module with same name as directory: tools/<name>/<name>.py
        try:
            mod_same_name = importlib.import_module(f"{full_pkg_name}.{name}")
            if _call_register_if_present(mod_same_name):
                continue
        except ModuleNotFoundError:
            pass
        except Exception as exc:
            logger.warning("Failed to import %s.%s: %s", full_pkg_name, name, exc)

        # 3) Try conventional tool.py: tools/<name>/tool.py
        try:
            mod_tool = importlib.import_module(f"{full_pkg_name}.tool")
            if _call_register_if_present(mod_tool):
                continue
        except ModuleNotFoundError:
            pass
        except Exception as exc:
            logger.warning("Failed to import %s.tool: %s", full_pkg_name, exc)

        # 4) Fallback to path-based import for unconventional filenames
        candidates = [
            entry / f"{name}.py",            # tools/<name>/<name>.py
            entry / "tool.py",               # tools/<name>/tool.py
            entry / f"{name}.tool.py",       # tools/<name>/<name>.tool.py
        ]

        loaded = False
        for candidate in candidates:
            if not candidate.exists():
                continue
            module_name = f"{full_pkg_name}._auto_{candidate.stem.replace('.', '_')}"
            try:
                spec = importlib.util.spec_from_file_location(module_name, candidate)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    sys.modules[module_name] = module
                    spec.loader.exec_module(module)  # type: ignore[attr-defined]
                    if _call_register_if_present(module):
                        loaded = True
                        break
            except Exception as exc:
                logger.warning("Failed to load module from %s: %s", candidate, exc)

        if not loaded:
            logger.info("No register_all() found for %s", full_pkg_name)

