import { create } from "zustand"
import type { TFunction } from "i18next"

import { toast } from "@/components/ui/toast"
import {
  fetchLyrics,
  fetchPlatformMatchOptions,
  generatePoster,
  resolvePlatformUrl,
  searchCatalog,
} from "@/features/poster/api"
import { enabledCatalogSources } from "@/features/poster/catalogs/registry"
import { getDestination } from "@/features/poster/destinations/registry"
import { enabledLyricsSources } from "@/features/poster/lyrics/registry"
import {
  limitLines,
  lyricsAreReady,
  nonemptyLines,
} from "@/features/poster/lyrics-utils"
import { friendlyError, platformUrlError } from "@/features/poster/poster-errors"
import type { LyricsSource } from "@/features/poster/lyrics/types"
import type {
  CatalogProvider,
  LyricsLine,
  PlatformLinkMatch,
  PosterKind,
  PosterOutput,
  PosterPlatform,
  SearchResult,
  Theme,
} from "@/features/poster/types"
import {
  clearAllHistory,
  deleteHistoryItem,
  getAllHistory,
  type PosterHistoryItem,
  saveHistoryItem,
} from "@/lib/poster-history-db"

export type AsyncState = "idle" | "loading" | "success" | "error"
export type PlatformChoiceMode = "automatic" | "candidates" | "manual"

let searchAbort: AbortController | null = null
let lyricsAbort: AbortController | null = null
let platformAbort: AbortController | null = null
let generationAbort: AbortController | null = null
let editVersion = 0

export type PosterState = {
  // Preferences
  kind: PosterKind
  theme: Theme
  accent: boolean
  setKind: (kind: PosterKind) => void
  setTheme: (theme: Theme) => void
  setAccent: (accent: boolean) => void

  // Catalog / Search
  query: string
  provider: CatalogProvider
  searchResults: SearchResult[]
  searchState: AsyncState
  searchError?: string
  selected?: SearchResult
  setQuery: (query: string) => void
  setProvider: (provider: CatalogProvider, t: TFunction) => void
  search: (t: TFunction, overrideProvider?: CatalogProvider) => Promise<void>
  selectResult: (result: SearchResult, t: TFunction) => void
  resetSelection: () => void

  // Lyrics
  lyricsSources: LyricsSource[]
  lyricsSource?: string
  lyricsState: AsyncState
  lyricsError?: string
  lyrics: LyricsLine[]
  instrumental: boolean
  lyricsMode: "catalog" | "manual"
  selectedLines: number[]
  lyricEdits: Record<number, string>
  manualLyrics: string
  instrumentalText: string
  setLyricsSource: (source: string, t: TFunction) => void
  setLyricsMode: (mode: "catalog" | "manual") => void
  toggleLyric: (index: number, checked: boolean) => boolean
  clearLyricSelection: () => void
  editLyric: (index: number, value: string) => void
  setManualLyrics: (lyrics: string) => void
  setInstrumentalText: (text: string) => void
  loadLyrics: (selected: SearchResult, source: string, t: TFunction) => Promise<void>

  // Platform Links
  qrPlatform: PosterPlatform | ""
  platformUrl: string
  platformChoiceMode: PlatformChoiceMode
  platformMatchState: AsyncState
  platformMatch?: PlatformLinkMatch
  platformMatchError?: string
  platformManualState: AsyncState
  platformManualMatch?: PlatformLinkMatch
  platformManualError?: string
  platformCandidateState: AsyncState
  platformCandidates: PlatformLinkMatch[]
  platformCandidateError?: string
  platformCandidateResolvingUrl?: string
  setQrPlatform: (platform: PosterPlatform | "", t: TFunction) => void
  setPlatformUrl: (url: string) => void
  showPlatformCandidates: (t: TFunction) => void
  showManualPlatformLink: () => void
  resolveManualPlatformUrl: (t: TFunction) => Promise<void>
  selectPlatformCandidate: (candidate: PlatformLinkMatch, t: TFunction) => Promise<void>
  clearPlatform: () => void

  // Album Options
  indexing: boolean
  shuffle: boolean
  setIndexing: (indexing: boolean) => void
  setShuffle: (shuffle: boolean) => void

  // Generation & Output
  generationState: AsyncState
  generationError?: { message: string; requestId?: string }
  output?: PosterOutput
  outputStale: boolean
  markOutputStale: () => void
  clearOutput: () => void
  showOutput: (output: PosterOutput) => void
  generate: (t: TFunction) => Promise<void>

  // History
  isHistoryOpen: boolean
  historyItems: PosterHistoryItem[]
  isHistoryLoading: boolean
  setIsHistoryOpen: (open: boolean) => void
  loadHistory: () => Promise<void>
  removeHistoryItem: (id: string) => Promise<void>
  clearAllHistory: () => Promise<void>
  restoreFromHistory: (item: PosterHistoryItem, t: TFunction) => void
}

