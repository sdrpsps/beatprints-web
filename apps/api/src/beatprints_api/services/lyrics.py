"""Lyrics retrieval and selection for track poster generation."""

from BeatPrints import deez
from beatprints_api.exceptions import UpstreamError
from beatprints_api.integrations.lyrics import (
    default_lyrics_source,
    get_lyrics_source,
    lyrics_sources,
)
from beatprints_api.models.catalog import (
    LyricsLine,
    LyricsPreviewData,
    LyricsSourceData,
    LyricsSourcesData,
)
from beatprints_api.models.poster import TrackPosterRequest


def sources() -> LyricsSourcesData:
    default_source = default_lyrics_source()
    return LyricsSourcesData(
        sources=[
            LyricsSourceData(
                key=source.key,
                label=source.label,
                default=source.key == default_source.key,
            )
            for source in lyrics_sources()
        ]
    )


def preview(
    provider: str,
    catalog_id: int | str,
    metadata: deez.TrackMetadata,
    source: str | None = None,
) -> LyricsPreviewData:
    adapter = get_lyrics_source(source) if source else default_lyrics_source()
    result = adapter.fetch(metadata)
    return LyricsPreviewData(
        provider=provider,
        catalog_id=catalog_id,
        source=adapter.key,
        instrumental=result.instrumental,
        lines=[
            LyricsLine(index=index, text=line)
            for index, line in enumerate(result.lines, start=1)
        ],
    )


def select(metadata: deez.TrackMetadata, request: TrackPosterRequest) -> str:
    if request.lyrics is not None:
        return request.lyrics.strip()
    source = default_lyrics_source()
    if source.select_default is not None:
        return source.select_default(metadata, request)

    result = source.fetch(metadata)
    if result.instrumental:
        return request.instrumental_text.strip()
    lines = result.lines
    if request.lyrics_range is not None:
        start, end = (int(value) for value in request.lyrics_range.split("-"))
        lines = lines[start - 1:end]
    if len(lines) != 4:
        raise UpstreamError("Fewer than four non-empty lyric lines were available")
    return "\n".join(lines)
