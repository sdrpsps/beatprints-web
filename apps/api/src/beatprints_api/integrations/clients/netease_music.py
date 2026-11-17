"""NetEase Music transport shared by catalog, destination, and lyrics adapters."""

import atexit

import httpx

from beatprints_api.exceptions import UpstreamError

SEARCH_URL = "https://music.163.com/api/search/get"
TRACK_URL = "https://music.163.com/api/song/detail/"
ALBUM_URL = "https://music.163.com/api/v1/album"
LYRICS_URL = "https://music.163.com/api/song/lyric/v1"


class NetEaseMusicClient:
    def __init__(self, http_client: httpx.Client | None = None) -> None:
        self.http = http_client or httpx.Client(
            timeout=15.0,
            follow_redirects=True,
            headers={
                "Referer": "https://music.163.com",
                "User-Agent": "BeatPrints-API/1.1",
            },
        )

    def close(self) -> None:
        self.http.close()

    def _get(self, url: str, **params: object) -> dict:
        try:
            response = self.http.get(url, params=params)
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise UpstreamError(f"NetEase Music request failed: {exc}") from exc
        if not isinstance(payload, dict):
            raise UpstreamError("NetEase Music returned an invalid response")
        if payload.get("code") not in (None, 200):
            raise UpstreamError(
                f"NetEase Music returned error code {payload.get('code')}"
            )
        return payload

    def search(self, query: str, item_type: str, limit: int) -> dict:
        return self._get(
            SEARCH_URL,
            type=1 if item_type == "track" else 10,
            s=query,
            limit=limit,
            offset=0,
        )

    def tracks(self, identifiers: list[int | str]) -> dict:
        return self._get(
            TRACK_URL, ids=f"[{','.join(str(value) for value in identifiers)}]"
        )

    def album(self, identifier: int | str) -> dict:
        return self._get(f"{ALBUM_URL}/{identifier}")

    def lyrics(self, identifier: int | str) -> dict:
        return self._get(LYRICS_URL, id=identifier, lv=-1, kv=-1, tv=-1, yv=1)


netease_music_client = NetEaseMusicClient()
atexit.register(netease_music_client.close)
