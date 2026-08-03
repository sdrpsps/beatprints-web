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
  type Studio,
} from "@/features/poster/components/studio-shared"

export function LyricsSection({ studio }: { studio: Studio }) {
  const { t } = useTranslation()
  if (studio.kind !== "track" || !studio.selected) return null
  const isManual = studio.lyricsMode === "manual"

  return (
    <section className={studioSectionClass}>
      <SectionHeading
        number="02"
        title={studio.instrumental ? t("poster.instrumentalTitle") : t("poster.lyrics")}
        description={
          studio.instrumental
            ? t("poster.instrumentalHelp")
            : t("poster.lyricsHelp")
        }
      />
      <LyricsSourcePicker studio={studio} />
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
          <ToggleGroupItem value="catalog">
            {t("poster.catalogLyrics")}
          </ToggleGroupItem>
          <ToggleGroupItem value="manual">
            {t("poster.manualLyrics")}
          </ToggleGroupItem>
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
  const { t } = useTranslation()
  if (studio.lyricsState === "loading") {
    return (
      <div className="flex min-h-[88px] items-center justify-center gap-[9px] text-[13px] text-muted-foreground">
        <Spinner />
        <span>{t("poster.matchingLyrics")}</span>
      </div>
    )
  }
  if (!studio.lyricsError) return null
  return (
    <Alert>
      <AlertCircleIcon />
      <AlertTitle>{t("poster.switchToManual")}</AlertTitle>
      <AlertDescription>{studio.lyricsError}</AlertDescription>
    </Alert>
  )
}

function InstrumentalField({ studio }: { studio: Studio }) {
  const { t } = useTranslation()
  return (
    <Field>
      <FieldLabel htmlFor="instrumental-text">
        {t("poster.instrumentalFieldLabel")}
      </FieldLabel>
      <Textarea
        id="instrumental-text"
        value={studio.instrumentalText}
        maxLength={200}
        placeholder={t("poster.instrumentalPlaceholder")}
        onChange={(event) => studio.setInstrumentalText(event.target.value)}
      />
      <FieldDescription>
        {studio.instrumentalLineCount} / 4 · {studio.instrumentalText.length} / 200
      </FieldDescription>
    </Field>
  )
}

function ManualLyricsField({ studio }: { studio: Studio }) {
  const { t } = useTranslation()
  return (
    <Field>
      <FieldLabel htmlFor="manual-lyrics">
        {t("poster.manualLyricsLabel")}
      </FieldLabel>
      <Textarea
        id="manual-lyrics"
        value={studio.manualLyrics}
        maxLength={2000}
        placeholder={t("poster.manualLyricsPlaceholder")}
        onChange={(event) => studio.setManualLyrics(event.target.value)}
      />
      <FieldDescription>
        {t("poster.manualLyricsHelp", { count: studio.manualLineCount })}
      </FieldDescription>
    </Field>
  )
}
