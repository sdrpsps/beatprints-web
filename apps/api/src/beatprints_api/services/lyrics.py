"""Lyrics retrieval and selection for track poster generation."""

from BeatPrints import deez, errors as beatprints_errors, lyrics
from beatprints_api.exceptions import UpstreamError
from beatprints_api.models.catalog import LyricsLine, LyricsPreviewData
from beatprints_api.models.poster import TrackPosterRequest


def fetch(metadata: deez.TrackMetadata):
    try:
        lyric_result = lyrics.Lyrics(metadata).get_lyrics()
        instrumental = lyric_result.check_instrumental(metadata)
    except beatprints_errors.NoLyricsAvailable as exc:
        raise UpstreamError("No lyrics were found for this recording") from exc
    except Exception as exc:
        raise UpstreamError("Lyrics provider request failed") from exc
    lines = [line.strip() for line in (lyric_result.lyrics or "").splitlines() if line.strip()]
    return lyric_result, instrumental, lines


def preview(provider: str, catalog_id: int | str, metadata: deez.TrackMetadata) -> LyricsPreviewData:
    _lyric_result, instrumental, lines = fetch(metadata)
    return LyricsPreviewData(
        provider=provider, catalog_id=catalog_id, instrumental=instrumental,
        lines=[LyricsLine(index=index, text=line) for index, line in enumerate(lines, start=1)],
    )


def select(metadata: deez.TrackMetadata, request: TrackPosterRequest) -> str:
    if request.lyrics is not None:
        return request.lyrics.strip()
    lyric_result, instrumental, nonempty_lines = fetch(metadata)
    if instrumental:
        return request.instrumental_text.strip()
    if request.lyrics_range is not None:
        return lyric_result.select_lines(request.lyrics_range)
    if len(nonempty_lines) < 4:
        raise UpstreamError("Fewer than four non-empty lyric lines were available")
    return "\n".join(nonempty_lines[:4])
