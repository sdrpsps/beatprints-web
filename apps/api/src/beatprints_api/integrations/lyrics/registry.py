"""The one enablement list for lyric source integrations."""

from beatprints_api.exceptions import UnsupportedLyricsSourceError
from beatprints_api.integrations.lyrics.base import LyricsSourceAdapter

_adapters: dict[str, LyricsSourceAdapter] = {}
_default_key: str | None = None


def register(adapter: LyricsSourceAdapter, *, default: bool = False) -> LyricsSourceAdapter:
    """Register an enabled source; only one source provides legacy defaults."""

    global _default_key
    if not adapter.key:
        raise ValueError("Lyrics source adapters require a stable key")
    if adapter.key in _adapters:
        raise ValueError(f"Lyrics source adapter already registered: {adapter.key}")
    if default and _default_key is not None:
        raise ValueError("Only one lyrics source can be the default")
    _adapters[adapter.key] = adapter
    if default:
        _default_key = adapter.key
    return adapter


def get_lyrics_source(key: str) -> LyricsSourceAdapter:
    try:
        return _adapters[key]
    except KeyError as exc:
        available = ", ".join(sorted(_adapters)) or "none"
        raise UnsupportedLyricsSourceError(
            f"Unsupported or disabled lyrics source: {key}. Enabled sources: {available}"
        ) from exc


def lyrics_sources() -> tuple[LyricsSourceAdapter, ...]:
    return tuple(_adapters[key] for key in sorted(_adapters))


def default_lyrics_source() -> LyricsSourceAdapter:
    if _default_key is not None:
        return _adapters[_default_key]
    if _adapters:
        return _adapters[sorted(_adapters)[0]]
    raise RuntimeError("No lyrics source is enabled")


# Importing an adapter is the sole enablement mechanism. Temporarily removing a
# source requires commenting out one import here; no core service changes.
from beatprints_api.integrations.lyrics import lrclib  # noqa: E402, F401
