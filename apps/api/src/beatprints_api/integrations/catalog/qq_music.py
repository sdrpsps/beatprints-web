"""QQ Music source catalog adapter."""

from datetime import UTC, datetime

import httpx

from BeatPrints import deez
from beatprints_api.exceptions import UpstreamError
from beatprints_api.integrations.catalog.base import CatalogAdapter
from beatprints_api.integrations.catalog.registry import register

SEARCH_URL = "https://c.y.qq.com/soso/fcgi-bin/client_search_cp"
TRACK_URL = "https://c.y.qq.com/v8/fcg-bin/fcg_play_single_song.fcg"
ALBUM_URL = "https://c.y.qq.com/v8/fcg-bin/fcg_v8_album_info_cp.fcg"


def _get(url: str, **params: object) -> dict:
    try:
        response = httpx.get(url, params=params, timeout=15.0)
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise UpstreamError(f"QQ Music catalog request failed: {exc}") from exc
    if not isinstance(payload, dict):
        raise UpstreamError("QQ Music catalog returned an invalid response")
    return payload


def _artists(values: object) -> list[str]:
    if not isinstance(values, list):
        return []
    return [
        str(value["name"])
        for value in values
        if isinstance(value, dict) and value.get("name")
    ]


def _album_artists(row: dict) -> list[str]:
    artists = _artists(row.get("singer_list")) or _artists(row.get("singer"))
    if artists:
        return artists
    singer_name = str(row.get("singername") or "").strip()
    return [singer_name] if singer_name else []


def _released(value: object) -> str:
    if isinstance(value, (int, float)) and value > 0:
        seconds = value / 1000 if value > 10_000_000_000 else value
        return datetime.fromtimestamp(seconds, tz=UTC).date().isoformat()
    text = str(value or "").strip()
    if text.isdigit() and int(text) > 0:
        seconds = int(text)
        if seconds > 10_000_000_000:
            seconds //= 1000
        return datetime.fromtimestamp(seconds, tz=UTC).date().isoformat()
    return text if text else ""


def _year(value: object) -> int | None:
    text = _released(value)
    try:
        return int(text[:4])
    except ValueError:
        return None


def _duration(seconds: object) -> tuple[int, str]:
    value = int(seconds or 0)
    minutes, remaining_seconds = divmod(value, 60)
    return value, f"{minutes:02d}:{remaining_seconds:02d}"


def _cover(album_id: object) -> str:
    return f"https://y.gtimg.cn/music/photo_new/T002R300x300M000{album_id}.jpg"


def _label(row: dict) -> str:
    company = str(row.get("company") or "").strip()
    company_new = row.get("company_new") or {}
    company_name = (
        str(company_new.get("name") or "").strip()
        if isinstance(company_new, dict)
        else ""
    )
    for value in (company, company_name):
        if value and value.casefold() not in {"0", "unknown", "unknown label"}:
            return value
    return ""


def _track_result(row: dict) -> dict | None:
    songmid = row.get("songmid") or row.get("mid")
    album = row.get("album") or {}
    album_mid = row.get("albummid") or album.get("mid")
    title = row.get("songname") or row.get("title")
    album_title = row.get("albumname") or album.get("name")
    if not songmid or not album_mid or not title or not album_title:
        return None
    seconds, duration = _duration(row.get("interval"))
    released = _released(row.get("pubtime") or row.get("time_public"))
    return {
        "id": str(songmid),
        "provider": "qq_music",
        "type": "track",
        "title": title,
        "artists": _artists(row.get("singer")),
        "cover_url": _cover(album_mid),
        "link": f"https://y.qq.com/n/ryqq/songDetail/{songmid}",
        "release_date": released or None,
        "release_year": _year(released),
        "release_date_precision": "day" if released else None,
        "album": {"id": str(album.get("mid") or album_mid), "title": album_title},
        "duration_seconds": seconds,
        "duration": duration,
    }


def _album_result(row: dict) -> dict | None:
    album_mid = row.get("albumMID") or row.get("mid")
    title = row.get("albumName") or row.get("name")
    if not album_mid or not title:
        return None
    released = _released(row.get("publicTime") or row.get("aDate"))
    return {
        "id": str(album_mid),
        "provider": "qq_music",
        "type": "album",
        "title": title,
        "artists": _album_artists(row),
        "cover_url": _cover(album_mid),
        "link": f"https://y.qq.com/n/ryqq/albumDetail/{album_mid}",
        "release_date": released or None,
        "release_year": _year(released),
        "release_date_precision": "day" if released else None,
        "track_count": row.get("song_count") or row.get("total_song_num"),
    }


def search(query: str, item_type: str, limit: int) -> list[dict]:
    payload = _get(
        SEARCH_URL,
        format="json",
        p=1,
        n=limit,
        w=query,
        t=0 if item_type == "track" else 8,
    )
    data = payload.get("data") or {}
    if not isinstance(data, dict):
        return []
    section = data.get("song" if item_type == "track" else "album") or {}
    rows = section.get("list") if isinstance(section, dict) else []
    result: list[dict] = []
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, dict):
            continue
        normalized = _track_result(row) if item_type == "track" else _album_result(row)
        if normalized is not None:
            result.append(normalized)
    return result


def track_metadata(catalog_id: int | str) -> deez.TrackMetadata:
    data = _get(TRACK_URL, songmid=str(catalog_id), format="json").get("data") or []
    row = data[0] if isinstance(data, list) and data else None
    if not isinstance(row, dict):
        raise UpstreamError("QQ Music track was not found")
    normalized = _track_result(row)
    if (
        normalized is None
        or not normalized["title"]
        or not normalized["album"]["title"]
    ):
        raise UpstreamError("QQ Music track response was incomplete")
    try:
        album = (
            _get(
                ALBUM_URL,
                albummid=normalized["album"]["id"],
                format="json",
            ).get("data")
            or {}
        )
    except UpstreamError:
        album = {}
    metadata = deez.TrackMetadata(
        title=normalized["title"],
        artists=normalized["artists"],
        album=normalized["album"]["title"],
        released=normalized["release_date"] or "",
        duration=normalized["duration"],
        cover=normalized["cover_url"],
        label=_label(album) if isinstance(album, dict) else "",
    )
    metadata.link = normalized["link"]
    return metadata


def album_metadata(catalog_id: int | str) -> deez.AlbumMetadata:
    data = _get(ALBUM_URL, albummid=str(catalog_id), format="json").get("data") or {}
    if not isinstance(data, dict):
        raise UpstreamError("QQ Music album was not found")
    normalized = _album_result(data)
    tracks = [
        str(row.get("title") or row["songname"])
        for row in data.get("list") or []
        if isinstance(row, dict) and (row.get("title") or row.get("songname"))
    ]
    if normalized is None or not normalized["title"] or not tracks:
        raise UpstreamError("QQ Music album response was incomplete")
    metadata = deez.AlbumMetadata(
        title=normalized["title"],
        artists=normalized["artists"],
        released=normalized["release_date"] or "",
        tracks=tracks,
        cover=normalized["cover_url"],
        label=_label(data),
    )
    metadata.link = normalized["link"]
    return metadata


adapter = register(
    CatalogAdapter(
        key="qq_music",
        label="QQ 音乐",
        configured=lambda: True,
        search=search,
        track_metadata=track_metadata,
        album_metadata=album_metadata,
    )
)
