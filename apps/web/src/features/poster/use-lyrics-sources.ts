import { useEffect, useRef, useState } from "react"
import type { TFunction } from "i18next"

import { fetchLyricsSources } from "@/features/poster/api"
import { friendlyError } from "@/features/poster/poster-errors"
import type { AsyncState } from "@/features/poster/use-platform-link-flow"
import type { LyricsSource, PosterKind, SearchResult } from "@/features/poster/types"

type LyricsSourcesOptions = {
  kind: PosterKind
  selected?: SearchResult
  t: TFunction
}

export function useLyricsSources({ kind, selected, t }: LyricsSourcesOptions) {
  const [sourcesState, setSourcesState] = useState<AsyncState>("idle")
  const [sourcesError, setSourcesError] = useState<string>()
  const [sources, setSources] = useState<LyricsSource[]>([])
  const [lyricsSource, setLyricsSource] = useState<string>()
  const request = useRef<AbortController | null>(null)

  useEffect(() => {
    request.current?.abort()
    setSourcesState("idle")
    setSourcesError(undefined)
    setSources([])
    setLyricsSource(undefined)
    if (kind !== "track" || !selected) return

    const controller = new AbortController()
    request.current = controller
    setSourcesState("loading")
    void (async () => {
      try {
        const response = await fetchLyricsSources(controller.signal)
        if (controller.signal.aborted) return

        setSources(response.sources)
        setLyricsSource(
          response.sources.find((source) => source.default)?.key ??
            response.sources[0]?.key,
        )
        setSourcesState("success")
      } catch (error) {
        if (controller.signal.aborted) return

        setSourcesState("error")
        setSourcesError(
          friendlyError(error, t("poster.errors.lyricsErrorDefault"), t).message,
        )
      }
    })()

    return () => controller.abort()
  }, [kind, selected, t])

  return {
    sourcesState,
    sourcesError,
    lyricsSources: sources,
    lyricsSource,
    setLyricsSource,
  }
}
