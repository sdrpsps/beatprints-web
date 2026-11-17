"""Apple Music catalog search and exact-ID metadata via its web catalog."""

from BeatPrints import deez

from beatprints_api.exceptions import UpstreamError
from beatprints_api.integrations.apple_music_client import apple_music_client
from beatprints_api.integrations.catalog.base import CatalogAdapter
from beatprints_api.integrations.catalog.registry import register
from beatprints_api.integrations.regions.apple_music import REGIONS


def search(query: str, item_type: str, limit: int) -> list[dict]:
    rows = apple_music_client.search(query, item_type, limit)
    results = [
        item
        for row in rows
        if (item := apple_music_client.normalize(row, item_type)) is not None
    ]
    if rows and not results:
        raise UpstreamError("Apple Music search returned incomplete results")
    return results


def _lookup(catalog_id: int | str, item_type: str, include: str) -> tuple[dict, dict]:
    row = apple_music_client.item(catalog_id, item_type, include=include)
    item = apple_music_client.normalize(row, item_type)
    if item is None:
        raise UpstreamError(f"Apple Music {item_type} metadata was incomplete")
    return item, row


def track_metadata(catalog_id: int | str) -> deez.TrackMetadata:
    item, _ = _lookup(catalog_id, "track", "albums")
    label = ""
    album_id = item["album"]["id"]
    if album_id:
        try:
            label = apple_music_client.album_label(
                apple_music_client.item(album_id, "album")
            )
        except UpstreamError:
            # Missing optional label data must not prevent poster generation.
            pass
    metadata = deez.TrackMetadata(
        title=item["title"],
        artists=item["artists"],
        album=item["album"]["title"],
        released=item["release_date"] or "",
        duration=item["duration"],
        cover=item["cover_url"],
        label=label,
    )
    metadata.link = item["link"]
    metadata.isrc = item["isrc"]
    return metadata


def album_metadata(catalog_id: int | str) -> deez.AlbumMetadata:
    item, row = _lookup(catalog_id, "album", "tracks")
    metadata = deez.AlbumMetadata(
        title=item["title"],
        artists=item["artists"],
        released=item["release_date"] or "",
        tracks=apple_music_client.album_tracks(row),
        cover=item["cover_url"],
        label=apple_music_client.album_label(row),
    )
    metadata.link = item["link"]
    return metadata


adapter = register(
    CatalogAdapter(
        key="apple_music",
        label="Apple Music",
        supports_regions=True,
        regions=REGIONS,
        configured=lambda: True,
        search=search,
        track_metadata=track_metadata,
        album_metadata=album_metadata,
    )
)
