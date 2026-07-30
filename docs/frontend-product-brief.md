# BeatPrints Frontend Product Brief

## Product definition

BeatPrints helps a listener or music collector turn a real song or album into a finished,
downloadable poster. It searches music catalogs for trustworthy metadata and cover artwork,
lets the user make a small number of editorial choices, and delegates poster rendering to the
BeatPrints backend.

The product should feel closer to composing a piece of music ephemera—liner notes, a record
sleeve insert, or a concert print—than operating an AI image generator. The cover and final
poster are the visual center of the experience.

The underlying BeatPrints generator is licensed CC BY-NC-SA 4.0 for non-commercial use.
Product surfaces and exported-work attribution must not imply unrestricted commercial use.

## Primary track-poster journey

### 1. Find the recording

The user searches by song, artist, album, or an approximate combination. The frontend calls:

```http
GET /v1/search?query=<query>&type=track&provider=<deezer|spotify|all>&limit=<1..20>
```

Search results already contain the data needed for a useful selection card:

- `id` and `provider`
- `title` and `artists`
- `cover_url`
- source `link`
- `release_date`, `release_year`, and date precision
- album ID and title
- formatted and numeric duration
- explicit-content flag
- ISRC when available

The UI must preserve the selected result's `provider + id`. The poster request should send
those values as `provider + catalog_id`. Do not send the original query after an exact result
has been selected because the backend query path searches again and uses the first match.

The result list needs loading, no-results, upstream-unavailable, source-not-configured, and
retry states. Spotify may return HTTP 503 when server credentials are not configured;
`provider=all` still returns Deezer results when Spotify is unavailable.

### 2. Confirm the matched recording

Show the selected cover and enough metadata to disambiguate recordings with the same title:

- title and artists
- album
- release year/date
- duration
- explicit marker when applicable
- metadata source

Changing the selected recording invalidates any lyrics and platform-link choices tied to the
previous selection.

### 3. Select four lyric lines

The intended product interaction is to show lyrics for the selected recording and let the user
choose exactly four lines for the poster.

The generation endpoint currently supports:

- `lyrics`: explicit text supplied by the caller, recommended as four lines;
- `lyrics_range`: an inclusive `start-end` string such as `11-14`; the selected range must
  resolve to exactly four non-empty LRClib lines;
- neither field: the backend selects the first four non-empty LRClib lines;
- instrumental recordings: `instrumental_text` is rendered instead.

The frontend reads normalized lyrics for the exact selected recording with:

```http
GET /v1/lyrics?provider=<deezer|spotify>&catalog_id=<selected-result-id>
```

The endpoint returns ordered, non-empty lyric lines with stable one-based indices and an
`instrumental` flag. The frontend defaults to the first four lines, allows any four lines to be
selected, and submits their final text as `lyrics` so the generated result exactly matches the
selection. If lyrics are unavailable, the user can enter four lines manually. Instrumental
recordings default to no lyric-area text and may use an optional custom short line.

Four non-contiguous lines are allowed. The frontend submits explicit `lyrics`; the older
`lyrics_range` model remains available to direct API consumers that prefer a contiguous
interval.

### 4. Optionally choose a poster platform

The metadata provider and poster platform are separate concepts:

- `provider` chooses where metadata is fetched: `deezer` or `spotify`.
- `qr_platform` optionally chooses the one platform rendered on the poster:
  `spotify`, `apple_music`, `qq_music`, or `netease_music`.

When the user chooses no platform, omit `qr_platform`; the poster contains no platform label
or QR code.

When Spotify supplies the metadata and `qr_platform=spotify`, the backend can reuse Spotify's
source link. For Apple Music, the frontend should request a conservative automatic match using
the selected result's unchanged `provider + id` through
`GET /v1/platform-links/apple-music?provider=<deezer|spotify>&catalog_id=<id>&type=<track|album>`.
The backend retrieves that exact source item, searches the configured Apple Music storefront,
and returns a link only when the title, artist, and release-specific metadata meet its confidence
threshold. QQ Music and NetEase Music currently still require a caller-supplied matching URL.
If the listener supplies a different Apple Music URL, the frontend can read that link's current
public Apple metadata through `GET /v1/platform-links/apple-music/resolve?url=<apple-music-url>`
and update only the Apple Music confirmation card. The poster's primary metadata, lyrics, and
cover remain tied to the originally selected Spotify or Deezer catalog result.

Only one platform is rendered per poster. For Spotify, a canonical Spotify track or album link
renders Spotify's native Spotify Code, which is scan-ready in the Spotify mobile app. The other
platforms use a standard QR code whose dark color is extracted from the cover while the QR
background remains white.

