"""Poster rendering, artwork safety checks, and destination-code composition."""

import atexit
import colorsys
import ipaddress
import socket
import tempfile
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx
from PIL import Image

from BeatPrints import image as beatprints_image, poster, write
from beatprints_api.exceptions import UpstreamError
from beatprints_api.integrations.catalog import get_catalog_adapter
from beatprints_api.integrations.destinations import DestinationAdapter, get_destination_adapter
from beatprints_api.integrations.destinations.scannable import empty_scannable, fallback_scannable
from beatprints_api.models.poster import AlbumPosterRequest, PosterPlatformLinks, TrackPosterRequest
from beatprints_api.palette import extract_palette, install_pylette_compatibility_module

install_pylette_compatibility_module()
beatprints_image.get_palette = extract_palette

MAX_COVER_BYTES = 15 * 1024 * 1024
ALLOWED_COVER_TYPES = {"image/jpeg", "image/png", "image/webp"}
cover_client = httpx.Client(
    follow_redirects=False, timeout=httpx.Timeout(15.0, connect=5.0),
    limits=httpx.Limits(max_connections=20, max_keepalive_connections=10, keepalive_expiry=30.0),
    headers={"User-Agent": "BeatPrints-API/0.1"},
)
atexit.register(cover_client.close)
rendering_lock = threading.Lock()


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


write.font = _cached_font
write._check_glyph = _cached_check_glyph
for _font_weight in ("Regular", "Bold", "Light"):
    write.font(_font_weight)


def _is_public_host(hostname: str) -> bool:
    try:
        addresses = socket.getaddrinfo(hostname, None)
    except socket.gaierror as exc:
        raise UpstreamError(f"Could not resolve cover host: {hostname}") from exc
    return any(ipaddress.ip_address(address[4][0]).is_global for address in addresses)


def _validate_cover_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("cover_url must be an HTTP(S) URL")
    if parsed.username or parsed.password:
        raise ValueError("cover_url must not contain credentials")
    if not _is_public_host(parsed.hostname):
        raise ValueError("cover_url must resolve to a public Internet address")


def download_cover(url: str, destination: Path) -> None:
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


def _poster_bytes(directory: Path) -> tuple[bytes, str]:
    generated = list(directory.glob("*.png"))
    if len(generated) != 1:
        raise RuntimeError("BeatPrints did not generate exactly one poster")
    path = generated[0]
    return path.read_bytes(), path.name


def selected_platform_link(
    links: PosterPlatformLinks | None, selected_platform: str | None,
    provider: str | None, source_link: str | None,
) -> tuple[DestinationAdapter, str] | None:
    if selected_platform is None:
        return None
    adapter = get_destination_adapter(selected_platform)
    values = links.root if links is not None else {}
    link = values.get(selected_platform)
    if link is None and source_link and provider and adapter.reuses_source_link(provider):
        link = source_link
    if link is None:
        raise ValueError(f"platform_links.{selected_platform} is required for qr_platform={selected_platform}")
    return adapter, str(link)


def _relative_luminance(color: tuple[int, int, int]) -> float:
    channels = [
        channel / 255 / 12.92 if channel / 255 <= 0.04045 else ((channel / 255 + 0.055) / 1.055) ** 2.4
        for channel in color
    ]
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def _contrast_with_white(color: tuple[int, int, int]) -> float:
    return 1.05 / (_relative_luminance(color) + 0.05)


def cover_qr_color(cover_path: Path) -> tuple[int, int, int]:
    with Image.open(cover_path) as cover:
        palette = extract_palette(cover, size=8)
    saturation = lambda color: colorsys.rgb_to_hsv(*(channel / 255 for channel in color))[1]
    high_contrast = [color for color in palette if _contrast_with_white(color) >= 4.5]
    if high_contrast:
        return max(high_contrast, key=saturation)
    selected = max(palette, key=saturation)
    for step in range(19, -1, -1):
        darkened = tuple(round(channel * step / 20) for channel in selected)
        if _contrast_with_white(darkened) >= 4.5:
            return darkened
    return 0, 0, 0


@contextmanager
def provider_rendering(
    provider: str | None, platform_link: tuple[DestinationAdapter, str] | None,
    qr_color: tuple[int, int, int] | None,
):
    with rendering_lock:
        original_cover, original_scannable = beatprints_image.cover, beatprints_image.scannable
        beatprints_image.scannable = empty_scannable
        if provider is not None:
            cover_renderer = get_catalog_adapter(provider).cover_renderer
            if cover_renderer is not None:
                beatprints_image.cover = cover_renderer
        if platform_link is not None and qr_color is not None:
            adapter, link = platform_link
            beatprints_image.scannable = adapter.scannable(link) or fallback_scannable(adapter.label, link, qr_color)
        try:
            yield
        finally:
            beatprints_image.cover, beatprints_image.scannable = original_cover, original_scannable


def _renderable_lyrics(value: str) -> str:
    return value or " "


def render_track(request: TrackPosterRequest, metadata, selected_lyrics: str) -> PosterResult:
    provider = request.provider if request.metadata is None else None
    platform_link = selected_platform_link(request.platform_links, request.qr_platform, provider, getattr(metadata, "link", None))
    with tempfile.TemporaryDirectory(prefix="beatprints-") as temp:
        directory, cover_path = Path(temp), Path(temp) / "cover"
        download_cover(metadata.cover, cover_path)
        qr_color = cover_qr_color(cover_path) if platform_link is not None else None
        with provider_rendering(provider, platform_link, qr_color):
            poster.Poster(str(directory)).track(metadata=metadata, lyrics=_renderable_lyrics(selected_lyrics), accent=request.accent, theme=request.theme, pcover=str(cover_path))
        content, filename = _poster_bytes(directory)
        return PosterResult(content, filename, {})


def render_album(request: AlbumPosterRequest, metadata) -> PosterResult:
    provider = request.provider if request.metadata is None else None
    platform_link = selected_platform_link(request.platform_links, request.qr_platform, provider, getattr(metadata, "link", None))
    with tempfile.TemporaryDirectory(prefix="beatprints-") as temp:
        directory, cover_path = Path(temp), Path(temp) / "cover"
        download_cover(metadata.cover, cover_path)
        qr_color = cover_qr_color(cover_path) if platform_link is not None else None
        with provider_rendering(provider, platform_link, qr_color):
            poster.Poster(str(directory)).album(metadata=metadata, indexing=request.indexing, accent=request.accent, theme=request.theme, pcover=str(cover_path))
        content, filename = _poster_bytes(directory)
        return PosterResult(content, filename, {})
