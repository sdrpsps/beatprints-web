export type PosterKind = "track" | "album"
export type CatalogProvider = string
export type SearchProvider = CatalogProvider | "all"
export type PosterPlatform = string

export type Theme =
  | "Light"
  | "Dark"
  | "Catppuccin"
  | "Gruvbox"
  | "Nord"
  | "RosePine"
  | "Everforest"

export type SearchResult = {
  id: number | string
  provider: CatalogProvider
  type: PosterKind
  title: string
  artists: string[]
  cover_url: string
  link: string
  release_date?: string
  release_year?: number
  release_date_precision?: "year" | "month" | "day"
  album?: {
    id: number | string
    title: string
  }
  duration_seconds?: number
  duration?: string
  explicit?: boolean
  track_count?: number
  isrc?: string
}

export type LyricsLine = {
  index: number
  text: string
}

export type LyricsPreview = {
  provider: CatalogProvider
  catalog_id: number | string
  source: string
  instrumental: boolean
  lines: LyricsLine[]
}

/** Metadata returned for a confirmed optional QR destination, regardless of platform. */
export type PlatformLinkMatch = {
  url: string
  title: string
  artists: string[]
  type: PosterKind
  album?: string
  release_year?: number
  duration_seconds?: number
  track_count?: number
  cover_url?: string
}

export type PlatformMatchOptions = {
  match?: PlatformLinkMatch
  candidates: PlatformLinkMatch[]
}

export type PosterPreferences = {
  kind: PosterKind
  theme: Theme
  accent: boolean
}

export type PosterOutput = {
  url: string
  filename: string
  title: string
  processTime?: string
}

export type PosterRequest = {
  provider: CatalogProvider
  catalog_id: number | string
  theme: Theme
  accent: boolean
  lyrics?: string
  instrumental_text?: string
  indexing?: boolean
  shuffle?: boolean
  qr_platform?: PosterPlatform
  platform_links?: Record<PosterPlatform, string>
}
