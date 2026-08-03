import { useEffect, useRef, useState } from "react"
import type { TFunction } from "i18next"

import { fetchLyrics } from "@/features/poster/api"
import { friendlyError } from "@/features/poster/poster-errors"
import type { AsyncState } from "@/features/poster/use-platform-link-flow"
import type {
  LyricsLine,
  PosterKind,
  SearchResult,
} from "@/features/poster/types"

type LyricsPreviewOptions = {
  kind: PosterKind
  selected?: SearchResult
  source?: string
  t: TFunction
}

export function useLyricsPreview({
  kind,
  selected,
  source,
  t,
}: LyricsPreviewOptions) {
  const [lyricsState, setLyricsState] = useState<AsyncState>("idle")
  const [lyricsError, setLyricsError] = useState<string>()
  const [lyrics, setLyrics] = useState<LyricsLine[]>([])
  const [instrumental, setInstrumental] = useState(false)
  const request = useRef<AbortController | null>(null)

  useEffect(() => {
    request.current?.abort()
    setLyricsState("idle")
    setLyricsError(undefined)
    setLyrics([])
    setInstrumental(false)
    if (kind !== "track" || !selected || !source) return

    const controller = new AbortController()
    request.current = controller
    setLyricsState("loading")
    void (async () => {
      try {
        const preview = await fetchLyrics(
          selected.provider,
          selected.id,
          source,
          controller.signal,
        )
        if (controller.signal.aborted) return

        setInstrumental(preview.instrumental)
        setLyrics(preview.lines)
        setLyricsState("success")
      } catch (error) {
        if (controller.signal.aborted) return

        setLyrics([])
        setLyricsState("error")
        setLyricsError(
          friendlyError(error, t("poster.errors.lyricsErrorDefault"), t)
            .message,
        )
      }
    })()

    return () => controller.abort()
  }, [kind, selected, source, t])

  return { lyricsState, lyricsError, lyrics, instrumental }
}
