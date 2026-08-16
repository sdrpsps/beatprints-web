import { AlertCircleIcon, ImageIcon } from "lucide-react"
import { useTranslation } from "react-i18next"

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Spinner } from "@/components/ui/spinner"
import {
  selectCanGenerate,
  usePosterStore,
} from "@/features/poster/poster-store"

export function GenerateSection() {
  const { t } = useTranslation()
  const selected = usePosterStore((s) => s.selected)
  const canGenerate = usePosterStore(selectCanGenerate)
  const generationState = usePosterStore((s) => s.generationState)
  const generationError = usePosterStore((s) => s.generationError)
  const outputStale = usePosterStore((s) => s.outputStale)
  const generate = usePosterStore((s) => s.generate)

  if (!selected) return null

  return (
    <div className="flex flex-col gap-3 pt-7">
      {generationError ? (
        <Alert variant="destructive">
          <AlertCircleIcon />
          <AlertTitle>{t("poster.generationFailed")}</AlertTitle>
          <AlertDescription>
            {generationError.message}
            {generationError.requestId ? (
              <span className="mt-2 block font-[var(--font-utility)] text-[10px]">
                {t("poster.requestIdPrefix")}{generationError.requestId}
              </span>
            ) : null}
          </AlertDescription>
        </Alert>
      ) : null}
      <Button
        className="w-full"
        size="lg"
        disabled={!canGenerate}
        onClick={() => void generate(t)}
      >
        {generationState === "loading" ? (
          <Spinner data-icon="inline-start" />
        ) : (
          <ImageIcon data-icon="inline-start" />
        )}
        {generationState === "loading"
          ? t("poster.generating")
          : outputStale
            ? t("poster.applyAndRegenerate")
            : t("poster.generate")}
      </Button>
      {!canGenerate && generationState !== "loading" ? (
        <p className="m-0 text-center text-xs text-muted-foreground">
          {t("poster.completionNotice")}
        </p>
      ) : null}
    </div>
  )
}
