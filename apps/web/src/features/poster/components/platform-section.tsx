import { ExternalLinkIcon } from "lucide-react"

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
import { zhCN } from "@/features/poster/copy"
import type { PosterPlatform } from "@/features/poster/types"

const platformItems = [
  { value: "none", label: "不添加" },
  { value: "spotify", label: "Spotify" },
  { value: "apple_music", label: "Apple Music" },
  { value: "qq_music", label: "QQ 音乐" },
  { value: "netease_music", label: "网易云音乐" },
] as const

const platformLabels: Record<PosterPlatform, string> = {
  spotify: "Spotify",
  apple_music: "Apple Music",
  qq_music: "QQ 音乐",
  netease_music: "网易云音乐",
}

export function PlatformSection({ studio }: { studio: Studio }) {
  if (!studio.selected) return null
  return (
    <section className={studioSectionClass}>
      <SectionHeading
        number={studio.kind === "track" ? "03" : "02"}
        title={zhCN.platform}
        description="可选。只添加一个二维码目的地；不选择就不会显示平台标识。"
      />
      <FieldSet>
        <FieldLegend className="sr-only">二维码平台</FieldLegend>
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
  const platform = studio.qrPlatform as PosterPlatform
  return (
    <Field data-invalid={Boolean(studio.currentPlatformError) || undefined}>
      <FieldLabel htmlFor="platform-url">
        {platformLabels[platform]} 链接
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
          placeholder="粘贴歌曲或专辑的公开链接"
          onChange={(event) => studio.setPlatformUrl(event.target.value)}
        />
      </InputGroup>
      <FieldDescription>
        首版需要手动提供；后续会接入跨平台自动匹配。
      </FieldDescription>
      {studio.currentPlatformError ? (
        <FieldError>{studio.currentPlatformError}</FieldError>
      ) : null}
    </Field>
  )
}
