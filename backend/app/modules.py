"""Eight independent OPUS PRO tool profiles.

These profile IDs and lookback sizes reflect the agreed OPUS interface plan.
They are configuration profiles, not claims about Mark Pro's proprietary
algorithms. Each profile can be wired to independently evaluated analytics.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class ToolModule:
    key: str
    title: str
    lookback_records: int
    description: str
    enabled: bool = True


_PROFILE_CONFIG = (
    ("opus-1.1", "OPUS 1.1", 20),
    ("opus-1.0", "OPUS 1.0", 30),
    ("opus-1.2", "OPUS 1.2", 50),
    ("opus-1.4", "OPUS 1.4", 75),
    ("opus-1.8", "OPUS 1.8", 100),
    ("opus-1.6", "OPUS 1.6", 150),
    ("opus-2.0", "OPUS 2.0", 200),
    ("opus-2.2", "OPUS 2.2", 500),
)

TOOL_MODULES = tuple(
    ToolModule(
        key=key,
        title=title,
        lookback_records=lookback,
        description=f"Independent analytics profile using up to {lookback} verified historical observations.",
    )
    for key, title, lookback in _PROFILE_CONFIG
)


def list_modules() -> list[dict[str, object]]:
    return [
        {
            "key": module.key,
            "title": module.title,
            "lookback_records": module.lookback_records,
            "description": module.description,
            "enabled": module.enabled,
        }
        for module in TOOL_MODULES
    ]
