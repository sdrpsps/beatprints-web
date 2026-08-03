"""NetEase Cloud Music lyrics source adapter."""

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

SEARCH_URL = "https://music.163.com/api/search/get"
LYRICS_URL = "https://music.163.com/api/song/lyric/v1"
_HEADERS = {
    "Referer": "https://music.163.com",
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
        raise UpstreamError(f"NetEase lyrics request failed: {exc}") from exc
    if not isinstance(payload, dict):
        raise UpstreamError("NetEase lyrics source returned an invalid response")
    if payload.get("code") not in (None, 200):
        raise UpstreamError(
            f"NetEase lyrics source returned error code {payload.get('code')}"
        )
    return payload


def _artists(row: dict) -> list[str]:
    values = row.get("artists") or []
    if not isinstance(values, list):
        return []
    return [
        str(value["name"])
        for value in values
        if isinstance(value, dict) and value.get("name")
    ]


def _select_song(payload: dict, metadata: deez.TrackMetadata) -> int | None:
    result = payload.get("result") or {}
    if not isinstance(result, dict):
        return None
    rows = result.get("songs") or []
    if not isinstance(rows, list):
        return None
    for row in rows:
        if not isinstance(row, dict):
            continue
        album = row.get("album") or {}
        if not isinstance(album, dict):
            album = {}
        duration_ms = row.get("duration")
        duration = round(duration_ms / 1000) if isinstance(duration_ms, int) else None
        if row.get("id") and confident_track_match(
            metadata,
            title=row.get("name"),
            artists=_artists(row),
            album=album.get("name"),
            candidate_duration_seconds=duration,
        ):
            return int(row["id"])
    return None


def fetch(metadata: deez.TrackMetadata) -> LyricsSourceResult:
    song_id = None
    for title in search_title_variants(metadata.title):
        query = " ".join([title, *metadata.artists])
        song_id = _select_song(
            _get_json(SEARCH_URL, s=query, type=1, limit=10, offset=0), metadata
        )
        if song_id is not None:
            break
    if song_id is None:
        raise LyricsNotFoundError("No confident NetEase lyrics match was found")

    payload = _get_json(LYRICS_URL, id=song_id, lv=-1, kv=-1, tv=-1, yv=1)
    if payload.get("pureMusic") is True:
        return LyricsSourceResult(instrumental=True, lines=())

    lrc = payload.get("lrc") or {}
    raw_lyrics = lrc.get("lyric") if isinstance(lrc, dict) else None
    lines = lrc_lines(raw_lyrics)
    if len(lines) <= 2 and any(instrumental_text(line) for line in lines):
        return LyricsSourceResult(instrumental=True, lines=())
    if not lines:
        raise LyricsNotFoundError("No lyrics were found for this NetEase recording")
    return LyricsSourceResult(instrumental=False, lines=lines)


adapter = register(LyricsSourceAdapter(key="netease", label="网易云音乐", fetch=fetch))
