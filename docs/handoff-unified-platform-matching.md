# Unified platform matching handoff

## Status

The QR destination matching flow has been consolidated into one shared matching engine for
Spotify, Apple Music, QQ Music, and NetEase Music. The frontend and backend now use one lookup
request that returns both an optional automatic confirmation and ranked alternatives.

This change intentionally does not preserve the previous automatic-match or candidates API. The
only API consumer is this repository's frontend.

## Public API

The platform-link API now exposes only these routes:

```http
GET /v1/platform-links/{platform}/options
  ?provider=<deezer|spotify>
  &catalog_id=<selected-source-id>
  &type=<track|album>
  &limit=8

GET /v1/platform-links/{platform}/resolve?url=<public-platform-url>
```

`/options` returns an optional confirmed match and candidates collected during the same lookup:

```json
{
  "code": 0,
  "data": {
    "match": {
      "url": "https://example.com/item",
      "title": "Example",
      "artists": ["Artist"],
      "type": "track"
    },
    "candidates": []
  },
  "message": "success"
}
```

When no candidate is safe to confirm, `match` is omitted and `candidates` remains available for
explicit user selection. Selecting a candidate still calls `/resolve` so the confirmation card
uses current destination metadata.

Removed routes:

```text
GET /v1/platform-links/{platform}
GET /v1/platform-links/{platform}/candidates
```

## Architecture

`DestinationAdapter` is the platform boundary. Each adapter supplies:

- destination search;
- public-link resolution;
- optional capabilities such as ISRC search;
- optional exact source reuse, currently Spotify source to Spotify destination.

The shared engine owns:

- query generation;
- candidate normalization and platform-ID deduplication;
- bilingual/base-title comparison;
- recording and edition marker detection;
- order-independent multi-artist comparison;
- release year, album, duration, and track-count evidence;
- hard-conflict rejection;
- candidate ranking;
- top-two ambiguity rejection;
- automatic confirmation.

Platform-specific behavior should be added to an adapter. Each destination now lives in its own
module under `beatprints_api/integrations/destinations/`; `registry.py` is the complete enabled list. Commenting
out one adapter import there disables that destination's matching, resolution, and poster rendering
together. Matching thresholds and evidence rules remain in the shared engine unless a platform
exposes a genuinely unique stable identifier or exact-catalog capability.

## Important matching rules

- Always begin from the exact selected source `provider + catalog_id + type`.
- Exact ISRC is stronger than localized display-text differences.
- Same-script artist conflicts are rejected.
- Cross-script artist names remain unknown unless destination artist-search retrieval provides
  supporting evidence.
- Candidate search retrieval is supporting evidence, not proof by itself.
- Track duration is graded at 2, 5, and 15-second boundaries; a difference above 15 seconds is a
  hard conflict for automatic confirmation.
- Album year and track-count conflicts block automatic confirmation.
- Close first- and second-ranked candidates are not automatically confirmed.
- Version markers use word boundaries and suffix/parenthetical regions so words such as `Olive`
  and `Demons` do not accidentally become `live` or `demo` versions.
- Candidates are deduplicated by destination platform ID when available, falling back to URL.

## Frontend behavior

Choosing a destination makes one `/options` request.

- With `match`: show the confirmation card.
- Without `match` but with candidates: immediately show the candidate list.
- With no candidates: offer manual public-link entry.
- Candidate selection and manual links use `/resolve`.
- Resolving a destination never replaces the source poster metadata, lyrics, cover, or catalog ID.

The UI deliberately does not display internal scores or field-difference explanations.

## Key files

- `apps/api/src/beatprints_api/services/beatprints.py`: shared matching engine and poster generation.
- `apps/api/src/beatprints_api/integrations/destinations/`: independent destination adapters and shared QR helpers.
- `apps/api/src/beatprints_api/integrations/destinations/registry.py`: enabled-adapter imports and lookup.
- `apps/api/src/beatprints_api/api/routes/catalog.py`: `/options` and `/resolve` routes.
- `apps/api/src/beatprints_api/models/dto.py`: platform-neutral response models.
- `apps/api/src/beatprints_api/spotify.py`: Spotify IDs and ISRC metadata.
- `apps/web/src/features/poster/api.ts`: frontend platform-link client.
- `apps/web/src/features/poster/use-poster-studio.ts`: matching and candidate state flow.
- `apps/api/tests/test_destination_matching.py`: shared matching regression cases.
- `apps/api/tests/test_api.py`: unified API contract coverage.

## Verification

Last verified on 2026-08-03:

```bash
env -i PATH=/usr/bin:/bin:/usr/sbin:/sbin \
  .venv/bin/python -m pytest apps/api/tests -q
# 85 passed

pnpm --filter @beatprints/web lint
pnpm --filter @beatprints/web build
```

The lint command reports existing Fast Refresh warnings in shadcn-managed UI files. The build
reports the existing JavaScript chunk-size warning. Neither warning was introduced by this work.

The clean environment used for API tests avoids an invalid proxy value injected by the local
login shell. If normal test collection raises `httpx.InvalidURL: Invalid port: ':1'`, use the clean
environment command above or correct the local proxy configuration.

## Suggested follow-up work

1. Add real recorded fixture responses for each destination, particularly Apple Music and
   Spotify, so adapter normalization is tested independently of network services.
2. Add album track-list comparison only when year and track count cannot disambiguate editions;
   avoid making it an unconditional extra upstream request.
3. Completed: multi-source lyrics selection now keeps LRCLIB alongside independently registered
   sources, keeps preview responses simple, and submits the user's final four lines explicitly.
