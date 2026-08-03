import { useEffect, useRef, useState } from "react"
import type { TFunction } from "i18next"

import {
  fetchPlatformMatchOptions,
  resolvePlatformUrl,
} from "@/features/poster/api"
import { getDestination } from "@/features/poster/destinations/registry"
import { friendlyError } from "@/features/poster/poster-errors"
import type {
  PlatformLinkMatch,
  PosterKind,
  PosterPlatform,
  SearchResult,
} from "@/features/poster/types"

export type AsyncState = "idle" | "loading" | "success" | "error"
export type PlatformChoiceMode = "automatic" | "candidates" | "manual"

export function platformUrlError(
  platform: PosterPlatform,
  value: string,
  t: TFunction,
) {
  let url: URL
  try {
    url = new URL(value)
  } catch {
    return t("poster.errors.urlErrorInvalid")
  }

  if (!["http:", "https:"].includes(url.protocol)) {
    return t("poster.errors.urlErrorProtocol")
  }

  const destination = getDestination(platform)
  const host = url.hostname.toLowerCase()
  if (
    !destination ||
    !destination.domains.some(
      (domain) => host === domain || host.endsWith(`.${domain}`),
    )
  ) {
    return t("poster.errors.urlErrorDomain")
  }
}

type PlatformLinkFlowOptions = {
  selected?: SearchResult
  kind: PosterKind
  t: TFunction
  markOutputStale: () => void
}

