import { useEffect, useState } from "react"

import { enabledLyricsSources } from "@/features/poster/lyrics/registry"
import type { AsyncState } from "@/features/poster/use-platform-link-flow"
import type { PosterKind, SearchResult } from "@/features/poster/types"

type LyricsSourcesOptions = {
  kind: PosterKind
  selected?: SearchResult
}

const sources = enabledLyricsSources()

export function useLyricsSources({
  kind,
  selected,
}: LyricsSourcesOptions) {
  const [lyricsSource, setLyricsSource] = useState<string>()

  useEffect(() => {
    if (kind !== "track" || !selected) {
      setLyricsSource(undefined)
      return
    }

    setLyricsSource(
      sources.find((source) => source.default)?.key ?? sources[0]?.key,
    )
  }, [kind, selected])

  const active = kind === "track" && Boolean(selected)

  return {
    sourcesState: (active ? "success" : "idle") as AsyncState,
    sourcesError: undefined,
    lyricsSources: sources,
    lyricsSource,
    setLyricsSource,
  }
}
