import { Music2Icon } from "lucide-react"
import { useTranslation } from "react-i18next"

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Spinner } from "@/components/ui/spinner"
import { PlatformCandidates } from "@/features/poster/components/platform-candidates"
import { PlatformFallbackActions } from "@/features/poster/components/platform-fallback-actions"
import { PlatformItemCard } from "@/features/poster/components/platform-item-card"
import { ManualPlatformLink } from "@/features/poster/components/platform-manual-link"
import type { Studio } from "@/features/poster/components/studio-shared"
import { getDestination } from "@/features/poster/destinations/registry"

export function PlatformLinkFlow({ studio }: { studio: Studio }) {
  if (studio.platformChoiceMode === "candidates") {
    return <PlatformCandidates studio={studio} />
  }
  if (studio.platformChoiceMode === "manual") {
    return <ManualPlatformLink studio={studio} />
  }
  return <AutomaticPlatformMatch studio={studio} />
}

function AutomaticPlatformMatch({ studio }: { studio: Studio }) {
  const { t } = useTranslation()
  const destination = getDestination(studio.qrPlatform)
  const label = destination ? t(destination.labelKey) : studio.qrPlatform

  if (studio.platformMatchState === "loading") {
    return (
      <Alert>
        <Spinner aria-hidden="true" />
        <AlertTitle>
          {t("poster.platformMatching", { platform: label })}
        </AlertTitle>
      </Alert>
    )
  }
  if (studio.platformMatchState === "success" && studio.platformMatch) {
    return (
      <>
        <PlatformItemCard
          match={studio.platformMatch}
          source={studio.selected!}
          platform={label}
          actions={
            <Button
              render={
                <a
                  href={studio.platformMatch.url}
                  target="_blank"
                  rel="noreferrer"
                />
              }
              variant="outline"
              size="sm"
            >
              {t("poster.openPlatform")}
            </Button>
          }
        />
        <PlatformFallbackActions studio={studio} />
      </>
    )
  }
  if (studio.platformMatchState === "error") {
    return (
      <>
        <Alert variant="destructive">
          <Music2Icon aria-hidden="true" />
          <AlertTitle>{label}</AlertTitle>
          <AlertDescription>{studio.currentPlatformError}</AlertDescription>
        </Alert>
        <PlatformFallbackActions studio={studio} />
      </>
    )
  }
  return null
}
