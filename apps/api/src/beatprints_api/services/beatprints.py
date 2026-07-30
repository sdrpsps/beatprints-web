import atexit
import colorsys
import copy
import io
import ipaddress
import random
import re
import socket
import tempfile
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date
from difflib import SequenceMatcher
from functools import lru_cache
from pathlib import Path
from urllib.parse import parse_qs, urljoin, urlparse

import deezer
import httpx
import qrcode
from PIL import Image, ImageDraw, ImageFont
from qrcode.constants import ERROR_CORRECT_M

from beatprints_api.config import settings
from beatprints_api.models.dto import (
    AlbumPosterRequest,
    AppleMusicMatchData,
    LyricsLine,
    LyricsPreviewData,
    PosterPlatformLinks,
    SpotifyMatchData,
    TrackPosterRequest,
)
from beatprints_api.palette import extract_palette, install_pylette_compatibility_module
from beatprints_api.spotify import SpotifyCodeClient, SpotifyClient

install_pylette_compatibility_module()

from BeatPrints import (
    deez,
    errors as beatprints_errors,
    image as beatprints_image,
    lyrics,
    poster,
    write,
)

beatprints_image.get_palette = extract_palette

MAX_COVER_BYTES = 15 * 1024 * 1024
ALLOWED_COVER_TYPES = {"image/jpeg", "image/png", "image/webp"}
spotify_client = SpotifyClient(
    settings.spotify_client_id,
    settings.spotify_client_secret,
    settings.spotify_market,
)
spotify_code_client = SpotifyCodeClient()
cover_client = httpx.Client(
    follow_redirects=False,
    timeout=httpx.Timeout(15.0, connect=5.0),
    limits=httpx.Limits(
        max_connections=20,
        max_keepalive_connections=10,
        keepalive_expiry=30.0,
    ),
    headers={"User-Agent": "BeatPrints-API/0.1"},
)
atexit.register(cover_client.close)
rendering_lock = threading.Lock()
PLATFORM_LABELS = {
    "spotify": "Spotify",
    "apple_music": "Apple Music",
    "qq_music": "QQ 音乐",
    "netease_music": "网易云",
}
SPOTIFY_CODE_SCALE = 1.06
SPOTIFY_CODE_WIDTH = 560
SPOTIFY_CODE_HEIGHT = 120
APPLE_MUSIC_SYMBOL_PATH = (
    Path(__file__).resolve().parents[1] / "assets" / "apple-music-symbol.png"
)
APPLE_MUSIC_SEARCH_URL = "https://itunes.apple.com/search"


class UpstreamError(RuntimeError):
    """Raised when a metadata, lyrics, or cover provider fails."""


class AppleMusicNoMatchError(UpstreamError):
    """Raised when Apple Music has no sufficiently confident catalog match."""


@dataclass(frozen=True)
class PosterResult:
    content: bytes
    filename: str
    timings_ms: dict[str, float]


_uncached_font = write.font
_uncached_check_glyph = write._check_glyph


@lru_cache(maxsize=3)
def _cached_font(weight: str):
    return _uncached_font(weight)


@lru_cache(maxsize=4096)
def _cached_check_glyph(font, glyph: str) -> bool:
    return _uncached_check_glyph(font, glyph)


# BeatPrints repeatedly parses the same multilingual fonts and cmap tables while
# rendering a poster. The rendering lock makes these process-wide objects safe to
# reuse, and warming them here moves the first-request penalty to process startup.
write.font = _cached_font
write._check_glyph = _cached_check_glyph
for _font_weight in ("Regular", "Bold", "Light"):
    write.font(_font_weight)


def _normalized_label(value: object) -> str:
    label = str(value or "").strip()
    if label.casefold() in {"unknown", "unknown label", "unknown records"}:
        return ""
    return label


def _match_text(value: object) -> str:
    """Normalize catalog text while retaining non-Latin artist and title characters."""

    return "".join(
        character for character in str(value or "").casefold() if character.isalnum()
    )


def _text_similarity(left: object, right: object) -> float:
    normalized_left = _match_text(left)
    normalized_right = _match_text(right)
    if not normalized_left or not normalized_right:
        return 0.0
    if normalized_left == normalized_right:
        return 1.0
    return SequenceMatcher(None, normalized_left, normalized_right).ratio()


def _metadata_artists(metadata: deez.TrackMetadata | deez.AlbumMetadata) -> str:
    return " ".join(str(artist) for artist in metadata.artists)


def _duration_seconds(value: str) -> int | None:
    try:
        minutes, seconds = value.split(":", maxsplit=1)
        return int(minutes) * 60 + int(seconds)
    except AttributeError, ValueError:
        return None


