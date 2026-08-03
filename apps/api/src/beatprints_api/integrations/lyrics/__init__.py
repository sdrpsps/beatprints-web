"""Independently registered lyrics sources."""

from beatprints_api.integrations.lyrics.base import LyricsSourceAdapter, LyricsSourceResult
from beatprints_api.integrations.lyrics.registry import (
    default_lyrics_source,
    default_lyrics_source_key,
    get_lyrics_source,
    lyrics_sources,
)

__all__ = [
    "LyricsSourceAdapter",
    "LyricsSourceResult",
    "default_lyrics_source",
    "default_lyrics_source_key",
    "get_lyrics_source",
    "lyrics_sources",
]
