import { Music2Icon } from "lucide-react"
import { useTranslation } from "react-i18next"

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Spinner } from "@/components/ui/spinner"
import { PlatformCandidates } from "@/features/poster/components/platform-candidates"
import { PlatformFallbackActions } from "@/features/poster/components/platform-fallback-actions"
import { PlatformItemCard } from "@/features/poster/components/platform-item-card"
import { ManualPlatformLink } from "@/features/poster/components/platform-manual-link"
import { getDestination } from "@/features/poster/destinations/registry"
import { usePosterStore } from "@/features/poster/poster-store"

export function PlatformLinkFlow() {
  const platformChoiceMode = usePosterStore((s) => s.platformChoiceMode)

  if (platformChoiceMode === "candidates") {
    return <PlatformCandidates />
  }
  if (platformChoiceMode === "manual") {
    return <ManualPlatformLink />
  }
  return <AutomaticPlatformMatch />
}

function AutomaticPlatformMatch() {
  const { t } = useTranslation()
  const selected = usePosterStore((s) => s.selected)
  const qrPlatform = usePosterStore((s) => s.qrPlatform)
  const platformMatchState = usePosterStore((s) => s.platformMatchState)
  const platformMatch = usePosterStore((s) => s.platformMatch)
  const platformMatchError = usePosterStore((s) => s.platformMatchError)

  const destination = getDestination(qrPlatform)
  const label = destination ? t(destination.labelKey) : qrPlatform

  if (platformMatchState === "loading") {
    return (
      <Alert>
        <Spinner aria-hidden="true" />
        <AlertTitle>
          {t("poster.platformMatching", { platform: label })}
        </AlertTitle>
      </Alert>
    )
  }
  if (platformMatchState === "success" && platformMatch) {
    return (
      <>
        <PlatformItemCard
          match={platformMatch}
          source={selected!}
          platform={label}
          actions={
            <Button
              render={
                <a
                  href={platformMatch.url}
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
        <PlatformFallbackActions />
      </>
    )
  }
  if (platformMatchState === "error") {
    return (
      <>
        <Alert variant="destructive">
          <Music2Icon aria-hidden="true" />
          <AlertTitle>{label}</AlertTitle>
          <AlertDescription>{platformMatchError}</AlertDescription>
        </Alert>
        <PlatformFallbackActions />
      </>
    )
  }
  return null
}
