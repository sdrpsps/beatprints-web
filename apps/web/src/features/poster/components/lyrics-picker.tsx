import { memo, useState } from "react"
import { CheckIcon, ListXIcon, PencilIcon } from "lucide-react"
import { useTranslation } from "react-i18next"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import {
  Field,
  FieldGroup,
  FieldLabel,
  FieldLegend,
  FieldSet,
} from "@/components/ui/field"
import { Input } from "@/components/ui/input"
import { ScrollArea } from "@/components/ui/scroll-area"
import { toast } from "@/components/ui/toast"
import { usePosterStore } from "@/features/poster/poster-store"
import type { LyricsLine } from "@/features/poster/types"

const LyricRow = memo(function LyricRow({
  line,
  checked,
  value,
  isEditing,
  onToggle,
  onEdit,
  onStartEdit,
  onFinishEdit,
}: {
  line: LyricsLine
  checked: boolean
  value: string
  isEditing: boolean
  onToggle: (index: number, checked: boolean) => void
  onEdit: (index: number, value: string) => void
  onStartEdit: (index: number) => void
  onFinishEdit: () => void
}) {
  const { t } = useTranslation()

  return (
    <Field className="min-h-7.5" orientation="horizontal">
      <Checkbox
        id={`lyric-${line.index}`}
        checked={checked}
        onCheckedChange={(next) => onToggle(line.index, next === true)}
      />
      <span className="min-w-6 font-utility text-[9px] font-semibold tracking-widest text-muted-foreground">
        {String(line.index).padStart(2, "0")}
      </span>
      {isEditing ? (
        <Input
          className="flex-1"
          value={value}
          aria-label={t("poster.editLineAriaLabel", { index: line.index })}
          onChange={(event) => onEdit(line.index, event.target.value)}
        />
      ) : (
        <FieldLabel
          className="flex-1 cursor-pointer text-[13px] leading-[1.55] font-[450]"
          htmlFor={`lyric-${line.index}`}
        >
          {value}
        </FieldLabel>
      )}
      <Button
        className="shrink-0"
        type="button"
        variant={isEditing ? "secondary" : "ghost"}
        size="icon-xs"
        aria-label={
          isEditing
            ? t("poster.finishEditLineAriaLabel", { index: line.index })
            : t("poster.editLineAriaLabel", { index: line.index })
        }
        title={
          isEditing
            ? t("poster.finishEditTitle")
            : t("poster.editLineTitle")
        }
        onClick={() =>
          isEditing ? onFinishEdit() : onStartEdit(line.index)
        }
      >
        {isEditing ? <CheckIcon /> : <PencilIcon />}
      </Button>
    </Field>
  )
})

export function LyricsPicker() {
  const { t } = useTranslation()
  const lyrics = usePosterStore((s) => s.lyrics)
  const selectedLines = usePosterStore((s) => s.selectedLines)
  const lyricEdits = usePosterStore((s) => s.lyricEdits)
  const toggleLyric = usePosterStore((s) => s.toggleLyric)
  const editLyric = usePosterStore((s) => s.editLyric)
  const clearLyricSelection = usePosterStore((s) => s.clearLyricSelection)
  const [editingLine, setEditingLine] = useState<number>()

  const handleToggle = (index: number, checked: boolean) => {
    const accepted = toggleLyric(index, checked)
    if (!accepted) {
      toast.add({
        type: "warning",
        title: t("poster.maxLyricsToastTitle"),
        description: t("poster.maxLyricsToastDesc"),
      })
    }
  }

  return (
    <FieldSet>
      <div className="flex items-center justify-between gap-4">
        <FieldLegend variant="label">{t("poster.fullLyrics")}</FieldLegend>
        <div className="flex flex-wrap justify-end gap-1.5">
          <Button
            type="button"
            variant="outline"
            size="xs"
            disabled={selectedLines.length === 0}
            onClick={clearLyricSelection}
          >
            <ListXIcon data-icon="inline-start" />
            {t("poster.clearLyricSelection")}
          </Button>
          <Badge
            variant={selectedLines.length === 4 ? "default" : "secondary"}
          >
            {t("poster.selectedLyricsCount", { count: selectedLines.length })}
          </Badge>
        </div>
      </div>
      <ScrollArea className="editorial-scroll lyrics-scroll h-90 overflow-hidden rounded-lg border bg-card/20">
        <FieldGroup className="p-3 pr-4">
          {lyrics.map((line) => {
            const checked = selectedLines.includes(line.index)
            const value = lyricEdits[line.index] ?? line.text
            const isEditing = editingLine === line.index

            return (
              <LyricRow
                key={line.index}
                line={line}
                checked={checked}
                value={value}
                isEditing={isEditing}
                onToggle={handleToggle}
                onEdit={editLyric}
                onStartEdit={(idx) => setEditingLine(idx)}
                onFinishEdit={() => setEditingLine(undefined)}
              />
            )
          })}
        </FieldGroup>
      </ScrollArea>
    </FieldSet>
  )
}
