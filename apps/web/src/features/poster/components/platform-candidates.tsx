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
import type { Studio } from "@/features/poster/components/studio-shared"
import { getDestination } from "@/features/poster/destinations/registry"

export function PlatformCandidates({ studio }: { studio: Studio }) {
  const { t } = useTranslation()
  const label = getDestination(studio.qrPlatform)?.label ?? studio.qrPlatform

  if (studio.platformCandidateState === "loading") {
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
  if (studio.platformCandidateState === "error") {
    return (
      <>
        <Alert variant="destructive">
          <Music2Icon aria-hidden="true" />
          <AlertTitle>{t("poster.platformCandidatesFailed")}</AlertTitle>
          <AlertDescription>{studio.platformCandidateError}</AlertDescription>
        </Alert>
        <PlatformFallbackActions studio={studio} />
      </>
    )
  }
  if (
    studio.platformCandidateState === "success" &&
    studio.platformCandidates.length === 0
  ) {
    return <NoPlatformCandidates studio={studio} />
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
      {studio.platformCandidateError ? (
        <Alert variant="destructive">
          <Music2Icon aria-hidden="true" />
          <AlertTitle>{t("poster.platformCandidateResolveFailed")}</AlertTitle>
          <AlertDescription>{studio.platformCandidateError}</AlertDescription>
        </Alert>
      ) : null}
      <ItemGroup>
        {studio.platformCandidates.map((candidate) => (
          <PlatformCandidateItem
            key={candidate.url}
            candidate={candidate}
            studio={studio}
            platform={label}
          />
        ))}
      </ItemGroup>
      <Button
        type="button"
        variant="ghost"
        size="sm"
        onClick={studio.showManualPlatformLink}
      >
        {t("poster.manualPlatformLink")}
      </Button>
    </>
  )
}

function NoPlatformCandidates({ studio }: { studio: Studio }) {
  const { t } = useTranslation()

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
          onClick={studio.showManualPlatformLink}
        >
          {t("poster.manualPlatformLink")}
        </Button>
      </EmptyContent>
    </Empty>
  )
}
