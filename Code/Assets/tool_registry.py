# Code/Assets/Tools/tool_registry.py
from typing import Callable, Dict, Any


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: Dict[str, Callable[..., Any]] = {}

    def register(self, name: str, fn: Callable[..., Any]) -> None:
        if name in self._tools:
            raise ValueError(f"Tool '{name}' is already registered.")
        self._tools[name] = fn

    def get(self, name: str) -> Callable[..., Any]:
        if name not in self._tools:
            raise KeyError(f"Tool '{name}' is not registered.")
        return self._tools[name]

    def list(self) -> Dict[str, Callable[..., Any]]:
        return dict(self._tools)


# global singleton (import this everywhere)
tool_registry = ToolRegistry()
