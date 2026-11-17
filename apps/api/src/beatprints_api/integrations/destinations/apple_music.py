"""Apple Music destination resolution and search via its web catalog."""

from pathlib import Path
from urllib.parse import parse_qs, urlparse

from pydantic import ValidationError

from beatprints_api.exceptions import PlatformLinkNoMatchError, UpstreamError
from beatprints_api.integrations.apple_music_client import (
    AppleMusicNotFound,
    apple_music_client,
)
from beatprints_api.integrations.destinations.base import DestinationAdapter
from beatprints_api.integrations.destinations.registry import register
from beatprints_api.integrations.destinations.scannable import (
    icon_qr_scannable,
    standard_icon_qr_scannable,
)
from beatprints_api.integrations.region import current_region
from beatprints_api.integrations.regions.apple_music import REGIONS
from beatprints_api.models.destinations import PlatformLinkMatchData

ASSET_PATH = Path(__file__).resolve().parents[2] / "assets" / "apple-music-symbol.png"


def _result_data(row: dict, item_type: str) -> PlatformLinkMatchData:
    item = apple_music_client.normalize(row, item_type)
    if item is None:
        raise PlatformLinkNoMatchError(
            "Apple Music did not return a usable catalog item"
        )
    try:
        return PlatformLinkMatchData(
            url=item["link"],
            title=item["title"],
            artists=item["artists"],
            album=item["album"]["title"] if item_type == "track" else None,
            release_year=item["release_year"],
            duration_seconds=item.get("duration_seconds"),
            track_count=item.get("track_count"),
            cover_url=item["cover_url"],
            type=item_type,
        )
    except ValidationError as exc:
        raise PlatformLinkNoMatchError(
            "Apple Music did not return a usable catalog item"
        ) from exc


def search(query: str, item_type: str) -> list[dict]:
    if query.startswith("isrc:"):
        rows = (
            apple_music_client.search_isrc(query.removeprefix("isrc:"))
            if item_type == "track"
            else []
        )
    else:
        rows = apple_music_client.search(query, item_type, 10)
    candidates: list[dict] = []
    for row in rows:
        try:
            candidate = _result_data(row, item_type).model_dump(mode="json")
        except PlatformLinkNoMatchError:
            continue
        candidate["platform_id"] = str(row["id"])
        if item_type == "track":
            normalized = apple_music_client.normalize(row, item_type)
            candidate["isrc"] = normalized.get("isrc") if normalized else None
        candidates.append(candidate)
    if rows and not candidates:
        raise UpstreamError("Apple Music search returned incomplete results")
    return candidates


def resolve(url: str) -> PlatformLinkMatchData:
    parsed = urlparse(url)
    if parsed.scheme != "https" or (parsed.hostname or "").lower() != "music.apple.com":
        raise PlatformLinkNoMatchError("URL is not an Apple Music link")
    parts = [part for part in parsed.path.split("/") if part]
    track_ids = parse_qs(parsed.query).get("i", [])
    if not parts or not parts[-1].isascii() or not parts[-1].isdigit():
        raise PlatformLinkNoMatchError("Apple Music link does not contain a catalog ID")
    if len(track_ids) == 1 and "album" in parts:
        identifier, item_type = track_ids[0], "track"
    elif track_ids:
        raise PlatformLinkNoMatchError("URL is not an Apple Music track link")
    elif "song" in parts:
        identifier, item_type = parts[-1], "track"
    elif "album" in parts:
        identifier, item_type = parts[-1], "album"
    else:
        raise PlatformLinkNoMatchError("URL is not an Apple Music track or album link")
    if not identifier.isascii() or not identifier.isdigit():
        raise PlatformLinkNoMatchError("Apple Music link does not contain a catalog ID")
    try:
        row = apple_music_client.item(identifier, item_type)
    except AppleMusicNotFound as exc:
        raise PlatformLinkNoMatchError(
            "Apple Music catalog item was not found"
        ) from exc
    return _result_data(row, item_type)


def _resolve_source(
    provider: str, catalog_id: int | str, item_type: str
) -> PlatformLinkMatchData | None:
    if provider != "apple_music":
        return None
    kind = "song" if item_type == "track" else "album"
    result = resolve(
        f"https://music.apple.com/{current_region().lower()}/{kind}/{catalog_id}"
    )
    if result.type != item_type:
        raise PlatformLinkNoMatchError("Apple Music catalog item type did not match")
    return result


def _scannable_link(url: str) -> str:
    """Remove Apple's optional title and tracking parameters to fit a sunflower code."""
    parsed = urlparse(url)
    parts = [part for part in parsed.path.split("/") if part]
    track_ids = parse_qs(parsed.query).get("i", [])
    identifier = (
        track_ids[0]
        if track_ids
        else next((part for part in reversed(parts) if part.isdigit()), None)
    )
    if not identifier or not identifier.isdigit():
        return url
    storefront = parts[0] if parts and len(parts[0]) == 2 else "us"
    kind = "song" if track_ids or "song" in parts else "album"
    return f"https://music.apple.com/{storefront}/{kind}/{identifier}"


adapter = register(
    DestinationAdapter(
        key="apple_music",
        supports_regions=True,
        regions=REGIONS,
        label="Apple Music",
        search=search,
        supports_isrc=True,
        resolve=resolve,
        resolve_source=_resolve_source,
        reuses_source_link=lambda provider: provider == "apple_music",
        scannable=lambda link: icon_qr_scannable(_scannable_link(link), ASSET_PATH),
        standard_scannable=lambda link: standard_icon_qr_scannable(link, ASSET_PATH),
    )
)
