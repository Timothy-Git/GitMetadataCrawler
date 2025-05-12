from typing import Callable, Dict
from backend.graphql.git_types import FetchJob

class PluginException(Exception):
    pass

class PluginRegistry:
    _plugins: Dict[str, Callable[[FetchJob], str]] = {}

    @classmethod
    def register(cls, name: str, func: Callable[[FetchJob], str]):
        if name in cls._plugins:
            raise PluginException(f"Plugin '{name}' already registered.")
        cls._plugins[name] = func

    @classmethod
    def get(cls, name: str) -> Callable[[FetchJob], str]:
        if name not in cls._plugins:
            raise PluginException(f"Plugin '{name}' not found.")
        return cls._plugins[name]

    @classmethod
    def all_names(cls):
        return list(cls._plugins.keys())