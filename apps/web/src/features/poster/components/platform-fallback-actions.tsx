import { ListMusicIcon } from "lucide-react"
import { useTranslation } from "react-i18next"

import { Button } from "@/components/ui/button"
import type { Studio } from "@/features/poster/components/studio-shared"

export function PlatformFallbackActions({ studio }: { studio: Studio }) {
  const { t } = useTranslation()

  return (
    <div className="flex flex-wrap gap-2">
      <Button
        type="button"
        variant="outline"
        size="sm"
        onClick={() => void studio.showPlatformCandidates()}
      >
        <ListMusicIcon data-icon="inline-start" aria-hidden="true" />
        {t("poster.choosePlatformVersion")}
      </Button>
      <Button
        type="button"
        variant="ghost"
        size="sm"
        onClick={studio.showManualPlatformLink}
      >
        {t("poster.manualPlatformLink")}
      </Button>
    </div>
  )
}