const defaultSources = enabledCatalogSources()
const defaultProvider =
  defaultSources.find((source) => source.default)?.key ?? defaultSources[0]?.key ?? ""
const lyricSources = enabledLyricsSources()

const emptyLyrics = {
  lyricsSource: undefined,
  lyricsState: "idle" as const,
  lyricsError: undefined,
  lyrics: [] as LyricsLine[],
  instrumental: false,
  lyricsMode: "catalog" as const,
  selectedLines: [] as number[],
  lyricEdits: {} as Record<number, string>,
  manualLyrics: "",
  instrumentalText: "",
}
const emptyPlatform = {
  qrPlatform: "",
  platformUrl: "",
  platformChoiceMode: "automatic" as const,
  platformMatchState: "idle" as const,
  platformMatch: undefined,
  platformMatchError: undefined,
  platformManualState: "idle" as const,
  platformManualMatch: undefined,
  platformManualError: undefined,
  platformCandidateState: "idle" as const,
  platformCandidates: [] as PlatformLinkMatch[],
  platformCandidateError: undefined,
  platformCandidateResolvingUrl: undefined,
}

function selectedLyrics(state: PosterState) {
  return state.lyrics
    .filter((line) => state.selectedLines.includes(line.index))
    .map((line) => (state.lyricEdits[line.index] ?? line.text).trim())
}

function needsPlatformUrl(state: PosterState) {
  return Boolean(state.qrPlatform) &&
    !getDestination(state.qrPlatform)?.reusesSourceLink(state.selected?.provider ?? "")
}

