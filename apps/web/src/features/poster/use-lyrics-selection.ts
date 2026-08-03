import { useEffect, useState } from "react"
import type { TFunction } from "i18next"

import {
  limitLines,
  lyricsAreReady,
  nonemptyLines,
} from "@/features/poster/lyrics-utils"
import { useLyricsPreview } from "@/features/poster/use-lyrics-preview"
import { useLyricsSources } from "@/features/poster/use-lyrics-sources"
import type { PosterKind, SearchResult } from "@/features/poster/types"

type LyricsSelectionOptions = {
  kind: PosterKind
  selected?: SearchResult
  t: TFunction
  markOutputStale: () => void
}

export function useLyricsSelection({
  kind,
  selected,
  t,
  markOutputStale,
}: LyricsSelectionOptions) {
  const [selectedLines, setSelectedLines] = useState<number[]>([])
  const [lyricEdits, setLyricEdits] = useState<Record<number, string>>({})
  const [lyricsMode, setLyricsModeState] = useState<"catalog" | "manual">(
    "catalog",
  )
  const [manualLyrics, setManualLyricsState] = useState("")
  const [instrumentalText, setInstrumentalTextState] = useState("")
  const sources = useLyricsSources({ kind, selected, t })
  const preview = useLyricsPreview({
    kind,
    selected,
    source: sources.lyricsSource,
    t,
  })

  useEffect(() => {
    setSelectedLines([])
    setLyricEdits({})
    setLyricsModeState("catalog")
    setManualLyricsState("")
    setInstrumentalTextState("")
  }, [kind, selected])

  useEffect(() => {
    setSelectedLines([])
    setLyricEdits({})
  }, [sources.lyricsSource])

  useEffect(() => {
    if (preview.lyricsState === "success") {
      setLyricsModeState(preview.instrumental ? "manual" : "catalog")
    }
    if (preview.lyricsState === "error") {
      setLyricsModeState("manual")
    }
  }, [preview.instrumental, preview.lyricsState])

  const lyricsState =
    sources.sourcesState === "loading" ? sources.sourcesState : preview.lyricsState
  const lyricsError = sources.sourcesError ?? preview.lyricsError

  function toggleLyric(index: number, checked: boolean) {
    if (
      checked &&
      !selectedLines.includes(index) &&
      selectedLines.length >= 4
    ) {
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

  function editLyric(index: number, value: string) {
    setLyricEdits((current) => ({
      ...current,
      [index]: value.replace(/\r?\n/g, " "),
    }))
    if (selectedLines.includes(index)) markOutputStale()
  }

  const selectedLyrics = preview.lyrics
    .filter((line) => selectedLines.includes(line.index))
    .map((line) => (lyricEdits[line.index] ?? line.text).trim())
  const manualLineCount = nonemptyLines(manualLyrics).length
  const instrumentalLineCount = nonemptyLines(instrumentalText).length
  const lyricsReady = lyricsAreReady({
    kind,
    instrumental: preview.instrumental,
    instrumentalText,
    lyricsMode,
    lyricsState,
    selectedLines,
    selectedLyrics,
    manualLyrics,
  })
  const lyricsText =
    lyricsMode === "catalog"
      ? selectedLyrics.join("\n")
      : nonemptyLines(manualLyrics).join("\n")

  return {
    lyricsState,
    lyricsError,
    lyrics: preview.lyrics,
    lyricsSources: sources.lyricsSources,
    lyricsSource: sources.lyricsSource,
    setLyricsSource: (source: string) => {
      sources.setLyricsSource(source)
      markOutputStale()
    },
    selectedLines,
    toggleLyric,
    clearLyricSelection: () => {
      setSelectedLines([])
      markOutputStale()
    },
    lyricEdits,
    editLyric,
    lyricsMode,
    setLyricsMode: (value: "catalog" | "manual") => {
      setLyricsModeState(value)
      markOutputStale()
    },
    manualLyrics,
    setManualLyrics: (value: string) => {
      setManualLyricsState(limitLines(value))
      markOutputStale()
    },
    manualLineCount,
    instrumental: preview.instrumental,
    instrumentalText,
    setInstrumentalText: (value: string) => {
      setInstrumentalTextState(limitLines(value))
      markOutputStale()
    },
    instrumentalLineCount,
    lyricsReady,
    lyricsText,
  }
}
