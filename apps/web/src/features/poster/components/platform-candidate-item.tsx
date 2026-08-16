import { useTranslation } from "react-i18next"

import { Button } from "@/components/ui/button"
import { Spinner } from "@/components/ui/spinner"
import { PlatformItemCard } from "@/features/poster/components/platform-item-card"
import { usePosterStore } from "@/features/poster/poster-store"
import type { PlatformLinkMatch } from "@/features/poster/types"

export function PlatformCandidateItem({
  candidate,
  platform,
}: {
  candidate: PlatformLinkMatch
  platform: string
}) {
  const { t } = useTranslation()
  const selected = usePosterStore((s) => s.selected)
  const platformCandidateResolvingUrl = usePosterStore(
    (s) => s.platformCandidateResolvingUrl,
  )
  const selectPlatformCandidate = usePosterStore(
    (s) => s.selectPlatformCandidate,
  )

  const resolving = platformCandidateResolvingUrl === candidate.url

  return (
    <PlatformItemCard
      match={candidate}
      source={selected!}
      platform={platform}
      actions={
        <Button
          type="button"
          variant="outline"
          size="sm"
          disabled={Boolean(platformCandidateResolvingUrl)}
          onClick={() => void selectPlatformCandidate(candidate, t)}
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
