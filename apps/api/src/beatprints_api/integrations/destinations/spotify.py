"""Spotify destination adapter."""

import io
import re
from pathlib import Path
from urllib.parse import urlparse

from PIL import Image

from BeatPrints import image as beatprints_image
from beatprints_api.integrations.destinations.base import DestinationAdapter
from beatprints_api.integrations.destinations.registry import register
from beatprints_api.exceptions import PlatformLinkNoMatchError, UpstreamError
from beatprints_api.models.dto import PlatformLinkMatchData
from beatprints_api.integrations.catalog.spotify import spotify_client
from beatprints_api.integrations.destinations.spotify_code import spotify_code_client

CODE_SCALE = 1.06
CODE_WIDTH = 560
CODE_HEIGHT = 120


def _release_year(value: object) -> int | None:
    try:
        return int(str(value)[:4])
    except ValueError:
        return None


def _duration_seconds(value: str) -> int | None:
    try:
        minutes, seconds = value.split(":", maxsplit=1)
        return int(minutes) * 60 + int(seconds)
    except (AttributeError, ValueError):
        return None


def _uri(link: str) -> str | None:
    parsed = urlparse(link)
    if parsed.scheme == "spotify":
        parts = parsed.path.split(":")
        if len(parts) == 2 and parts[0] in {"track", "album"}:
            return link
    host = (parsed.hostname or "").lower()
    if host not in {"open.spotify.com", "play.spotify.com"}:
        return None
    parts = [part for part in parsed.path.split("/") if part]
    for index, part in enumerate(parts[:-1]):
        if part in {"track", "album"} and re.fullmatch(r"[A-Za-z0-9]{22}", parts[index + 1]):
            return f"spotify:{part}:{parts[index + 1]}"
    return None


def resolve(url: str) -> PlatformLinkMatchData:
    uri = _uri(url)
    if uri is None:
        raise PlatformLinkNoMatchError("URL is not a supported Spotify track or album link")
    _prefix, item_type, catalog_id = uri.split(":", maxsplit=2)
    if item_type == "track":
        value = spotify_client.track_metadata(catalog_id)
        return PlatformLinkMatchData(
            url=value["link"], title=value["title"], artists=value["artists"], album=value["album"],
            release_year=_release_year(value["released"]), duration_seconds=_duration_seconds(value["duration"]),
            cover_url=value["cover"], type="track",
        )
    value = spotify_client.album_metadata(catalog_id)
    return PlatformLinkMatchData(
        url=value["link"], title=value["title"], artists=value["artists"], release_year=_release_year(value["released"]),
        track_count=len(value["tracks"]), cover_url=value["cover"], type="album",
    )


def search(query: str, item_type: str) -> list[dict]:
    candidates: list[dict] = []
    for result in spotify_client.search(query, item_type, 10):
        url = result.get("link")
        title = result.get("title")
        if not url or not title:
            continue
        album = result.get("album") or {}
        candidates.append({
            "url": url, "title": title, "artists": result.get("artists") or [], "type": item_type,
            "album": album.get("title") if item_type == "track" else None,
            "release_year": result.get("release_year"), "duration_seconds": result.get("duration_seconds"),
            "track_count": result.get("track_count"), "cover_url": result.get("cover_url"),
            "isrc": result.get("isrc"), "platform_id": result.get("id"),
        })
    return candidates


def _resolve_source(provider: str, catalog_id: int | str, item_type: str) -> PlatformLinkMatchData | None:
    return resolve(f"spotify:{item_type}:{catalog_id}") if provider == "spotify" else None


def scannable(link: str):
    uri = _uri(link)
    if uri is None:
        return None
    content = spotify_code_client.png(uri, CODE_WIDTH)
    try:
        with Image.open(io.BytesIO(content)) as source:
            code = source.convert("L")
    except OSError as exc:
        raise UpstreamError("Spotify Code service returned an invalid PNG") from exc

    def render(theme: str = "Light") -> Image.Image:
        color = beatprints_image.t.THEMES[theme]
        mask = code.point(lambda value: 255 - value)
        content_box = mask.getbbox()
        if content_box is None:
            raise UpstreamError("Spotify Code image contains no scannable content")
        colored = Image.new("RGBA", mask.crop(content_box).size, color + (0,))
        colored.putalpha(mask.crop(content_box))
        canvas = Image.new("RGBA", (CODE_WIDTH, CODE_HEIGHT), (0, 0, 0, 0))
        target_width = min(CODE_WIDTH, round(colored.width * CODE_SCALE))
        target_height = round(colored.height * target_width / colored.width)
        if target_height > CODE_HEIGHT:
            target_height = CODE_HEIGHT
            target_width = round(colored.width * target_height / colored.height)
        fitted = colored.resize((target_width, target_height), Image.Resampling.LANCZOS)
        canvas.alpha_composite(fitted, ((CODE_WIDTH - fitted.width) // 2, (CODE_HEIGHT - fitted.height) // 2))
        return canvas

    return render


adapter = register(DestinationAdapter(key="spotify", label="Spotify", search=search, resolve=resolve, scannable=scannable, supports_isrc=True, resolve_source=_resolve_source, reuses_source_link=lambda provider: provider == "spotify"))
