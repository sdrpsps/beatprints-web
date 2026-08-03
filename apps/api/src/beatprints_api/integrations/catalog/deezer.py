"""Deezer source catalog adapter."""

import atexit

import deezer
import httpx

from BeatPrints import deez
from beatprints_api.integrations.catalog.base import CatalogAdapter
from beatprints_api.integrations.catalog.registry import register

_http = httpx.Client(
    timeout=httpx.Timeout(10.0, connect=5.0),
    headers={"User-Agent": "BeatPrints-API/0.1"},
)
atexit.register(_http.close)


def _normalized_label(value: object) -> str:
    label = str(value or "").strip()
    return "" if label.casefold() in {"unknown", "unknown label", "unknown records"} else label


def track_metadata(catalog_id: int | str) -> deez.TrackMetadata:
    metadata = deez.Deezer().get_track(int(catalog_id))
    metadata.label = _normalized_label(metadata.label)
    return metadata


def album_metadata(catalog_id: int | str) -> deez.AlbumMetadata:
    metadata = deez.Deezer().get_album(int(catalog_id), shuffle=False)
    metadata.label = _normalized_label(metadata.label)
    return metadata


def track_isrc(catalog_id: int | str, metadata: deez.TrackMetadata) -> str | None:
    value = getattr(metadata, "isrc", None)
    if value:
        return str(value)
    try:
        response = _http.get(f"https://api.deezer.com/track/{catalog_id}")
        response.raise_for_status()
        value = response.json().get("isrc")
        return str(value) if value else None
    except (httpx.HTTPError, ValueError):
        return None


def search(query: str, item_type: str, limit: int) -> list[dict]:
    client = deezer.Client()
    search_fn = client.search if item_type == "track" else client.search_albums
    results = search_fn(query)[:limit]
    formatted: list[dict] = []
    for item in results:
        data = item.as_dict()
        primary_artist = data.get("artist") or {}
        try:
            release_date = item.release_date
        except Exception:
            release_date = None
        try:
            artists = [artist.name for artist in item.contributors]
        except Exception:
            artists = [primary_artist["name"]] if primary_artist.get("name") else []

        if item_type == "track":
            album = data.get("album") or {}
            seconds = int(data.get("duration") or 0)
            minutes, remaining_seconds = divmod(seconds, 60)
            formatted.append({
                "id": data["id"], "provider": "deezer", "type": "track", "title": data["title"],
                "artists": artists, "cover_url": album.get("cover_xl") or album.get("cover_big"),
                "link": data["link"],
                "release_date": release_date.isoformat() if release_date is not None else None,
                "release_year": release_date.year if release_date is not None else None,
                "release_date_precision": "day", "album": {"id": album["id"], "title": album["title"]},
                "duration_seconds": seconds, "duration": f"{minutes:02d}:{remaining_seconds:02d}",
                "explicit": bool(data.get("explicit_lyrics")), "isrc": data.get("isrc"),
            })
        else:
            formatted.append({
                "id": data["id"], "provider": "deezer", "type": "album", "title": data["title"],
                "artists": artists, "cover_url": data.get("cover_xl") or data.get("cover_big"),
                "link": data["link"],
                "release_date": release_date.isoformat() if release_date is not None else None,
                "release_year": release_date.year if release_date is not None else None,
                "release_date_precision": "day", "explicit": bool(data.get("explicit_lyrics")),
                "track_count": data.get("nb_tracks"),
            })
    return formatted


adapter = register(CatalogAdapter(
    key="deezer", label="Deezer", configured=lambda: True, search=search,
    track_metadata=track_metadata, album_metadata=album_metadata, track_isrc=track_isrc,
))
