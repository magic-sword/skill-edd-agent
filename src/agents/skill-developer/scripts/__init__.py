from typing import Any

def __getattr__(name: str) -> Any:
    """Attribute handler for lazy imports."""
    if name == "skill_developer":
        from .handler import skill_developer
        return skill_developer

    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

__all__ = ['skill_developer']
