"""Fetch and cache public GitHub release notes for the poster UI."""

from collections import OrderedDict
from threading import Lock
from time import monotonic

import httpx

from beatprints_api.exceptions import UpstreamServiceError

_CACHE_TTL = 3600
_CACHE_LIMIT = 8
_cache: OrderedDict[str, tuple[float, str]] = OrderedDict()
_lock = Lock()


def get_release_notes(version: str) -> str:
    with _lock:
        cached = _cache.get(version)
        if cached and monotonic() - cached[0] < _CACHE_TTL:
            _cache.move_to_end(version)
            return cached[1]
        try:
            response = httpx.get(
                f"https://api.github.com/repos/sdrpsps/beatprints-web/releases/tags/v{version}",
                headers={"Accept": "application/vnd.github+json", "User-Agent": "BeatPrints-Web"},
                timeout=httpx.Timeout(5.0, connect=3.0),
                follow_redirects=False,
            )
            response.raise_for_status()
            body = response.json().get("body")
            if not isinstance(body, str) or not body.strip():
                raise ValueError("Release notes are empty")
        except (httpx.HTTPError, ValueError, AttributeError):
            if cached:
                return cached[1]
            raise UpstreamServiceError("Release notes are unavailable", unavailable=True) from None
        _cache[version] = (monotonic(), body)
        _cache.move_to_end(version)
        while len(_cache) > _CACHE_LIMIT:
            _cache.popitem(last=False)
        return body
