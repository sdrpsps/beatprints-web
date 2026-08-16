import { ListMusicIcon } from "lucide-react"
import { useTranslation } from "react-i18next"

import { Button } from "@/components/ui/button"
import { usePosterStore } from "@/features/poster/poster-store"

export function PlatformFallbackActions() {
  const { t } = useTranslation()
  const showPlatformCandidates = usePosterStore((s) => s.showPlatformCandidates)
  const showManualPlatformLink = usePosterStore((s) => s.showManualPlatformLink)

  return (
    <div className="flex flex-wrap gap-2">
      <Button
        type="button"
        variant="outline"
        size="sm"
        onClick={() => void showPlatformCandidates(t)}
      >
        <ListMusicIcon data-icon="inline-start" aria-hidden="true" />
        {t("poster.choosePlatformVersion")}
      </Button>
      <Button
        type="button"
        variant="ghost"
        size="sm"
        onClick={showManualPlatformLink}
      >
        {t("poster.manualPlatformLink")}
      </Button>
    </div>
  )
}
