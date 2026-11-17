"""NetEase Cloud Music destination adapter."""

from pathlib import Path
from urllib.parse import parse_qs, urlparse

from beatprints_api.integrations.clients.netease_music import netease_music_client
from beatprints_api.integrations.destinations.base import DestinationAdapter
from beatprints_api.integrations.destinations.registry import register
from beatprints_api.integrations.destinations.scannable import (
    icon_qr_scannable,
    standard_icon_qr_scannable,
)
from beatprints_api.exceptions import PlatformLinkNoMatchError, UpstreamError
from beatprints_api.models.destinations import PlatformLinkMatchData

ASSET_PATH = Path(__file__).resolve().parents[2] / "assets" / "netease-music-symbol.png"


def _artists(values: list[dict] | None) -> list[str]:
    return [str(value["name"]) for value in values or [] if value.get("name")]


def _year(value: object) -> int | None:
    text = str(value or "")
    if text.isdigit() and len(text) >= 10:
        from datetime import datetime

        return datetime.fromtimestamp(int(text[:10])).year
    try:
        return int(text[:4])
    except ValueError:
        return None


def search(query: str, item_type: str) -> list[dict]:
    payload = netease_music_client.search(query, item_type, 10)
    result = payload.get("result") or {}
    if not isinstance(result, dict):
        return []
    rows = result.get("songs", []) if item_type == "track" else result.get("albums", [])
    output: list[dict] = []
    for row in rows:
        if item_type == "track" and row.get("id"):
            album = row.get("album") or {}
            output.append(
                {
                    "platform_id": row["id"],
                    "title": row.get("name"),
                    "artists": _artists(row.get("artists")),
                    "album": album.get("name"),
                    "duration_seconds": round((row.get("duration") or 0) / 1000),
                    "release_year": _year(album.get("publishTime")),
                    "cover_url": album.get("picUrl"),
                    "url": f"https://music.163.com/#/song?id={row['id']}",
                    "type": "track",
                }
            )
        elif item_type == "album" and row.get("id"):
            output.append(
                {
                    "platform_id": row["id"],
                    "title": row.get("name"),
                    "artists": _artists(row.get("artists")),
                    "release_year": _year(row.get("publishTime")),
                    "track_count": row.get("size"),
                    "cover_url": row.get("picUrl"),
                    "url": f"https://music.163.com/#/album?id={row['id']}",
                    "type": "album",
                }
            )
    return output


def _id_from_url(url: str) -> tuple[str, str] | None:
    parsed = urlparse(url)
    hostname = (parsed.hostname or "").lower()
    if not (hostname == "music.163.com" or hostname.endswith(".music.163.com")):
        return None
    params = parse_qs(parsed.query or parsed.fragment.split("?", 1)[-1])
    item_id = (params.get("id") or [None])[0]
    if item_id:
        return (
            "album" if "album" in (parsed.path + parsed.fragment) else "track"
        ), item_id
    return None


def resolve(url: str) -> PlatformLinkMatchData:
    parsed = _id_from_url(url)
    if not parsed:
        raise PlatformLinkNoMatchError(
            "URL is not a supported NetEase Music track or album link"
        )
    item_type, item_id = parsed
    if item_type == "track":
        rows = netease_music_client.tracks([item_id]).get("songs") or []
        if not rows:
            raise PlatformLinkNoMatchError("NetEase Music track was not found")
        row = rows[0]
        album = row.get("album") or {}
        return PlatformLinkMatchData(
            title=row.get("name"),
            artists=_artists(row.get("artists")),
            album=album.get("name"),
            duration_seconds=round((row.get("duration") or 0) / 1000),
            cover_url=album.get("picUrl"),
            url=f"https://music.163.com/#/song?id={item_id}",
            type="track",
        )
    data = netease_music_client.album(item_id)
    album = data.get("album") or {}
    if not album:
        raise PlatformLinkNoMatchError("NetEase Music album was not found")
    if not isinstance(album, dict) or not album.get("name"):
        raise UpstreamError("NetEase Music album response was incomplete")
    return PlatformLinkMatchData(
        title=album.get("name"),
        artists=_artists(album.get("artists")),
        release_year=_year(album.get("publishTime")),
        track_count=album.get("size") or len(data.get("songs") or []),
        cover_url=album.get("picUrl"),
        url=f"https://music.163.com/#/album?id={item_id}",
        type="album",
    )


def _resolve_source(
    provider: str, catalog_id: int | str, item_type: str
) -> PlatformLinkMatchData | None:
    if provider != "netease_music":
        return None
    path = "song" if item_type == "track" else "album"
    return resolve(f"https://music.163.com/#/{path}?id={catalog_id}")


adapter = register(
    DestinationAdapter(
        key="netease_music",
        label="网易云音乐",
        search=search,
        resolve=resolve,
        scannable=lambda link: icon_qr_scannable(
            link, ASSET_PATH, version="2", mask=24, margin=19
        ),
        standard_scannable=lambda link: standard_icon_qr_scannable(link, ASSET_PATH),
        resolve_source=_resolve_source,
        reuses_source_link=lambda provider: provider == "netease_music",
    )
)
