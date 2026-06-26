"""Pure SKUD domain helpers.

Adapters for UPROX/ZKTeco will live behind these domain models so the UI and
attendance calculation do not depend on PeopleForce or device-specific payloads.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Iterable


@dataclass(frozen=True)
class NormalizedPunch:
    occurred_at: datetime
    direction: str
    source_event_id: str


def collapse_near_duplicates(events: Iterable[NormalizedPunch], seconds: int = 180) -> list[NormalizedPunch]:
    """Collapse repeated same-direction punches inside a short window.

    This mirrors the useful ZKTeco "stutter" rule from sunc_v4, but keeps it
    pure so raw events remain immutable in the database.
    """

    ordered = sorted(events, key=lambda item: item.occurred_at)
    if not ordered:
        return []

    collapsed: list[NormalizedPunch] = [ordered[0]]
    threshold = timedelta(seconds=seconds)
    for event in ordered[1:]:
        previous = collapsed[-1]
        if event.direction == previous.direction and event.occurred_at - previous.occurred_at <= threshold:
            collapsed[-1] = event
            continue
        collapsed.append(event)
    return collapsed
