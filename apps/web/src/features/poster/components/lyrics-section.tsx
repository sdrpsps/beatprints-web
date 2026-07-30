import { AlertCircleIcon } from "lucide-react"

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import {
  Field,
  FieldDescription,
  FieldError,
  FieldLabel,
} from "@/components/ui/field"
import { Spinner } from "@/components/ui/spinner"
import { Textarea } from "@/components/ui/textarea"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import { LyricsPicker } from "@/features/poster/components/lyrics-picker"
import {
  SectionHeading,
  studioSectionClass,
  type Studio,
} from "@/features/poster/components/studio-shared"
import { zhCN } from "@/features/poster/copy"

export function LyricsSection({ studio }: { studio: Studio }) {
  if (studio.kind !== "track" || !studio.selected) return null
  const isManual = studio.lyricsMode === "manual"

  return (
    <section className={studioSectionClass}>
      <SectionHeading
        number="02"
        title={studio.instrumental ? "纯音乐文字" : zhCN.lyrics}
        description={
          studio.instrumental
            ? "默认不显示文字，也可以填写最多四行、合计不超过 200 字的短句。"
            : zhCN.lyricsHelp
        }
      />
      <LyricsStatus studio={studio} />
      {!studio.instrumental && studio.lyrics.length > 0 ? (
        <ToggleGroup
          value={[studio.lyricsMode]}
          onValueChange={(values) => {
            const value = values[0]
            if (value === "catalog" || value === "manual") {
              studio.setLyricsMode(value)
            }
          }}
          variant="outline"
          size="sm"
        >
          <ToggleGroupItem value="catalog">{zhCN.catalogLyrics}</ToggleGroupItem>
          <ToggleGroupItem value="manual">{zhCN.manualLyrics}</ToggleGroupItem>
        </ToggleGroup>
      ) : null}
      {!studio.instrumental && !isManual && studio.lyrics.length > 0 ? (
        <LyricsPicker studio={studio} />
      ) : null}
      {studio.instrumental ? <InstrumentalField studio={studio} /> : null}
      {!studio.instrumental && isManual ? (
        <ManualLyricsField studio={studio} />
      ) : null}
    </section>
  )
}

function LyricsStatus({ studio }: { studio: Studio }) {
  if (studio.lyricsState === "loading") {
    return (
      <div className="flex min-h-[88px] items-center justify-center gap-[9px] text-[13px] text-muted-foreground">
        <Spinner />
        <span>正在匹配歌词…</span>
      </div>
    )
  }
  if (!studio.lyricsError) return null
  return (
    <Alert>
      <AlertCircleIcon />
      <AlertTitle>改为手动填写</AlertTitle>
      <AlertDescription>{studio.lyricsError}</AlertDescription>
    </Alert>
  )
}

function InstrumentalField({ studio }: { studio: Studio }) {
  return (
    <Field>
      <FieldLabel htmlFor="instrumental-text">可选短句</FieldLabel>
      <Textarea
        id="instrumental-text"
        value={studio.instrumentalText}
        maxLength={200}
        placeholder="留空则海报不显示歌词文字"
        onChange={(event) => studio.setInstrumentalText(event.target.value)}
      />
      <FieldDescription>
        {studio.instrumentalLineCount} / 4 行 · {studio.instrumentalText.length}{" "}
        / 200 字
      </FieldDescription>
    </Field>
  )
}

function ManualLyricsField({ studio }: { studio: Studio }) {
  const invalid = studio.manualLineCount !== 4
  return (
    <Field data-invalid={invalid || undefined}>
      <FieldLabel htmlFor="manual-lyrics">海报文字</FieldLabel>
      <Textarea
        id="manual-lyrics"
        value={studio.manualLyrics}
        maxLength={2000}
        aria-invalid={invalid}
        placeholder={"第一行\n第二行\n第三行\n第四行"}
        onChange={(event) => studio.setManualLyrics(event.target.value)}
      />
      <FieldDescription>
        最多四行，空行会被忽略。当前 {studio.manualLineCount} / 4 行。
      </FieldDescription>
      {invalid ? <FieldError>需要正好四行非空文字。</FieldError> : null}
    </Field>
  )
}
