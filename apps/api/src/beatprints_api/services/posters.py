"""Poster-generation orchestration across catalog, lyrics, and rendering."""

import random
import time

from beatprints_api.models.poster import AlbumPosterRequest, TrackPosterRequest
from beatprints_api.services import catalog, lyrics, rendering


def _elapsed_ms(started_at: float) -> float:
    return (time.perf_counter() - started_at) * 1000


def generate_track(request: TrackPosterRequest) -> rendering.PosterResult:
    timings: dict[str, float] = {}
    started_at = time.perf_counter()
    metadata = catalog.track_metadata(request)
    timings["metadata"] = _elapsed_ms(started_at)
    started_at = time.perf_counter()
    selected_lyrics = lyrics.select(metadata, request)
    timings["lyrics"] = _elapsed_ms(started_at)
    started_at = time.perf_counter()
    result = rendering.render_track(request, metadata, selected_lyrics)
    timings["render"] = _elapsed_ms(started_at)
    return rendering.PosterResult(result.content, result.filename, timings)


def generate_album(request: AlbumPosterRequest) -> rendering.PosterResult:
    timings: dict[str, float] = {}
    started_at = time.perf_counter()
    metadata = catalog.album_metadata(request)
    if request.metadata is not None and request.shuffle:
        random.shuffle(metadata.tracks)
    timings["metadata"] = _elapsed_ms(started_at)
    started_at = time.perf_counter()
    result = rendering.render_album(request, metadata)
    timings["render"] = _elapsed_ms(started_at)
    return rendering.PosterResult(result.content, result.filename, timings)
