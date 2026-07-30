"""Read public QQ Music and NetEase Cloud Music catalogue metadata.

These web catalogue endpoints are used only for destination-link matching; no
account, playback, or download API is called.
"""

from datetime import UTC, datetime
from urllib.parse import parse_qs, urlparse

import httpx


class ChinaMusicError(RuntimeError):
    pass


HEADERS = {"User-Agent": "BeatPrints-API/0.1", "Referer": "https://music.163.com/"}


def _year(value: object) -> int | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        numeric = int(text)
    except ValueError:
        numeric = None
    if numeric is not None:
        if numeric <= 0:
            return None
        if 1000 <= numeric <= 9999:
            return numeric
        try:
            timestamp = numeric / 1000 if numeric >= 10_000_000_000 else numeric
            return datetime.fromtimestamp(timestamp, tz=UTC).year
        except (ValueError, OSError):
            return None
    try:
        return int(text[:4])
    except ValueError:
        return None


def _get(url: str, **params: object) -> dict:
    try:
        response = httpx.get(url, params=params, headers=HEADERS, timeout=15.0)
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise ChinaMusicError(f"Chinese music catalogue request failed: {exc}") from exc
    if not isinstance(payload, dict):
        raise ChinaMusicError("Chinese music catalogue returned an invalid response")
    return payload


def _artists(values: list[dict] | None) -> list[str]:
    return [str(value["name"]) for value in values or [] if value.get("name")]


def _secure_url(value: object) -> str | None:
    url = str(value or "").strip()
    return f"https:{url}" if url.startswith("//") else url.replace("http://", "https://", 1) or None


def qq_search(query: str, item_type: str) -> list[dict]:
    payload = _get(
        "https://c.y.qq.com/soso/fcgi-bin/client_search_cp",
        format="json", p=1, n=10, w=query, t=0 if item_type == "track" else 8,
    )
    data = payload.get("data") or {}
    rows = (data.get("song") or {}).get("list", []) if item_type == "track" else (data.get("album") or {}).get("list", [])
    result: list[dict] = []
    for row in rows:
        if item_type == "track" and row.get("songmid"):
            result.append({"title": row.get("songname"), "artists": _artists(row.get("singer")), "album": row.get("albumname"), "duration_seconds": row.get("interval"), "release_year": _year(row.get("pubtime")), "cover_url": f"https://y.gtimg.cn/music/photo_new/T002R300x300M000{row.get('albummid')}.jpg", "url": f"https://y.qq.com/n/ryqq/songDetail/{row['songmid']}"})
        elif item_type == "album" and row.get("albumMID"):
            result.append({"title": row.get("albumName"), "artists": _artists(row.get("singer_list")), "release_year": _year(row.get("publicTime")), "track_count": row.get("song_count"), "cover_url": _secure_url(row.get("albumPic")), "url": f"https://y.qq.com/n/ryqq/albumDetail/{row['albumMID']}"})
    return result


def netease_search(query: str, item_type: str) -> list[dict]:
    payload = _get("https://music.163.com/api/search/get", type=1 if item_type == "track" else 10, s=query, limit=10, offset=0)
    result = payload.get("result") or {}
    if not isinstance(result, dict):
        return []
    rows = result.get("songs", []) if item_type == "track" else result.get("albums", [])
    output: list[dict] = []
    for row in rows:
        if item_type == "track" and row.get("id"):
            album = row.get("album") or {}
            output.append({"title": row.get("name"), "artists": _artists(row.get("artists")), "album": album.get("name"), "duration_seconds": round((row.get("duration") or 0) / 1000), "release_year": _year(album.get("publishTime")), "cover_url": album.get("picUrl"), "url": f"https://music.163.com/#/song?id={row['id']}"})
        elif item_type == "album" and row.get("id"):
            output.append({"title": row.get("name"), "artists": _artists(row.get("artists")), "release_year": _year(row.get("publishTime")), "track_count": row.get("size"), "cover_url": row.get("picUrl"), "url": f"https://music.163.com/#/album?id={row['id']}"})
    return output


def _id_from_url(url: str, platform: str) -> tuple[str, str] | None:
    parsed = urlparse(url)
    if platform == "qq_music":
        parts = [part for part in parsed.path.split("/") if part]
        for kind, item_type in (("songDetail", "track"), ("albumDetail", "album")):
            if kind in parts and parts.index(kind) + 1 < len(parts):
                return item_type, parts[parts.index(kind) + 1]
    if platform == "netease_music" and parsed.hostname and parsed.hostname.endswith("music.163.com"):
        params = parse_qs(parsed.query or parsed.fragment.split("?", 1)[-1])
        item_id = (params.get("id") or [None])[0]
        if item_id:
            return ("album" if "album" in (parsed.path + parsed.fragment) else "track"), item_id
    return None


def qq_resolve(url: str) -> dict:
    parsed = _id_from_url(url, "qq_music")
    if not parsed:
        raise ChinaMusicError("URL is not a supported QQ Music track or album link")
    item_type, item_id = parsed
    if item_type == "track":
        data = _get("https://c.y.qq.com/v8/fcg-bin/fcg_play_single_song.fcg", songmid=item_id, format="json").get("data") or []
        if not data: raise ChinaMusicError("QQ Music track was not found")
        row = data[0]; album = row.get("album") or {}
        return {"title": row.get("title"), "artists": _artists(row.get("singer")), "album": album.get("name"), "duration_seconds": row.get("interval"), "release_year": _year(row.get("time_public")), "cover_url": f"https://y.gtimg.cn/music/photo_new/T002R300x300M000{album.get('mid')}.jpg", "url": f"https://y.qq.com/n/ryqq/songDetail/{item_id}", "type": "track"}
    row = _get("https://c.y.qq.com/v8/fcg-bin/fcg_v8_album_info_cp.fcg", albummid=item_id, format="json").get("data") or {}
    singer_name = str(row.get("singername") or "").strip()
    return {"title": row.get("name"), "artists": [singer_name] if singer_name else [], "release_year": _year(row.get("aDate")), "track_count": row.get("total_song_num") or len(row.get("list") or []), "cover_url": f"https://y.gtimg.cn/music/photo_new/T002R300x300M000{item_id}.jpg", "url": f"https://y.qq.com/n/ryqq/albumDetail/{item_id}", "type": "album"}


def netease_resolve(url: str) -> dict:
    parsed = _id_from_url(url, "netease_music")
    if not parsed: raise ChinaMusicError("URL is not a supported NetEase Music track or album link")
    item_type, item_id = parsed
    if item_type == "track":
        rows = _get("https://music.163.com/api/song/detail/", ids=f"[{item_id}]").get("songs") or []
        if not rows: raise ChinaMusicError("NetEase Music track was not found")
        row = rows[0]; album = row.get("album") or {}
        return {"title": row.get("name"), "artists": _artists(row.get("artists")), "album": album.get("name"), "duration_seconds": round((row.get("duration") or 0) / 1000), "cover_url": album.get("picUrl"), "url": f"https://music.163.com/#/song?id={item_id}", "type": "track"}
    data = _get(f"https://music.163.com/api/v1/album/{item_id}"); album = data.get("album") or {}
    return {"title": album.get("name"), "artists": _artists(album.get("artists")), "release_year": _year(album.get("publishTime")), "track_count": album.get("size") or len(data.get("songs") or []), "cover_url": album.get("picUrl"), "url": f"https://music.163.com/#/album?id={item_id}", "type": "album"}
