import { ExternalLinkIcon } from "lucide-react"
import { useTranslation } from "react-i18next"

import {
  Field,
  FieldDescription,
  FieldError,
  FieldLabel,
  FieldLegend,
  FieldSet,
} from "@/components/ui/field"
import {
  InputGroup,
  InputGroupAddon,
  InputGroupInput,
} from "@/components/ui/input-group"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import {
  SectionHeading,
  studioSectionClass,
  type Studio,
} from "@/features/poster/components/studio-shared"
import type { PosterPlatform } from "@/features/poster/types"

export function PlatformSection({ studio }: { studio: Studio }) {
  const { t } = useTranslation()
  if (!studio.selected) return null

  const platformItems = [
    { value: "none", label: t("poster.platformNone") },
    { value: "spotify", label: "Spotify" },
    { value: "apple_music", label: "Apple Music" },
    { value: "qq_music", label: t("poster.qqMusic") },
    { value: "netease_music", label: t("poster.neteaseMusic") },
  ] as const

  return (
    <section className={studioSectionClass}>
      <SectionHeading
        number={studio.kind === "track" ? "03" : "02"}
        title={t("poster.platform")}
        description={t("poster.platformHelp")}
      />
      <FieldSet>
        <FieldLegend className="sr-only">{t("poster.qrPlatformLabel")}</FieldLegend>
        <ToggleGroup
          value={[studio.qrPlatform || "none"]}
          onValueChange={(values) => {
            const value = values[0]
            if (!value) return
            studio.setQrPlatform(
              value === "none" ? "" : (value as PosterPlatform),
            )
          }}
          variant="outline"
          size="sm"
          className="flex-wrap"
        >
          {platformItems.map((item) => (
            <ToggleGroupItem key={item.value} value={item.value}>
              {item.label}
            </ToggleGroupItem>
          ))}
        </ToggleGroup>
      </FieldSet>
      {studio.platformNeedsUrl && studio.qrPlatform ? (
        <PlatformUrlField studio={studio} />
      ) : null}
    </section>
  )
}

function PlatformUrlField({ studio }: { studio: Studio }) {
  const { t } = useTranslation()
  const platform = studio.qrPlatform as PosterPlatform

  const platformLabels: Record<PosterPlatform, string> = {
    spotify: "Spotify",
    apple_music: "Apple Music",
    qq_music: t("poster.qqMusic"),
    netease_music: t("poster.neteaseMusic"),
  }

  return (
    <Field data-invalid={Boolean(studio.currentPlatformError) || undefined}>
      <FieldLabel htmlFor="platform-url">
        {platformLabels[platform]} {t("poster.platformLinkSuffix")}
      </FieldLabel>
      <InputGroup>
        <InputGroupAddon>
          <ExternalLinkIcon aria-hidden="true" />
        </InputGroupAddon>
        <InputGroupInput
          id="platform-url"
          type="url"
          inputMode="url"
          value={studio.platformUrl}
          aria-invalid={Boolean(studio.currentPlatformError)}
          placeholder={t("poster.platformUrlPlaceholder")}
          onChange={(event) => studio.setPlatformUrl(event.target.value)}
        />
      </InputGroup>
      <FieldDescription>
        {t("poster.platformUrlHelp")}
      </FieldDescription>
      {studio.currentPlatformError ? (
        <FieldError>{studio.currentPlatformError}</FieldError>
      ) : null}
    </Field>
  )
}
