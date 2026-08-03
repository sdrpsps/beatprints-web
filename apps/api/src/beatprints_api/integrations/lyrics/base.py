"""Contracts for independently enabled lyric sources."""

from collections.abc import Callable
from dataclasses import dataclass

from BeatPrints import deez


@dataclass(frozen=True)
class LyricsSourceResult:
    """Normalized lyrics that can be presented for explicit line selection."""

    instrumental: bool
    lines: tuple[str, ...]


@dataclass(frozen=True)
class LyricsSourceAdapter:
    """One independently enabled lyrics integration.

    The adapter owns retrieval and line normalization. Core services only use
    this contract, so a source can be added or removed in the registry.
    """

    key: str
    label: str
    fetch: Callable[[deez.TrackMetadata], LyricsSourceResult]
    select_default: Callable[[deez.TrackMetadata, object], str] | None = None
