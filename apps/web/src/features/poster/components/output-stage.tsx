import { useEffect, useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import {
  ArrowDownToLineIcon,
  ArrowLeftRightIcon,
  Disc3Icon,
  TriangleAlertIcon,
} from "lucide-react"

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button, buttonVariants } from "@/components/ui/button"
import { Spinner } from "@/components/ui/spinner"
import type { Studio } from "@/features/poster/components/studio-shared"
import { cn } from "@/lib/utils"

export function OutputStage({ studio }: { studio: Studio }) {
  const { t } = useTranslation()
  const stageRef = useRef<HTMLDivElement>(null)
  const [readyOutputUrl, setReadyOutputUrl] = useState<string>()
  const isGenerating = studio.generationState === "loading"
  const outputReady =
    Boolean(studio.output) && readyOutputUrl === studio.output?.url
  const showLoadingOverlay =
    isGenerating || Boolean(studio.output && !outputReady)
  const elapsedSeconds = studio.output?.processTime
    ? `${(Number(studio.output.processTime) / 1000).toFixed(2)}s`
    : "—"

  useEffect(() => {
    if (studio.generationState === "success") {
      stageRef.current?.focus()
    }
  }, [studio.generationState])

  return (
    <aside
      className="sticky top-6 max-[960px]:static max-[960px]:order-2"
      aria-label={t("poster.outputAriaLabel")}
    >
      <div className="flex justify-between gap-5 pb-2.5 font-[var(--font-utility)] text-[10px] font-semibold tracking-[0.14em] text-muted-foreground">
        <span>OUTPUT / PNG</span>
        <span>{elapsedSeconds}</span>
      </div>
      {studio.outputStale ? (
        <Alert className="output-stale-alert">
          <TriangleAlertIcon />
          <AlertTitle>{t("poster.settingsChanged")}</AlertTitle>
          <AlertDescription>
            {t("poster.staleOutputNotice")}
          </AlertDescription>
        </Alert>
      ) : null}
      <div
        ref={stageRef}
        className={cn(
          "output-stage relative grid min-h-[min(74vh,900px)] place-items-center overflow-hidden bg-[var(--stage)] outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50 max-[960px]:min-h-[68vh] max-sm:min-h-[64vh]",
          studio.output && "min-h-0 p-[clamp(16px,3vw,38px)]",
        )}
        tabIndex={-1}
        aria-live="polite"
      >
        {studio.output ? (
          <img
            key={studio.output.url}
            className={cn(
              "block max-h-[80vh] max-w-full object-contain shadow-[0_24px_70px_rgba(5,6,10,0.28)]",
              outputReady && "poster-output motion-reduce:animate-none",
            )}
            src={studio.output.url}
            alt={t("poster.posterAlt", { title: studio.output.title })}
            onLoad={() => setReadyOutputUrl(studio.output?.url)}
          />
        ) : null}
        {!studio.output && !isGenerating ? (
          <EmptyOutputState studio={studio} />
        ) : null}
        <div
          className={cn(
            "pointer-events-none absolute inset-0 z-2 grid place-items-center bg-[color-mix(in_srgb,var(--stage)_88%,transparent)] p-6 text-center opacity-0 backdrop-blur-[5px] transition-opacity duration-200 ease-[cubic-bezier(0.23,1,0.32,1)] motion-reduce:transition-none",
            showLoadingOverlay && "pointer-events-auto opacity-100",
          )}
          aria-hidden={!showLoadingOverlay}
        >
          <div className="flex max-w-[280px] flex-col items-center gap-2 text-muted-foreground">
            <Spinner />
            <strong className="mt-1.5 text-sm text-foreground">
              {t("poster.generating")}
            </strong>
            <span className="text-xs leading-[1.55]">
              {t("poster.generatingNotice")}
            </span>
          </div>
        </div>
      </div>
      {studio.output ? <OutputActions studio={studio} /> : null}
    </aside>
  )
}

function EmptyOutputState({ studio }: { studio: Studio }) {
  const { t } = useTranslation()
  const selectedLabel = studio.selected
    ? `${studio.selected.title} · ${studio.selected.artists.join("、")}`
    : t("poster.emptyOutputDescription")

  return (
    <div className="flex max-w-[280px] flex-col items-center gap-2.5 px-6 text-center text-muted-foreground/55">
      <Disc3Icon
        className="mb-1 size-9 stroke-[1.25]"
        aria-hidden="true"
      />
      <strong className="text-[13px] font-medium text-foreground/45">
        {t("poster.emptyOutputTitle")}
      </strong>
      <span className="line-clamp-2 text-xs leading-[1.55]">
        {selectedLabel}
      </span>
    </div>
  )
}

function OutputActions({ studio }: { studio: Studio }) {
  const { t } = useTranslation()
  return (
    <div className="flex flex-wrap gap-2 pt-3.5 max-sm:[&>*]:flex-[1_1_100%]">
      <a
        className={buttonVariants({ size: "lg" })}
        href={studio.output?.url}
        download={studio.output?.filename}
      >
        <ArrowDownToLineIcon data-icon="inline-start" />
        {t("poster.download")}
      </a>
      <Button variant="ghost" size="lg" onClick={studio.resetSelection}>
        <ArrowLeftRightIcon data-icon="inline-start" />
        {t("poster.startOver")}
      </Button>
    </div>
  )
}
