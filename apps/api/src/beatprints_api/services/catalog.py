"""Source catalog orchestration independent of individual music platforms."""

import copy
import random
import time
from functools import lru_cache

from BeatPrints import deez
from beatprints_api.config import settings
from beatprints_api.exceptions import UpstreamError
from beatprints_api.integrations.catalog import catalog_adapters, get_catalog_adapter
from beatprints_api.models.dto import AlbumPosterRequest, TrackPosterRequest


def _metadata_cache_token() -> int:
    return int(time.monotonic() // settings.metadata_cache_ttl_seconds)


@lru_cache(maxsize=settings.metadata_cache_max_entries)
def _cached_track_metadata(
    provider: str, track_id: int | str, _cache_token: int
) -> deez.TrackMetadata:
    return get_catalog_adapter(provider).track_metadata(track_id)


@lru_cache(maxsize=settings.metadata_cache_max_entries)
def _cached_album_metadata(
    provider: str, album_id: int | str, _cache_token: int
) -> deez.AlbumMetadata:
    return get_catalog_adapter(provider).album_metadata(album_id)


def _catalog_reference(
    request: TrackPosterRequest | AlbumPosterRequest, item_type: str
) -> tuple[str, int | str]:
    if request.catalog_id is not None:
        return request.provider, request.catalog_id
    results = search_catalog(request.query or "", item_type, 1, request.provider)
    if not results:
        raise UpstreamError(f"No matching {item_type} found")
    return request.provider, results[0]["id"]


def track_metadata(request: TrackPosterRequest) -> deez.TrackMetadata:
    if request.metadata is not None:
        value = request.metadata
        return deez.TrackMetadata(
            title=value.title, artists=value.artists, album=value.album,
            released=value.released, duration=value.duration, cover=str(value.cover_url),
            label=value.label,
        )
    provider, track_id = _catalog_reference(request, "track")
    return copy.deepcopy(_cached_track_metadata(provider, track_id, _metadata_cache_token()))


def album_metadata(request: AlbumPosterRequest) -> deez.AlbumMetadata:
    if request.metadata is not None:
        value = request.metadata
        return deez.AlbumMetadata(
            title=value.title, artists=value.artists, released=value.released,
            tracks=value.tracks.copy(), cover=str(value.cover_url), label=value.label,
        )
    provider, album_id = _catalog_reference(request, "album")
    metadata = copy.deepcopy(_cached_album_metadata(provider, album_id, _metadata_cache_token()))
    if request.shuffle:
        random.shuffle(metadata.tracks)
    return metadata


def source_isrc(
    provider: str, catalog_id: int | str, metadata: deez.TrackMetadata
) -> str | None:
    value = get_catalog_adapter(provider).track_isrc(catalog_id, metadata)
    return str(value) if value else None


def clear_metadata_cache() -> None:
    _cached_track_metadata.cache_clear()
    _cached_album_metadata.cache_clear()


def search_catalog(
    query: str, item_type: str, limit: int, provider: str
) -> list[dict]:
    if provider != "all":
        adapter = get_catalog_adapter(provider)
        return adapter.search(query, item_type, limit)
    results: list[dict] = []
    for adapter in catalog_adapters():
        if adapter.configured():
            results.extend(adapter.search(query, item_type, limit))
    return results
