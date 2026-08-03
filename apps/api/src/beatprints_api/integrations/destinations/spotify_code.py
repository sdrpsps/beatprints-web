"""Spotify Code artwork client used only by the Spotify destination."""

import atexit
from urllib.parse import quote

import httpx

from beatprints_api.integrations.catalog.spotify import SpotifyError


class SpotifyCodeClient:
    """Fetch Spotify's scan-ready code artwork for a Spotify URI."""

    SCANNABLES_URL = "https://scannables.scdn.co/uri/plain"
    MAX_IMAGE_BYTES = 2 * 1024 * 1024

    def __init__(self) -> None:
        self._http = httpx.Client(
            timeout=httpx.Timeout(10.0, connect=5.0),
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5, keepalive_expiry=30.0),
            headers={"User-Agent": "BeatPrints-API/0.1"},
        )
        atexit.register(self._http.close)

    def png(self, uri: str, width: int) -> bytes:
        url = f"{self.SCANNABLES_URL}/png/ffffff/black/{width}/{quote(uri, safe=':')}"
        try:
            response = self._http.get(url)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise SpotifyError(f"Could not generate Spotify Code: {exc}") from exc
        content_type = response.headers.get("content-type", "").split(";", 1)[0]
        if content_type != "image/png":
            raise SpotifyError("Spotify Code service returned an unexpected image type")
        if len(response.content) > self.MAX_IMAGE_BYTES:
            raise SpotifyError("Spotify Code image exceeds the 2 MB limit")
        return response.content


spotify_code_client = SpotifyCodeClient()
