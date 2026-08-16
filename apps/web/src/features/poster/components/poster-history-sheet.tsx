import { useEffect, useState } from "react"
import {
  ArrowDownToLineIcon,
  CheckIcon,
  ClockIcon,
  CopyIcon,
  Disc3Icon,
  HistoryIcon,
  Music2Icon,
  RotateCcwIcon,
  Share2Icon,
  Trash2Icon,
  XIcon,
} from "lucide-react"
import { useTranslation } from "react-i18next"

import { Badge } from "@/components/ui/badge"
import { Button, buttonVariants } from "@/components/ui/button"
import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty"
import { ScrollArea } from "@/components/ui/scroll-area"
import {
  Sheet,
  SheetClose,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet"
import { toast } from "@/components/ui/toast"
import { usePosterStore } from "@/features/poster/poster-store"
import {
  canCopyImageToClipboard,
  copyImageBlobToClipboard,
} from "@/lib/clipboard"
import type { PosterHistoryItem } from "@/lib/poster-history-db"
import { canShareImage, shareImageBlob } from "@/lib/share"

function HistoryCard({
  item,
  onRestore,
  onRemove,
  onView,
}: {
  item: PosterHistoryItem
  onRestore: (item: PosterHistoryItem) => void
  onRemove: (id: string) => void
  onView: (item: PosterHistoryItem) => void
}) {
  const { t } = useTranslation()
  const [copied, setCopied] = useState(false)
  const [imageUrl, setImageUrl] = useState<string>("")

  useEffect(() => {
    const url = URL.createObjectURL(item.blob)
    setImageUrl(url)
    return () => URL.revokeObjectURL(url)
  }, [item.blob])

  const handleCopy = async () => {
    try {
      setCopied(true)
      await copyImageBlobToClipboard(item.blob)
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
      await shareImageBlob(item.blob, item.filename, item.title)
    } catch {
      // Ignored if user cancels share dialog
    }
  }

  const dateStr = new Date(item.createdAt).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  })

  return (
    <div className="flex flex-col gap-3 rounded-lg border bg-card/60 p-3.5 transition-colors duration-150 hover:bg-card">
      <div className="flex items-start gap-3">
        {imageUrl ? (
          <button
            type="button"
            className="group relative size-16 shrink-0 cursor-pointer overflow-hidden rounded border bg-muted focus-visible:outline-2 focus-visible:outline-ring"
            onClick={() => onView(item)}
            title={t("poster.viewPoster")}
          >
            <img
              src={imageUrl}
              alt={item.title}
              className="size-full object-cover transition-transform duration-200 group-hover:scale-105"
            />
          </button>
        ) : (
          <div className="grid size-16 shrink-0 place-items-center rounded border bg-muted text-muted-foreground">
            {item.kind === "album" ? (
              <Disc3Icon className="size-6" />
            ) : (
              <Music2Icon className="size-6" />
            )}
          </div>
        )}

        <div className="flex min-w-0 flex-1 flex-col gap-1">
          <div className="flex items-center justify-between gap-2">
            <span className="truncate text-[13px] font-semibold text-foreground">
              {item.title}
            </span>
            <span className="flex items-center gap-1 font-[var(--font-utility)] text-[10px] text-muted-foreground">
              <ClockIcon className="size-3" />
              {dateStr}
            </span>
          </div>

          <p className="truncate text-xs text-muted-foreground">
            {item.artists.join(", ")}
          </p>

          <div className="mt-1 flex flex-wrap items-center gap-1.5">
            <Badge variant="outline" className="text-[10px] py-0 px-1.5">
              {item.kind === "album" ? t("poster.album") : t("poster.track")}
            </Badge>
            <Badge variant="secondary" className="text-[10px] py-0 px-1.5">
              {item.theme}
            </Badge>
            {item.accent ? (
              <Badge variant="secondary" className="text-[10px] py-0 px-1.5">
                Accent
              </Badge>
            ) : null}
          </div>
        </div>
      </div>

      <div className="flex items-center justify-between gap-1.5 border-t pt-2.5">
        <div className="flex items-center gap-1">
          <Button
            type="button"
            variant="outline"
            size="xs"
            onClick={() => onRestore(item)}
            title={t("poster.restoreSettings")}
          >
            <RotateCcwIcon data-icon="inline-start" />
            {t("poster.restoreSettings")}
          </Button>

          {canCopyImageToClipboard() ? (
            <Button
              type="button"
              variant="ghost"
              size="icon-xs"
              onClick={handleCopy}
              title={t("poster.copyImage")}
            >
              {copied ? <CheckIcon /> : <CopyIcon />}
            </Button>
          ) : null}

          {canShareImage(item.blob) ? (
            <Button
              type="button"
              variant="ghost"
              size="icon-xs"
              onClick={handleShare}
              title={t("poster.share")}
            >
              <Share2Icon />
            </Button>
          ) : null}

          {imageUrl ? (
            <a
              className={buttonVariants({ variant: "ghost", size: "icon-xs" })}
              href={imageUrl}
              download={item.filename}
              title={t("poster.download")}
            >
              <ArrowDownToLineIcon />
            </a>
          ) : null}
        </div>

        <Button
          type="button"
          variant="ghost"
          size="icon-xs"
          className="text-muted-foreground hover:text-destructive"
          onClick={() => onRemove(item.id)}
          title={t("poster.deleteHistoryItem")}
        >
          <Trash2Icon />
        </Button>
      </div>
    </div>
  )
}

