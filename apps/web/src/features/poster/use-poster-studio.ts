import { useEffect, useMemo, useRef, useState } from "react"
import type { TFunction } from "i18next"
import { useTranslation } from "react-i18next"

import {
  ApiError,
  fetchPlatformCandidates,
  fetchLyrics,
  generatePoster,
  matchPlatformLink,
  resolvePlatformUrl,
  searchCatalog,
} from "@/features/poster/api"
import type {
  PlatformLinkMatch,
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
  t: TFunction,
) {
  if (!(error instanceof ApiError)) {
    return { message: fallback }
  }
  const messages: Record<number, string> = {
    401: t("poster.errors.error401"),
    404: t("poster.errors.appleMusicNoMatch"),
    422: t("poster.errors.error422"),
    502: t("poster.errors.error502"),
    503: t("poster.errors.error503"),
  }
  return {
    message: messages[error.status] ?? error.message ?? fallback,
    requestId: error.requestId,
  }
}

function platformFlowError(
  error: unknown,
  fallback: string,
  t: TFunction,
) {
  if (error instanceof ApiError && error.status === 404) {
    return { message: fallback, requestId: error.requestId }
  }
  return friendlyError(error, fallback, t)
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
  t: TFunction,
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
  const [provider, setProviderState] = useState<CatalogProvider>("spotify")
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
  const [appleMusicState, setAppleMusicState] = useState<
    "idle" | "loading" | "success" | "error"
  >("idle")
  const [appleMusicMatch, setAppleMusicMatch] = useState<PlatformLinkMatch>()
  const [appleMusicError, setAppleMusicError] = useState<string>()
  const [appleMusicLinkMode, setAppleMusicLinkMode] = useState<
    "automatic" | "manual"
  >("automatic")
  const [appleMusicManualState, setAppleMusicManualState] = useState<
    "idle" | "loading" | "success" | "error"
  >("idle")
  const [appleMusicManualMatch, setAppleMusicManualMatch] = useState<PlatformLinkMatch>()
  const [appleMusicManualError, setAppleMusicManualError] = useState<string>()
  const [spotifyMatchState, setSpotifyMatchState] = useState<"idle" | "loading" | "success" | "error">("idle")
  const [spotifyMatch, setSpotifyMatch] = useState<PlatformLinkMatch>()
  const [spotifyMatchError, setSpotifyMatchError] = useState<string>()
  const [spotifyLinkMode, setSpotifyLinkMode] = useState<"automatic" | "manual">("automatic")
  const [spotifyManualState, setSpotifyManualState] = useState<"idle" | "loading" | "success" | "error">("idle")
  const [spotifyManualMatch, setSpotifyManualMatch] = useState<PlatformLinkMatch>()
  const [spotifyManualError, setSpotifyManualError] = useState<string>()
  const [chinaState, setChinaState] = useState<"idle" | "loading" | "success" | "error">("idle")
  const [chinaMatch, setChinaMatch] = useState<PlatformLinkMatch>()
  const [chinaError, setChinaError] = useState<string>()
  const [chinaMode, setChinaMode] = useState<"automatic" | "manual">("automatic")
  const [chinaManualState, setChinaManualState] = useState<"idle" | "loading" | "success" | "error">("idle")
  const [chinaManualMatch, setChinaManualMatch] = useState<PlatformLinkMatch>()
  const [chinaManualError, setChinaManualError] = useState<string>()
  const [platformChoiceMode, setPlatformChoiceMode] = useState<
    "automatic" | "candidates" | "manual"
  >("automatic")
  const [platformCandidateState, setPlatformCandidateState] = useState<
    "idle" | "loading" | "success" | "error"
  >("idle")
  const [platformCandidates, setPlatformCandidates] = useState<
    PlatformLinkMatch[]
  >([])
  const [platformCandidateError, setPlatformCandidateError] =
    useState<string>()
  const [platformCandidateResolvingUrl, setPlatformCandidateResolvingUrl] =
    useState<string>()
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
  const appleMusicRequest = useRef<AbortController | null>(null)
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
      appleMusicRequest.current?.abort()
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
    appleMusicRequest.current?.abort()
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
    setAppleMusicState("idle")
    setAppleMusicMatch(undefined)
    setAppleMusicError(undefined)
    setAppleMusicLinkMode("automatic")
    setAppleMusicManualState("idle")
    setAppleMusicManualMatch(undefined)
    setAppleMusicManualError(undefined)
    setSpotifyMatchState("idle")
    setSpotifyMatch(undefined)
    setSpotifyMatchError(undefined)
    setSpotifyLinkMode("automatic")
    setSpotifyManualState("idle")
    setSpotifyManualMatch(undefined)
    setSpotifyManualError(undefined)
    setChinaState("idle")
    setChinaMatch(undefined)
    setChinaError(undefined)
    setChinaMode("automatic")
    setChinaManualState("idle")
    setChinaManualMatch(undefined)
    setChinaManualError(undefined)
    setPlatformChoiceMode("automatic")
    setPlatformCandidateState("idle")
    setPlatformCandidates([])
    setPlatformCandidateError(undefined)
    setPlatformCandidateResolvingUrl(undefined)
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
      setSelectedLines([])
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
    appleMusicRequest.current?.abort()
    setQrPlatformState(value)
    setPlatformUrlState("")
    setAppleMusicState("idle")
    setAppleMusicMatch(undefined)
    setAppleMusicError(undefined)
    setAppleMusicLinkMode("automatic")
    setAppleMusicManualState("idle")
    setAppleMusicManualMatch(undefined)
    setAppleMusicManualError(undefined)
    setSpotifyMatchState("idle")
    setSpotifyMatch(undefined)
    setSpotifyMatchError(undefined)
    setSpotifyLinkMode("automatic")
    setSpotifyManualState("idle")
    setSpotifyManualMatch(undefined)
    setSpotifyManualError(undefined)
    setChinaState("idle")
    setChinaMatch(undefined)
    setChinaError(undefined)
    setChinaMode("automatic")
    setChinaManualState("idle")
    setChinaManualMatch(undefined)
    setChinaManualError(undefined)
    setPlatformChoiceMode("automatic")
    setPlatformCandidateState("idle")
    setPlatformCandidates([])
    setPlatformCandidateError(undefined)
    setPlatformCandidateResolvingUrl(undefined)
    markOutputStale()
    if (value === "apple_music" && selected) {
      const controller = new AbortController()
      appleMusicRequest.current = controller
      setAppleMusicState("loading")
      void matchPlatformLink("apple_music", selected.provider, selected.id, kind, controller.signal)
        .then((match) => {
          if (controller.signal.aborted) return
          setPlatformUrlState(match.url)
          setAppleMusicMatch(match)
          setAppleMusicState("success")
        })
        .catch((error: unknown) => {
          if (controller.signal.aborted) return
          setAppleMusicState("error")
          setAppleMusicError(
            friendlyError(error, t("poster.errors.appleMusicMatchError"), t).message,
          )
        })
    }
    if (value === "spotify" && selected?.provider === "deezer") {
      const controller = new AbortController()
      appleMusicRequest.current = controller
      setSpotifyMatchState("loading")
      void matchPlatformLink("spotify", selected.provider, selected.id, kind, controller.signal)
        .then((match) => {
          if (controller.signal.aborted) return
          setPlatformUrlState(match.url)
          setSpotifyMatch(match)
          setSpotifyMatchState("success")
        })
        .catch((error: unknown) => {
          if (controller.signal.aborted) return
          setSpotifyMatchState("error")
          setSpotifyMatchError(friendlyError(error, t("poster.errors.spotifyMatchError"), t).message)
        })
    }
    if ((value === "qq_music" || value === "netease_music") && selected) {
      const controller = new AbortController()
      appleMusicRequest.current = controller
      setChinaState("loading")
      void matchPlatformLink(
        value,
        selected.provider,
        selected.id,
        kind,
        controller.signal,
      )
        .then((match) => {
          if (controller.signal.aborted) return
          setPlatformUrlState(match.url)
          setChinaMatch(match)
          setChinaState("success")
        })
        .catch((error: unknown) => {
          if (controller.signal.aborted) return
          setChinaState("error")
          setChinaError(
            platformFlowError(
              error,
              t("poster.errors.platformMatchError"),
              t,
            ).message,
          )
        })
    }
  }

  function changePlatformUrl(value: string) {
    setPlatformUrlState(value)
    if (qrPlatform === "apple_music" && appleMusicLinkMode === "manual") {
      setAppleMusicManualState("idle")
      setAppleMusicManualMatch(undefined)
      setAppleMusicManualError(undefined)
    }
    if (qrPlatform === "spotify" && selected?.provider === "deezer" && spotifyLinkMode === "manual") {
      setSpotifyMatchError(undefined)
      setSpotifyManualState("idle")
      setSpotifyManualMatch(undefined)
      setSpotifyManualError(undefined)
    }
    if ((qrPlatform === "qq_music" || qrPlatform === "netease_music") && chinaMode === "manual") {
      setChinaManualState("idle"); setChinaManualMatch(undefined); setChinaManualError(undefined)
    }
    markOutputStale()
  }

  function changeAppleMusicLinkMode(value: "automatic" | "manual") {
    if (value === appleMusicLinkMode) return
    appleMusicRequest.current?.abort()
    setPlatformChoiceMode(value === "manual" ? "manual" : "automatic")
    setAppleMusicLinkMode(value)
    setAppleMusicState("idle")
    setAppleMusicMatch(undefined)
    setAppleMusicError(undefined)
    setPlatformUrlState("")
    setAppleMusicManualState("idle")
    setAppleMusicManualMatch(undefined)
    setAppleMusicManualError(undefined)
    markOutputStale()
  }

  function changeSpotifyLinkMode(value: "automatic" | "manual") {
    if (value === spotifyLinkMode) return
    appleMusicRequest.current?.abort()
    setPlatformChoiceMode(value === "manual" ? "manual" : "automatic")
    setSpotifyLinkMode(value)
    setSpotifyMatchState("idle")
    setSpotifyMatch(undefined)
    setSpotifyMatchError(undefined)
    setPlatformUrlState("")
    setSpotifyManualState("idle")
    setSpotifyManualMatch(undefined)
    setSpotifyManualError(undefined)
    markOutputStale()
  }

  async function resolveManualSpotifyUrl() {
    const error = platformUrlError("spotify", platformUrl, t)
    if (error) {
      setSpotifyManualState("error")
      setSpotifyManualError(error)
      return
    }
    const controller = new AbortController()
    appleMusicRequest.current?.abort()
    appleMusicRequest.current = controller
    setSpotifyManualState("loading")
    setSpotifyManualError(undefined)
    try {
      const match = await resolvePlatformUrl("spotify", platformUrl.trim(), controller.signal)
      if (controller.signal.aborted) return
      setSpotifyManualMatch(match)
      setSpotifyManualState("success")
    } catch (error) {
      if (controller.signal.aborted) return
      setSpotifyManualState("error")
      setSpotifyManualError(friendlyError(error, t("poster.errors.spotifyMatchError"), t).message)
    }
  }

  function changeChinaMode(value: "automatic" | "manual") {
    if (value === chinaMode) return
    appleMusicRequest.current?.abort()
    setPlatformChoiceMode(value === "manual" ? "manual" : "automatic")
    setChinaMode(value)
    setChinaState("idle")
    setChinaMatch(undefined)
    setChinaError(undefined)
    setPlatformUrlState("")
    setChinaManualState("idle")
    setChinaManualMatch(undefined)
    setChinaManualError(undefined)
    markOutputStale()
  }

  async function resolveManualChinaUrl() {
    if (qrPlatform !== "qq_music" && qrPlatform !== "netease_music") return
    const error = platformUrlError(qrPlatform, platformUrl, t)
    if (error) {
      setChinaManualState("error")
      setChinaManualError(error)
      return
    }
    const controller = new AbortController()
    appleMusicRequest.current?.abort()
    appleMusicRequest.current = controller
    setChinaManualState("loading")
    setChinaManualError(undefined)
    try {
      const match = await resolvePlatformUrl(
        qrPlatform,
        platformUrl.trim(),
        controller.signal,
      )
      if (controller.signal.aborted) return
      setChinaManualMatch(match)
      setChinaManualState("success")
    } catch (cause) {
      if (!controller.signal.aborted) {
        setChinaManualState("error")
        setChinaManualError(
          platformFlowError(
            cause,
            t("poster.errors.platformLinkResolveError"),
            t,
          ).message,
        )
      }
    }
  }

  async function resolveManualAppleMusicUrl() {
    const error = platformUrlError("apple_music", platformUrl, t)
    if (error) {
      setAppleMusicManualState("error")
      setAppleMusicManualError(error)
      return
    }
    appleMusicRequest.current?.abort()
    const controller = new AbortController()
    appleMusicRequest.current = controller
    setAppleMusicManualState("loading")
    setAppleMusicManualError(undefined)
    try {
      const match = await resolvePlatformUrl("apple_music", platformUrl.trim(), controller.signal)
      if (controller.signal.aborted) return
      setAppleMusicManualMatch(match)
      setAppleMusicManualState("success")
    } catch (error) {
      if (controller.signal.aborted) return
      setAppleMusicManualState("error")
      setAppleMusicManualError(
        friendlyError(error, t("poster.errors.appleMusicMatchError"), t).message,
      )
    }
  }

  function clearPlatformMatches() {
    setPlatformUrlState("")
    setAppleMusicState("idle")
    setAppleMusicMatch(undefined)
    setAppleMusicError(undefined)
    setSpotifyMatchState("idle")
    setSpotifyMatch(undefined)
    setSpotifyMatchError(undefined)
    setChinaState("idle")
    setChinaMatch(undefined)
    setChinaError(undefined)
  }

  async function showPlatformCandidates() {
    if (!selected || !qrPlatform) return
    appleMusicRequest.current?.abort()
    const controller = new AbortController()
    appleMusicRequest.current = controller
    clearPlatformMatches()
    setPlatformChoiceMode("candidates")
    setPlatformCandidateState("loading")
    setPlatformCandidates([])
    setPlatformCandidateError(undefined)
    setPlatformCandidateResolvingUrl(undefined)
    markOutputStale()
    try {
      const candidates = await fetchPlatformCandidates(
        qrPlatform,
        selected.provider,
        selected.id,
        kind,
        controller.signal,
      )
      if (controller.signal.aborted) return
      setPlatformCandidates(candidates)
      setPlatformCandidateState("success")
    } catch (error) {
      if (controller.signal.aborted) return
      setPlatformCandidateState("error")
      setPlatformCandidateError(
        platformFlowError(
          error,
          t("poster.errors.platformCandidatesError"),
          t,
        ).message,
      )
    }
  }

  function showManualPlatformLink() {
    setPlatformChoiceMode("manual")
    if (qrPlatform === "apple_music") {
      changeAppleMusicLinkMode("manual")
    } else if (qrPlatform === "spotify") {
      changeSpotifyLinkMode("manual")
    } else if (
      qrPlatform === "qq_music" ||
      qrPlatform === "netease_music"
    ) {
      changeChinaMode("manual")
    }
    setPlatformCandidateState("idle")
    setPlatformCandidates([])
    setPlatformCandidateError(undefined)
    setPlatformCandidateResolvingUrl(undefined)
  }

  async function selectPlatformCandidate(candidate: PlatformLinkMatch) {
    if (!qrPlatform) return
    appleMusicRequest.current?.abort()
    const controller = new AbortController()
    appleMusicRequest.current = controller
    setPlatformCandidateResolvingUrl(candidate.url)
    setPlatformCandidateError(undefined)
    try {
      const match = await resolvePlatformUrl(
        qrPlatform,
        candidate.url,
        controller.signal,
      )
      if (controller.signal.aborted) return
      if (match.type !== kind) {
        setPlatformCandidateError(t("poster.errors.platformCandidateType"))
        return
      }
      setPlatformUrlState(match.url)
      if (qrPlatform === "apple_music") {
        setAppleMusicLinkMode("automatic")
        setAppleMusicMatch(match)
        setAppleMusicState("success")
      } else if (qrPlatform === "spotify") {
        setSpotifyLinkMode("automatic")
        setSpotifyMatch(match)
        setSpotifyMatchState("success")
      } else {
        setChinaMode("automatic")
        setChinaMatch(match)
        setChinaState("success")
      }
      setPlatformChoiceMode("automatic")
      setPlatformCandidateState("idle")
      setPlatformCandidates([])
      markOutputStale()
    } catch (error) {
      if (controller.signal.aborted) return
      setPlatformCandidateError(
        platformFlowError(
          error,
          t("poster.errors.platformCandidateResolveError"),
          t,
        ).message,
      )
    } finally {
      if (!controller.signal.aborted) {
        setPlatformCandidateResolvingUrl(undefined)
      }
    }
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
    qrPlatform === "apple_music" && appleMusicLinkMode === "automatic"
      ? appleMusicError
      : qrPlatform === "spotify" && selected?.provider === "deezer" && spotifyLinkMode === "automatic"
        ? spotifyMatchError
      : (qrPlatform === "qq_music" || qrPlatform === "netease_music") && chinaMode === "automatic"
        ? chinaError
      : platformNeedsUrl && qrPlatform
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
          selectedLines.length <= 4 &&
          selectedLyrics.every(Boolean)
        : manualLineCount <= 4)
  const canGenerate =
    Boolean(selected) &&
    lyricsReady &&
    !currentPlatformError &&
    platformChoiceMode !== "candidates" &&
    (qrPlatform !== "apple_music" ||
      (appleMusicLinkMode === "manual"
        ? appleMusicManualState === "success"
        : appleMusicState === "success")) &&
    (qrPlatform !== "spotify" ||
      selected?.provider !== "deezer" ||
      (spotifyLinkMode === "manual"
        ? spotifyManualState === "success"
        : spotifyMatchState === "success")) &&
    (!["qq_music", "netease_music"].includes(qrPlatform) ||
      (chinaMode === "manual"
        ? chinaManualState === "success"
        : chinaState === "success")) &&
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
    appleMusicState,
    appleMusicMatch,
    appleMusicLinkMode,
    setAppleMusicLinkMode: changeAppleMusicLinkMode,
    appleMusicManualState,
    appleMusicManualMatch,
    appleMusicManualError,
    resolveManualAppleMusicUrl,
    spotifyMatchState,
    spotifyMatch,
    spotifyLinkMode,
    setSpotifyLinkMode: changeSpotifyLinkMode,
    spotifyManualState,
    spotifyManualMatch,
    spotifyManualError,
    resolveManualSpotifyUrl,
    chinaState, chinaMatch, chinaMode, setChinaMode: changeChinaMode, chinaManualState, chinaManualMatch, chinaManualError, resolveManualChinaUrl,
    platformChoiceMode,
    platformCandidateState,
    platformCandidates,
    platformCandidateError,
    platformCandidateResolvingUrl,
    showPlatformCandidates,
    showManualPlatformLink,
    selectPlatformCandidate,
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