export function usePlatformLinkFlow({
  selected,
  kind,
  t,
  markOutputStale,
}: PlatformLinkFlowOptions) {
  const [qrPlatform, setQrPlatformState] = useState<PosterPlatform | "">("")
  const [platformUrl, setPlatformUrlState] = useState("")
  const [platformChoiceMode, setPlatformChoiceMode] =
    useState<PlatformChoiceMode>("automatic")
  const [platformMatchState, setPlatformMatchState] =
    useState<AsyncState>("idle")
  const [platformMatch, setPlatformMatch] = useState<PlatformLinkMatch>()
  const [platformMatchError, setPlatformMatchError] = useState<string>()
  const [platformManualState, setPlatformManualState] =
    useState<AsyncState>("idle")
  const [platformManualMatch, setPlatformManualMatch] =
    useState<PlatformLinkMatch>()
  const [platformManualError, setPlatformManualError] = useState<string>()
  const [platformCandidateState, setPlatformCandidateState] =
    useState<AsyncState>("idle")
  const [platformCandidates, setPlatformCandidates] = useState<
    PlatformLinkMatch[]
  >([])
  const [platformCandidateError, setPlatformCandidateError] = useState<string>()
  const [platformCandidateResolvingUrl, setPlatformCandidateResolvingUrl] =
    useState<string>()
  const request = useRef<AbortController | null>(null)

  useEffect(() => () => request.current?.abort(), [])

  function resetMatch() {
    request.current?.abort()
    setPlatformUrlState("")
    setPlatformChoiceMode("automatic")
    setPlatformMatchState("idle")
    setPlatformMatch(undefined)
    setPlatformMatchError(undefined)
    setPlatformManualState("idle")
    setPlatformManualMatch(undefined)
    setPlatformManualError(undefined)
    setPlatformCandidateState("idle")
    setPlatformCandidates([])
    setPlatformCandidateError(undefined)
    setPlatformCandidateResolvingUrl(undefined)
  }

  function clear() {
    resetMatch()
    setQrPlatformState("")
  }

  async function loadOptions(
    platform: PosterPlatform,
    mode: PlatformChoiceMode = "automatic",
  ) {
    if (!selected) return

    request.current?.abort()
    const controller = new AbortController()
    request.current = controller
    setPlatformCandidateState("loading")
    setPlatformCandidateError(undefined)
    if (mode === "automatic") setPlatformMatchState("loading")

    try {
      const options = await fetchPlatformMatchOptions(
        platform,
        selected.provider,
        selected.id,
        kind,
        controller.signal,
      )
      if (controller.signal.aborted) return

      setPlatformCandidates(options.candidates)
      setPlatformCandidateState("success")
      if (mode === "automatic" && options.match) {
        setPlatformUrlState(options.match.url)
        setPlatformMatch(options.match)
        setPlatformMatchState("success")
      } else if (mode === "automatic") {
        setPlatformMatchState("error")
        setPlatformChoiceMode("candidates")
      }
    } catch (error) {
      if (controller.signal.aborted) return

      const message = friendlyError(
        error,
        t("poster.errors.platformMatchError"),
        t,
      ).message
      setPlatformCandidateState("error")
      setPlatformCandidateError(message)
      setPlatformMatchState("error")
      setPlatformMatchError(message)
      setPlatformChoiceMode("candidates")
    }
  }

  function setQrPlatform(value: PosterPlatform | "") {
    resetMatch()
    setQrPlatformState(value)
    markOutputStale()
    if (!value || !selected) return

    const destination = getDestination(value)
    if (destination?.reusesSourceLink(selected.provider)) {
      setPlatformUrlState(selected.link)
      setPlatformMatchState("success")
      return
    }

    void loadOptions(value)
  }

  function setPlatformUrl(value: string) {
    setPlatformUrlState(value)
    setPlatformManualState("idle")
    setPlatformManualMatch(undefined)
    setPlatformManualError(undefined)
    markOutputStale()
  }

  function showPlatformCandidates() {
    if (!qrPlatform) return

    resetMatch()
    setPlatformChoiceMode("candidates")
    void loadOptions(qrPlatform, "candidates")
    markOutputStale()
  }

  function showManualPlatformLink() {
    request.current?.abort()
    setPlatformChoiceMode("manual")
    setPlatformManualState("idle")
    setPlatformManualMatch(undefined)
    setPlatformManualError(undefined)
    setPlatformCandidateState("idle")
    setPlatformCandidates([])
    setPlatformCandidateError(undefined)
  }

  async function resolveManualPlatformUrl() {
    if (!qrPlatform) return

    const error = platformUrlError(qrPlatform, platformUrl, t)
    if (error) {
      setPlatformManualState("error")
      setPlatformManualError(error)
      return
    }

    request.current?.abort()
    const controller = new AbortController()
    request.current = controller
    setPlatformManualState("loading")
    setPlatformManualError(undefined)
    try {
      const match = await resolvePlatformUrl(
        qrPlatform,
        platformUrl.trim(),
        controller.signal,
      )
      if (controller.signal.aborted) return

      setPlatformUrlState(match.url)
      setPlatformManualMatch(match)
      setPlatformManualState("success")
    } catch (cause) {
      if (controller.signal.aborted) return

      setPlatformManualState("error")
      setPlatformManualError(
        friendlyError(cause, t("poster.errors.platformLinkResolveError"), t)
          .message,
      )
    }
  }

  async function selectPlatformCandidate(candidate: PlatformLinkMatch) {
    if (!qrPlatform) return

    request.current?.abort()
    const controller = new AbortController()
    request.current = controller
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
      setPlatformMatch(match)
      setPlatformMatchState("success")
      setPlatformChoiceMode("automatic")
      setPlatformCandidateState("idle")
      setPlatformCandidates([])
      markOutputStale()
    } catch (cause) {
      if (!controller.signal.aborted) {
        setPlatformCandidateError(
          friendlyError(
            cause,
            t("poster.errors.platformCandidateResolveError"),
            t,
          ).message,
        )
      }
    } finally {
      if (!controller.signal.aborted) {
        setPlatformCandidateResolvingUrl(undefined)
      }
    }
  }

  const platformNeedsUrl =
    Boolean(qrPlatform) &&
    Boolean(selected) &&
    !getDestination(qrPlatform)?.reusesSourceLink(selected?.provider ?? "")
  const currentPlatformError = platformNeedsUrl
    ? platformChoiceMode === "manual"
      ? (platformManualError ?? platformUrlError(qrPlatform, platformUrl, t))
      : platformMatchError
    : undefined
  const platformReady =
    !qrPlatform ||
    !platformNeedsUrl ||
    (platformChoiceMode === "manual"
      ? platformManualState === "success"
      : platformMatchState === "success")

  return {
    qrPlatform,
    setQrPlatform,
    platformUrl,
    setPlatformUrl,
    platformNeedsUrl,
    currentPlatformError,
    platformReady,
    platformChoiceMode,
    platformMatchState,
    platformMatch,
    platformManualState,
    platformManualMatch,
    platformManualError,
    platformCandidateState,
    platformCandidates,
    platformCandidateError,
    platformCandidateResolvingUrl,
    showPlatformCandidates,
    showManualPlatformLink,
    resolveManualPlatformUrl,
    selectPlatformCandidate,
    clear,
  }
}
