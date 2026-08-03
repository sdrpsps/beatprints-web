"""LrcApi-backed lyrics source adapter."""

import atexit
import re
import unicodedata

import httpx

from BeatPrints import deez

from beatprints_api.config import settings
from beatprints_api.exceptions import UpstreamError
from beatprints_api.integrations.lyrics.base import LyricsSourceAdapter, LyricsSourceResult
from beatprints_api.integrations.lyrics.registry import register

_http = httpx.Client(
    timeout=httpx.Timeout(10.0, connect=5.0),
    headers={"User-Agent": "BeatPrints-API/0.1"},
)
atexit.register(_http.close)

_TIMESTAMP = re.compile(r"\[\d{1,2}:\d{2}(?:\.\d{1,3})?\]")
_METADATA_LINE = re.compile(r"^\[[A-Za-z]{1,12}:.+\]\s*$")


def _normal(value: object) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).casefold()
    return "".join(character for character in text if character.isalnum())


def _metadata_artists(metadata: deez.TrackMetadata) -> list[str]:
    artists = getattr(metadata, "artists", []) or []
    if isinstance(artists, str):
        return [artists]
    return [str(artist) for artist in artists if str(artist).strip()]


def _is_confident_match(candidate: object, metadata: deez.TrackMetadata) -> bool:
    if not isinstance(candidate, dict):
        return False
    if _normal(candidate.get("title")) != _normal(getattr(metadata, "title", "")):
        return False
    candidate_artist = _normal(candidate.get("artist"))
    return bool(candidate_artist) and any(
        _normal(artist) == candidate_artist for artist in _metadata_artists(metadata)
    )


def _lines(lrc: str) -> tuple[str, ...]:
    lines: list[str] = []
    for raw_line in lrc.splitlines():
        if _METADATA_LINE.match(raw_line):
            continue
        text = _TIMESTAMP.sub("", raw_line).strip()
        if text:
            lines.append(text)
    return tuple(lines)


def fetch(metadata: deez.TrackMetadata) -> LyricsSourceResult:
    artists = _metadata_artists(metadata)
    headers = {"Authorization": settings.lrc_api_auth} if settings.lrc_api_auth else None
    try:
        response = _http.get(
            f"{settings.lrc_api_base_url}/jsonapi",
            params={
                "title": getattr(metadata, "title", ""),
                "artist": ", ".join(artists),
                "album": getattr(metadata, "album", "") or "",
            },
            headers=headers,
        )
        response.raise_for_status()
        candidates = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise UpstreamError("LrcApi request failed") from exc

    if not isinstance(candidates, list):
        raise UpstreamError("LrcApi returned an invalid lyrics response")
    candidate = next(
        (item for item in candidates if _is_confident_match(item, metadata)), None
    )
    if candidate is None:
        raise UpstreamError("No confident lyrics result was found with LrcApi")
    lines = _lines(str(candidate.get("lrc") or ""))
    if not lines:
        raise UpstreamError("No lyrics were found for this recording")
    return LyricsSourceResult(instrumental=False, lines=lines)


adapter = register(LyricsSourceAdapter(key="lrcapi", label="LrcApi", fetch=fetch))
