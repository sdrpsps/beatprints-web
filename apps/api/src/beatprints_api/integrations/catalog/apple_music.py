"""Apple Music catalog search and current metadata via the iTunes catalog API."""

import httpx

from BeatPrints import deez
from beatprints_api.config import settings
from beatprints_api.exceptions import UpstreamError
from beatprints_api.integrations.catalog.base import CatalogAdapter
from beatprints_api.integrations.catalog.registry import register

SEARCH_URL = "https://itunes.apple.com/search"
LOOKUP_URL = "https://itunes.apple.com/lookup"


def _get(url: str, **params: object) -> list[dict]:
    try:
        response = httpx.get(url, params={**params, "country": settings.apple_music_storefront}, timeout=15.0)
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise UpstreamError(f"Apple Music catalog request failed: {exc}") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("results"), list):
        raise UpstreamError("Apple Music catalog returned an invalid response")
    return [row for row in payload["results"] if isinstance(row, dict)]


def _normalize(row: dict, item_type: str) -> dict | None:
    track = item_type == "track"
    if row.get("wrapperType") != ("track" if track else "collection"):
        return None
    identifier = row.get("trackId" if track else "collectionId")
    title = row.get("trackName" if track else "collectionName")
    link = row.get("trackViewUrl" if track else "collectionViewUrl")
    cover = row.get("artworkUrl100")
    if not identifier or not title or not link or not cover or (track and not row.get("collectionName")):
        return None
    date = str(row.get("releaseDate") or "")[:10]
    try:
        year = int(date[:4])
    except ValueError:
        year = None
    result = {
        "id": str(identifier), "provider": "apple_music", "type": item_type,
        "title": title, "artists": [row["artistName"]] if row.get("artistName") else [],
        "cover_url": str(cover).replace("100x100", "600x600"), "link": link,
        "release_date": date or None, "release_year": year,
        "release_date_precision": "day" if date else None,
    }
    if track:
        seconds = round((row.get("trackTimeMillis") or 0) / 1000)
        result.update(album={"id": str(row.get("collectionId") or ""), "title": row["collectionName"]},
                      duration_seconds=seconds, duration=f"{seconds // 60:02d}:{seconds % 60:02d}",
                      explicit=row.get("trackExplicitness") == "explicit")
    else:
        result["track_count"] = row.get("trackCount")
    return result


def search(query: str, item_type: str, limit: int) -> list[dict]:
    rows = _get(SEARCH_URL, term=query, media="music", entity="song" if item_type == "track" else "album", limit=limit)
    return [item for row in rows if (item := _normalize(row, item_type)) is not None]


def _lookup(catalog_id: int | str, item_type: str) -> tuple[dict, list[dict]]:
    params = {"id": str(catalog_id)}
    if item_type == "album":
        params["entity"] = "song"
        params["limit"] = 200
    rows = _get(LOOKUP_URL, **params)
    for row in rows:
        item = _normalize(row, item_type)
        if item and item["id"] == str(catalog_id):
            return item, rows
    raise UpstreamError(f"Apple Music {item_type} was not found or was incomplete")


def track_metadata(catalog_id: int | str) -> deez.TrackMetadata:
    item, _ = _lookup(catalog_id, "track")
    metadata = deez.TrackMetadata(title=item["title"], artists=item["artists"], album=item["album"]["title"],
                                  released=item["release_date"] or "", duration=item["duration"],
                                  cover=item["cover_url"], label="")
    metadata.link = item["link"]
    return metadata


def album_metadata(catalog_id: int | str) -> deez.AlbumMetadata:
    item, rows = _lookup(catalog_id, "album")
    tracks = [str(row["trackName"]) for row in rows if row.get("wrapperType") == "track" and row.get("trackName")]
    if not tracks:
        raise UpstreamError("Apple Music album response contained no tracks")
    metadata = deez.AlbumMetadata(title=item["title"], artists=item["artists"], released=item["release_date"] or "",
                                  tracks=tracks, cover=item["cover_url"], label="")
    metadata.link = item["link"]
    return metadata


adapter = register(CatalogAdapter(key="apple_music", label="Apple Music", configured=lambda: True,
                                  search=search, track_metadata=track_metadata, album_metadata=album_metadata))
