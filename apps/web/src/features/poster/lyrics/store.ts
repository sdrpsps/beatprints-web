import type { LyricsSource } from "@/features/poster/lyrics/types"

const sources = new Map<string, LyricsSource>()

export function registerLyricsSource(source: LyricsSource) {
  sources.set(source.key, source)
  return source
}

export function enabledLyricsSources() {
  return [...sources.values()].sort((left, right) => left.order - right.order)
}
