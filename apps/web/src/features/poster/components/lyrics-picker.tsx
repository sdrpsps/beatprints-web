import { useState } from "react"
import { CheckIcon, ListXIcon, PencilIcon } from "lucide-react"

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
import type { Studio } from "@/features/poster/components/studio-shared"

export function LyricsPicker({ studio }: { studio: Studio }) {
  const [editingLine, setEditingLine] = useState<number>()

  return (
    <FieldSet>
      <div className="flex items-center justify-between gap-4">
        <FieldLegend variant="label">整首歌词</FieldLegend>
        <div className="flex flex-wrap justify-end gap-1.5">
          <Button
            type="button"
            variant="outline"
            size="xs"
            disabled={studio.selectedLines.length === 0}
            onClick={studio.clearLyricSelection}
          >
            <ListXIcon data-icon="inline-start" />
            取消全选
          </Button>
          <Badge
            variant={studio.selectedLines.length === 4 ? "default" : "secondary"}
          >
            已选 {studio.selectedLines.length} / 4
          </Badge>
        </div>
      </div>
      <ScrollArea className="lyrics-scroll h-[360px] rounded-lg border">
        <FieldGroup className="py-3 pr-5 pl-3">
          {studio.lyrics.map((line) => {
            const checked = studio.selectedLines.includes(line.index)
            const value = studio.lyricEdits[line.index] ?? line.text
            return (
              <Field
                className="min-h-[30px]"
                key={line.index}
                orientation="horizontal"
              >
                <Checkbox
                  id={`lyric-${line.index}`}
                  checked={checked}
                  onCheckedChange={(next) => {
                    const accepted = studio.toggleLyric(
                      line.index,
                      next === true,
                    )
                    if (!accepted) {
                      toast.add({
                        type: "warning",
                        title: "最多选择四行歌词",
                        description: "请先取消一行，再选择新的歌词。",
                      })
                    }
                  }}
                />
                <span className="min-w-6 font-[var(--font-utility)] text-[9px] font-semibold tracking-[0.1em] text-muted-foreground">
                  {String(line.index).padStart(2, "0")}
                </span>
                {editingLine === line.index ? (
                  <Input
                    className="flex-1"
                    value={value}
                    aria-label={`编辑第 ${line.index} 行歌词`}
                    onChange={(event) =>
                      studio.editLyric(line.index, event.target.value)
                    }
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
                  variant={editingLine === line.index ? "secondary" : "ghost"}
                  size="icon-xs"
                  aria-label={
                    editingLine === line.index
                      ? `完成编辑第 ${line.index} 行歌词`
                      : `编辑第 ${line.index} 行歌词`
                  }
                  title={editingLine === line.index ? "完成编辑" : "编辑这一行"}
                  onClick={() =>
                    setEditingLine((current) =>
                      current === line.index ? undefined : line.index,
                    )
                  }
                >
                  {editingLine === line.index ? <CheckIcon /> : <PencilIcon />}
                </Button>
              </Field>
            )
          })}
        </FieldGroup>
      </ScrollArea>
    </FieldSet>
  )
}
