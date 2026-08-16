import { AlertCircleIcon } from "lucide-react"
import { useTranslation } from "react-i18next"

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import {
  Field,
  FieldDescription,
  FieldLabel,
} from "@/components/ui/field"
import { Spinner } from "@/components/ui/spinner"
import { Textarea } from "@/components/ui/textarea"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import { LyricsPicker } from "@/features/poster/components/lyrics-picker"
import { LyricsSourcePicker } from "@/features/poster/components/lyrics-source-picker"
import {
  SectionHeading,
  studioSectionClass,
} from "@/features/poster/components/studio-shared"
import { usePosterStore } from "@/features/poster/poster-store"

export function LyricsSection() {
  const { t } = useTranslation()
  const kind = usePosterStore((s) => s.kind)
  const selected = usePosterStore((s) => s.selected)
  const instrumental = usePosterStore((s) => s.instrumental)
  const lyricsMode = usePosterStore((s) => s.lyricsMode)
  const setLyricsMode = usePosterStore((s) => s.setLyricsMode)
  const lyrics = usePosterStore((s) => s.lyrics)

  if (kind !== "track" || !selected) return null
  const isManual = lyricsMode === "manual"

  return (
    <section className={studioSectionClass}>
      <SectionHeading
        number="02"
        title={instrumental ? t("poster.instrumentalTitle") : t("poster.lyrics")}
        description={
          instrumental
            ? t("poster.instrumentalHelp")
            : t("poster.lyricsHelp")
        }
      />
      <LyricsSourcePicker />
      <LyricsStatus />
      {!instrumental && lyrics.length > 0 ? (
        <ToggleGroup
          value={[lyricsMode]}
          onValueChange={(values) => {
            const value = values[0]
            if (value === "catalog" || value === "manual") {
              setLyricsMode(value)
            }
          }}
          variant="outline"
          size="sm"
        >
          <ToggleGroupItem value="catalog">
            {t("poster.catalogLyrics")}
          </ToggleGroupItem>
          <ToggleGroupItem value="manual">
            {t("poster.manualLyrics")}
          </ToggleGroupItem>
        </ToggleGroup>
      ) : null}
      {!instrumental && !isManual && lyrics.length > 0 ? (
        <LyricsPicker />
      ) : null}
      {instrumental ? <InstrumentalField /> : null}
      {!instrumental && isManual ? <ManualLyricsField /> : null}
    </section>
  )
}

function LyricsStatus() {
  const { t } = useTranslation()
  const lyricsState = usePosterStore((s) => s.lyricsState)
  const lyricsError = usePosterStore((s) => s.lyricsError)

  if (lyricsState === "loading") {
    return (
      <div className="flex min-h-[88px] items-center justify-center gap-[9px] text-[13px] text-muted-foreground">
        <Spinner />
        <span>{t("poster.matchingLyrics")}</span>
      </div>
    )
  }
  if (!lyricsError) return null
  return (
    <Alert>
      <AlertCircleIcon />
      <AlertTitle>{t("poster.switchToManual")}</AlertTitle>
      <AlertDescription>{lyricsError}</AlertDescription>
    </Alert>
  )
}

function InstrumentalField() {
  const { t } = useTranslation()
  const instrumentalText = usePosterStore((s) => s.instrumentalText)
  const setInstrumentalText = usePosterStore((s) => s.setInstrumentalText)
  const instrumentalLineCount = instrumentalText.split("\n").filter((l) => l.trim().length > 0).length

  return (
    <Field>
      <FieldLabel htmlFor="instrumental-text">
        {t("poster.instrumentalFieldLabel")}
      </FieldLabel>
      <Textarea
        id="instrumental-text"
        value={instrumentalText}
        maxLength={200}
        placeholder={t("poster.instrumentalPlaceholder")}
        onChange={(event) => setInstrumentalText(event.target.value)}
      />
      <FieldDescription>
        {instrumentalLineCount} / 4 · {instrumentalText.length} / 200
      </FieldDescription>
    </Field>
  )
}

function ManualLyricsField() {
  const { t } = useTranslation()
  const manualLyrics = usePosterStore((s) => s.manualLyrics)
  const setManualLyrics = usePosterStore((s) => s.setManualLyrics)
  const manualLineCount = manualLyrics.split("\n").filter((l) => l.trim().length > 0).length

  return (
    <Field>
      <FieldLabel htmlFor="manual-lyrics">
        {t("poster.manualLyricsLabel")}
      </FieldLabel>
      <Textarea
        id="manual-lyrics"
        value={manualLyrics}
        maxLength={2000}
        placeholder={t("poster.manualLyricsPlaceholder")}
        onChange={(event) => setManualLyrics(event.target.value)}
      />
      <FieldDescription>
        {t("poster.manualLyricsHelp", { count: manualLineCount })}
      </FieldDescription>
    </Field>
  )
}
