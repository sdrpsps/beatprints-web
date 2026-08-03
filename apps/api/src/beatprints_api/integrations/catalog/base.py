"""Contracts for independently enabled source music catalogs."""

from collections.abc import Callable
from dataclasses import dataclass

from BeatPrints import deez


@dataclass(frozen=True)
class CatalogAdapter:
    """One source catalog's search and metadata capabilities.

    The adapter owns source-specific API calls and normalization.  Core services
    consume only this contract, so an enabled catalog can be added or removed by
    changing the catalog registry imports.
    """

    key: str
    label: str
    configured: Callable[[], bool]
    search: Callable[[str, str, int], list[dict]]
    track_metadata: Callable[[int | str], deez.TrackMetadata]
    album_metadata: Callable[[int | str], deez.AlbumMetadata]
    track_isrc: Callable[[int | str, deez.TrackMetadata], str | None] = (
        lambda _catalog_id, metadata: getattr(metadata, "isrc", None)
    )
    cover_renderer: Callable[[str, str | None], object] | None = None
