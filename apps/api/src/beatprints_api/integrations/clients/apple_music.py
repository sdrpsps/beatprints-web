"""Shared anonymous Apple Music web catalog client without adapter registration."""

import base64
import json
import re
import threading
import time
from html.parser import HTMLParser
from urllib.parse import parse_qs, parse_qsl, urljoin, urlsplit

import httpx

from beatprints_api.exceptions import UpstreamError
from beatprints_api.integrations.region import current_region

WEB_URL = "https://music.apple.com/"
API_URL = "https://amp-api.music.apple.com"
JWT_PATTERN = re.compile(r"eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+")


class AppleMusicNotFound(UpstreamError):
    """The requested catalog item is not available in the current storefront."""


class _Scripts(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.urls: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "script":
            src = dict(attrs).get("src")
            if (
                src
                and "index" in urlsplit(src).path
                and urlsplit(src).path.endswith(".js")
            ):
                self.urls.append(src)


def _web_token(script: str) -> tuple[str, float] | None:
    """Select the unexpired public web-player token, without exposing it."""
    best: tuple[str, float] | None = None
    for token in JWT_PATTERN.findall(script):
        try:
            payload = token.split(".")[1]
            claims = json.loads(
                base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4))
            )
            expiry = float(claims["exp"])
            if claims.get("iss") != "AMPWebPlay" or expiry <= time.time() + 60:
                continue
        except ValueError, TypeError, KeyError, UnicodeDecodeError:
            continue
        if best is None or expiry > best[1]:
            best = token, expiry
    return best


