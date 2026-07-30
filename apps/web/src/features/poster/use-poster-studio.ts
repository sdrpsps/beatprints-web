import { useEffect, useMemo, useRef, useState } from "react"
import { useTranslation } from "react-i18next"

import {
  ApiError,
  fetchLyrics,
  generatePoster,
  searchCatalog,
} from "@/features/poster/api"
import type {
  LyricsLine,
  CatalogProvider,
  PosterKind,
  PosterOutput,
  PosterPlatform,
  PosterPreferences,
  SearchProvider,
  SearchResult,
  Theme,
} from "@/features/poster/types"

const PREFERENCES_KEY = "beatprints.preferences"

const defaultPreferences: PosterPreferences = {
  kind: "track",
  theme: "Light",
  accent: true,
}

function loadPreferences(): PosterPreferences {
  try {
    const value = localStorage.getItem(PREFERENCES_KEY)
    if (!value) return defaultPreferences
    return { ...defaultPreferences, ...JSON.parse(value) }
  } catch {
    return defaultPreferences
  }
}

function friendlyError(
  error: unknown,
  fallback: string,
  t: (key: string) => string,
) {
  if (!(error instanceof ApiError)) {
    return { message: fallback }
  }
  const messages: Record<number, string> = {
    401: t("poster.errors.error401"),
    422: t("poster.errors.error422"),
    502: t("poster.errors.error502"),
    503: t("poster.errors.error503"),
  }
  return {
    message: messages[error.status] ?? error.message ?? fallback,
    requestId: error.requestId,
  }
}

export function nonemptyLines(value: string) {
  return value
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)
}

function limitLines(value: string, maximum = 4) {
  return value.split(/\r?\n/).slice(0, maximum).join("\n")
}

export function platformUrlError(
  platform: PosterPlatform,
  value: string,
  t: (key: string) => string,
): string | undefined {
  let url: URL
  try {
    url = new URL(value)
  } catch {
    return t("poster.errors.urlErrorInvalid")
  }
  if (!["http:", "https:"].includes(url.protocol)) {
    return t("poster.errors.urlErrorProtocol")
  }
  const host = url.hostname.toLowerCase()
  const domains: Record<PosterPlatform, string[]> = {
    spotify: ["spotify.com"],
    apple_music: ["music.apple.com"],
    qq_music: ["y.qq.com", "qq.com"],
    netease_music: ["music.163.com", "163.com"],
  }
  if (!domains[platform].some((domain) => host === domain || host.endsWith(`.${domain}`))) {
    return t("poster.errors.urlErrorDomain")
  }
}

