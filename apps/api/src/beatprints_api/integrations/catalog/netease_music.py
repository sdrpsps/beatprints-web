"""NetEase Cloud Music source catalog adapter."""

from datetime import UTC, datetime

import httpx

from BeatPrints import deez
from beatprints_api.exceptions import UpstreamError
from beatprints_api.integrations.catalog.base import CatalogAdapter
from beatprints_api.integrations.catalog.registry import register

SEARCH_URL = "https://music.163.com/api/search/get"
TRACK_URL = "https://music.163.com/api/song/detail/"
ALBUM_URL = "https://music.163.com/api/v1/album"


def _get(url: str, **params: object) -> dict:
    try:
        response = httpx.get(
            url,
            params=params,
            headers={
                "Referer": "https://music.163.com",
                "User-Agent": "BeatPrints-API/1.1",
            },
            timeout=15.0,
            follow_redirects=True,
        )
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise UpstreamError(f"NetEase Music catalog request failed: {exc}") from exc
    if not isinstance(payload, dict):
        raise UpstreamError("NetEase Music catalog returned an invalid response")
    return payload


def _artists(values: object) -> list[str]:
    if not isinstance(values, list):
        return []
    return [
        str(value["name"])
        for value in values
        if isinstance(value, dict) and value.get("name")
    ]


def _released(value: object) -> str:
    if isinstance(value, (int, float)) and value > 0:
        return datetime.fromtimestamp(value / 1000, tz=UTC).date().isoformat()
    text = str(value or "").strip()
    return text if text else ""


def _year(value: object) -> int | None:
    try:
        return int(_released(value)[:4])
    except ValueError:
        return None


def _duration(milliseconds: object) -> tuple[int, str]:
    seconds = round(int(milliseconds or 0) / 1000)
    minutes, remaining_seconds = divmod(seconds, 60)
    return seconds, f"{minutes:02d}:{remaining_seconds:02d}"


def _secure_url(value: object) -> str | None:
    url = str(value or "").strip()
    return url.replace("http://", "https://", 1) or None


def _label(album: dict) -> str:
    value = str(album.get("company") or "").strip()
    return "" if value.casefold() in {"unknown", "unknown label", "0"} else value


def _track_result(row: dict) -> dict | None:
    song_id = row.get("id")
    album = row.get("album") or {}
    title = row.get("name")
    cover_url = _secure_url(album.get("picUrl"))
    if (
        not song_id
        or not title
        or not isinstance(album, dict)
        or not album.get("name")
        or not cover_url
    ):
        return None
    seconds, duration = _duration(row.get("duration"))
    released = _released(album.get("publishTime"))
    return {
        "id": str(song_id),
        "provider": "netease_music",
        "type": "track",
        "title": title,
        "artists": _artists(row.get("artists")),
        "cover_url": cover_url,
        "link": f"https://music.163.com/#/song?id={song_id}",
        "release_date": released or None,
        "release_year": _year(released),
        "release_date_precision": "day" if released else None,
        "album": {"id": str(album.get("id") or ""), "title": album["name"]},
        "duration_seconds": seconds,
        "duration": duration,
    }


def _album_result(row: dict) -> dict | None:
    album_id = row.get("id")
    title = row.get("name")
    cover_url = _secure_url(row.get("picUrl"))
    if not album_id or not title or not cover_url:
        return None
    released = _released(row.get("publishTime"))
    return {
        "id": str(album_id),
        "provider": "netease_music",
        "type": "album",
        "title": title,
        "artists": _artists(row.get("artists")),
        "cover_url": cover_url,
        "link": f"https://music.163.com/#/album?id={album_id}",
        "release_date": released or None,
        "release_year": _year(released),
        "release_date_precision": "day" if released else None,
        "track_count": row.get("size"),
    }


def search(query: str, item_type: str, limit: int) -> list[dict]:
    payload = _get(
        SEARCH_URL,
        type=1 if item_type == "track" else 10,
        s=query,
        limit=limit,
        offset=0,
    )
    result = payload.get("result") or {}
    if not isinstance(result, dict):
        return []
    rows = result.get("songs" if item_type == "track" else "albums") or []
    if item_type == "track" and isinstance(rows, list):
        ids = [
            str(row["id"]) for row in rows if isinstance(row, dict) and row.get("id")
        ]
        if ids:
            details = _get(TRACK_URL, ids=f"[{','.join(ids)}]").get("songs") or []
            detail_by_id = {
                str(row["id"]): row
                for row in details
                if isinstance(row, dict) and row.get("id")
            }
            rows = [
                (
                    detail_by_id.get(str(row.get("id")), row)
                    if isinstance(row, dict)
                    else row
                )
                for row in rows
            ]
    output: list[dict] = []
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, dict):
            continue
        normalized = _track_result(row) if item_type == "track" else _album_result(row)
        if normalized is not None:
            output.append(normalized)
    return output


def track_metadata(catalog_id: int | str) -> deez.TrackMetadata:
    rows = _get(TRACK_URL, ids=f"[{catalog_id}]").get("songs") or []
    row = rows[0] if isinstance(rows, list) and rows else None
    if not isinstance(row, dict):
        raise UpstreamError("NetEase Music track was not found")
    normalized = _track_result(row)
    if normalized is None or not normalized["title"]:
        raise UpstreamError("NetEase Music track response was incomplete")
    metadata = deez.TrackMetadata(
        title=normalized["title"],
        artists=normalized["artists"],
        album=normalized["album"]["title"],
        released=normalized["release_date"] or "",
        duration=normalized["duration"],
        cover=normalized["cover_url"],
        label=_label(row.get("album") or {}),
    )
    metadata.link = normalized["link"]
    return metadata


def album_metadata(catalog_id: int | str) -> deez.AlbumMetadata:
    data = _get(f"{ALBUM_URL}/{catalog_id}")
    album = data.get("album") or {}
    if not isinstance(album, dict):
        raise UpstreamError("NetEase Music album was not found")
    normalized = _album_result(album)
    tracks = [
        str(row["name"])
        for row in data.get("songs") or []
        if isinstance(row, dict) and row.get("name")
    ]
    if normalized is None or not normalized["title"] or not tracks:
        raise UpstreamError("NetEase Music album response was incomplete")
    metadata = deez.AlbumMetadata(
        title=normalized["title"],
        artists=normalized["artists"],
        released=normalized["release_date"] or "",
        tracks=tracks,
        cover=normalized["cover_url"],
        label=_label(album),
    )
    metadata.link = normalized["link"]
    return metadata


adapter = register(
    CatalogAdapter(
        key="netease_music",
        label="网易云音乐",
        configured=lambda: True,
        search=search,
        track_metadata=track_metadata,
        album_metadata=album_metadata,
    )
)
