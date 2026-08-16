import { useTranslation } from "react-i18next"

import { FieldLegend, FieldSet } from "@/components/ui/field"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import { PlatformLinkFlow } from "@/features/poster/components/platform-link-flow"
import {
  SectionHeading,
  studioSectionClass,
} from "@/features/poster/components/studio-shared"
import { enabledDestinations, getDestination } from "@/features/poster/destinations/registry"
import { usePosterStore } from "@/features/poster/poster-store"
import type { PosterPlatform } from "@/features/poster/types"

export function PlatformSection() {
  const { t } = useTranslation()
  const kind = usePosterStore((s) => s.kind)
  const selected = usePosterStore((s) => s.selected)
  const qrPlatform = usePosterStore((s) => s.qrPlatform)
  const setQrPlatform = usePosterStore((s) => s.setQrPlatform)

  if (!selected) return null

  const destination = qrPlatform ? getDestination(qrPlatform) : null
  const platformNeedsUrl =
    Boolean(qrPlatform) &&
    Boolean(selected) &&
    !destination?.reusesSourceLink(selected?.provider ?? "")

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
        number={kind === "track" ? "03" : "02"}
        title={t("poster.platform")}
        description={t("poster.platformHelp")}
      />
      <FieldSet>
        <FieldLegend className="sr-only">
          {t("poster.qrPlatformLabel")}
        </FieldLegend>
        <ToggleGroup
          value={[qrPlatform || "none"]}
          onValueChange={(values) => {
            const value = values[0]
            if (!value) return

            setQrPlatform(
              value === "none" ? "" : (value as PosterPlatform),
              t,
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
      {platformNeedsUrl && qrPlatform ? <PlatformLinkFlow /> : null}
    </section>
  )
}
