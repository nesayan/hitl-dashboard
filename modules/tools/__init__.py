import importlib
import inspect
import pkgutil
from pathlib import Path

from langchain_core.tools import StructuredTool

_package_dir = Path(__file__).parent

TOOLS: list[StructuredTool] = []

for finder, module_name, _ in pkgutil.iter_modules([str(_package_dir)]):
    module = importlib.import_module(f"{__name__}.{module_name}")

    for name, func in inspect.getmembers(module, inspect.isfunction):
        if not name.startswith("_"):
            continue
        tool_name = name.lstrip("_")
        metadata = getattr(func, "_meta", {"requires_approval": False})
        TOOLS.append(
            StructuredTool.from_function(
                func=func,
                name=tool_name,
                description=func.__doc__ or tool_name,
                metadata=metadata,
            )
        )
