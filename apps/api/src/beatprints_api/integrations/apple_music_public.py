"""Read public Apple Music pages when the iTunes search catalog is incomplete.

Apple Music's server-rendered pages expose catalog IDs and album track listings.
Use those exact IDs with the iTunes lookup API for current normalized metadata.
The page format is an upstream implementation detail and may change.
"""

import json
from html.parser import HTMLParser
from typing import Callable

import httpx

from beatprints_api.exceptions import UpstreamError
from beatprints_api.integrations.region import current_region


class _PageDataParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._in_data = False
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "script" and dict(attrs).get("id") == "serialized-server-data":
            self._in_data = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "script":
            self._in_data = False

    def handle_data(self, data: str) -> None:
        if self._in_data:
            self.parts.append(data)


def _sections(path: str, params: dict | None = None) -> list[dict]:
    try:
        response = httpx.get(
            f"https://music.apple.com/{current_region().lower()}/{path}",
            params=params, timeout=15.0, follow_redirects=True,
        )
        response.raise_for_status()
        parser = _PageDataParser()
        parser.feed(response.text)
        payload = json.loads("".join(parser.parts))
        pages = payload["data"]
        if not isinstance(pages, list) or not pages:
            raise ValueError("missing page data")
        if path == "search":
            intent = pages[0].get("intent")
            expected_term = params.get("term") if params else None
            if (
                not isinstance(intent, dict)
                or intent.get("$kind") != "SearchResultsPageIntent"
                or str(intent.get("storefront", "")).casefold() != current_region().casefold()
                or not isinstance(intent.get("term"), str)
                or not isinstance(expected_term, str)
                or intent["term"].strip().casefold() != expected_term.strip().casefold()
            ):
                raise UpstreamError("Apple Music search returned a different storefront or query")
        sections = pages[0]["data"]["sections"]
        if not isinstance(sections, list):
            raise ValueError("missing page sections")
        return [section for section in sections if isinstance(section, dict)]
    except (httpx.HTTPError, ValueError, KeyError, TypeError, IndexError) as exc:
        raise UpstreamError(f"Apple Music public catalog request failed: {exc}") from exc


SEARCH_UNAVAILABLE = "Apple Music search is unavailable for the selected region"


def search_rows(
    query: str,
    item_type: str,
    limit: int,
    lookup: Callable[[str], list[dict]],
) -> list[dict]:
    """Find ranked exact IDs and resolve them in the current storefront."""
    kind = "song" if item_type == "track" else "album"
    identifiers: list[str] = []
    try:
        sections = _sections("search", {"term": query})
    except UpstreamError as exc:
        raise UpstreamError(SEARCH_UNAVAILABLE) from exc
    for section in sections:
        items = section.get("items")
        if not isinstance(items, list):
            continue
        for item in items:
            descriptor = item.get("contentDescriptor") if isinstance(item, dict) else None
            if not isinstance(descriptor, dict) or descriptor.get("kind") != kind:
                continue
            identities = descriptor.get("identifiers")
            identifier = str(identities.get("storeAdamID", "")) if isinstance(identities, dict) else ""
            if identifier.isascii() and identifier.isdigit() and identifier not in identifiers:
                identifiers.append(identifier)
                if len(identifiers) >= limit:
                    break
        if len(identifiers) >= limit:
            break
    if not identifiers:
        return []
    try:
        rows = lookup(",".join(identifiers))
    except UpstreamError as exc:
        raise UpstreamError(SEARCH_UNAVAILABLE) from exc
    key = "trackId" if item_type == "track" else "collectionId"
    expected = "track" if item_type == "track" else "collection"
    by_id = {str(row.get(key)): row for row in rows if row.get("wrapperType") == expected}
    resolved = [by_id[identifier] for identifier in identifiers if identifier in by_id]
    if not resolved:
        raise UpstreamError(SEARCH_UNAVAILABLE)
    return resolved


def album_tracks(catalog_id: int | str) -> list[str]:
    """Retrieve the selected album's current track list from its public page."""
    identifier = str(catalog_id)
    if not identifier.isascii() or not identifier.isdigit():
        raise UpstreamError("Apple Music album ID is invalid")
    for section in _sections(f"album/{identifier}"):
        if section.get("id") != f"track-list - {identifier}":
            continue
        items = section.get("items")
        if not isinstance(items, list):
            break
        tracks = [item["title"] for item in items if isinstance(item, dict) and isinstance(item.get("title"), str) and item["title"].strip()]
        if tracks:
            return tracks
    raise UpstreamError("Apple Music album response contained no tracks")
