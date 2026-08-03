import { useTranslation } from "react-i18next"

import { Button } from "@/components/ui/button"
import { Spinner } from "@/components/ui/spinner"
import { PlatformItemCard } from "@/features/poster/components/platform-item-card"
import type { Studio } from "@/features/poster/components/studio-shared"
import type { PlatformLinkMatch } from "@/features/poster/types"

export function PlatformCandidateItem({
  candidate,
  studio,
  platform,
}: {
  candidate: PlatformLinkMatch
  studio: Studio
  platform: string
}) {
  const { t } = useTranslation()
  const resolving = studio.platformCandidateResolvingUrl === candidate.url

  return (
    <PlatformItemCard
      match={candidate}
      source={studio.selected!}
      platform={platform}
      actions={
        <Button
          type="button"
          variant="outline"
          size="sm"
          disabled={Boolean(studio.platformCandidateResolvingUrl)}
          onClick={() => void studio.selectPlatformCandidate(candidate)}
        >
          {resolving ? (
            <Spinner data-icon="inline-start" aria-hidden="true" />
          ) : null}
          {t("poster.selectPlatformVersion")}
        </Button>
      }
    />
  )
}