export function usePosterStudio() {
  const { t } = useTranslation()
  const initial = useMemo(loadPreferences, [])
  const [kind, setKindState] = useState<PosterKind>(initial.kind)
  const [theme, setThemeState] = useState<Theme>(initial.theme)
  const [accent, setAccentState] = useState(initial.accent)
  const [query, setQuery] = useState("")
  const [provider, setProviderState] = useState<CatalogProvider>("deezer")
  const [searchResults, setSearchResults] = useState<SearchResult[]>([])
  const [searchState, setSearchState] = useState<
    "idle" | "loading" | "success" | "error"
  >("idle")
  const [searchError, setSearchError] = useState<string>()
  const [selected, setSelected] = useState<SearchResult>()
  const [lyricsState, setLyricsState] = useState<
    "idle" | "loading" | "success" | "error"
  >("idle")
  const [lyricsError, setLyricsError] = useState<string>()
  const [lyrics, setLyrics] = useState<LyricsLine[]>([])
  const [selectedLines, setSelectedLines] = useState<number[]>([])
  const [lyricEdits, setLyricEdits] = useState<Record<number, string>>({})
  const [lyricsMode, setLyricsMode] = useState<"catalog" | "manual">("catalog")
  const [manualLyrics, setManualLyrics] = useState("")
  const [instrumental, setInstrumental] = useState(false)
  const [instrumentalText, setInstrumentalText] = useState("")
  const [qrPlatform, setQrPlatformState] = useState<PosterPlatform | "">("")
  const [platformUrl, setPlatformUrlState] = useState("")
  const [indexing, setIndexingState] = useState(true)
  const [shuffle, setShuffleState] = useState(false)
  const [generationState, setGenerationState] = useState<
    "idle" | "loading" | "success" | "error"
  >("idle")
  const [generationError, setGenerationError] = useState<{
    message: string
    requestId?: string
  }>()
  const [output, setOutput] = useState<PosterOutput>()
  const [outputStale, setOutputStale] = useState(false)
  const searchRequest = useRef<AbortController | null>(null)
  const lyricsRequest = useRef<AbortController | null>(null)
  const generationRequest = useRef<AbortController | null>(null)

  useEffect(() => {
    localStorage.setItem(
      PREFERENCES_KEY,
      JSON.stringify({ kind, theme, accent } satisfies PosterPreferences),
    )
  }, [kind, theme, accent])

  useEffect(
    () => () => {
      searchRequest.current?.abort()
      lyricsRequest.current?.abort()
      generationRequest.current?.abort()
      if (output) URL.revokeObjectURL(output.url)
    },
    [output],
  )

  function clearOutput() {
    setGenerationState("idle")
    setGenerationError(undefined)
    setOutputStale(false)
    setOutput((current) => {
      if (current) URL.revokeObjectURL(current.url)
      return undefined
    })
  }

  function markOutputStale() {
    setGenerationError(undefined)
    setOutputStale((current) => current || Boolean(output))
  }

  function clearSelectionState() {
    lyricsRequest.current?.abort()
    setSelected(undefined)
    setLyricsState("idle")
    setLyricsError(undefined)
    setLyrics([])
    setSelectedLines([])
    setLyricEdits({})
    setLyricsMode("catalog")
    setManualLyrics("")
    setInstrumental(false)
    setInstrumentalText("")
    setQrPlatformState("")
    setPlatformUrlState("")
  }

  function resetSelection() {
    clearSelectionState()
    clearOutput()
  }

  function setKind(value: PosterKind) {
    if (value === kind) return
    markOutputStale()
    setKindState(value)
    setQuery("")
    setSearchResults([])
    setSearchState("idle")
    setSearchError(undefined)
    clearSelectionState()
  }

  async function search(source: SearchProvider = provider) {
    const normalized = query.trim()
    if (!normalized) return
    searchRequest.current?.abort()
    const controller = new AbortController()
    searchRequest.current = controller
    setSearchState("loading")
    setSearchError(undefined)
    try {
      const results = await searchCatalog(
        normalized,
        kind,
        source,
        controller.signal,
      )
      setSearchResults(results)
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

  function changeProvider(value: CatalogProvider) {
    if (value === provider) return
    setProviderState(value)
    if (selected) {
      markOutputStale()
      clearSelectionState()
    }
    if (query.trim()) {
      void search(value)
    }
  }

  async function selectResult(result: SearchResult) {
    markOutputStale()
    clearSelectionState()
    setSelected(result)
    if (kind !== "track") return

    lyricsRequest.current?.abort()
    const controller = new AbortController()
    lyricsRequest.current = controller
    setLyricsState("loading")
    try {
      const preview = await fetchLyrics(
        result.provider,
        result.id,
        controller.signal,
      )
      if (controller.signal.aborted) return
      setInstrumental(preview.instrumental)
      setLyrics(preview.lines)
      setSelectedLines(preview.lines.slice(0, 4).map((line) => line.index))
      setLyricsMode(preview.instrumental ? "manual" : "catalog")
      setLyricsState("success")
    } catch (error) {
      if (controller.signal.aborted) return
      setLyrics([])
      setSelectedLines([])
      setLyricsMode("manual")
      setLyricsState("error")
      setLyricsError(
        friendlyError(error, t("poster.errors.lyricsErrorDefault"), t).message,
      )
    }
  }

  function toggleLyric(index: number, checked: boolean) {
    if (checked && selectedLines.includes(index)) return true
    if (checked && !selectedLines.includes(index) && selectedLines.length >= 4) {
      return false
    }
    setSelectedLines(
      checked
        ? [...selectedLines, index]
        : selectedLines.filter((value) => value !== index),
    )
    markOutputStale()
    return true
  }

  function clearLyricSelection() {
    if (selectedLines.length === 0) return
    setSelectedLines([])
    markOutputStale()
  }

  function editLyric(index: number, value: string) {
    setLyricEdits((current) => ({
      ...current,
      [index]: value.replace(/\r?\n/g, " "),
    }))
    if (selectedLines.includes(index)) markOutputStale()
  }

  function changeLyricsMode(value: "catalog" | "manual") {
    setLyricsMode(value)
    markOutputStale()
  }

  function changeManualLyrics(value: string) {
    setManualLyrics(limitLines(value))
    markOutputStale()
  }

  function changeInstrumentalText(value: string) {
    setInstrumentalText(limitLines(value))
    markOutputStale()
  }

  function changeQrPlatform(value: PosterPlatform | "") {
    setQrPlatformState(value)
    setPlatformUrlState("")
    markOutputStale()
  }

  function changePlatformUrl(value: string) {
    setPlatformUrlState(value)
    markOutputStale()
  }

  function changeTheme(value: Theme) {
    setThemeState(value)
    markOutputStale()
  }

  function changeAccent(value: boolean) {
    setAccentState(value)
    markOutputStale()
  }

  function changeIndexing(value: boolean) {
    setIndexingState(value)
    markOutputStale()
  }

  function changeShuffle(value: boolean) {
    setShuffleState(value)
    markOutputStale()
  }

  const platformNeedsUrl =
    Boolean(qrPlatform) &&
    !(qrPlatform === "spotify" && selected?.provider === "spotify")
  const currentPlatformError =
    platformNeedsUrl && qrPlatform
      ? platformUrlError(qrPlatform, platformUrl, t)
      : undefined
  const manualLineCount = nonemptyLines(manualLyrics).length
  const instrumentalLineCount = nonemptyLines(instrumentalText).length
  const selectedLyrics = lyrics
    .filter((line) => selectedLines.includes(line.index))
    .map((line) => (lyricEdits[line.index] ?? line.text).trim())
  const lyricsReady =
    kind === "album" ||
    (instrumental
      ? instrumentalText.length <= 200 && instrumentalLineCount <= 4
      : lyricsMode === "catalog"
        ? lyricsState === "success" &&
          selectedLines.length === 4 &&
          selectedLyrics.every(Boolean)
        : manualLineCount === 4)
  const canGenerate =
    Boolean(selected) &&
    lyricsReady &&
    !currentPlatformError &&
    generationState !== "loading"

  async function generate() {
    if (!selected || !canGenerate) return
    generationRequest.current?.abort()
    const controller = new AbortController()
    generationRequest.current = controller
    setGenerationState("loading")
    setGenerationError(undefined)
    setOutputStale(Boolean(output))

    const request = {
      provider: selected.provider,
      catalog_id: selected.id,
      theme,
      accent,
      ...(kind === "track"
        ? instrumental
          ? { instrumental_text: instrumentalText.trim() }
          : {
              lyrics:
                lyricsMode === "catalog"
                  ? selectedLyrics.join("\n")
                  : nonemptyLines(manualLyrics).join("\n"),
            }
        : { indexing, shuffle }),
      ...(qrPlatform
        ? {
            qr_platform: qrPlatform,
            ...(platformNeedsUrl
              ? { platform_links: { [qrPlatform]: platformUrl.trim() } }
              : {}),
          }
        : {}),
    }

    try {
      setGenerationState("loading")
      const result = await generatePoster(kind, request, controller.signal)
      if (controller.signal.aborted) return
      const url = URL.createObjectURL(result.blob)
      setOutput({
        url,
        filename: result.filename,
        title: selected.title,
        processTime: result.processTime,
      })
      setGenerationState("success")
      setOutputStale(false)
    } catch (error) {
      if (controller.signal.aborted) return
      setGenerationState("error")
      setGenerationError(
        friendlyError(error, t("poster.errors.generationErrorDefault"), t),
      )
    }
  }

  return {
    kind,
    setKind,
    theme,
    setTheme: changeTheme,
    accent,
    setAccent: changeAccent,
    query,
    setQuery,
    provider,
    setProvider: changeProvider,
    searchResults,
    searchState,
    searchError,
    search,
    selected,
    selectResult,
    resetSelection,
    lyricsState,
    lyricsError,
    lyrics,
    selectedLines,
    toggleLyric,
    clearLyricSelection,
    lyricEdits,
    editLyric,
    lyricsMode,
    setLyricsMode: changeLyricsMode,
    manualLyrics,
    setManualLyrics: changeManualLyrics,
    manualLineCount,
    instrumental,
    instrumentalText,
    setInstrumentalText: changeInstrumentalText,
    instrumentalLineCount,
    qrPlatform,
    setQrPlatform: changeQrPlatform,
    platformUrl,
    setPlatformUrl: changePlatformUrl,
    platformNeedsUrl,
    currentPlatformError,
    indexing,
    setIndexing: changeIndexing,
    shuffle,
    setShuffle: changeShuffle,
    generationState,
    generationError,
    output,
    outputStale,
    canGenerate,
    generate,
    clearOutput,
    markOutputStale,
  }
}
