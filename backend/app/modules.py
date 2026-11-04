"""Eight isolated OPUS tool module definitions.

Names and domain logic remain configurable until the authorized requirements
for each tool are confirmed. This avoids inventing Mark Pro internals.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class ToolModule:
    key: str
    title: str
    description: str
    enabled: bool = False


TOOL_MODULES = tuple(
    ToolModule(
        key=f"tool-{index:02d}",
        title=f"OPUS Tool {index}",
        description="Module placeholder; configure only from verified requirements.",
    )
    for index in range(1, 9)
)


def list_modules() -> list[dict[str, object]]:
    return [
        {
            "key": module.key,
            "title": module.title,
            "description": module.description,
            "enabled": module.enabled,
        }
        for module in TOOL_MODULES
    ]
