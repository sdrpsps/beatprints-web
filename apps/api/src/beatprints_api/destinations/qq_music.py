"""QQ Music destination adapter."""

from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import httpx

from beatprints_api.destinations.base import DestinationAdapter
from beatprints_api.destinations.registry import register
from beatprints_api.destinations.scannable import icon_qr_scannable
from beatprints_api.exceptions import PlatformLinkNoMatchError, UpstreamError
from beatprints_api.models.dto import PlatformLinkMatchData

ASSET_PATH = Path(__file__).resolve().parents[1] / "assets" / "qq-music-symbol.png"


def _get(url: str, **params: object) -> dict:
    try:
        response = httpx.get(url, params=params, timeout=15.0)
        response.raise_for_status()
        value = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise UpstreamError(f"QQ Music request failed: {exc}") from exc
    return value if isinstance(value, dict) else {}


def _artists(values: list[dict] | None) -> list[str]:
    return [str(value["name"]) for value in values or [] if value.get("name")]


def _year(value: object) -> int | None:
    text = str(value or "")
    if text.isdigit() and len(text) >= 10:
        return datetime.fromtimestamp(int(text[:10])).year
    try:
        return int(text[:4])
    except ValueError:
        return None


def _cover(album_id: object) -> str:
    return f"https://y.gtimg.cn/music/photo_new/T002R300x300M000{album_id}.jpg"


def _secure_url(value: object) -> str | None:
    url = str(value or "").strip()
    return f"https:{url}" if url.startswith("//") else url.replace("http://", "https://", 1) or None


def search(query: str, item_type: str) -> list[dict]:
    payload = _get(
        "https://c.y.qq.com/soso/fcgi-bin/client_search_cp",
        format="json",
        p=1,
        n=10,
        w=query,
        t=0 if item_type == "track" else 8,
    )
    data = payload.get("data") or {}
    rows = (data.get("song") or {}).get("list", []) if item_type == "track" else (data.get("album") or {}).get("list", [])
    result: list[dict] = []
    for row in rows:
        if item_type == "track" and row.get("songmid"):
            result.append({
                "platform_id": row["songmid"], "title": row.get("songname"),
                "artists": _artists(row.get("singer")), "album": row.get("albumname"),
                "duration_seconds": row.get("interval"), "release_year": _year(row.get("pubtime")),
                "cover_url": _cover(row.get("albummid")),
                "url": f"https://y.qq.com/n/ryqq/songDetail/{row['songmid']}", "type": "track",
            })
        elif item_type == "album" and row.get("albumMID"):
            result.append({
                "platform_id": row["albumMID"], "title": row.get("albumName"),
                "artists": _artists(row.get("singer_list")), "release_year": _year(row.get("publicTime")),
                "track_count": row.get("song_count"), "cover_url": _secure_url(row.get("albumPic")),
                "url": f"https://y.qq.com/n/ryqq/albumDetail/{row['albumMID']}", "type": "album",
            })
    return result


def _id_from_url(url: str) -> tuple[str, str] | None:
    parsed = urlparse(url)
    hostname = (parsed.hostname or "").lower()
    if not (hostname == "y.qq.com" or hostname.endswith(".y.qq.com")):
        return None
    parts = [part for part in parsed.path.split("/") if part]
    for kind, item_type in (("songDetail", "track"), ("albumDetail", "album")):
        if kind in parts and parts.index(kind) + 1 < len(parts):
            return item_type, parts[parts.index(kind) + 1]
    return None


def resolve(url: str) -> PlatformLinkMatchData:
    parsed = _id_from_url(url)
    if not parsed:
        raise PlatformLinkNoMatchError("URL is not a supported QQ Music track or album link")
    item_type, item_id = parsed
    if item_type == "track":
        data = _get("https://c.y.qq.com/v8/fcg-bin/fcg_play_single_song.fcg", songmid=item_id, format="json").get("data") or []
        if not data:
            raise PlatformLinkNoMatchError("QQ Music track was not found")
        row = data[0]
        album = row.get("album") or {}
        return PlatformLinkMatchData(
            title=row.get("title"), artists=_artists(row.get("singer")), album=album.get("name"),
            duration_seconds=row.get("interval"), release_year=_year(row.get("time_public")),
            cover_url=_cover(album.get("mid")), url=f"https://y.qq.com/n/ryqq/songDetail/{item_id}", type="track",
        )
    row = _get("https://c.y.qq.com/v8/fcg-bin/fcg_v8_album_info_cp.fcg", albummid=item_id, format="json").get("data") or {}
    singer_name = str(row.get("singername") or "").strip()
    return PlatformLinkMatchData(
        title=row.get("name"), artists=[singer_name] if singer_name else [], release_year=_year(row.get("aDate")),
        track_count=row.get("total_song_num") or len(row.get("list") or []), cover_url=_cover(item_id),
        url=f"https://y.qq.com/n/ryqq/albumDetail/{item_id}", type="album",
    )


adapter = register(DestinationAdapter(key="qq_music", label="QQ 音乐", search=search, resolve=resolve, scannable=lambda link: icon_qr_scannable(link, ASSET_PATH)))
