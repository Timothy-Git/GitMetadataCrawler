import strawberry
from enum import Enum

# Import plugins:
import backend.plugins.language_metrics_plugin  # noqa: F401

from backend.utils.plugin_registry import PluginRegistry


def create_plugin_enum():
    names = PluginRegistry.all_names()
    if not names:
        return Enum("PluginEnum", {"NO_PLUGINS_REGISTERED": "NO_PLUGINS_REGISTERED"})

    # Build enum values with descriptions
    enum_dict = {}
    for name in names:
        func = PluginRegistry.get(name)
        desc = getattr(func, "description", None)
        enum_dict[name.upper()] = strawberry.enum_value(
            name, description=desc or f"Plugin '{name}'"
        )
    return Enum("PluginEnum", enum_dict)


PluginEnum = strawberry.enum(create_plugin_enum())
