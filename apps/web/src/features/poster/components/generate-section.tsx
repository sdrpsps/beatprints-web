import { AlertCircleIcon, ImageIcon } from "lucide-react"
import { useTranslation } from "react-i18next"

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Spinner } from "@/components/ui/spinner"
import type { Studio } from "@/features/poster/components/studio-shared"

export function GenerateSection({ studio }: { studio: Studio }) {
  const { t } = useTranslation()
  if (!studio.selected) return null
  return (
    <div className="flex flex-col gap-3 pt-7">
      {studio.generationError ? (
        <Alert variant="destructive">
          <AlertCircleIcon />
          <AlertTitle>{t("poster.generationFailed")}</AlertTitle>
          <AlertDescription>
            {studio.generationError.message}
            {studio.generationError.requestId ? (
              <span className="mt-2 block font-[var(--font-utility)] text-[10px]">
                {t("poster.requestIdPrefix")}{studio.generationError.requestId}
              </span>
            ) : null}
          </AlertDescription>
        </Alert>
      ) : null}
      <Button
        className="w-full"
        size="lg"
        disabled={!studio.canGenerate}
        onClick={() => void studio.generate()}
      >
        {studio.generationState === "loading" ? (
          <Spinner data-icon="inline-start" />
        ) : (
          <ImageIcon data-icon="inline-start" />
        )}
        {studio.generationState === "loading"
          ? t("poster.generating")
          : studio.outputStale
            ? t("poster.applyAndRegenerate")
            : t("poster.generate")}
      </Button>
      {!studio.canGenerate && studio.generationState !== "loading" ? (
        <p className="m-0 text-center text-xs text-muted-foreground">
          {t("poster.completionNotice")}
        </p>
      ) : null}
    </div>
  )
}
