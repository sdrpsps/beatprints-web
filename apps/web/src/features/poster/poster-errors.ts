import type { TFunction } from "i18next"

import { getDestination } from "@/features/poster/destinations/registry"
import type { PosterPlatform } from "@/features/poster/types"

import { ApiError } from "@/features/poster/api"

export function friendlyError(error: unknown, fallback: string, t: TFunction) {
  if (!(error instanceof ApiError)) return { message: fallback }

  const messages: Record<number, string> = {
    401: t("poster.errors.error401"),
    404: t("poster.errors.platformMatchError"),
    422: t("poster.errors.error422"),
    502: t("poster.errors.error502"),
    503: t("poster.errors.error503"),
  }

  return {
    message: messages[error.status] ?? error.message ?? fallback,
    requestId: error.requestId,
  }
}

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
