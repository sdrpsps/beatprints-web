import atexit
import re
import threading
import time
from typing import Literal
from urllib.parse import quote

import httpx


class SpotifyError(RuntimeError):
    """Raised when Spotify is unavailable or rejects a request."""


class SpotifyNotConfiguredError(SpotifyError):
    """Raised when Spotify credentials were not configured."""


class SpotifyCodeClient:
    """Fetches Spotify's own scan-ready code artwork for a Spotify URI.

    Spotify Codes are not part of the public Web API and have no official Python
    SDK. Spotify's own code service returns the image that its mobile scanner
    recognizes, so keeping this small adapter local is safer than depending on
    an unmaintained third-party code generator.
    """

    SCANNABLES_URL = "https://scannables.scdn.co/uri/plain"
    MAX_IMAGE_BYTES = 2 * 1024 * 1024

    def __init__(self) -> None:
        self._http = httpx.Client(
            timeout=httpx.Timeout(10.0, connect=5.0),
            limits=httpx.Limits(
                max_connections=10,
                max_keepalive_connections=5,
                keepalive_expiry=30.0,
            ),
            headers={"User-Agent": "BeatPrints-API/0.1"},
        )
        atexit.register(self._http.close)

    def png(self, uri: str, width: int) -> bytes:
        """Return Spotify's standard black-on-white PNG code for ``uri``."""

        url = (
            f"{self.SCANNABLES_URL}/png/ffffff/black/{width}/" f"{quote(uri, safe=':')}"
        )
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


