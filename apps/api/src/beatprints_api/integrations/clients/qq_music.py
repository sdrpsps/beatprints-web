"""QQ Music transport shared by catalog, destination, and lyrics adapters."""

import atexit

import httpx

from beatprints_api.exceptions import UpstreamError

SEARCH_URL = "https://c.y.qq.com/soso/fcgi-bin/client_search_cp"
TRACK_URL = "https://c.y.qq.com/v8/fcg-bin/fcg_play_single_song.fcg"
ALBUM_URL = "https://c.y.qq.com/v8/fcg-bin/fcg_v8_album_info_cp.fcg"
LYRICS_URL = "https://c.y.qq.com/lyric/fcgi-bin/fcg_query_lyric_new.fcg"


class QQMusicClient:
    def __init__(self, http_client: httpx.Client | None = None) -> None:
        self.http = http_client or httpx.Client(
            timeout=15.0,
            follow_redirects=True,
            headers={
                "Referer": "https://y.qq.com/",
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
            raise UpstreamError(f"QQ Music request failed: {exc}") from exc
        if not isinstance(payload, dict):
            raise UpstreamError("QQ Music returned an invalid response")
        if payload.get("code") not in (None, 0) or payload.get("retcode") not in (
            None,
            0,
        ):
            raise UpstreamError("QQ Music returned an error response")
        return payload

    def search(self, query: str, item_type: str, limit: int) -> dict:
        return self._get(
            SEARCH_URL,
            format="json",
            p=1,
            n=limit,
            w=query,
            t=0 if item_type == "track" else 8,
        )

    def track(self, identifier: int | str) -> dict:
        return self._get(TRACK_URL, songmid=str(identifier), format="json")

    def album(self, identifier: int | str) -> dict:
        return self._get(ALBUM_URL, albummid=str(identifier), format="json")

    def lyrics(self, identifier: int | str) -> dict:
        return self._get(
            LYRICS_URL, songmid=str(identifier), format="json", nobase64=1, g_tk=5381
        )


qq_music_client = QQMusicClient()
atexit.register(qq_music_client.close)
