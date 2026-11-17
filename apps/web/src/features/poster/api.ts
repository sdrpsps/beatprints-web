import i18next from "i18next"

import type {
  PlatformLinkMatch,
  PlatformMatchOptions,
  CatalogProvider,
  LyricsPreview,
  PosterKind,
  PosterPlatform,
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

async function getJson<T>(path: string, signal?: AbortSignal, cache?: RequestCache) {
  const response = await fetch(endpoint(path), { signal, cache })
  if (!response.ok) {
    throw await readError(response)
  }
  const body = (await response.json()) as ApiEnvelope<T>
  return body.data
}

export type IntegrationCapability = {
  key: string
  label: string
  available: boolean
  reason: string | null
  default: boolean
  fixed_code: boolean
  supports_regions?: boolean
  regions?: string[]
  reuses_source_links: string[]
}
export type Capabilities = {
  wechat_qr: boolean
  catalogs: IntegrationCapability[]
  lyrics: IntegrationCapability[]
  destinations: IntegrationCapability[]
}

export function parseCapabilities(value: unknown): Capabilities {
  if (!value || typeof value !== "object") throw new Error("Invalid capabilities")
  const data = value as Record<string, unknown>
  const validItems = (items: unknown): items is IntegrationCapability[] => {
    if (!Array.isArray(items)) return false
    const keys = new Set<string>()
    return items.every((item: unknown) => {
      if (!item || typeof item !== "object") return false
      const entry = item as Record<string, unknown>
      if (typeof entry.key !== "string" || !entry.key || keys.has(entry.key) ||
          typeof entry.label !== "string" || !entry.label || typeof entry.available !== "boolean" ||
          typeof entry.default !== "boolean" || typeof entry.fixed_code !== "boolean" ||
          (entry.supports_regions !== undefined && typeof entry.supports_regions !== "boolean") ||
          (entry.supports_regions === true && (!Array.isArray(entry.regions) || entry.regions.length === 0 || !entry.regions.every((code) => typeof code === "string" && /^[A-Z]{2}$/.test(code)))) ||
          !(entry.reason === null || typeof entry.reason === "string") ||
          !Array.isArray(entry.reuses_source_links) || !entry.reuses_source_links.every((key) => typeof key === "string")) return false
      keys.add(entry.key)
      return true
    })
  }
  if (typeof data.wechat_qr !== "boolean" || !validItems(data.catalogs) ||
      !validItems(data.lyrics) || !validItems(data.destinations)) throw new Error("Incompatible capabilities")
  return data as Capabilities
}

export async function fetchCapabilities(signal?: AbortSignal) {
  return parseCapabilities(await getJson<unknown>("/v1/capabilities", signal, "no-store"))
}

export async function fetchReleaseNotes(version: string, signal?: AbortSignal) {
  return getJson<{ body: string }>(`/v1/release-notes?${new URLSearchParams({ version })}`, signal)
}

export async function searchCatalog(
  query: string,
  kind: PosterKind,
  provider: SearchProvider,
  signal?: AbortSignal,
  region?: string,
) {
  const params = new URLSearchParams({
    query,
    type: kind,
    provider,
    limit: "8",
  })
  if (region) params.set("region", region)
  return getJson<SearchResult[]>(`/v1/search?${params}`, signal)
}

export async function fetchLyrics(
  provider: CatalogProvider,
  catalogId: number | string,
  source: string,
  signal?: AbortSignal,
  region?: string,
) {
  const params = new URLSearchParams({
    provider,
    catalog_id: String(catalogId),
    source,
  })
  if (region) params.set("region", region)
  return getJson<LyricsPreview>(`/v1/lyrics?${params}`, signal)
}

/**
 * Resolve the optional QR destination from the exact source item the listener selected.
 * The endpoint is intentionally platform-agnostic; provider-specific matching remains server-side.
 */
export async function fetchPlatformMatchOptions(
  platform: PosterPlatform,
  provider: CatalogProvider,
  catalogId: number | string,
  kind: PosterKind,
  signal?: AbortSignal,
  sourceRegion?: string,
  destinationRegion?: string,
) {
  const params = new URLSearchParams({
    provider,
    catalog_id: String(catalogId),
    type: kind,
    limit: "8",
  })
  if (sourceRegion) params.set("source_region", sourceRegion)
  if (destinationRegion) params.set("destination_region", destinationRegion)
  return getJson<PlatformMatchOptions>(
    `/v1/platform-links/${platform}/options?${params}`,
    signal,
  )
}

export async function resolvePlatformUrl(
  platform: PosterPlatform,
  url: string,
  signal?: AbortSignal,
  region?: string,
) {
  const params = new URLSearchParams({ url })
  if (region) params.set("region", region)
  return getJson<PlatformLinkMatch>(
    `/v1/platform-links/${platform}/resolve?${params}`,
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
