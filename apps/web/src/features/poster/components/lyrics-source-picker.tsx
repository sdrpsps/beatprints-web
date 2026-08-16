import { useTranslation } from "react-i18next"

import { Field, FieldTitle } from "@/components/ui/field"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import { usePosterStore } from "@/features/poster/poster-store"

export function LyricsSourcePicker() {
  const { t } = useTranslation()
  const lyricsSources = usePosterStore((s) => s.lyricsSources)
  const lyricsSource = usePosterStore((s) => s.lyricsSource)
  const setLyricsSource = usePosterStore((s) => s.setLyricsSource)

  if (lyricsSources.length < 2) return null

  return (
    <Field orientation="horizontal" className="justify-end">
      <FieldTitle>{t("poster.lyricsSourceLabel")}</FieldTitle>
      <ToggleGroup
        aria-label={t("poster.lyricsSourceLabel")}
        value={lyricsSource ? [lyricsSource] : []}
        onValueChange={(values) => {
          const value = values[0]
          if (value && value !== lyricsSource) setLyricsSource(value, t)
        }}
        variant="outline"
        size="sm"
      >
        {lyricsSources.map((source) => (
          <ToggleGroupItem key={source.key} value={source.key}>
            {t(source.labelKey)}
          </ToggleGroupItem>
        ))}
      </ToggleGroup>
    </Field>
  )
}
