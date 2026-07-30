# BeatPrints Agent Guidelines

## Product context

BeatPrints is a music-poster creation tool, not a generic image generator or analytics
dashboard. Its primary track-poster journey is:

1. Search for a track and select the exact catalog result.
2. Review the matched cover, title, artists, album, release information, and duration.
3. Select exactly four lyric lines.
4. Optionally choose one music platform to add as the poster's QR destination.
5. Choose poster appearance options and generate the final PNG.

Album posters are a related path: select an album, optionally configure track indexing and
shuffle, optionally choose one QR platform, choose appearance options, and generate the PNG.

Use `docs/frontend-product-brief.md` as the source of truth for the frontend journey, API
mapping, current backend capabilities, and known integration gaps. Preserve these distinctions:

- Metadata source (`provider`: Deezer or Spotify) is not the same as the optional poster QR
  destination (`qr_platform`: Spotify, Apple Music, QQ Music, or NetEase Music).
- After a user selects a search result, generation should use the result's unchanged
  `provider + id` as `provider + catalog_id`; do not fall back to a query that silently picks
  the first result.
- No QR platform means no platform mark or QR code on the poster.
- The generated poster PNG is the primary outcome. Cover artwork and music metadata should
  drive the interface's visual identity; avoid generic AI-product and dashboard conventions.
- BeatPrints is licensed CC BY-NC-SA 4.0 for non-commercial use and requires attribution.

### Cross-platform link matching

When implementing or changing a QR platform destination, preserve the established matching
journey for both **tracks and albums**:

1. Start from the user's exact selected `provider + id` and pass it unchanged as
   `provider + catalog_id` plus `type=track|album`. Do not replace this with a text query that
   silently selects a first result.
2. Match conservatively. Prefer stable identifiers such as ISRC; only use title, artist, release,
   and duration fallbacks when they meet a strict confidence threshold. Return an explicit no-match
   result rather than linking a plausibly named but unconfirmed release.
3. Display a successful match in the same `Item`-style hierarchy as a source search result: cover,
   title, artists, and contextual metadata. Tracks show their album; albums show release year and
   track count. The right-side confirmation action is labelled only “Open”.
4. When an automatic result is absent or the user rejects it, offer ranked candidates for every
   supported QR destination. Candidate search may be broader than automatic confirmation, but it
   must never silently select a weak result. Candidate rows use the source-search `Item` hierarchy
   and a “Select” action. Resolving a selected candidate must fetch its current metadata before
   returning to the confirmation card.
5. A user must also be able to manually paste a public platform link.
   Resolving that link must fetch its **current** track or album metadata and refresh only the
   platform confirmation card. It must never overwrite the selected source item's poster title,
   artists, cover, lyrics, release data, or catalog ID.
6. Keep automatic matching, candidate search and resolution, manual-link resolution,
   error/no-match fallback, disabled generation, and confirmation-card rendering equivalent for
   tracks and albums. Add backend regression tests for every supported destination and both item
   types whenever this flow changes.
7. Platform artwork must use the shared poster-theme color rule used by Spotify Code. Do not let
   Apple Music's symbol or QR code use a separate cover-derived color path; platform-specific
   differences should be limited to the mark and code format, not their color source.

Spotify, Apple Music, QQ Music, and NetEase Music implement this contract. Any future
cross-platform destination should follow the same API and interaction pattern unless the product
requirements explicitly say otherwise.

## Frontend scope

These rules apply to all work under `apps/web`.

### Component-first development

- For every new screen, flow, or component, first look for an existing shadcn component or
  a composition of shadcn components. Prefer composition over creating a UI primitive from
  scratch.
- Treat `apps/web/components.json` as the source of truth for the shadcn base, style, icon
  library, aliases, and installation paths. This project uses Base UI, Tailwind CSS v4, and
  the `base-nova` style.
- The repository-installed `shadcn` skill is mandatory for shadcn work. If the usage or API
  of a component is unclear, invoke it before designing or coding. For every component being
  created, fixed, or used, fetch its current documentation and examples before implementation:

  ```bash
  pnpm dlx shadcn@latest docs <component> -c apps/web
  pnpm dlx shadcn@latest search @shadcn -q "<need>" -c apps/web
  pnpm dlx shadcn@latest add <component> -c apps/web --dry-run
  ```

- Use the official `@shadcn` registry for primitives. Do not guess a source for page blocks or
  third-party registry items; use the registry named by the user or ask which registry to use.
- Install components from the repository root with:

  ```bash
  pnpm dlx shadcn@latest add <component> -c apps/web
  ```

- Do not hand-roll replacements for shadcn primitives such as buttons, inputs, dialogs,
  sheets, popovers, menus, tabs, tooltips, toasts, forms, tables, cards, or navigation
  elements when the registry already supplies them.
- A custom primitive is allowed only when the shadcn registry and reasonable compositions
  cannot meet a concrete interaction or accessibility requirement. Record that reason in
  the implementation summary.

### Design workflow

For a new screen, user flow, or substantial visual redesign:

1. State the target user, the screen's single job, and the real content it needs.
2. Invoke the `shadcn` skill, inspect project context, search installed and registry
   components, and read current documentation for the selected components.
3. Invoke the repository-installed `frontend-design` skill to define the interaction and
   visual direction. Ground the design in music artwork, lyrics, track metadata, and the act
   of composing a physical-style poster rather than in generic SaaS imagery.
4. Establish a compact design plan: semantic color tokens, typography roles, layout,
   responsive behavior, and one justified signature element.
5. Implement the plan by composing installed shadcn components. Customize through props,
   variants, tokens, and wrapper compositions before editing primitive internals.
6. Verify loading, empty, error, success, disabled, focus, keyboard, mobile, and reduced-motion
   states as applicable.
7. Run lint and build, then visually inspect the result at desktop and mobile widths.

Do not use `frontend-design` as permission to replace working shadcn behavior. It guides
information hierarchy, interaction, copy, layout, typography, color, and motion around the
component system.

### Frontend boundaries

- `apps/web/src/components/ui/`: shadcn-managed primitives. Keep generated filenames and
  public APIs recognizable; do not place business-specific components here.
- `apps/web/src/components/`: reusable application-level compositions made from UI
  primitives.
- `apps/web/src/features/<feature>/`: feature-specific state, hooks, services, and composed
  components.
- `apps/web/src/pages/`: route-level page composition; keep reusable UI out of page files.
- `apps/web/src/hooks/`: cross-feature React hooks.
- `apps/web/src/lib/`: framework-independent helpers and integrations.

When a directory does not exist yet, create it only when the first real file needs it.
Avoid speculative abstractions and barrel files.

### Quality gates

Before considering frontend work complete:

```bash
pnpm --filter @beatprints/web lint
pnpm --filter @beatprints/web build
```

Preserve the `@/* -> ./src/*` mappings in both `apps/web/tsconfig.json` and
`apps/web/tsconfig.app.json`, and the matching `@` alias in `apps/web/vite.config.ts`.
Confirm shadcn still resolves paths into `apps/web/src` after changing build configuration:

```bash
pnpm dlx shadcn@latest info -c apps/web
```

The project-level `shadcn` and `frontend-design` skills are recorded by `skills-lock.json`
and installed under `.agents/skills`. Keep the skill directories and lock file in version
control.