class SpotifyClient:
    TOKEN_URL = "https://accounts.spotify.com/api/token"
    API_URL = "https://api.spotify.com/v1"

    def __init__(
        self,
        client_id: str | None,
        client_secret: str | None,
        market: str = "US",
    ) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.market = market
        self._token: str | None = None
        self._token_expires_at = 0.0
        self._token_lock = threading.Lock()
        self._http = httpx.Client(
            timeout=httpx.Timeout(15.0, connect=5.0),
            limits=httpx.Limits(
                max_connections=20,
                max_keepalive_connections=10,
                keepalive_expiry=30.0,
            ),
            headers={"User-Agent": "BeatPrints-API/0.1"},
        )
        atexit.register(self._http.close)

    @property
    def configured(self) -> bool:
        return bool(self.client_id and self.client_secret)

    def _access_token(self) -> str:
        if not self.configured:
            raise SpotifyNotConfiguredError(
                "Spotify search is not configured. Set SPOTIFY_CLIENT_ID and "
                "SPOTIFY_CLIENT_SECRET."
            )

        with self._token_lock:
            if self._token and time.monotonic() < self._token_expires_at:
                return self._token

            try:
                response = self._http.post(
                    self.TOKEN_URL,
                    data={"grant_type": "client_credentials"},
                    auth=(self.client_id or "", self.client_secret or ""),
                    timeout=10.0,
                )
                response.raise_for_status()
            except httpx.HTTPError as exc:
                raise SpotifyError(
                    f"Could not authenticate with Spotify: {exc}"
                ) from exc

            payload = response.json()
            self._token = payload["access_token"]
            self._token_expires_at = time.monotonic() + max(
                int(payload.get("expires_in", 3600)) - 30,
                1,
            )
            return self._token

    def search(
        self,
        query: str,
        search_type: Literal["track", "album"],
        limit: int,
    ) -> list[dict]:
        payload = self._get(
            "/search",
            params={
                "q": query,
                "type": search_type,
                "limit": min(limit, 10),
                "market": self.market,
            },
        )
        key = "tracks" if search_type == "track" else "albums"
        items = payload[key]["items"]
        return [
            (
                self._format_track(item)
                if search_type == "track"
                else self._format_album(item)
            )
            for item in items
        ]

    def _get(self, path: str, params: dict | None = None) -> dict:
        token = self._access_token()
        try:
            response = self._http.get(
                f"{self.API_URL}{path}",
                params=params,
                headers={"Authorization": f"Bearer {token}"},
                timeout=15.0,
            )
            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After", "unknown")
                raise SpotifyError(
                    f"Spotify rate limit exceeded; retry after {retry_after} seconds"
                )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise SpotifyError(f"Spotify request failed: {exc}") from exc
        return response.json()

    def track_metadata(self, track_id: str) -> dict:
        track = self._get(f"/tracks/{track_id}", {"market": self.market})
        album = self._get(f"/albums/{track['album']['id']}", {"market": self.market})
        seconds = int(track["duration_ms"]) // 1000
        minutes, remaining_seconds = divmod(seconds, 60)
        return {
            "title": track["name"],
            "artists": [artist["name"] for artist in track["artists"]],
            "album": album["name"],
            "released": album["release_date"],
            "duration": f"{minutes:02d}:{remaining_seconds:02d}",
            "cover": self._cover_url(album),
            "label": self._album_label(album),
            "link": track["external_urls"]["spotify"],
        }

    def album_metadata(self, album_id: str) -> dict:
        album = self._get(f"/albums/{album_id}", {"market": self.market})
        tracks_page = album["tracks"]
        tracks = [item["name"] for item in tracks_page["items"]]
        while tracks_page.get("next"):
            next_url = tracks_page["next"]
            path = next_url.removeprefix(self.API_URL)
            tracks_page = self._get(path)
            tracks.extend(item["name"] for item in tracks_page["items"])
        return {
            "title": album["name"],
            "artists": [artist["name"] for artist in album["artists"]],
            "released": album["release_date"],
            "tracks": tracks,
            "cover": self._cover_url(album),
            "label": self._album_label(album),
            "link": album["external_urls"]["spotify"],
        }

    @staticmethod
    def _cover_url(item: dict) -> str:
        images = item.get("images") or []
        if not images:
            raise SpotifyError("Spotify result did not include cover art")
        return images[0]["url"]

    @staticmethod
    def _album_label(album: dict) -> str:
        """Return a real label value, deriving it from copyright data if needed."""

        label = str(album.get("label") or "").strip()
        if label and label.casefold() not in {
            "unknown",
            "unknown label",
            "unknown records",
        }:
            return label

        copyrights = album.get("copyrights") or []
        ordered = sorted(
            copyrights,
            key=lambda item: 0 if str(item.get("type", "")).upper() == "P" else 1,
        )
        for copyright_item in ordered:
            text = str(copyright_item.get("text") or "").strip()
            if not text:
                continue
            derived = re.sub(
                r"^\s*(?:[℗©]|[(][PCpc][)])?\s*(?:\d{4})?\s*[-–—:]?\s*",
                "",
                text,
            ).strip()
            if derived:
                return derived
        return ""

    @classmethod
    def _format_track(cls, item: dict) -> dict:
        album = item["album"]
        seconds = int(item["duration_ms"]) // 1000
        minutes, remaining_seconds = divmod(seconds, 60)
        release_date = album.get("release_date")
        return {
            "id": item["id"],
            "provider": "spotify",
            "type": "track",
            "title": item["name"],
            "artists": [artist["name"] for artist in item["artists"]],
            "cover_url": cls._cover_url(album),
            "link": item["external_urls"]["spotify"],
            "release_date": release_date,
            "release_year": (
                int(release_date[:4])
                if release_date and len(release_date) >= 4
                else None
            ),
            "release_date_precision": album.get("release_date_precision"),
            "album": {
                "id": album["id"],
                "title": album["name"],
            },
            "duration_seconds": seconds,
            "duration": f"{minutes:02d}:{remaining_seconds:02d}",
            "explicit": item.get("explicit"),
            "isrc": (item.get("external_ids") or {}).get("isrc"),
        }

    @classmethod
    def _format_album(cls, item: dict) -> dict:
        release_date = item.get("release_date")
        return {
            "id": item["id"],
            "provider": "spotify",
            "type": "album",
            "title": item["name"],
            "artists": [artist["name"] for artist in item["artists"]],
            "cover_url": cls._cover_url(item),
            "link": item["external_urls"]["spotify"],
            "release_date": release_date,
            "release_year": (
                int(release_date[:4])
                if release_date and len(release_date) >= 4
                else None
            ),
            "release_date_precision": item.get("release_date_precision"),
            "track_count": item.get("total_tracks"),
        }
