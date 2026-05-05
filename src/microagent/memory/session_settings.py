"""Session runtime settings."""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass, fields, replace
from typing import Any


def resolve_session_limit(
    explicit_limit: int | None, settings: SessionSettings | None
) -> int | None:
    """Return the effective limit for a `session.get_items()` call."""
    if explicit_limit is not None:
        return explicit_limit
    if settings is not None:
        return settings.limit
    return None


@dataclass
class SessionSettings:
    """Per-run session configuration overrides."""

    limit: int | None = None
    """Maximum number of items to retrieve. If None, retrieves all items."""

    def resolve(self, override: SessionSettings | None) -> SessionSettings:
        """Overlay non-None values from `override` onto `self`."""
        if override is None:
            return self
        changes = {
            f.name: getattr(override, f.name)
            for f in fields(self)
            if getattr(override, f.name) is not None
        }
        return replace(self, **changes)

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


__all__ = ["SessionSettings", "resolve_session_limit"]