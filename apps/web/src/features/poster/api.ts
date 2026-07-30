import i18next from "i18next"

import type {
  AppleMusicMatch,
  CatalogProvider,
  LyricsPreview,
  PosterKind,
  PosterRequest,
  SearchProvider,
  SearchResult,
} from "@/features/poster/types"

type ApiEnvelope<T> = {
  code: number
  data: T
  message: string
}

const configuredBase = import.meta.env.VITE_API_BASE_URL?.trim()
const API_BASE = configuredBase?.replace(/\/$/, "") ?? ""

export class ApiError extends Error {
  status: number
  requestId?: string

  constructor(message: string, status: number, requestId?: string) {
    super(message)
    this.name = "ApiError"
    this.status = status
    this.requestId = requestId
  }
}

function endpoint(path: string) {
  return `${API_BASE}${path}`
}

async function readError(response: Response) {
  const requestId = response.headers.get("X-Request-ID") ?? undefined
  const defaultMessage = i18next.t("poster.requestFailed", { status: response.status })
  try {
    const body = (await response.json()) as Partial<ApiEnvelope<unknown>>
    return new ApiError(
      body.message || defaultMessage,
      response.status,
      requestId,
    )
  } catch {
    return new ApiError(defaultMessage, response.status, requestId)
  }
}

async function getJson<T>(path: string, signal?: AbortSignal) {
  const response = await fetch(endpoint(path), { signal })
  if (!response.ok) {
    throw await readError(response)
  }
  const body = (await response.json()) as ApiEnvelope<T>
  return body.data
}

export async function searchCatalog(
  query: string,
  kind: PosterKind,
  provider: SearchProvider,
  signal?: AbortSignal,
) {
  const params = new URLSearchParams({
    query,
    type: kind,
    provider,
    limit: "8",
  })
  return getJson<SearchResult[]>(`/v1/search?${params}`, signal)
}

export async function fetchLyrics(
  provider: CatalogProvider,
  catalogId: number | string,
  signal?: AbortSignal,
) {
  const params = new URLSearchParams({
    provider,
    catalog_id: String(catalogId),
  })
  return getJson<LyricsPreview>(`/v1/lyrics?${params}`, signal)
}

export async function matchAppleMusic(
  provider: CatalogProvider,
  catalogId: number | string,
  kind: PosterKind,
  signal?: AbortSignal,
) {
  const params = new URLSearchParams({
    provider,
    catalog_id: String(catalogId),
    type: kind,
  })
  return getJson<AppleMusicMatch>(
    `/v1/platform-links/apple-music?${params}`,
    signal,
  )
}

export async function resolveAppleMusicUrl(url: string, signal?: AbortSignal) {
  const params = new URLSearchParams({ url })
  return getJson<AppleMusicMatch>(
    `/v1/platform-links/apple-music/resolve?${params}`,
    signal,
  )
}

export async function matchSpotifyFromDeezer(
  catalogId: number | string,
  kind: PosterKind,
  signal?: AbortSignal,
) {
  const params = new URLSearchParams({
    provider: "deezer",
    catalog_id: String(catalogId),
    type: kind,
  })
  return getJson<AppleMusicMatch>(`/v1/platform-links/spotify?${params}`, signal)
}

export async function resolveSpotifyUrl(url: string, signal?: AbortSignal) {
  const params = new URLSearchParams({ url })
  return getJson<AppleMusicMatch>(
    `/v1/platform-links/spotify/resolve?${params}`,
    signal,
  )
}

function responseFilename(response: Response) {
  const disposition = response.headers.get("Content-Disposition") ?? ""
  const utf8Match = disposition.match(/filename\*=UTF-8''([^;]+)/i)
  if (utf8Match?.[1]) {
    try {
      return decodeURIComponent(utf8Match[1])
    } catch {
      // Fall back to the ASCII filename when an upstream response is malformed.
    }
  }
  const match = disposition.match(/filename="?([^";]+)"?/i)
  return match?.[1] ?? "beatprints-poster.png"
}

export async function generatePoster(
  kind: PosterKind,
  request: PosterRequest,
  signal?: AbortSignal,
) {
  const response = await fetch(endpoint(`/v1/posters/${kind}`), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
    signal,
  })
  if (!response.ok) {
    throw await readError(response)
  }
  return {
    blob: await response.blob(),
    filename: responseFilename(response),
    processTime: response.headers.get("X-Process-Time") ?? undefined,
  }
}
