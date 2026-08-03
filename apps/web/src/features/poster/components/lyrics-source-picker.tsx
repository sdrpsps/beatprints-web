import { useTranslation } from "react-i18next"

import { Field, FieldTitle } from "@/components/ui/field"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import type { Studio } from "@/features/poster/components/studio-shared"

export function LyricsSourcePicker({ studio }: { studio: Studio }) {
  const { t } = useTranslation()
  if (studio.lyricsSources.length < 2) return null

  return (
    <Field orientation="horizontal" className="justify-end">
      <FieldTitle>{t("poster.lyricsSourceLabel")}</FieldTitle>
      <ToggleGroup
        aria-label={t("poster.lyricsSourceLabel")}
        value={studio.lyricsSource ? [studio.lyricsSource] : []}
        onValueChange={(values) => {
          const value = values[0]
          if (value && value !== studio.lyricsSource) studio.setLyricsSource(value)
        }}
        variant="outline"
        size="sm"
      >
        {studio.lyricsSources.map((source) => (
          <ToggleGroupItem key={source.key} value={source.key}>
            {t(source.labelKey)}
          </ToggleGroupItem>
        ))}
      </ToggleGroup>
    </Field>
  )
}
