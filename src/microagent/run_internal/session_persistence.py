"""Session persistence helpers."""
from __future__ import annotations

import inspect
from typing import Any

from ..items import TResponseInputItem
from ..memory.session import Session
from ..memory.session_settings import SessionSettings
from ..memory.util import SessionInputCallback


async def prepare_input_with_session(
    raw_input: str | list[TResponseInputItem],
    session: Session | None,
    input_callback: SessionInputCallback | None,
    session_settings: SessionSettings | None,
    *,
    include_history_in_prepared_input: bool = True,
    preserve_dropped_new_items: bool = False,
) -> tuple[list[TResponseInputItem], list[TResponseInputItem] | None]:
    """Compose history + new input; return `(prepared_input, items_to_persist)`."""
    new_items: list[TResponseInputItem] = (
        [{"role": "user", "content": raw_input}]
        if isinstance(raw_input, str)
        else [dict(i) for i in raw_input]
    )
    if session is None:
        return new_items, None
    history = await session.get_items(limit=(session_settings.limit if session_settings else None))
    if input_callback is not None:
        merged = input_callback(list(history), list(new_items))
        if inspect.isawaitable(merged):
            merged = await merged
        prepared = list(merged)
    else:
        prepared = (list(history) if include_history_in_prepared_input else []) + list(new_items)
    return prepared, list(new_items)


async def save_result_to_session(
    session: Session | None,
    new_input_items: list[TResponseInputItem] | None,
    generated_input_items: list[TResponseInputItem],
) -> None:
    if session is None:
        return
    to_persist: list[TResponseInputItem] = []
    if new_input_items:
        to_persist.extend(new_input_items)
    to_persist.extend(generated_input_items)
    if to_persist:
        await session.add_items(to_persist)


__all__ = ["prepare_input_with_session", "save_result_to_session"]