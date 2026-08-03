import type { PosterKind } from "@/features/poster/types"

export function nonemptyLines(value: string) {
  return value
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)
}

export function limitLines(value: string, maximum = 4) {
  return value.split(/\r?\n/).slice(0, maximum).join("\n")
}

type LyricsReadinessOptions = {
  kind: PosterKind
  instrumental: boolean
  instrumentalText: string
  lyricsMode: "catalog" | "manual"
  lyricsState: "idle" | "loading" | "success" | "error"
  selectedLines: number[]
  selectedLyrics: string[]
  manualLyrics: string
}

export function lyricsAreReady({
  kind,
  instrumental,
  instrumentalText,
  lyricsMode,
  lyricsState,
  selectedLines,
  selectedLyrics,
  manualLyrics,
}: LyricsReadinessOptions) {
  if (kind === "album") return true
  if (instrumental) {
    return (
      instrumentalText.length <= 200 &&
      nonemptyLines(instrumentalText).length <= 4
    )
  }
  if (lyricsMode === "catalog") {
    return (
      lyricsState === "success" &&
      selectedLines.length <= 4 &&
      selectedLyrics.every(Boolean)
    )
  }
  return nonemptyLines(manualLyrics).length <= 4
}
