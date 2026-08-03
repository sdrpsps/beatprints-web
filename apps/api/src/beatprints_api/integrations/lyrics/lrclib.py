"""LRCLIB-backed lyrics source adapter."""

from BeatPrints import deez, errors as beatprints_errors, lyrics

from beatprints_api.exceptions import LyricsNotFoundError, UpstreamError
from beatprints_api.integrations.lyrics.base import LyricsSourceAdapter, LyricsSourceResult
from beatprints_api.integrations.lyrics.registry import register
from beatprints_api.models.poster import TrackPosterRequest


def _fetch(metadata: deez.TrackMetadata):
    try:
        lyric_result = lyrics.Lyrics(metadata).get_lyrics()
        instrumental = lyric_result.check_instrumental(metadata)
    except beatprints_errors.NoLyricsAvailable as exc:
        raise LyricsNotFoundError("No lyrics were found for this recording") from exc
    except Exception as exc:
        raise UpstreamError("Lyrics provider request failed") from exc
    lines = tuple(
        line.strip() for line in (lyric_result.lyrics or "").splitlines() if line.strip()
    )
    return lyric_result, instrumental, lines


def fetch(metadata: deez.TrackMetadata) -> LyricsSourceResult:
    _lyric_result, instrumental, lines = _fetch(metadata)
    return LyricsSourceResult(instrumental=instrumental, lines=lines)


def select_default(metadata: deez.TrackMetadata, request: object) -> str:
    """Keep pre-selector API clients compatible with the configured default."""

    if not isinstance(request, TrackPosterRequest):
        raise TypeError("Default lyrics selection requires a track poster request")
    lyric_result, instrumental, lines = _fetch(metadata)
    if instrumental:
        return request.instrumental_text.strip()
    if request.lyrics_range is not None:
        return lyric_result.select_lines(request.lyrics_range)
    if len(lines) < 4:
        raise UpstreamError("Fewer than four non-empty lyric lines were available")
    return "\n".join(lines[:4])


adapter = register(
    LyricsSourceAdapter(
        key="lrclib",
        label="LRCLIB",
        fetch=fetch,
        select_default=select_default,
    )
)
