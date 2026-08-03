import type { TFunction } from "i18next"

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
