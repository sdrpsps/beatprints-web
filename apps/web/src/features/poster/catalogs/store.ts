import type { CatalogSource } from "@/features/poster/catalogs/types"

const sources = new Map<string, CatalogSource>()

export function registerCatalogSource(source: CatalogSource) {
  sources.set(source.key, source)
  return source
}

export function enabledCatalogSources() {
  return [...sources.values()]
}

export function getCatalogSource(key: string) {
  return sources.get(key)
}
