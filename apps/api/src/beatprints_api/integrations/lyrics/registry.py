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
    return tuple(_adapters.values())


def default_lyrics_source() -> LyricsSourceAdapter:
    key = default_lyrics_source_key()
    if key is None:
        raise RuntimeError("No lyrics source is enabled")
    return _adapters[key]


def default_lyrics_source_key() -> str | None:
    if _default_key is not None:
        return _default_key
    return next(iter(_adapters), None)


# Importing an adapter is the sole enablement mechanism. Temporarily removing a
# source requires commenting out one import here; no core service changes.
from beatprints_api.integrations.lyrics import qq_music as _qq_music  # noqa: E402, F401
from beatprints_api.integrations.lyrics import netease as _netease  # noqa: E402, F401
from beatprints_api.integrations.lyrics import lrclib as _lrclib  # noqa: E402, F401