def _release_year(value: object) -> int | None:
    try:
        return date.fromisoformat(str(value)[:10]).year
    except ValueError:
        try:
            return int(str(value)[:4])
        except ValueError:
            return None


def _apple_music_results(query: str, entity: str) -> list[dict]:
    try:
        response = cover_client.get(
            APPLE_MUSIC_SEARCH_URL,
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
    return [result for result in results if isinstance(result, dict)]


def _apple_music_result_data(result: dict) -> AppleMusicMatchData:
    is_track = result.get("wrapperType") == "track"
    title = result.get("trackName") if is_track else result.get("collectionName")
    url = result.get("trackViewUrl") if is_track else result.get("collectionViewUrl")
    if not isinstance(title, str) or not isinstance(url, str):
        raise AppleMusicNoMatchError("Apple Music did not return a usable catalog item")
    return AppleMusicMatchData(
        url=url,
        title=title,
        artists=[result["artistName"]] if isinstance(result.get("artistName"), str) else [],
        album=result.get("collectionName") if is_track else None,
        release_year=None if is_track else _release_year(result.get("releaseDate")),
        track_count=None if is_track else result.get("trackCount"),
        cover_url=result.get("artworkUrl100"),
        type="track" if is_track else "album",
    )


def resolve_apple_music_url(url: str) -> AppleMusicMatchData:
    """Return public Apple Music metadata for a manually supplied Apple URL."""

    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if not (host == "music.apple.com" or host.endswith(".music.apple.com")):
        raise AppleMusicNoMatchError("URL is not an Apple Music link")
    track_ids = parse_qs(parsed.query).get("i", [])
    identifier = track_ids[0] if track_ids else next(
        (part for part in reversed(parsed.path.split("/")) if part.isdigit()), None
    )
    if not identifier:
        raise AppleMusicNoMatchError("Apple Music link does not contain a catalog ID")
    try:
        response = cover_client.get(
            "https://itunes.apple.com/lookup",
            params={"id": identifier, "country": settings.apple_music_storefront},
        )
        response.raise_for_status()
        results = response.json().get("results", [])
    except (httpx.HTTPError, ValueError) as exc:
        raise UpstreamError(f"Apple Music lookup failed: {exc}") from exc
    for result in results:
        if isinstance(result, dict) and result.get("wrapperType") in {"track", "collection"}:
            return _apple_music_result_data(result)
    raise AppleMusicNoMatchError("Apple Music link did not resolve to a catalog item")


def _apple_music_track_match(metadata: deez.TrackMetadata) -> AppleMusicMatchData:
    source_duration = _duration_seconds(metadata.duration)
    candidates: list[tuple[float, dict]] = []
    for candidate in _apple_music_results(
        f"{metadata.title} {_metadata_artists(metadata)}", "song"
    ):
        url = candidate.get("trackViewUrl")
        if not url:
            continue
        title_score = _text_similarity(metadata.title, candidate.get("trackName"))
        artist_score = _text_similarity(
            _metadata_artists(metadata), candidate.get("artistName")
        )
        album_score = _text_similarity(metadata.album, candidate.get("collectionName"))
        candidate_duration = candidate.get("trackTimeMillis")
        duration_score = 0.5
        if source_duration and isinstance(candidate_duration, int):
            difference = abs(source_duration - candidate_duration / 1000)
            duration_score = max(0.0, 1 - difference / 15)
        score = (
            title_score * 0.52
            + artist_score * 0.30
            + album_score * 0.10
            + duration_score * 0.08
        )
        if title_score >= 0.88 and artist_score >= 0.72 and score >= 0.84:
            candidates.append((score, candidate))
    if not candidates:
        raise AppleMusicNoMatchError("No confident Apple Music match was found")
    _score, match = max(candidates, key=lambda item: item[0])
    return AppleMusicMatchData(
        url=match["trackViewUrl"],
        title=match["trackName"],
        artists=[match["artistName"]],
        album=match.get("collectionName"),
        type="track",
        cover_url=match.get("artworkUrl100"),
    )


def _apple_music_album_match(metadata: deez.AlbumMetadata) -> AppleMusicMatchData:
    source_year = _release_year(metadata.released)
    candidates: list[tuple[float, dict]] = []
    for candidate in _apple_music_results(
        f"{metadata.title} {_metadata_artists(metadata)}", "album"
    ):
        url = candidate.get("collectionViewUrl")
        if not url:
            continue
        title_score = _text_similarity(metadata.title, candidate.get("collectionName"))
        artist_score = _text_similarity(
            _metadata_artists(metadata), candidate.get("artistName")
        )
        candidate_year = _release_year(candidate.get("releaseDate"))
        year_score = (
            0.5
            if not source_year or not candidate_year
            else float(source_year == candidate_year)
        )
        score = title_score * 0.64 + artist_score * 0.26 + year_score * 0.10
        if title_score >= 0.90 and artist_score >= 0.72 and score >= 0.85:
            candidates.append((score, candidate))
    if not candidates:
        raise AppleMusicNoMatchError("No confident Apple Music match was found")
    _score, match = max(candidates, key=lambda item: item[0])
    return AppleMusicMatchData(
        url=match["collectionViewUrl"],
        title=match["collectionName"],
        artists=[match["artistName"]],
        type="album",
        release_year=_release_year(match.get("releaseDate")),
        track_count=match.get("trackCount"),
        cover_url=match.get("artworkUrl100"),
    )


def _is_public_host(hostname: str) -> bool:
    try:
        addresses = socket.getaddrinfo(hostname, None)
    except socket.gaierror as exc:
        raise UpstreamError(f"Could not resolve cover host: {hostname}") from exc

    # Some container/VPN DNS resolvers return an internal IPv6 proxy address next
    # to a valid public address. Requiring every answer to be public would reject
    # legitimate CDNs in those environments. Internal-only hosts are still blocked.
    return any(ipaddress.ip_address(address[4][0]).is_global for address in addresses)


def _validate_cover_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("cover_url must be an HTTP(S) URL")
    if parsed.username or parsed.password:
        raise ValueError("cover_url must not contain credentials")
    if not _is_public_host(parsed.hostname):
        raise ValueError("cover_url must resolve to a public Internet address")


def _download_cover(url: str, destination: Path) -> None:
    try:
        current_url = url
        for _ in range(6):
            _validate_cover_url(current_url)
            with cover_client.stream("GET", current_url) as response:
                if response.is_redirect:
                    location = response.headers.get("location")
                    if not location:
                        raise UpstreamError("Cover provider returned an empty redirect")
                    current_url = urljoin(current_url, location)
                    continue

                response.raise_for_status()
                content_type = response.headers.get("content-type", "").split(";")[0]
                if content_type not in ALLOWED_COVER_TYPES:
                    raise ValueError("cover_url must return a JPEG, PNG, or WebP image")

                size = 0
                with destination.open("wb") as output:
                    for chunk in response.iter_bytes():
                        size += len(chunk)
                        if size > MAX_COVER_BYTES:
                            raise ValueError("Cover image exceeds the 15 MB limit")
                        output.write(chunk)
                return
        raise UpstreamError("Cover provider returned too many redirects")
    except httpx.HTTPError as exc:
        raise UpstreamError(f"Could not download cover image: {exc}") from exc


def _metadata_cache_token() -> int:
    return int(time.monotonic() // settings.metadata_cache_ttl_seconds)


@lru_cache(maxsize=settings.metadata_cache_max_entries)
def _cached_track_metadata(
    provider: str,
    track_id: int | str,
    _cache_token: int,
) -> deez.TrackMetadata:
    if provider == "spotify":
        value = spotify_client.track_metadata(str(track_id))
        metadata = deez.TrackMetadata(
            title=value["title"],
            artists=value["artists"],
            album=value["album"],
            released=value["released"],
            duration=value["duration"],
            cover=value["cover"],
            label=_normalized_label(value["label"]),
        )
        metadata.link = value["link"]
        return metadata

    metadata = deez.Deezer().get_track(int(track_id))
    metadata.label = _normalized_label(metadata.label)
    return metadata


def _track_metadata(request: TrackPosterRequest) -> deez.TrackMetadata:
    if request.metadata is not None:
        value = request.metadata
        return deez.TrackMetadata(
            title=value.title,
            artists=value.artists,
            album=value.album,
            released=value.released,
            duration=value.duration,
            cover=str(value.cover_url),
            label=value.label,
        )

    provider, track_id = _catalog_reference(request, "track")
    return copy.deepcopy(
        _cached_track_metadata(provider, track_id, _metadata_cache_token())
    )


@lru_cache(maxsize=settings.metadata_cache_max_entries)
def _cached_album_metadata(
    provider: str,
    album_id: int | str,
    _cache_token: int,
) -> deez.AlbumMetadata:
    if provider == "spotify":
        value = spotify_client.album_metadata(str(album_id))
        metadata = deez.AlbumMetadata(
            title=value["title"],
            artists=value["artists"],
            released=value["released"],
            tracks=value["tracks"],
            cover=value["cover"],
            label=_normalized_label(value["label"]),
        )
        metadata.link = value["link"]
        return metadata

    metadata = deez.Deezer().get_album(int(album_id), shuffle=False)
    metadata.label = _normalized_label(metadata.label)
    return metadata


def _album_metadata(request: AlbumPosterRequest) -> deez.AlbumMetadata:
    if request.metadata is not None:
        value = request.metadata
        return deez.AlbumMetadata(
            title=value.title,
            artists=value.artists,
            released=value.released,
            tracks=value.tracks.copy(),
            cover=str(value.cover_url),
            label=value.label,
        )

    provider, album_id = _catalog_reference(request, "album")
    metadata = copy.deepcopy(
        _cached_album_metadata(provider, album_id, _metadata_cache_token())
    )
    if request.shuffle:
        random.shuffle(metadata.tracks)
    return metadata


def match_apple_music(
    provider: str,
    catalog_id: int | str,
    item_type: str,
) -> AppleMusicMatchData:
    """Match an exact selected Spotify/Deezer catalog item to Apple Music."""

    if item_type == "track":
        metadata = _track_metadata(
            TrackPosterRequest(provider=provider, catalog_id=catalog_id)
        )
        return _apple_music_track_match(metadata)
    metadata = _album_metadata(
        AlbumPosterRequest(provider=provider, catalog_id=catalog_id)
    )
    return _apple_music_album_match(metadata)


def match_deezer_to_spotify(
    catalog_id: int | str, item_type: str
) -> SpotifyMatchData:
    """Conservatively match an exact Deezer item to a Spotify catalog item."""

    if item_type == "track":
        metadata = _track_metadata(
            TrackPosterRequest(provider="deezer", catalog_id=catalog_id)
        )
        try:
            source = cover_client.get(f"https://api.deezer.com/track/{catalog_id}")
            source.raise_for_status()
            isrc = source.json().get("isrc")
        except (httpx.HTTPError, ValueError) as exc:
            raise UpstreamError(f"Deezer ISRC lookup failed: {exc}") from exc
        candidates = spotify_client.search(
            f"isrc:{isrc}" if isrc else f"{metadata.title} {_metadata_artists(metadata)}",
            "track",
            10,
        )
        for candidate in candidates:
            if isrc and candidate.get("isrc") == isrc:
                return SpotifyMatchData(
                    url=candidate["link"],
                    title=candidate["title"],
                    artists=candidate["artists"],
                    album=(candidate.get("album") or {}).get("title"),
                    cover_url=candidate["cover_url"],
                    type="track",
                )
        for candidate in candidates:
            title_score = _text_similarity(metadata.title, candidate.get("title"))
            artist_score = _text_similarity(
                _metadata_artists(metadata),
                " ".join(candidate.get("artists") or []),
            )
            duration_score = 0.5
            if _duration_seconds(metadata.duration) and candidate.get("duration_seconds"):
                duration_score = max(
                    0.0,
                    1
                    - abs(
                        _duration_seconds(metadata.duration)
                        - candidate["duration_seconds"]
                    )
                    / 15,
                )
            if (
                title_score >= 0.9
                and artist_score >= 0.75
                and title_score * 0.6 + artist_score * 0.3 + duration_score * 0.1
                >= 0.86
            ):
                return SpotifyMatchData(
                    url=candidate["link"],
                    title=candidate["title"],
                    artists=candidate["artists"],
                    album=(candidate.get("album") or {}).get("title"),
                    cover_url=candidate["cover_url"],
                    type="track",
                )
    else:
        metadata = _album_metadata(
            AlbumPosterRequest(provider="deezer", catalog_id=catalog_id)
        )
        candidates = spotify_client.search(
            f"{metadata.title} {_metadata_artists(metadata)}", "album", 10
        )
        for candidate in candidates:
            if (
                _text_similarity(metadata.title, candidate.get("title")) >= 0.92
                and _text_similarity(
                    _metadata_artists(metadata),
                    " ".join(candidate.get("artists") or []),
                )
                >= 0.75
            ):
                return SpotifyMatchData(
                    url=candidate["link"],
                    title=candidate["title"],
                    artists=candidate["artists"],
                    release_year=candidate.get("release_year"),
                    track_count=candidate.get("track_count"),
                    cover_url=candidate["cover_url"],
                    type="album",
                )
    raise AppleMusicNoMatchError("No confident Spotify match was found")


def resolve_spotify_url(url: str) -> SpotifyMatchData:
    """Read current Spotify metadata for a manually supplied Spotify URL."""

    uri = _spotify_uri(url)
    if uri is None:
        raise AppleMusicNoMatchError(
            "URL is not a supported Spotify track or album link"
        )
    _prefix, item_type, catalog_id = uri.split(":", maxsplit=2)
    if item_type == "track":
        value = spotify_client.track_metadata(catalog_id)
        return SpotifyMatchData(
            url=value["link"],
            title=value["title"],
            artists=value["artists"],
            album=value["album"],
            cover_url=value["cover"],
            type="track",
        )
    value = spotify_client.album_metadata(catalog_id)
    return SpotifyMatchData(
        url=value["link"],
        title=value["title"],
        artists=value["artists"],
        release_year=_release_year(value["released"]),
        track_count=len(value["tracks"]),
        cover_url=value["cover"],
        type="album",
    )


def clear_metadata_cache() -> None:
    _cached_track_metadata.cache_clear()
    _cached_album_metadata.cache_clear()


def _catalog_reference(
    request: TrackPosterRequest | AlbumPosterRequest,
    item_type: str,
) -> tuple[str, int | str]:
    if request.catalog_id is not None:
        return request.provider, request.catalog_id

    results = search_catalog(request.query or "", item_type, 1, request.provider)
    if not results:
        raise UpstreamError(f"No matching {item_type} found")
    return request.provider, results[0]["id"]


def _poster_bytes(directory: Path) -> tuple[bytes, str]:
    generated = list(directory.glob("*.png"))
    if len(generated) != 1:
        raise RuntimeError("BeatPrints did not generate exactly one poster")
    path = generated[0]
    return path.read_bytes(), path.name


def _spotify_cover(_url: str, path: str | None) -> Image.Image:
    if path is None:
        raise ValueError("Spotify rendering requires a downloaded cover")
    with Image.open(path) as source:
        cover = source.convert("RGB")
    if cover.width != cover.height:
        raise ValueError("Spotify artwork must be square and cannot be cropped")
    return cover.resize(beatprints_image.s.COVER, Image.Resampling.LANCZOS)


def _empty_scannable(_theme: str = "Light") -> Image.Image:
    return Image.new("RGBA", beatprints_image.s.SCANCODE, (0, 0, 0, 0))


def _selected_platform_link(
    links: PosterPlatformLinks | None,
    selected_platform: str | None,
    provider: str | None,
    source_link: str | None,
) -> tuple[str, str] | None:
    if selected_platform is None:
        return None
    values = (
        links.model_dump(mode="json", exclude_none=True) if links is not None else {}
    )
    if (
        selected_platform == "spotify"
        and provider == "spotify"
        and source_link
        and "spotify" not in values
    ):
        values["spotify"] = source_link
    link = values.get(selected_platform)
    if link is None:
        return None
    return PLATFORM_LABELS[selected_platform], link


def _qr_font(size: int) -> ImageFont.FreeTypeFont:
    font_paths = write.font("Regular")
    path = next(
        (path for path in font_paths if "NotoSansSC" in path),
        next(iter(font_paths)),
    )
    return ImageFont.truetype(path, size)


def _relative_luminance(color: tuple[int, int, int]) -> float:
    channels = []
    for value in color:
        channel = value / 255
        channels.append(
            channel / 12.92
            if channel <= 0.04045
            else ((channel + 0.055) / 1.055) ** 2.4
        )
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def _contrast_with_white(color: tuple[int, int, int]) -> float:
    return 1.05 / (_relative_luminance(color) + 0.05)


def _cover_qr_color(cover_path: Path) -> tuple[int, int, int]:
    with Image.open(cover_path) as cover:
        palette = extract_palette(cover, size=8)

    def saturation(color: tuple[int, int, int]) -> float:
        return colorsys.rgb_to_hsv(*(channel / 255 for channel in color))[1]

    high_contrast = [color for color in palette if _contrast_with_white(color) >= 4.5]
    if high_contrast:
        return max(high_contrast, key=saturation)

    selected = max(palette, key=saturation)
    for step in range(19, -1, -1):
        factor = step / 20
        darkened = tuple(round(channel * factor) for channel in selected)
        if _contrast_with_white(darkened) >= 4.5:
            return darkened
    return 0, 0, 0


def _platform_scannable(
    item: tuple[str, str],
    color: tuple[int, int, int],
):
    def render(_theme: str = "Light") -> Image.Image:
        width, height = beatprints_image.s.SCANCODE
        canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(canvas)
        label, link = item
        qr = qrcode.QRCode(
            version=None,
            error_correction=ERROR_CORRECT_M,
            box_size=4,
            border=2,
        )
        qr.add_data(link)
        qr.make(fit=True)
        code = qr.make_image(fill_color=color, back_color="white").convert("RGBA")
        qr_size = 112
        code = code.resize((qr_size, qr_size), Image.Resampling.NEAREST)
        canvas.alpha_composite(code, (0, (height - qr_size) // 2))
        draw.text(
            (136, height // 2),
            label,
            fill=color + (255,),
            font=_qr_font(28),
            anchor="lm",
        )
        return canvas

    return render


def _apple_music_icon(color: tuple[int, int, int], size: int) -> Image.Image:
    """Tint the alpha mask derived from the supplied Apple Music SVG."""

    try:
        with Image.open(APPLE_MUSIC_SYMBOL_PATH) as source:
            mask = source.convert("RGBA").getchannel("A")
    except OSError as exc:
        raise RuntimeError("Apple Music symbol asset is unavailable") from exc
    mask = mask.resize((size, size), Image.Resampling.LANCZOS)
    icon = Image.new("RGBA", (size, size), color + (0,))
    icon.putalpha(mask)
    return icon


def _transparent_qr(
    qr: qrcode.QRCode, color: tuple[int, int, int], target_size: int
) -> Image.Image:
    """Draw a transparent, poster-friendly dot QR with stable finder patterns."""

    modules = qr.get_matrix()
    module_count = len(modules)
    scale = 4
    size = target_size * scale
    module_size = size / module_count
    code = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(code)
    border = qr.border
    last_finder_start = module_count - border - 7

    def in_finder(x: int, y: int) -> bool:
        return (
            (border <= x < border + 7 and border <= y < border + 7)
            or (
                last_finder_start <= x < last_finder_start + 7
                and border <= y < border + 7
            )
            or (
                border <= x < border + 7
                and last_finder_start <= y < last_finder_start + 7
            )
        )

    for y, row in enumerate(modules):
        for x, enabled in enumerate(row):
            if enabled:
                left = round(x * module_size)
                top = round(y * module_size)
                right = round((x + 1) * module_size)
                bottom = round((y + 1) * module_size)
                if not in_finder(x, y):
                    inset = round(module_size * 0.12)
                    draw.ellipse(
                        (
                            left + inset,
                            top + inset,
                            right - inset - 1,
                            bottom - inset - 1,
                        ),
                        fill=color + (255,),
                    )
    # Keep the finder pattern recognizably square for camera detectors, with only
    # a small softening at its outer corners to match the dot treatment.
    finder_radius = round(module_size * 0.3)
    for x, y in (
        (border, border),
        (last_finder_start, border),
        (border, last_finder_start),
    ):
        left = round(x * module_size)
        top = round(y * module_size)
        right = round((x + 7) * module_size) - 1
        bottom = round((y + 7) * module_size) - 1
        draw.rounded_rectangle(
            (left, top, right, bottom), radius=finder_radius, fill=color + (255,)
        )
        inner_left = round((x + 1) * module_size)
        inner_top = round((y + 1) * module_size)
        inner_right = round((x + 6) * module_size) - 1
        inner_bottom = round((y + 6) * module_size) - 1
        draw.rounded_rectangle(
            (inner_left, inner_top, inner_right, inner_bottom),
            radius=round(module_size * 0.2),
            fill=(0, 0, 0, 0),
        )
        center_left = round((x + 2) * module_size)
        center_top = round((y + 2) * module_size)
        center_right = round((x + 5) * module_size) - 1
        center_bottom = round((y + 5) * module_size) - 1
        draw.rounded_rectangle(
            (center_left, center_top, center_right, center_bottom),
            radius=round(module_size * 0.2),
            fill=color + (255,),
        )
    return code.resize((target_size, target_size), Image.Resampling.LANCZOS)


def _apple_music_scannable(item: tuple[str, str]):
    """Render Apple Music artwork using the poster theme, like Spotify Code."""

    def render(theme: str = "Light") -> Image.Image:
        width, height = beatprints_image.s.SCANCODE
        canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        _label, link = item
        color = beatprints_image.t.THEMES[theme]

        qr = qrcode.QRCode(
            version=None,
            # Apple Music URLs are long. L minimizes module density so the code stays
            # visually open at poster size; the rendered modules remain large enough
            # for a clean, unobstructed print scan.
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=4,
            border=2,
        )
        qr.add_data(link)
        qr.make(fit=True)
        code_size = 112
        code = _transparent_qr(qr, color, code_size)
        icon_size = 74
        icon = _apple_music_icon(color, icon_size)
        canvas.alpha_composite(icon, (0, (height - icon_size) // 2))
        qr_x = 98
        qr_y = (height - code_size) // 2
        canvas.alpha_composite(code, (qr_x, qr_y))
        return canvas

    return render


def _spotify_uri(link: str) -> str | None:
    """Return a canonical Spotify track or album URI for a supported web link."""

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
        if part in {"track", "album"}:
            item_id = parts[index + 1]
            if re.fullmatch(r"[A-Za-z0-9]{22}", item_id):
                return f"spotify:{part}:{item_id}"
    return None


def _spotify_code_scannable(link: str):
    """Render a Spotify Code in BeatPrints' fixed bottom-left slot."""

    uri = _spotify_uri(link)
    if uri is None:
        return None
    width, height = SPOTIFY_CODE_WIDTH, SPOTIFY_CODE_HEIGHT
    content = spotify_code_client.png(uri, width)
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
        mask = mask.crop(content_box)
        colored = Image.new("RGBA", mask.size, color + (0,))
        colored.putalpha(mask)
        canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        target_width = min(width, round(colored.width * SPOTIFY_CODE_SCALE))
        target_height = round(colored.height * target_width / colored.width)
        if target_height > height:
            target_height = height
            target_width = round(colored.width * target_height / colored.height)
        fitted = colored.resize((target_width, target_height), Image.Resampling.LANCZOS)
        canvas.alpha_composite(
            fitted,
            ((width - fitted.width) // 2, (height - fitted.height) // 2),
        )
        return canvas

    return render


@contextmanager
def _provider_rendering(
    provider: str | None,
    platform_link: tuple[str, str] | None,
    qr_color: tuple[int, int, int] | None,
):
    """Temporarily adapt BeatPrints' fixed Deezer rendering to a catalog provider."""

    with rendering_lock:
        original_cover = beatprints_image.cover
        original_scannable = beatprints_image.scannable
        beatprints_image.scannable = _empty_scannable
        if provider == "spotify":
            beatprints_image.cover = _spotify_cover
        if platform_link is not None and qr_color is not None:
            spotify_code = (
                _spotify_code_scannable(platform_link[1])
                if platform_link[0] == "Spotify"
                else None
            )
            beatprints_image.scannable = spotify_code or (
                _apple_music_scannable(platform_link)
                if platform_link[0] == "Apple Music"
                else _platform_scannable(platform_link, qr_color)
            )
        try:
            yield
        finally:
            beatprints_image.cover = original_cover
            beatprints_image.scannable = original_scannable


def _fetch_lyrics(metadata: deez.TrackMetadata):
    try:
        lyric_result = lyrics.Lyrics(metadata).get_lyrics()
        instrumental = lyric_result.check_instrumental(metadata)
    except beatprints_errors.NoLyricsAvailable as exc:
        raise UpstreamError("No lyrics were found for this recording") from exc
    except Exception as exc:
        raise UpstreamError("Lyrics provider request failed") from exc
    nonempty_lines = [
        line.strip()
        for line in (lyric_result.lyrics or "").splitlines()
        if line.strip()
    ]
    return lyric_result, instrumental, nonempty_lines


def preview_lyrics(provider: str, catalog_id: int | str) -> LyricsPreviewData:
    request = TrackPosterRequest(provider=provider, catalog_id=catalog_id)
    metadata = _track_metadata(request)
    _lyric_result, instrumental, lines = _fetch_lyrics(metadata)
    return LyricsPreviewData(
        provider=provider,
        catalog_id=catalog_id,
        instrumental=instrumental,
        lines=[
            LyricsLine(index=index, text=line)
            for index, line in enumerate(lines, start=1)
        ],
    )


def _select_lyrics(metadata: deez.TrackMetadata, request: TrackPosterRequest) -> str:
    if request.lyrics is not None:
        return request.lyrics.strip()

    lyric_result, instrumental, nonempty_lines = _fetch_lyrics(metadata)
    if instrumental:
        return request.instrumental_text.strip()
    if request.lyrics_range is not None:
        return lyric_result.select_lines(request.lyrics_range)

    if len(nonempty_lines) < 4:
        raise UpstreamError("Fewer than four non-empty lyric lines were available")
    return "\n".join(nonempty_lines[:4])


def _renderable_lyrics(value: str) -> str:
    # BeatPrints 0.1.0 indexes the first glyph even for an empty string.
    # A space is visually empty while keeping the upstream renderer safe.
    return value or " "


def _elapsed_ms(started_at: float) -> float:
    return (time.perf_counter() - started_at) * 1000


def generate_track(request: TrackPosterRequest) -> PosterResult:
    timings: dict[str, float] = {}
    started_at = time.perf_counter()
    metadata = _track_metadata(request)
    timings["metadata"] = _elapsed_ms(started_at)

    started_at = time.perf_counter()
    selected_lyrics = _select_lyrics(metadata, request)
    timings["lyrics"] = _elapsed_ms(started_at)
    provider = request.provider if request.metadata is None else None
    platform_link = _selected_platform_link(
        request.platform_links,
        request.qr_platform,
        provider,
        getattr(metadata, "link", None),
    )

    with tempfile.TemporaryDirectory(prefix="beatprints-") as temp:
        directory = Path(temp)
        cover_path = directory / "cover"

        started_at = time.perf_counter()
        _download_cover(metadata.cover, cover_path)
        timings["cover"] = _elapsed_ms(started_at)

        started_at = time.perf_counter()
        qr_color = _cover_qr_color(cover_path) if platform_link is not None else None
        timings["palette"] = _elapsed_ms(started_at)

        started_at = time.perf_counter()
        with _provider_rendering(provider, platform_link, qr_color):
            poster.Poster(str(directory)).track(
                metadata=metadata,
                lyrics=_renderable_lyrics(selected_lyrics),
                accent=request.accent,
                theme=request.theme,
                pcover=str(cover_path),
            )
        timings["render"] = _elapsed_ms(started_at)

        started_at = time.perf_counter()
        content, filename = _poster_bytes(directory)
        timings["read"] = _elapsed_ms(started_at)
        return PosterResult(content, filename, timings)


def generate_album(request: AlbumPosterRequest) -> PosterResult:
    timings: dict[str, float] = {}
    started_at = time.perf_counter()
    metadata = _album_metadata(request)
    if request.metadata is not None and request.shuffle:
        random.shuffle(metadata.tracks)
    timings["metadata"] = _elapsed_ms(started_at)

    provider = request.provider if request.metadata is None else None
    platform_link = _selected_platform_link(
        request.platform_links,
        request.qr_platform,
        provider,
        getattr(metadata, "link", None),
    )

    with tempfile.TemporaryDirectory(prefix="beatprints-") as temp:
        directory = Path(temp)
        cover_path = directory / "cover"

        started_at = time.perf_counter()
        _download_cover(metadata.cover, cover_path)
        timings["cover"] = _elapsed_ms(started_at)

        started_at = time.perf_counter()
        qr_color = _cover_qr_color(cover_path) if platform_link is not None else None
        timings["palette"] = _elapsed_ms(started_at)

        started_at = time.perf_counter()
        with _provider_rendering(provider, platform_link, qr_color):
            poster.Poster(str(directory)).album(
                metadata=metadata,
                indexing=request.indexing,
                accent=request.accent,
                theme=request.theme,
                pcover=str(cover_path),
            )
        timings["render"] = _elapsed_ms(started_at)

        started_at = time.perf_counter()
        content, filename = _poster_bytes(directory)
        timings["read"] = _elapsed_ms(started_at)
        return PosterResult(content, filename, timings)


def search_deezer(query: str, search_type: str, limit: int) -> list[dict]:
    client = deezer.Client()
    search_fn = client.search if search_type == "track" else client.search_albums
    results = search_fn(query)[:limit]

    formatted = []
    for item in results:
        data = item.as_dict()
        primary_artist = data.get("artist") or {}
        try:
            release_date = item.release_date
        except Exception:
            release_date = None
        try:
            artists = [artist.name for artist in item.contributors]
        except Exception:
            artists = [primary_artist["name"]] if primary_artist.get("name") else []

        if search_type == "track":
            album = data.get("album") or {}
            seconds = int(data.get("duration") or 0)
            minutes, remaining_seconds = divmod(seconds, 60)
            formatted.append(
                {
                    "id": data["id"],
                    "provider": "deezer",
                    "type": "track",
                    "title": data["title"],
                    "artists": artists,
                    "cover_url": album.get("cover_xl") or album.get("cover_big"),
                    "link": data["link"],
                    "release_date": (
                        release_date.isoformat() if release_date is not None else None
                    ),
                    "release_year": (
                        release_date.year if release_date is not None else None
                    ),
                    "release_date_precision": "day",
                    "album": {
                        "id": album["id"],
                        "title": album["title"],
                    },
                    "duration_seconds": seconds,
                    "duration": f"{minutes:02d}:{remaining_seconds:02d}",
                    "explicit": bool(data.get("explicit_lyrics")),
                    "isrc": data.get("isrc"),
                }
            )
        else:
            formatted.append(
                {
                    "id": data["id"],
                    "provider": "deezer",
                    "type": "album",
                    "title": data["title"],
                    "artists": artists,
                    "cover_url": data.get("cover_xl") or data.get("cover_big"),
                    "link": data["link"],
                    "release_date": (
                        release_date.isoformat() if release_date is not None else None
                    ),
                    "release_year": (
                        release_date.year if release_date is not None else None
                    ),
                    "release_date_precision": "day",
                    "explicit": bool(data.get("explicit_lyrics")),
                    "track_count": data.get("nb_tracks"),
                }
            )
    return formatted


def search_catalog(
    query: str,
    search_type: str,
    limit: int,
    provider: str,
) -> list[dict]:
    providers = {
        "deezer": lambda: search_deezer(query, search_type, limit),
        "spotify": lambda: spotify_client.search(query, search_type, limit),
    }
    if provider != "all":
        return providers[provider]()

    results = providers["deezer"]()
    if spotify_client.configured:
        results.extend(providers["spotify"]())
    return results
