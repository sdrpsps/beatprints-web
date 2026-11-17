import pytest
from BeatPrints.deez import TrackMetadata

from beatprints_api.exceptions import LyricsNotFoundError
from beatprints_api.integrations.lyrics import netease, qq_music
from beatprints_api.integrations.lyrics.base import LyricsSourceResult
from beatprints_api.integrations.lyrics.common import confident_track_match


def traditional_track() -> TrackMetadata:
    return TrackMetadata(
        title="修煉愛情",
        artists=["林俊傑"],
        album="因你 而在",
        released="2013-03-13",
        duration="04:47",
        cover="https://example.com/cover.jpg",
        label="",
    )


def search_response(provider, rows):
    if provider is qq_music:
        return {
            "data": {
                "song": {
                    "list": [
                        {
                            "songmid": str(identifier),
                            "songname": title,
                            "singer": [{"name": artist}],
                            "albumname": album,
                            "interval": duration,
                        }
                        for identifier, title, artist, album, duration in rows
                    ]
                }
            }
        }
    return {
        "result": {
            "songs": [
                {
                    "id": identifier,
                    "name": title,
                    "artists": [{"name": artist}],
                    "album": {"name": album},
                    "duration": duration * 1000,
                }
                for identifier, title, artist, album, duration in rows
            ]
        }
    }


@pytest.mark.parametrize("provider", [qq_music, netease])
def test_fetch_matches_simplified_candidates_without_changing_source(
    monkeypatch, provider
) -> None:
    track = traditional_track()
    client = (
        provider.qq_music_client
        if provider is qq_music
        else provider.netease_music_client
    )
    requests = []

    def search(query, item_type, limit):
        requests.append((query, item_type, limit))
        return search_response(provider, [(101, "修炼爱情", "林俊杰", "因你而在", 287)])

    def lyrics(identifier):
        assert str(identifier) == "101"
        if provider is qq_music:
            return {"lyric": "[00:01.00]First line"}
        return {"lrc": {"lyric": "[00:01.00]First line"}}

    monkeypatch.setattr(client, "search", search)
    monkeypatch.setattr(client, "lyrics", lyrics)

    assert provider.fetch(track) == LyricsSourceResult(False, ("First line",))
    assert requests == [("修煉愛情 林俊傑", "track", 10)]
    assert (track.title, track.artists, track.album) == (
        "修煉愛情",
        ["林俊傑"],
        "因你 而在",
    )


@pytest.mark.parametrize("provider", [qq_music, netease])
def test_original_script_candidate_is_preferred(provider) -> None:
    payload = search_response(
        provider,
        [
            (101, "修炼爱情", "林俊杰", "因你而在", 287),
            (102, "修煉愛情", "林俊傑", "因你 而在", 287),
        ],
    )
    assert str(provider._select_song(payload, traditional_track())) == "102"


@pytest.mark.parametrize("provider", [qq_music, netease])
@pytest.mark.parametrize(
    "row",
    [
        (101, "修炼爱情 (现场版)", "林俊杰", "因你而在", 287),
        (101, "修炼爱情", "林俊杰", "因你而在", 291),
        (101, "修炼爱情", "其他歌手", "其他专辑", 287),
    ],
)
def test_simplified_matching_rejects_unconfirmed_recordings(
    monkeypatch, provider, row
) -> None:
    client = (
        provider.qq_music_client
        if provider is qq_music
        else provider.netease_music_client
    )
    monkeypatch.setattr(
        client, "search", lambda *_args: search_response(provider, [row])
    )
    with pytest.raises(LyricsNotFoundError):
        provider.fetch(traditional_track())


def test_simplified_matching_normalizes_equivalent_version_markers() -> None:
    track = traditional_track()
    track.title = "修煉愛情 (現場版)"
    assert confident_track_match(
        track,
        title="修炼爱情 (现场版)",
        artists=["林俊杰"],
        album="因你而在",
        candidate_duration_seconds=287,
        simplify_chinese=True,
    )
    assert not confident_track_match(
        track,
        title="修炼爱情",
        artists=["林俊杰"],
        album="因你而在",
        candidate_duration_seconds=287,
        simplify_chinese=True,
    )


def test_simplified_matching_works_in_both_directions_for_album_and_artist() -> None:
    track = traditional_track()
    track.title = "修炼爱情"
    track.artists = ["林俊杰"]
    track.album = "因你而在"
    assert confident_track_match(
        track,
        title="修煉愛情",
        artists=["林俊傑"],
        album="其他專輯",
        candidate_duration_seconds=287,
        simplify_chinese=True,
    )
    assert confident_track_match(
        track,
        title="修煉愛情",
        artists=["其他歌手"],
        album="因你 而在",
        candidate_duration_seconds=287,
        simplify_chinese=True,
    )