class AppleMusicClient:
    def __init__(self, http_client: httpx.Client | None = None) -> None:
        self.http = http_client or httpx.Client(
            timeout=15.0,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        self._token: str | None = None
        self._expires_at = 0.0
        self._lock = threading.Lock()

    def _get_token(self) -> str:
        with self._lock:
            if self._token and self._expires_at > time.time() + 60:
                return self._token
            try:
                page = self.http.get(WEB_URL, follow_redirects=True)
                page.raise_for_status()
                if page.url.scheme != "https" or page.url.host != "music.apple.com":
                    raise UpstreamError(
                        "Apple Music web player redirected to an unexpected host"
                    )
                parser = _Scripts()
                parser.feed(page.text)
                for src in parser.urls:
                    url = urljoin(WEB_URL, src)
                    parsed = urlsplit(url)
                    if parsed.scheme != "https" or parsed.hostname not in {
                        "music.apple.com",
                        "js-cdn.music.apple.com",
                    }:
                        continue
                    response = self.http.get(url, follow_redirects=False)
                    response.raise_for_status()
                    found = _web_token(response.text)
                    if found:
                        self._token, self._expires_at = found
                        return self._token
            except httpx.HTTPError as exc:
                raise UpstreamError("Apple Music web player is unavailable") from exc
            raise UpstreamError("Apple Music web player token is unavailable")

    def _invalidate(self, token: str) -> None:
        with self._lock:
            if self._token == token:
                self._token = None
                self._expires_at = 0.0

    def _request(self, path: str, params: dict | None = None) -> dict:
        for attempt in range(2):
            token = self._get_token()
            try:
                response = self.http.get(
                    f"{API_URL}{path}",
                    params=params,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Origin": "https://music.apple.com",
                        "Referer": WEB_URL,
                    },
                    follow_redirects=False,
                )
                if response.status_code in (401, 403) and attempt == 0:
                    self._invalidate(token)
                    continue
                if response.status_code == 404:
                    raise AppleMusicNotFound("Apple Music catalog item was not found")
                response.raise_for_status()
                payload = response.json()
            except (httpx.HTTPError, ValueError) as exc:
                raise UpstreamError("Apple Music catalog request failed") from exc
            if not isinstance(payload, dict):
                raise UpstreamError("Apple Music catalog returned an invalid response")
            return payload
        raise UpstreamError("Apple Music catalog authentication failed")

    @staticmethod
    def _type(item_type: str) -> str:
        if item_type not in ("track", "album"):
            raise ValueError("Unsupported Apple Music catalog type")
        return "songs" if item_type == "track" else "albums"

    @staticmethod
    def _id(identifier: int | str) -> str:
        value = str(identifier)
        if not value.isascii() or not value.isdigit():
            raise AppleMusicNotFound("Apple Music catalog ID is invalid")
        return value

    def search(self, query: str, item_type: str, limit: int) -> list[dict]:
        resource = self._type(item_type)
        region = current_region().lower()
        payload = self._request(
            f"/v1/catalog/{region}/search",
            {"term": query, "types": "songs,albums", "limit": limit},
        )
        results = payload.get("results")
        if not isinstance(results, dict):
            raise UpstreamError("Apple Music search returned an invalid response")
        group = results.get(resource)
        if group is None:
            return []
        if not isinstance(group, dict) or not isinstance(group.get("data"), list):
            raise UpstreamError("Apple Music search returned an invalid response")
        rows = [row for row in group["data"] if isinstance(row, dict)]
        if group["data"] and not rows:
            raise UpstreamError("Apple Music search returned an invalid response")
        return rows

    def search_isrc(self, isrc: str, limit: int = 10) -> list[dict]:
        if not re.fullmatch(r"[A-Za-z]{2}[A-Za-z0-9]{3}[0-9]{7}", isrc):
            return []
        payload = self._request(
            f"/v1/catalog/{current_region().lower()}/songs",
            {"filter[isrc]": isrc.upper(), "limit": limit},
        )
        if not isinstance(payload.get("data"), list):
            raise UpstreamError("Apple Music ISRC lookup returned an invalid response")
        return [row for row in payload["data"] if isinstance(row, dict)]

    def item(
        self, identifier: int | str, item_type: str, *, include: str | None = None
    ) -> dict:
        identifier = self._id(identifier)
        resource = self._type(item_type)
        region = current_region().lower()
        payload = self._request(
            f"/v1/catalog/{region}/{resource}/{identifier}",
            {"include": include} if include else None,
        )
        rows = payload.get("data")
        if not isinstance(rows, list):
            raise UpstreamError("Apple Music catalog returned an invalid response")
        if not rows:
            raise AppleMusicNotFound("Apple Music catalog item was not found")
        for row in rows:
            if (
                isinstance(row, dict)
                and str(row.get("id")) == identifier
                and row.get("type") == resource
            ):
                return row
        raise UpstreamError("Apple Music catalog returned a different item")

    def album_tracks(self, album: dict) -> list[str]:
        identifier = self._id(album.get("id", ""))
        relationships = album.get("relationships")
        tracks = (
            relationships.get("tracks") if isinstance(relationships, dict) else None
        )
        if not isinstance(tracks, dict):
            raise UpstreamError("Apple Music album response contained no tracks")
        expected_path = (
            f"/v1/catalog/{current_region().lower()}/albums/{identifier}/tracks"
        )
        seen: set[str] = set()
        names: list[str] = []
        for _ in range(100):
            rows = tracks.get("data")
            if not isinstance(rows, list):
                raise UpstreamError("Apple Music album tracks were invalid")
            for row in rows:
                attributes = row.get("attributes") if isinstance(row, dict) else None
                name = attributes.get("name") if isinstance(attributes, dict) else None
                if not isinstance(name, str) or not name.strip():
                    raise UpstreamError("Apple Music album track was incomplete")
                names.append(name)
            next_url = tracks.get("next")
            if not next_url:
                if not names:
                    raise UpstreamError(
                        "Apple Music album response contained no tracks"
                    )
                return names
            if not isinstance(next_url, str) or next_url in seen:
                raise UpstreamError("Apple Music album pagination was invalid")
            seen.add(next_url)
            parsed = urlsplit(next_url)
            if parsed.scheme or parsed.netloc or parsed.path.lower() != expected_path:
                raise UpstreamError("Apple Music album pagination was invalid")
            tracks = self._request(expected_path, dict(parse_qsl(parsed.query)))
        raise UpstreamError("Apple Music album contained too many track pages")

    @staticmethod
    def _album_id_for_track(row: dict) -> str:
        attrs = row.get("attributes") if isinstance(row.get("attributes"), dict) else {}
        link = attrs.get("url")
        if isinstance(link, str):
            parsed = urlsplit(link)
            parts = [part for part in parsed.path.split("/") if part]
            track_ids = parse_qs(parsed.query).get("i", [])
            if (
                parsed.hostname == "music.apple.com"
                and "album" in parts
                and track_ids == [str(row.get("id"))]
                and parts[-1].isascii()
                and parts[-1].isdigit()
            ):
                return parts[-1]
        relationships = row.get("relationships")
        albums = (
            relationships.get("albums") if isinstance(relationships, dict) else None
        )
        rows = albums.get("data") if isinstance(albums, dict) else None
        if isinstance(rows, list):
            matches = [
                str(item.get("id"))
                for item in rows
                if isinstance(item, dict)
                and isinstance(item.get("attributes"), dict)
                and item["attributes"].get("name") == attrs.get("albumName")
                and str(item.get("id", "")).isascii()
                and str(item.get("id", "")).isdigit()
            ]
            if len(matches) == 1:
                return matches[0]
        return ""

    @staticmethod
    def normalize(row: dict, item_type: str) -> dict | None:
        resource = "songs" if item_type == "track" else "albums"
        attributes = row.get("attributes")
        if row.get("type") != resource or not isinstance(attributes, dict):
            return None
        identifier = str(row.get("id") or "")
        title = attributes.get("name")
        link = attributes.get("url")
        artwork = attributes.get("artwork")
        cover = artwork.get("url") if isinstance(artwork, dict) else None
        album_name = attributes.get("albumName")
        if (
            not identifier.isascii()
            or not identifier.isdigit()
            or not isinstance(title, str)
            or not title.strip()
            or not isinstance(link, str)
            or not link
            or not isinstance(cover, str)
            or not cover
            or (
                item_type == "track"
                and (not isinstance(album_name, str) or not album_name)
            )
        ):
            return None
        date = attributes.get("releaseDate")
        date = date.strip() if isinstance(date, str) else ""
        year = int(date[:4]) if len(date) >= 4 and date[:4].isdigit() else None
        precision = "day" if re.fullmatch(r"\d{4}-\d{2}-\d{2}", date) else None
        if not precision and re.fullmatch(r"\d{4}-\d{2}", date):
            precision = "month"
        if not precision and re.fullmatch(r"\d{4}", date):
            precision = "year"
        artist = attributes.get("artistName")
        result = {
            "id": identifier,
            "provider": "apple_music",
            "type": item_type,
            "title": title,
            "artists": [artist] if isinstance(artist, str) and artist else [],
            "cover_url": cover.replace("{w}", "600").replace("{h}", "600"),
            "link": link,
            "release_date": date or None,
            "release_year": year,
            "release_date_precision": precision,
        }
        if item_type == "track":
            milliseconds = attributes.get("durationInMillis")
            seconds = (
                round(milliseconds / 1000)
                if isinstance(milliseconds, (int, float)) and milliseconds >= 0
                else 0
            )
            isrc = attributes.get("isrc")
            isrc = isrc.strip().upper() if isinstance(isrc, str) else ""
            result.update(
                album={
                    "id": AppleMusicClient._album_id_for_track(row),
                    "title": album_name,
                },
                duration_seconds=seconds,
                duration=f"{seconds // 60:02d}:{seconds % 60:02d}",
                explicit=attributes.get("contentRating") == "explicit",
                isrc=(
                    isrc if re.fullmatch(r"[A-Z]{2}[A-Z0-9]{3}[0-9]{7}", isrc) else None
                ),
            )
        else:
            result["track_count"] = attributes.get("trackCount")
        return result

    @staticmethod
    def album_label(row: dict) -> str:
        attributes = row.get("attributes")
        if not isinstance(attributes, dict):
            return ""
        label = attributes.get("recordLabel")
        if (
            isinstance(label, str)
            and label.strip()
            and label.strip().casefold()
            not in {"unknown", "unknown label", "unknown records"}
        ):
            return label.strip()
        copyright_text = attributes.get("copyright")
        if not isinstance(copyright_text, str):
            return ""
        match = re.match(
            r"^\s*(?:℗|\([Pp]\))\s*(?:\d{4}\b)?\s*[-–—:]?\s*(.*?)\s*$",
            copyright_text,
        )
        return match.group(1) if match else ""


apple_music_client = AppleMusicClient()
