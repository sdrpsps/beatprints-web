import { useEffect, useRef, useState } from "react"
import type { TFunction } from "i18next"

import { generatePoster } from "@/features/poster/api"
import { friendlyError } from "@/features/poster/poster-errors"
import type { AsyncState } from "@/features/poster/use-platform-link-flow"
import type {
  PosterKind,
  PosterOutput,
  PosterRequest,
} from "@/features/poster/types"

export function usePosterGeneration() {
  const [generationState, setGenerationState] = useState<AsyncState>("idle")
  const [generationError, setGenerationError] = useState<{
    message: string
    requestId?: string
  }>()
  const [output, setOutput] = useState<PosterOutput>()
  const [outputStale, setOutputStale] = useState(false)
  const request = useRef<AbortController | null>(null)

  useEffect(
    () => () => {
      request.current?.abort()
      if (output) URL.revokeObjectURL(output.url)
    },
    [output],
  )

  function markOutputStale() {
    setGenerationError(undefined)
    setOutputStale((current) => current || Boolean(output))
  }

  function clearOutput() {
    setGenerationState("idle")
    setGenerationError(undefined)
    setOutputStale(false)
    setOutput((current) => {
      if (current) URL.revokeObjectURL(current.url)
      return undefined
    })
  }

  async function generate(
    kind: PosterKind,
    requestBody: PosterRequest,
    title: string,
    t: TFunction,
  ) {
    request.current?.abort()
    const controller = new AbortController()
    request.current = controller
    setGenerationState("loading")
    setGenerationError(undefined)
    setOutputStale(Boolean(output))

    try {
      const result = await generatePoster(kind, requestBody, controller.signal)
      if (controller.signal.aborted) return

      const url = URL.createObjectURL(result.blob)
      const nextOutput: PosterOutput = {
        url,
        filename: result.filename,
        title,
        processTime: result.processTime,
        blob: result.blob,
      }
      setOutput(nextOutput)
      setGenerationState("success")
      setOutputStale(false)
      return {
        blob: result.blob,
        filename: result.filename,
        processTime: result.processTime,
      }
    } catch (error) {
      if (controller.signal.aborted) return

      setGenerationState("error")
      setGenerationError(
        friendlyError(error, t("poster.errors.generationErrorDefault"), t),
      )
      return undefined
    }
  }

  function showOutput(newOutput: PosterOutput) {
    setOutput((current) => {
      if (current && current.url !== newOutput.url) {
        URL.revokeObjectURL(current.url)
      }
      return newOutput
    })
    setGenerationState("success")
    setOutputStale(false)
    setGenerationError(undefined)
  }

  return {
    generationState,
    generationError,
    output,
    outputStale,
    markOutputStale,
    clearOutput,
    showOutput,
    generate,
  }
}
