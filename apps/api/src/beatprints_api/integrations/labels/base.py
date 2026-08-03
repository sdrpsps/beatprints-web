"""Contract for an optional, evidence-based catalog-label resolver."""

from collections.abc import Callable
from dataclasses import dataclass

from BeatPrints import deez


@dataclass(frozen=True)
class LabelResolver:
    key: str
    configured: Callable[[], bool]
    resolve_track: Callable[[deez.TrackMetadata], str | None]
