import { ListMusicIcon, Music2Icon } from "lucide-react"
import { useTranslation } from "react-i18next"

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import {
  Empty,
  EmptyContent,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty"
import { ItemGroup } from "@/components/ui/item"
import { Spinner } from "@/components/ui/spinner"
import { PlatformCandidateItem } from "@/features/poster/components/platform-candidate-item"
import { PlatformFallbackActions } from "@/features/poster/components/platform-fallback-actions"
import { getDestination } from "@/features/poster/destinations/registry"
import { usePosterStore } from "@/features/poster/poster-store"

export function PlatformCandidates() {
  const { t } = useTranslation()
  const qrPlatform = usePosterStore((s) => s.qrPlatform)
  const platformCandidateState = usePosterStore((s) => s.platformCandidateState)
  const platformCandidateError = usePosterStore((s) => s.platformCandidateError)
  const platformCandidates = usePosterStore((s) => s.platformCandidates)
  const showManualPlatformLink = usePosterStore((s) => s.showManualPlatformLink)

  const destination = getDestination(qrPlatform)
  const label = destination ? t(destination.labelKey) : qrPlatform

  if (platformCandidateState === "loading") {
    return (
      <Alert>
        <Spinner aria-hidden="true" />
        <AlertTitle>
          {t("poster.searchingPlatformVersions", { platform: label })}
        </AlertTitle>
        <AlertDescription>
          {t("poster.searchingPlatformVersionsHelp")}
        </AlertDescription>
      </Alert>
    )
  }
  if (platformCandidateState === "error") {
    return (
      <>
        <Alert variant="destructive">
          <Music2Icon aria-hidden="true" />
          <AlertTitle>{t("poster.platformCandidatesFailed")}</AlertTitle>
          <AlertDescription>{platformCandidateError}</AlertDescription>
        </Alert>
        <PlatformFallbackActions />
      </>
    )
  }
  if (
    platformCandidateState === "success" &&
    platformCandidates.length === 0
  ) {
    return <NoPlatformCandidates />
  }

  return (
    <>
      <Alert>
        <ListMusicIcon aria-hidden="true" />
        <AlertTitle>
          {t("poster.choosePlatformVersionTitle", { platform: label })}
        </AlertTitle>
        <AlertDescription>
          {t("poster.choosePlatformVersionHelp")}
        </AlertDescription>
      </Alert>
      {platformCandidateError ? (
        <Alert variant="destructive">
          <Music2Icon aria-hidden="true" />
          <AlertTitle>{t("poster.platformCandidateResolveFailed")}</AlertTitle>
          <AlertDescription>{platformCandidateError}</AlertDescription>
        </Alert>
      ) : null}
      <ItemGroup>
        {platformCandidates.map((candidate) => (
          <PlatformCandidateItem
            key={candidate.url}
            candidate={candidate}
            platform={label}
          />
        ))}
      </ItemGroup>
      <Button
        type="button"
        variant="ghost"
        size="sm"
        onClick={showManualPlatformLink}
      >
        {t("poster.manualPlatformLink")}
      </Button>
    </>
  )
}

function NoPlatformCandidates() {
  const { t } = useTranslation()
  const showManualPlatformLink = usePosterStore((s) => s.showManualPlatformLink)

  return (
    <Empty className="border">
      <EmptyHeader>
        <EmptyMedia variant="icon">
          <ListMusicIcon aria-hidden="true" />
        </EmptyMedia>
        <EmptyTitle>{t("poster.noPlatformCandidates")}</EmptyTitle>
        <EmptyDescription>
          {t("poster.noPlatformCandidatesHelp")}
        </EmptyDescription>
      </EmptyHeader>
      <EmptyContent>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={showManualPlatformLink}
        >
          {t("poster.manualPlatformLink")}
        </Button>
      </EmptyContent>
    </Empty>
  )
}
