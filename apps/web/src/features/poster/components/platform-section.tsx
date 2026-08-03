import { useTranslation } from "react-i18next"

import { FieldLegend, FieldSet } from "@/components/ui/field"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import { PlatformLinkFlow } from "@/features/poster/components/platform-link-flow"
import {
  SectionHeading,
  studioSectionClass,
  type Studio,
} from "@/features/poster/components/studio-shared"
import { enabledDestinations } from "@/features/poster/destinations/registry"
import type { PosterPlatform } from "@/features/poster/types"

export function PlatformSection({ studio }: { studio: Studio }) {
  const { t } = useTranslation()
  if (!studio.selected) return null

  const items = [
    { value: "none", label: t("poster.platformNone") },
    ...enabledDestinations().map(({ key, labelKey }) => ({
      value: key,
      label: t(labelKey),
    })),
  ]

  return (
    <section className={studioSectionClass}>
      <SectionHeading
        number={studio.kind === "track" ? "03" : "02"}
        title={t("poster.platform")}
        description={t("poster.platformHelp")}
      />
      <FieldSet>
        <FieldLegend className="sr-only">
          {t("poster.qrPlatformLabel")}
        </FieldLegend>
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
          {items.map((item) => (
            <ToggleGroupItem key={item.value} value={item.value}>
              {item.label}
            </ToggleGroupItem>
          ))}
        </ToggleGroup>
      </FieldSet>
      {studio.platformNeedsUrl && studio.qrPlatform ? (
        <PlatformLinkFlow studio={studio} />
      ) : null}
    </section>
  )
}
