import { HistoryIcon } from "lucide-react"
import { useTranslation } from "react-i18next"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { usePosterStore } from "@/features/poster/poster-store"

export function HistoryNavButton() {
  const { t } = useTranslation()
  const historyCount = usePosterStore((s) => s.historyItems.length)
  const setIsHistoryOpen = usePosterStore((s) => s.setIsHistoryOpen)

  return (
    <Button
      variant="ghost"
      size="sm"
      className="inline-flex items-center gap-1.75 text-[13px] text-muted-foreground transition-colors duration-150 hover:text-foreground motion-reduce:transition-none [&_svg]:size-3.5"
      onClick={() => setIsHistoryOpen(true)}
      title={t("poster.historyTitle")}
      aria-label={t("poster.historyOpenAria")}
    >
      <HistoryIcon aria-hidden="true" />
      {t("app.history")}
      {historyCount > 0 ? (
        <Badge
          variant="secondary"
          className="ml-0.5 px-1.5 py-0 text-[10px] font-semibold"
        >
          {historyCount}
        </Badge>
      ) : null}
    </Button>
  )
}
