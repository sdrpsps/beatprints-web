"""QQ Music lyrics source adapter."""

import html

import httpx

from BeatPrints import deez

from beatprints_api.exceptions import LyricsNotFoundError, UpstreamError
from beatprints_api.integrations.lyrics.base import (
    LyricsSourceAdapter,
    LyricsSourceResult,
)
from beatprints_api.integrations.lyrics.common import (
    confident_track_match,
    instrumental_text,
    lrc_lines,
    search_title_variants,
)
from beatprints_api.integrations.lyrics.registry import register

SEARCH_URL = "https://c.y.qq.com/soso/fcgi-bin/client_search_cp"
LYRICS_URL = "https://c.y.qq.com/lyric/fcgi-bin/fcg_query_lyric_new.fcg"
_HEADERS = {
    "Referer": "https://y.qq.com/",
    "User-Agent": "BeatPrints-API/1.1",
}


def _get_json(url: str, **params: object) -> dict:
    try:
        response = httpx.get(
            url,
            params=params,
            headers=_HEADERS,
            timeout=15.0,
            follow_redirects=True,
        )
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise UpstreamError(f"QQ Music lyrics request failed: {exc}") from exc
    if not isinstance(payload, dict):
        raise UpstreamError("QQ Music lyrics source returned an invalid response")
    if payload.get("code") not in (None, 0) or payload.get("retcode") not in (
        None,
        0,
    ):
        raise UpstreamError("QQ Music lyrics source returned an error response")
    return payload


def _artists(row: dict) -> list[str]:
    values = row.get("singer") or []
    if not isinstance(values, list):
        return []
    return [
        str(value["name"])
        for value in values
        if isinstance(value, dict) and value.get("name")
    ]


def _album_name(row: dict) -> object:
    album = row.get("album") or {}
    return row.get("albumname") or (
        album.get("name") if isinstance(album, dict) else None
    )


def _select_song(payload: dict, metadata: deez.TrackMetadata) -> str | None:
    data = payload.get("data") or {}
    if not isinstance(data, dict):
        return None
    song = data.get("song") or {}
    rows = song.get("list") if isinstance(song, dict) else []
    if not isinstance(rows, list):
        return None
    for row in rows:
        if not isinstance(row, dict):
            continue
        duration = row.get("interval")
        if row.get("songmid") and confident_track_match(
            metadata,
            title=row.get("songname") or row.get("title"),
            artists=_artists(row),
            album=_album_name(row),
            candidate_duration_seconds=duration if isinstance(duration, int) else None,
        ):
            return str(row["songmid"])
    return None


def fetch(metadata: deez.TrackMetadata) -> LyricsSourceResult:
    song_mid = None
    for title in search_title_variants(metadata.title):
        query = " ".join([title, *metadata.artists])
        song_mid = _select_song(
            _get_json(
                SEARCH_URL,
                format="json",
                p=1,
                n=10,
                w=query,
                t=0,
            ),
            metadata,
        )
        if song_mid is not None:
            break
    if song_mid is None:
        raise LyricsNotFoundError("No confident QQ Music lyrics match was found")

    payload = _get_json(
        LYRICS_URL,
        songmid=song_mid,
        format="json",
        nobase64=1,
        g_tk=5381,
    )
    lines = lrc_lines(html.unescape(str(payload.get("lyric") or "")))
    if len(lines) <= 2 and any(instrumental_text(line) for line in lines):
        return LyricsSourceResult(instrumental=True, lines=())
    if not lines:
        raise LyricsNotFoundError("No lyrics were found for this QQ Music recording")
    return LyricsSourceResult(instrumental=False, lines=lines)


adapter = register(
    LyricsSourceAdapter(key="qq_music", label="QQ 音乐", fetch=fetch), default=True
)