export const usePosterStore = create<PosterState>((set, get) => ({
  // Preferences
  kind: "track",
  theme: "Light",
  accent: false,
  setKind: (kind) => {
    if (kind === get().kind) return
    searchAbort?.abort()
    lyricsAbort?.abort()
    generationAbort?.abort()
    get().clearPlatform()
    set({
      ...emptyLyrics, kind, selected: undefined,
      query: "", searchResults: [], searchState: "idle", searchError: undefined,
      generationState: get().output ? "success" : "idle",
    })
  },
  setTheme: (theme) => {
    get().markOutputStale()
    set({ theme })
  },
  setAccent: (accent) => {
    get().markOutputStale()
    set({ accent })
  },

  // Catalog / Search
  query: "",
  provider: defaultProvider,
  searchResults: [],
  searchState: "idle",
  searchError: undefined,
  selected: undefined,
  setQuery: (query) => set({ query }),
  setProvider: (provider, t) => {
    if (!provider || provider === get().provider) return
    searchAbort?.abort()
    set({ provider, searchResults: [], searchState: "idle", searchError: undefined })
    if (get().selected) {
      get().markOutputStale()
      get().resetSelection()
    }
    if (get().query.trim()) {
      void get().search(t, provider)
    }
  },
  search: async (t, overrideProvider) => {
    const activeProvider = overrideProvider ?? get().provider
    const normalized = get().query.trim()
    if (!normalized || !activeProvider) return

    searchAbort?.abort()
    const controller = new AbortController()
    searchAbort = controller

    set({ searchState: "loading", searchError: undefined })
    try {
      const results = await searchCatalog(
        normalized,
        get().kind,
        activeProvider,
        controller.signal,
      )
      if (controller.signal.aborted) return
      set({ searchResults: results, searchState: "success" })
    } catch (error) {
      if (controller.signal.aborted) return
      set({
        searchResults: [],
        searchState: "error",
        searchError: friendlyError(error, t("poster.errors.searchErrorDefault"), t).message,
      })
    }
  },
  selectResult: (result, t) => {
    lyricsAbort?.abort()
    generationAbort?.abort()
    get().markOutputStale()
    get().clearPlatform()
    set({ ...emptyLyrics, selected: result, generationState: "idle" })

    if (get().kind === "track") {
      const defaultLyricSource =
        lyricSources.find((s) => s.default)?.key ?? lyricSources[0]?.key ?? ""
      set({ lyricsSource: defaultLyricSource })
      void get().loadLyrics(result, defaultLyricSource, t)
    }
  },
  resetSelection: () => {
    lyricsAbort?.abort()
    get().clearPlatform()
    get().clearOutput()
    set({ ...emptyLyrics, selected: undefined })
  },

  // Lyrics
  lyricsSources: lyricSources,
  ...emptyLyrics,
  setLyricsSource: (source, t) => {
    set({ lyricsSource: source, selectedLines: [], lyricEdits: {} })
    get().markOutputStale()
    const selected = get().selected
    if (selected) {
      void get().loadLyrics(selected, source, t)
    }
  },
  setLyricsMode: (lyricsMode) => {
    get().markOutputStale()
    set({ lyricsMode })
  },
  toggleLyric: (index, checked) => {
    const { selectedLines } = get()
    if (checked && !selectedLines.includes(index) && selectedLines.length >= 4) {
      return false
    }
    const nextLines = checked
      ? [...new Set([...selectedLines, index])]
      : selectedLines.filter((val) => val !== index)
    get().markOutputStale()
    set({ selectedLines: nextLines })
    return true
  },
  clearLyricSelection: () => {
    get().markOutputStale()
    set({ selectedLines: [] })
  },
  editLyric: (index, value) => {
    const sanitized = value.replace(/\r?\n/g, " ")
    const lyricEdits = { ...get().lyricEdits, [index]: sanitized }
    if (get().selectedLines.includes(index)) {
      get().markOutputStale()
    }
    set({ lyricEdits })
  },
  setManualLyrics: (val) => {
    get().markOutputStale()
    set({ manualLyrics: limitLines(val) })
  },
  setInstrumentalText: (val) => {
    get().markOutputStale()
    set({ instrumentalText: limitLines(val) })
  },
  loadLyrics: async (selected, source, t) => {
    lyricsAbort?.abort()
    const controller = new AbortController()
    lyricsAbort = controller

    set({ lyricsState: "loading", lyricsError: undefined, lyrics: [], instrumental: false })
    try {
      const preview = await fetchLyrics(
        selected.provider,
        selected.id,
        source,
        controller.signal,
      )
      if (controller.signal.aborted) return

      set({
        instrumental: preview.instrumental,
        lyrics: preview.lines,
        lyricsState: "success",
        lyricsMode: preview.instrumental ? "manual" : "catalog",
      })
    } catch (error) {
      if (controller.signal.aborted) return
      set({
        lyrics: [],
        lyricsState: "error",
        lyricsMode: "manual",
        lyricsError: friendlyError(error, t("poster.errors.lyricsErrorDefault"), t).message,
      })
    }
  },

  // Platform Links
  ...emptyPlatform,
  clearPlatform: () => {
    platformAbort?.abort()
    get().markOutputStale()
    set(emptyPlatform)
  },
  setQrPlatform: (value, t) => {
    get().clearPlatform()
    set({ qrPlatform: value })

    const selected = get().selected
    if (!value || !selected) return

    // Auto-fetch options
    const controller = new AbortController()
    platformAbort = controller
    set({ platformCandidateState: "loading", platformMatchState: "loading" })

    void (async () => {
      try {
        const options = await fetchPlatformMatchOptions(
          value,
          selected.provider,
          selected.id,
          get().kind,
          controller.signal,
        )
        if (controller.signal.aborted) return

        set({
          platformCandidates: options.candidates,
          platformCandidateState: "success",
        })

        if (options.match) {
          set({
            platformUrl: options.match.url,
            platformMatch: options.match,
            platformMatchState: "success",
          })
        } else {
          set({
            platformMatchState: "error",
            platformChoiceMode: "candidates",
          })
        }
      } catch (error) {
        if (controller.signal.aborted) return
        const msg = friendlyError(error, t("poster.errors.platformMatchError"), t).message
        set({
          platformCandidateState: "error",
          platformCandidateError: msg,
          platformMatchState: "error",
          platformMatchError: msg,
          platformChoiceMode: "candidates",
        })
      }
    })()
  },
  setPlatformUrl: (url) => {
    platformAbort?.abort()
    get().markOutputStale()
    set({
      platformUrl: url,
      platformManualState: "idle",
      platformManualMatch: undefined,
      platformManualError: undefined,
    })
  },
  showPlatformCandidates: (t) => {
    const { qrPlatform, selected, kind, platformCandidateState } = get()
    if (!qrPlatform || !selected) return
    get().markOutputStale()
    if (platformCandidateState === "success") {
      platformAbort?.abort()
      set({ platformChoiceMode: "candidates", platformCandidateError: undefined, platformCandidateResolvingUrl: undefined })
      return
    }
    set({
      platformChoiceMode: "candidates",
      platformCandidateState: "loading",
      platformCandidateError: undefined,
    })

    platformAbort?.abort()
    const controller = new AbortController()
    platformAbort = controller

    void (async () => {
      try {
        const options = await fetchPlatformMatchOptions(
          qrPlatform,
          selected.provider,
          selected.id,
          kind,
          controller.signal,
        )
        if (controller.signal.aborted) return
        set({
          platformCandidates: options.candidates,
          platformCandidateState: "success",
        })
      } catch (error) {
        if (controller.signal.aborted) return
        set({
          platformCandidateState: "error",
          platformCandidateError: friendlyError(error, t("poster.errors.platformMatchError"), t).message,
        })
      }
    })()
  },
  showManualPlatformLink: () => {
    platformAbort?.abort()
    get().markOutputStale()
    set({
      platformChoiceMode: "manual",
      platformManualState: "idle",
      platformManualMatch: undefined,
      platformManualError: undefined,
      platformCandidateState: get().platformCandidateState === "loading" ? "idle" : get().platformCandidateState,
      platformCandidateResolvingUrl: undefined,
    })
  },
  resolveManualPlatformUrl: async (t) => {
    const { qrPlatform, platformUrl, kind } = get()
    if (!qrPlatform) return

    const error = platformUrlError(qrPlatform, platformUrl, t)
    if (error) {
      set({ platformManualState: "error", platformManualError: error })
      return
    }

    platformAbort?.abort()
    get().markOutputStale()
    const controller = new AbortController()
    platformAbort = controller
    set({ platformManualState: "loading", platformManualMatch: undefined, platformManualError: undefined })

    try {
      const match = await resolvePlatformUrl(
        qrPlatform,
        platformUrl.trim(),
        controller.signal,
      )
      if (controller.signal.aborted) return
      if (match.type !== kind) {
        set({ platformManualState: "error", platformManualError: t("poster.errors.platformCandidateType") })
        return
      }
      get().markOutputStale()
      set({
        platformUrl: match.url,
        platformManualMatch: match,
        platformManualState: "success",
      })
    } catch (cause) {
      if (controller.signal.aborted) return
      set({
        platformManualState: "error",
        platformManualError: friendlyError(cause, t("poster.errors.platformLinkResolveError"), t).message,
      })
    }
  },
  selectPlatformCandidate: async (candidate, t) => {
    const { qrPlatform, kind } = get()
    if (!qrPlatform) return

    platformAbort?.abort()
    const controller = new AbortController()
    platformAbort = controller
    set({
      platformCandidateResolvingUrl: candidate.url,
      platformCandidateError: undefined,
    })

    try {
      const match = await resolvePlatformUrl(
        qrPlatform,
        candidate.url,
        controller.signal,
      )
      if (controller.signal.aborted) return
      if (match.type !== kind) {
        set({ platformCandidateError: t("poster.errors.platformCandidateType") })
        return
      }

      get().markOutputStale()
      set({
        platformUrl: match.url,
        platformMatch: match,
        platformMatchState: "success",
        platformChoiceMode: "automatic",
      })
    } catch (cause) {
      if (!controller.signal.aborted) {
        set({
          platformCandidateError: friendlyError(cause, t("poster.errors.platformCandidateResolveError"), t).message,
        })
      }
    } finally {
      if (!controller.signal.aborted) {
        set({ platformCandidateResolvingUrl: undefined })
      }
    }
  },

  // Album Options
  indexing: false,
  shuffle: false,
  setIndexing: (indexing) => {
    get().markOutputStale()
    set({ indexing })
  },
  setShuffle: (shuffle) => {
    get().markOutputStale()
    set({ shuffle })
  },

  // Generation & Output
  generationState: "idle",
  generationError: undefined,
  output: undefined,
  outputStale: false,
  markOutputStale: () => {
    editVersion += 1
    set((state) => ({
      generationError: undefined,
      outputStale: state.outputStale || Boolean(state.output),
    }))
  },
  clearOutput: () => {
    generationAbort?.abort()
    editVersion += 1
    const current = get().output
    if (current) URL.revokeObjectURL(current.url)
    set({
      generationState: "idle",
      generationError: undefined,
      outputStale: false,
      output: undefined,
    })
  },
  showOutput: (newOutput) => {
    generationAbort?.abort()
    const current = get().output
    if (current && current.url !== newOutput.url) {
      URL.revokeObjectURL(current.url)
    }
    set({
      output: newOutput,
      generationState: "success",
      outputStale: false,
      generationError: undefined,
    })
  },
  generate: async (t) => {
    const state = get()
    if (!state.selected || !selectCanGenerate(state)) return
    const version = editVersion

    generationAbort?.abort()
    const controller = new AbortController()
    generationAbort = controller

    set({
      generationState: "loading",
      generationError: undefined,
      outputStale: Boolean(state.output),
    })

    const finalLyricsText = state.lyricsMode === "catalog"
      ? selectedLyrics(state).join("\n")
      : nonemptyLines(state.manualLyrics).join("\n")
    const platformNeedsUrl = needsPlatformUrl(state)

    const request = {
      provider: state.selected.provider,
      catalog_id: state.selected.id,
      theme: state.theme,
      accent: state.accent,
      ...(state.kind === "track"
        ? state.instrumental
          ? { lyrics: state.instrumentalText.trim(), instrumental_text: state.instrumentalText.trim() }
          : { lyrics: finalLyricsText }
        : { indexing: state.indexing, shuffle: state.shuffle }),
      ...(state.qrPlatform
        ? {
            qr_platform: state.qrPlatform,
            ...(platformNeedsUrl || state.platformUrl.trim()
              ? {
                  platform_links: {
                    [state.qrPlatform]: state.platformUrl.trim(),
                  },
                }
              : {}),
          }
        : {}),
    }

    try {
      const result = await generatePoster(state.kind, request, controller.signal)
      if (controller.signal.aborted) return

      const url = URL.createObjectURL(result.blob)
      const nextOutput: PosterOutput = {
        url,
        filename: result.filename,
        title: state.selected.title,
        processTime: result.processTime,
        blob: result.blob,
      }

      get().showOutput(nextOutput)
      set({ outputStale: version !== editVersion })

      // Automatically add to history
      const historyItem: PosterHistoryItem = {
        id:
          typeof crypto !== "undefined" && crypto.randomUUID
            ? crypto.randomUUID()
            : String(Date.now()),
        createdAt: Date.now(),
        kind: state.kind,
        title: state.selected.title,
        artists: state.selected.artists,
        coverUrl: state.selected.cover_url,
        theme: state.theme,
        accent: state.accent,
        filename: result.filename,
        processTime: result.processTime,
        blob: result.blob,
        snapshot: {
          provider: state.selected.provider,
          catalogId: state.selected.id,
          selectedItem: state.selected,
          lyrics: state.kind === "track" && !state.instrumental ? finalLyricsText : undefined,
          instrumental: state.kind === "track" && state.instrumental,
          instrumentalText: state.kind === "track" && state.instrumental ? state.instrumentalText : undefined,
          qrPlatform: state.qrPlatform || undefined,
          platformUrl: state.platformUrl || undefined,
          indexing: state.indexing,
          shuffle: state.shuffle,
        },
      }
      if (await saveHistoryItem(historyItem)) {
        void get().loadHistory()
      } else {
        toast.add({ type: "error", title: t("poster.historySaveFailed") })
      }
    } catch (error) {
      if (controller.signal.aborted) return
      set({
        generationState: "error",
        generationError: friendlyError(error, t("poster.errors.generationErrorDefault"), t),
      })
    }
  },

  // History
  isHistoryOpen: false,
  historyItems: [],
  isHistoryLoading: true,
  setIsHistoryOpen: (open) => set({ isHistoryOpen: open }),
  loadHistory: async () => {
    try {
      set({ isHistoryLoading: true })
      const list = await getAllHistory()
      set({ historyItems: list })
    } finally {
      set({ isHistoryLoading: false })
    }
  },
  removeHistoryItem: async (id) => {
    if (!await deleteHistoryItem(id)) return
    set((state) => ({
      historyItems: state.historyItems.filter((item) => item.id !== id),
    }))
  },
  clearAllHistory: async () => {
    if (!await clearAllHistory()) return
    set({ historyItems: [] })
  },
  restoreFromHistory: (item, t) => {
    searchAbort?.abort()
    get().resetSelection()
    const snapshot = item.snapshot
    set({
      kind: item.kind,
      theme: item.theme,
      accent: item.accent,
      provider: snapshot?.selectedItem?.provider ?? defaultProvider,
      selected: snapshot?.selectedItem,
      query: "",
      searchResults: [],
      searchState: "idle",
      searchError: undefined,
      lyricsMode: "manual",
      manualLyrics: snapshot?.lyrics ?? "",
      instrumental: snapshot?.instrumental ?? (snapshot?.instrumentalText !== undefined),
      instrumentalText: snapshot?.instrumentalText ?? "",
      indexing: snapshot?.indexing ?? false,
      shuffle: snapshot?.shuffle ?? false,
    })
    if (snapshot?.qrPlatform && getDestination(snapshot.qrPlatform) && snapshot.selectedItem) {
      if (snapshot.platformUrl) {
        set({ qrPlatform: snapshot.qrPlatform, platformUrl: snapshot.platformUrl, platformChoiceMode: "manual" })
        void get().resolveManualPlatformUrl(t)
      } else {
        get().setQrPlatform(snapshot.qrPlatform, t)
      }
    }

    const objectUrl = URL.createObjectURL(item.blob)
    get().showOutput({
      url: objectUrl,
      filename: item.filename,
      title: item.title,
      processTime: item.processTime,
      blob: item.blob,
    })

    set({ isHistoryOpen: false })
    toast.add({
      type: "default",
      title: t("poster.restoredToastTitle"),
      description: t("poster.restoredToastDesc"),
    })
  },
}))

// Selectors for derived computed state
export const selectCanGenerate = (state: PosterState): boolean => {
  if (!state.selected) return false
  if (state.generationState === "loading") return false

  const ready = lyricsAreReady({
    kind: state.kind,
    instrumental: state.instrumental,
    instrumentalText: state.instrumentalText,
    lyricsMode: state.lyricsMode,
    lyricsState: state.lyricsState,
    selectedLines: state.selectedLines,
    selectedLyrics: selectedLyrics(state),
    manualLyrics: state.manualLyrics,
  })

  if (!ready) return false

  if (state.qrPlatform) {
    if (!getDestination(state.qrPlatform)) return false
    if (state.platformChoiceMode === "candidates") return false
    if (state.platformChoiceMode === "manual" && state.platformManualState !== "success") {
      return false
    }
    if (state.platformChoiceMode === "automatic" && state.platformMatchState !== "success") {
      return false
    }
    if (needsPlatformUrl(state) && !state.platformUrl.trim()) return false
  }

  return true
}
