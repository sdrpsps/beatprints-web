import { useEffect, useRef, useState } from "react"
import type { TFunction } from "i18next"

import { searchCatalog } from "@/features/poster/api"
import { enabledCatalogSources } from "@/features/poster/catalogs/registry"
import { friendlyError } from "@/features/poster/poster-errors"
import type { AsyncState } from "@/features/poster/use-platform-link-flow"
import type {
  CatalogProvider,
  PosterKind,
  SearchResult,
} from "@/features/poster/types"

type CatalogSelectionOptions = {
  kind: PosterKind
  t: TFunction
  markOutputStale: () => void
}

export function useCatalogSelection({
  kind,
  t,
  markOutputStale,
}: CatalogSelectionOptions) {
  const [query, setQuery] = useState("")
  const [provider, setProviderState] = useState<CatalogProvider>(
    () => enabledCatalogSources()[0]?.key ?? "",
  )
  const [searchResults, setSearchResults] = useState<SearchResult[]>([])
  const [searchState, setSearchState] = useState<AsyncState>("idle")
  const [searchError, setSearchError] = useState<string>()
  const [selected, setSelected] = useState<SearchResult>()
  const request = useRef<AbortController | null>(null)

  useEffect(() => () => request.current?.abort(), [])

  function resetSelection() {
    setSelected(undefined)
  }

  function resetForKind() {
    request.current?.abort()
    setQuery("")
    setSearchResults([])
    setSearchState("idle")
    setSearchError(undefined)
    resetSelection()
  }

  async function search(source = provider) {
    const normalized = query.trim()
    if (!normalized || !source) return

    request.current?.abort()
    const controller = new AbortController()
    request.current = controller
    setSearchState("loading")
    setSearchError(undefined)
    try {
      setSearchResults(
        await searchCatalog(normalized, kind, source, controller.signal),
      )
      setSearchState("success")
    } catch (error) {
      if (controller.signal.aborted) return

      setSearchResults([])
      setSearchState("error")
      setSearchError(
        friendlyError(error, t("poster.errors.searchErrorDefault"), t).message,
      )
    }
  }

  function setProvider(value: CatalogProvider) {
    if (!value || value === provider) return

    setProviderState(value)
    if (selected) {
      markOutputStale()
      resetSelection()
    }
    if (query.trim()) void search(value)
  }

  function selectResult(result: SearchResult) {
    markOutputStale()
    setSelected(result)
  }

  return {
    query,
    setQuery,
    provider,
    setProvider,
    searchResults,
    searchState,
    searchError,
    search,
    selected,
    selectResult,
    resetSelection,
    resetForKind,
  }
}
