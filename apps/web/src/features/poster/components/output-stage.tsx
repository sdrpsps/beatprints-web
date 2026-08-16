import { useEffect, useRef, useState } from "react"
import {
  ArrowDownToLineIcon,
  ArrowLeftRightIcon,
  CheckIcon,
  CopyIcon,
  Disc3Icon,
  HistoryIcon,
  Share2Icon,
  TriangleAlertIcon,
} from "lucide-react"
import { useTranslation } from "react-i18next"

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Button, buttonVariants } from "@/components/ui/button"
import { Spinner } from "@/components/ui/spinner"
import { toast } from "@/components/ui/toast"
import { usePosterStore } from "@/features/poster/poster-store"
import {
  canCopyImageToClipboard,
  copyImageBlobToClipboard,
  copyImageUrlToClipboard,
} from "@/lib/clipboard"
import { canShareImage, shareImageBlob } from "@/lib/share"
import { cn } from "@/lib/utils"

export function OutputStage() {
  const { t } = useTranslation()
  const output = usePosterStore((s) => s.output)
  const outputStale = usePosterStore((s) => s.outputStale)
  const generationState = usePosterStore((s) => s.generationState)
  const selected = usePosterStore((s) => s.selected)
  const historyCount = usePosterStore((s) => s.historyItems.length)
  const setIsHistoryOpen = usePosterStore((s) => s.setIsHistoryOpen)

  const stageRef = useRef<HTMLDivElement>(null)
  const [readyOutputUrl, setReadyOutputUrl] = useState<string>()

  const isGenerating = generationState === "loading"
  const outputReady = Boolean(output) && readyOutputUrl === output?.url
  const showLoadingOverlay = isGenerating || Boolean(output && !outputReady)
  const elapsedSeconds = output?.processTime
    ? `${(Number(output.processTime) / 1000).toFixed(2)}s`
    : "—"

  useEffect(() => {
    if (generationState === "success") {
      stageRef.current?.focus()
    }
  }, [generationState])

  return (
    <aside
      className="sticky top-6 max-[960px]:static max-[960px]:order-2"
      aria-label={t("poster.outputAriaLabel")}
    >
      <div className="flex items-center justify-between gap-5 pb-2.5 font-[var(--font-utility)] text-[10px] font-semibold tracking-[0.14em] text-muted-foreground">
        <div className="flex items-center gap-2">
          <span>OUTPUT / PNG</span>
          <span>{elapsedSeconds}</span>
        </div>

        <Button
          type="button"
          variant="ghost"
          size="xs"
          className="h-5 px-1.5 text-[10px] font-medium tracking-normal text-muted-foreground hover:text-foreground"
          onClick={() => setIsHistoryOpen(true)}
          aria-label={t("poster.historyOpenAria")}
        >
          <HistoryIcon data-icon="inline-start" />
          {t("poster.historyTitle")}
          {historyCount > 0 ? (
            <Badge variant="secondary" className="ml-1 px-1 py-0 text-[9px]">
              {historyCount}
            </Badge>
          ) : null}
        </Button>
      </div>

      {outputStale ? (
        <Alert className="output-stale-alert mb-2.5">
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
          output && "min-h-0 p-[clamp(16px,3vw,38px)]",
        )}
        tabIndex={-1}
        aria-live="polite"
      >
        {output ? (
          <img
            key={output.url}
            className={cn(
              "block max-h-[80vh] max-w-full object-contain shadow-[0_24px_70px_rgba(5,6,10,0.28)]",
              outputReady && "poster-output motion-reduce:animate-none",
            )}
            src={output.url}
            alt={t("poster.posterAlt", { title: output.title })}
            onLoad={() => setReadyOutputUrl(output?.url)}
          />
        ) : null}

        {!output && !isGenerating ? (
          <EmptyOutputState selected={selected} />
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

      {output ? <OutputActions /> : null}
    </aside>
  )
}

function EmptyOutputState({
  selected,
}: {
  selected?: { title: string; artists: string[] }
}) {
  const { t } = useTranslation()
  const selectedLabel = selected
    ? `${selected.title} · ${selected.artists.join("、")}`
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

function OutputActions() {
  const { t } = useTranslation()
  const output = usePosterStore((s) => s.output)
  const resetSelection = usePosterStore((s) => s.resetSelection)
  const [copied, setCopied] = useState(false)

  if (!output) return null

  const handleCopy = async () => {
    try {
      setCopied(true)
      if (output.blob) {
        await copyImageBlobToClipboard(output.blob)
      } else {
        await copyImageUrlToClipboard(output.url)
      }
      toast.add({
        type: "default",
        title: t("poster.copiedToastTitle"),
        description: t("poster.copiedToastDesc"),
      })
    } catch {
      toast.add({
        type: "error",
        title: t("poster.copyFailedTitle"),
        description: t("poster.copyFailedDesc"),
      })
    } finally {
      setTimeout(() => setCopied(false), 2000)
    }
  }

  const handleShare = async () => {
    try {
      if (output.blob) {
        await shareImageBlob(output.blob, output.filename, output.title)
      }
    } catch {
      // User cancelled
    }
  }

  return (
    <div className="flex flex-wrap gap-2 pt-3.5 max-sm:[&>*]:flex-[1_1_100%]">
      <a
        className={buttonVariants({ size: "lg" })}
        href={output.url}
        download={output.filename}
      >
        <ArrowDownToLineIcon data-icon="inline-start" />
        {t("poster.download")}
      </a>

      {canCopyImageToClipboard() ? (
        <Button
          variant="outline"
          size="lg"
          onClick={handleCopy}
          title={t("poster.copyImage")}
        >
          {copied ? (
            <CheckIcon data-icon="inline-start" />
          ) : (
            <CopyIcon data-icon="inline-start" />
          )}
          {copied ? t("poster.copiedToastTitle") : t("poster.copyImage")}
        </Button>
      ) : null}

      {output.blob && canShareImage(output.blob) ? (
        <Button
          variant="outline"
          size="lg"
          onClick={handleShare}
          title={t("poster.sharePoster")}
        >
          <Share2Icon data-icon="inline-start" />
          {t("poster.share")}
        </Button>
      ) : null}

      <Button variant="ghost" size="lg" onClick={resetSelection}>
        <ArrowLeftRightIcon data-icon="inline-start" />
        {t("poster.startOver")}
      </Button>
    </div>
  )
}