export function PosterHistorySheet() {
  const { t } = useTranslation()
  const isHistoryOpen = usePosterStore((s) => s.isHistoryOpen)
  const setIsHistoryOpen = usePosterStore((s) => s.setIsHistoryOpen)
  const historyItems = usePosterStore((s) => s.historyItems)
  const removeHistoryItem = usePosterStore((s) => s.removeHistoryItem)
  const clearAllHistory = usePosterStore((s) => s.clearAllHistory)
  const restoreFromHistory = usePosterStore((s) => s.restoreFromHistory)
  const showOutput = usePosterStore((s) => s.showOutput)

  const handleView = (item: PosterHistoryItem) => {
    const url = URL.createObjectURL(item.blob)
    showOutput({
      url,
      filename: item.filename,
      title: item.title,
      processTime: item.processTime,
      blob: item.blob,
    })
    setIsHistoryOpen(false)
  }

  const handleClearAll = async () => {
    if (window.confirm(t("poster.clearHistoryConfirm"))) {
      await clearAllHistory()
    }
  }

  return (
    <Sheet open={isHistoryOpen} onOpenChange={setIsHistoryOpen}>
      <SheetContent
        side="right"
        showCloseButton={false}
        className="flex w-full flex-col p-0 sm:max-w-md"
      >
        <SheetHeader className="border-b p-5 pb-4">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <HistoryIcon className="size-4 text-muted-foreground" />
              <SheetTitle className="text-base font-semibold">{t("poster.historyTitle")}</SheetTitle>
              {historyItems.length > 0 ? (
                <Badge variant="secondary" className="px-1.5 py-0 text-xs">
                  {historyItems.length}
                </Badge>
              ) : null}
            </div>

            <div className="flex items-center gap-1">
              {historyItems.length > 0 ? (
                <Button
                  type="button"
                  variant="ghost"
                  size="xs"
                  className="h-7 text-xs text-muted-foreground hover:text-destructive"
                  onClick={handleClearAll}
                >
                  <Trash2Icon data-icon="inline-start" />
                  {t("poster.clearAllHistory")}
                </Button>
              ) : null}

              <SheetClose
                render={
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon-xs"
                    className="size-7 text-muted-foreground hover:text-foreground"
                  />
                }
              >
                <XIcon className="size-4" />
                <span className="sr-only">Close</span>
              </SheetClose>
            </div>
          </div>
          <SheetDescription className="mt-1.5 text-xs text-muted-foreground">
            {t("poster.historyDescription")}
          </SheetDescription>
        </SheetHeader>

        <ScrollArea className="flex-1 px-5 py-4">
          {historyItems.length === 0 ? (
            <Empty className="min-h-[300px] border-none">
              <EmptyHeader>
                <EmptyMedia variant="icon">
                  <HistoryIcon />
                </EmptyMedia>
                <EmptyTitle>{t("poster.historyEmptyTitle")}</EmptyTitle>
                <EmptyDescription>
                  {t("poster.historyEmptyDescription")}
                </EmptyDescription>
              </EmptyHeader>
            </Empty>
          ) : (
            <div className="flex flex-col gap-3">
              {historyItems.map((item) => (
                <HistoryCard
                  key={item.id}
                  item={item}
                  onRestore={(itm) => restoreFromHistory(itm, t)}
                  onRemove={removeHistoryItem}
                  onView={handleView}
                />
              ))}
            </div>
          )}
        </ScrollArea>
      </SheetContent>
    </Sheet>
  )
}