The UI should present this as an optional poster destination, not as the metadata search source.
Do not label both concepts simply as “音乐平台.”

### 5. Configure appearance and generate

Track posters support:

- `theme`: `Light`, `Dark`, `Catppuccin`, `Gruvbox`, `Nord`, `RosePine`, or `Everforest`;
- `accent`: whether to add a cover-derived accent at the bottom;
- `instrumental_text`: advanced fallback text for instrumental recordings.

The final request is:

```http
POST /v1/posters/track
Content-Type: application/json

{
  "provider": "spotify",
  "catalog_id": "<selected-result-id>",
  "lyrics": "line one\nline two\nline three\nline four",
  "qr_platform": "spotify",
  "theme": "Light",
  "accent": true
}
```

The QR fields are omitted when the user does not choose a destination. An Apple Music destination
includes the returned automatic-match URL under `platform_links`; QQ Music and NetEase Music
destinations include a caller-supplied matching URL. If an Apple Music match cannot be confirmed,
show a clear no-match state and do not allow generation with Apple Music selected.

Generation is server-side and concurrency-limited. The UI needs an honest pending state and
must prevent accidental duplicate submissions without implying fine-grained progress the API
does not provide.

Success is raw `image/png`, not the normal JSON envelope. The browser should create an object
URL for preview and download, then revoke it when replaced or unmounted. The backend does not
persist generated images after the response.

Failures use the JSON envelope:

```json
{
  "code": 42200,
  "data": {
    "errors": []
  },
  "message": "..."
}
```

Display actionable messages for validation, missing provider configuration, upstream catalog
or cover failures, and generation failures. Response headers expose `X-Request-ID` for support
and `X-Process-Time` for diagnostics.

## Album-poster journey

Album search uses the same search endpoint with `type=album`. Results include cover, artists,
release data, source link, explicit flag, and track count.

Generation uses:

```http
POST /v1/posters/album
```

It shares `provider`, `catalog_id`, optional `qr_platform`/`platform_links`, `theme`, and
`accent`. Album-specific options are:

- `indexing`: display `1.`, `2.`, and so on before track names;
- `shuffle`: randomize track order before rendering.

Album posters do not use lyrics.

## Advanced custom-metadata path

Both generation endpoints accept caller-supplied `metadata` instead of query or catalog ID.
Exactly one of `query`, `catalog_id`, or `metadata` is allowed. Custom metadata supports an
external public cover URL; the backend accepts JPEG, PNG, and WebP up to 15 MB and rejects
private-network hosts.

This is an advanced or fallback workflow, not the primary creation journey. Do not expose its
full complexity in the default flow unless product requirements call for manual correction.

## API integration constraints

- Protected `/v1` endpoints require a Bearer API key when the backend is configured with one.
  A long-lived server API key must not be embedded in a public Vite bundle. Production needs
  either user authentication plus a backend-for-frontend/proxy, or an intentionally public API
  deployment with appropriate abuse controls.
- The API must allow the deployed frontend origin through CORS.
- JSON endpoints use `{code, data, message}`; poster success responses are PNG.
- Search and generation depend on external providers and must be treated as fallible network
  operations.

## Design direction

- Make cover artwork and the emerging poster the dominant visual material.
- Treat the four lyric lines as an editorial selection, not a generic multi-select form.
- Use catalog metadata to establish trust and disambiguate recordings.
- Reveal platform QR options only when requested; absence is a valid default.
- Avoid generic AI sparkles, dashboard KPI cards, gratuitous gradients, and decoration that
  competes with the artwork.
- Use one signature interaction tied to the act of making a poster—for example a disciplined
  transition from catalog result to composed print preview—while keeping the surrounding UI
  quiet.
- Write interface copy from the listener's perspective: “选择四行歌词,” “添加平台入口,” and
  “生成海报,” rather than exposing backend terms such as `catalog_id` or `qr_platform`.

## Definition of done for the core journey

- The user can distinguish and select the correct recording.
- The selected recording survives every later step as an exact provider/catalog reference.
- Exactly four lyric lines are visibly selected before track generation.
- No QR code is added unless the user explicitly chooses a platform.
- A chosen non-Spotify platform cannot proceed without its matching URL.
- The user can review theme and accent choices before generation.
- Pending, success, failure, retry, and download behavior are complete.
- Keyboard, focus, responsive, reduced-motion, and image-loading states are verified.
- The generated PNG remains the focus of the completion state.
