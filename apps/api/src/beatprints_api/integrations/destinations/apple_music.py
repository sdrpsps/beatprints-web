"""Apple Music destination adapter."""

from pathlib import Path
from urllib.parse import parse_qs, urlparse

import httpx
from qrcode.constants import ERROR_CORRECT_L

from beatprints_api.config import settings
from beatprints_api.integrations.destinations.base import DestinationAdapter
from beatprints_api.integrations.destinations.registry import register
from beatprints_api.integrations.destinations.scannable import icon_qr_scannable
from beatprints_api.exceptions import PlatformLinkNoMatchError, UpstreamError
from beatprints_api.models.destinations import PlatformLinkMatchData

ASSET_PATH = Path(__file__).resolve().parents[2] / "assets" / "apple-music-symbol.png"
SEARCH_URL = "https://itunes.apple.com/search"
LOOKUP_URL = "https://itunes.apple.com/lookup"
http_client = httpx.Client(timeout=15.0)


def _release_year(value: object) -> int | None:
    try:
        return int(str(value)[:4])
    except ValueError:
        return None


def _result_data(result: dict) -> PlatformLinkMatchData:
    is_track = result.get("wrapperType") == "track"
    title = result.get("trackName") if is_track else result.get("collectionName")
    url = result.get("trackViewUrl") if is_track else result.get("collectionViewUrl")
    if not isinstance(title, str) or not isinstance(url, str):
        raise PlatformLinkNoMatchError("Apple Music did not return a usable catalog item")
    return PlatformLinkMatchData(
        url=url,
        title=title,
        artists=[result["artistName"]] if isinstance(result.get("artistName"), str) else [],
        album=result.get("collectionName") if is_track else None,
        release_year=_release_year(result.get("releaseDate")),
        duration_seconds=(
            round(result["trackTimeMillis"] / 1000)
            if is_track and isinstance(result.get("trackTimeMillis"), int)
            else None
        ),
        track_count=None if is_track else result.get("trackCount"),
        cover_url=result.get("artworkUrl100"),
        type="track" if is_track else "album",
    )


def search(query: str, item_type: str) -> list[dict]:
    entity = "song" if item_type == "track" else "album"
    try:
        response = http_client.get(
            SEARCH_URL,
            params={
                "term": query,
                "media": "music",
                "entity": entity,
                "country": settings.apple_music_storefront,
                "limit": 10,
            },
        )
        response.raise_for_status()
        results = response.json().get("results", [])
    except (httpx.HTTPError, ValueError) as exc:
        raise UpstreamError(f"Apple Music search failed: {exc}") from exc
    candidates: list[dict] = []
    for result in results:
        if not isinstance(result, dict):
            continue
        try:
            candidate = _result_data(result).model_dump(mode="json")
        except PlatformLinkNoMatchError:
            continue
        candidate["platform_id"] = (
            result.get("trackId") if candidate["type"] == "track" else result.get("collectionId")
        )
        candidates.append(candidate)
    return candidates


def resolve(url: str) -> PlatformLinkMatchData:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if not (host == "music.apple.com" or host.endswith(".music.apple.com")):
        raise PlatformLinkNoMatchError("URL is not an Apple Music link")
    track_ids = parse_qs(parsed.query).get("i", [])
    identifier = track_ids[0] if track_ids else next(
        (part for part in reversed(parsed.path.split("/")) if part.isdigit()), None
    )
    if not identifier:
        raise PlatformLinkNoMatchError("Apple Music link does not contain a catalog ID")
    try:
        response = http_client.get(
            LOOKUP_URL,
            params={"id": identifier, "country": settings.apple_music_storefront},
        )
        response.raise_for_status()
        results = response.json().get("results", [])
    except (httpx.HTTPError, ValueError) as exc:
        raise UpstreamError(f"Apple Music lookup failed: {exc}") from exc
    for result in results:
        if isinstance(result, dict) and result.get("wrapperType") in {"track", "collection"}:
            return _result_data(result)
    raise PlatformLinkNoMatchError("Apple Music link did not resolve to a catalog item")


adapter = register(
    DestinationAdapter(
        key="apple_music",
        label="Apple Music",
        search=search,
        resolve=resolve,
        scannable=lambda link: icon_qr_scannable(
            link, ASSET_PATH, error_correction=ERROR_CORRECT_L
        ),
    )
)
