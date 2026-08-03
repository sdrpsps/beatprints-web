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
GET /v1/search?query=<query>&type=track&provider=<qq_music|netease_music|spotify|all>&limit=<1..20>
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
`provider=all` still returns QQ Music and NetEase Music results when Spotify is unavailable.

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

### 3. Optionally select up to four lyric lines

The intended product interaction is to show lyrics for the selected recording and let the user
leave lyrics off the poster or choose up to four lines.

The generation endpoint currently supports:

- `lyrics`: optional explicit text supplied by the caller, limited to four lines; an empty
  string explicitly omits lyrics from the poster;
- `lyrics_range`: an inclusive `start-end` string such as `11-14`; the selected range must
  resolve to exactly four non-empty LRClib lines;
- neither field: the backend selects the first four non-empty QQ Music lyric lines;
- instrumental recordings: `instrumental_text` is rendered instead.

The frontend keeps its enabled lyric sources in a static registry, then reads normalized lyrics
for the exact selected recording with:

```http
GET /v1/lyrics?provider=<qq_music|netease_music|spotify>&catalog_id=<selected-result-id>&source=<source-key>
```

The endpoint returns ordered, non-empty lyric lines with stable one-based indices and an
`instrumental` flag. The frontend defaults to no selected lines, allows up to four lines to be
selected, and submits their final text as `lyrics` so the generated result exactly matches the
selection. An empty selection is submitted as an empty string so the backend does not fall back
to its legacy first-four-lines behavior. If lyrics are unavailable, the user can enter up to four
lines manually or leave the field empty. Instrumental recordings default to no lyric-area text
and may use optional custom text of up to four lines.

Up to four non-contiguous lines are allowed. The frontend submits explicit `lyrics`; the older
`lyrics_range` model remains available to direct API consumers that prefer a contiguous
interval.

### 4. Optionally choose a poster platform

The metadata provider and poster platform are separate concepts:

- `provider` chooses where metadata is fetched: `qq_music`, `netease_music`, or `spotify`.
- `qr_platform` optionally chooses one destination from the frontend's static registry.

The frontend maintains static catalog, lyric, and destination registries. They supply labels,
preferred defaults, and destination capabilities such as accepted public-link domains and source
providers whose canonical links can be reused directly. A destination's preferred default does
not override the product-level initial choice of no QR destination.

When the user chooses no platform, omit `qr_platform`; the poster contains no platform label
or QR code.

The frontend uses one API family for every QR destination. It must always pass the exact selected
result's unchanged `provider + id`, never a new text query:

```http
GET /v1/platform-links/<enabled-destination>/options
  ?provider=<qq_music|netease_music|spotify>&catalog_id=<id>&type=<track|album>
```

The backend retrieves that exact source item and runs one shared matching engine for every
destination. Destination adapters only implement catalog search, link resolution, canonical
metadata mapping, and optional platform capabilities such as Spotify ISRC lookup. The shared
engine applies title/version, artist, release, duration, track-count, ranking, and ambiguity rules.
The response contains an optional confirmed `match` and ranked `candidates` from the same lookup.
When the selected source and QR destination are the same enabled platform, the destination
reuses that source item's canonical link. Cross-platform destinations continue through the
conservative matching, candidate, and manual-link journey.

Candidate search deliberately has broader recall than automatic confirmation. It ranks by title,
artist, album, year, duration, and track count, but never silently confirms a weak result. The UI
can transition directly to the alternatives without another user action or another visible wait
because confirmation and alternatives come from the same response. It shows these
alternatives using the same cover/title/artist/context hierarchy as source search, with a “Select”
action. Selecting a candidate calls
`GET /v1/platform-links/<enabled-destination>/resolve?url=<public-url>` and uses the returned current metadata
for the platform confirmation card. Manual public-link entry remains the final fallback and uses
the same resolve behavior. Candidate or manual resolution refreshes only the QR destination and
confirmation card; the poster's source metadata, lyrics, cover, and catalog ID remain unchanged.

Only one platform is rendered per poster. For Spotify, a canonical Spotify track or album link
renders Spotify's native Spotify Code, which is scan-ready in the Spotify mobile app. The other
platforms use a standard QR code. Every platform mark and code uses the shared poster-theme color
rule; platform-specific differences are limited to the mark and code format.

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

The QR fields are omitted when the user does not choose a destination. Every cross-platform
destination includes its confirmed automatic, candidate-resolved, or manually resolved URL under
`platform_links`. If an automatic match cannot be confirmed, show ranked candidates and manual
link entry. Do not allow generation while browsing candidates or until the selected/manual URL has
been resolved into current metadata.

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
- Treat lyric lines as an optional editorial selection, not a generic multi-select form.
- Use catalog metadata to establish trust and disambiguate recordings.
- Reveal platform QR options only when requested; absence is a valid default.
- Avoid generic AI sparkles, dashboard KPI cards, gratuitous gradients, and decoration that
  competes with the artwork.
- Use one signature interaction tied to the act of making a poster—for example a disciplined
  transition from catalog result to composed print preview—while keeping the surrounding UI
  quiet.
- Write interface copy from the listener's perspective: “选择歌词,” “添加平台入口,” and
  “生成海报,” rather than exposing backend terms such as `catalog_id` or `qr_platform`.

## Definition of done for the core journey

- The user can distinguish and select the correct recording.
- The selected recording survives every later step as an exact provider/catalog reference.
- Zero to four lyric lines can be selected before track generation.
- No QR code is added unless the user explicitly chooses a platform.
- A chosen non-Spotify platform cannot proceed without its matching URL.
- The user can review theme and accent choices before generation.
- Pending, success, failure, retry, and download behavior are complete.
- Keyboard, focus, responsive, reduced-motion, and image-loading states are verified.
- The generated PNG remains the focus of the completion state.
