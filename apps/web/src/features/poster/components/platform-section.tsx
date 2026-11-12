import { useEffect, useId, useState } from "react"
import { ChevronRightIcon, Disc3Icon, PlusIcon } from "lucide-react"
import { useTranslation } from "react-i18next"

import { Button } from "@/components/ui/button"
import { FieldLegend, FieldSet } from "@/components/ui/field"
import { Item, ItemActions, ItemContent, ItemDescription, ItemMedia, ItemTitle } from "@/components/ui/item"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import { fetchCapabilities } from "@/features/poster/api"
import { PlatformLinkFlow } from "@/features/poster/components/platform-link-flow"
import { SectionHeading, studioSectionClass } from "@/features/poster/components/studio-shared"
import { enabledDestinations, getDestination } from "@/features/poster/destinations/registry"
import type { PosterDestination } from "@/features/poster/destinations/types"
import { usePosterStore } from "@/features/poster/poster-store"
import type { PosterPlatform, QrFormat } from "@/features/poster/types"

export function PlatformSection() {
  const { t } = useTranslation()
  const kind = usePosterStore((s) => s.kind)
  const selected = usePosterStore((s) => s.selected)
  const qrPlatform = usePosterStore((s) => s.qrPlatform)
  const setQrPlatform = usePosterStore((s) => s.setQrPlatform)
  const clearPlatform = usePosterStore((s) => s.clearPlatform)
  const [choosing, setChoosing] = useState(false)

  if (!selected) return null
  const destination = qrPlatform ? getDestination(qrPlatform) : null

  return (
    <section className={studioSectionClass}>
      <SectionHeading
        number={kind === "track" ? "03" : "02"}
        title={t("poster.listenEntry")}
        description={t("poster.listenEntryHelp")}
      />
      {!qrPlatform && !choosing ? (
        <Item variant="outline">
          <ItemMedia variant="icon"><Disc3Icon aria-hidden="true" /></ItemMedia>
          <ItemContent>
            <ItemTitle>{t("poster.listenEntryAddTitle")}</ItemTitle>
            <ItemDescription>{t("poster.listenEntryAddHelp")}</ItemDescription>
          </ItemContent>
          <ItemActions>
            <Button type="button" variant="outline" size="sm" onClick={() => setChoosing(true)} aria-expanded={false} aria-controls="platform-picker">
              <PlusIcon data-icon="inline-start" aria-hidden="true" />{t("poster.listenEntryAdd")}
            </Button>
          </ItemActions>
        </Item>
      ) : (
        <div className="flex flex-col gap-6">
          <div className="flex flex-col gap-3">
            <div className="flex items-center justify-between gap-3">
              <p className="text-sm font-medium">{t("poster.listenDestination")}</p>
              {qrPlatform ? (
                <Button type="button" variant="ghost" size="sm" onClick={() => { clearPlatform(); setChoosing(false) }}>
                  {t("poster.listenEntryRemove")}
                </Button>
              ) : null}
            </div>
            {destination ? (
              <Item variant="outline" size="sm">
                <ItemMedia><DestinationLogo destination={destination} /></ItemMedia>
                <ItemContent><ItemTitle>{t(destination.labelKey)}</ItemTitle></ItemContent>
                <ItemActions>
                  <Button type="button" variant="ghost" size="sm" onClick={() => setChoosing(!choosing)} aria-expanded={choosing} aria-controls="platform-picker">
                    {choosing ? t("poster.listenCancel") : t("poster.listenChange")}
                  </Button>
                </ItemActions>
              </Item>
            ) : null}
            {choosing ? (
              <FieldSet id="platform-picker">
                <FieldLegend>{t("poster.listenChoosePlatform")}</FieldLegend>
                <ToggleGroup
                  orientation="vertical"
                  value={qrPlatform ? [qrPlatform] : []}
                  onValueChange={(values) => {
                    const value = values[0] as PosterPlatform | undefined
                    if (!value) return
                    if (value !== qrPlatform) setQrPlatform(value, t)
                    setChoosing(false)
                  }}
                  variant="outline"
                  className="w-full"
                >
                  {enabledDestinations().map((option) => (
                    <ToggleGroupItem key={option.key} value={option.key} className="h-11 w-full justify-start gap-2.5 px-3">
                      <DestinationLogo destination={option} />
                      <span className="flex-1 text-left">{t(option.labelKey)}</span>
                      <ChevronRightIcon data-icon="inline-end" aria-hidden="true" />
                    </ToggleGroupItem>
                  ))}
                </ToggleGroup>
                {!qrPlatform ? <Button type="button" variant="ghost" size="sm" onClick={() => setChoosing(false)}>{t("poster.listenCancel")}</Button> : null}
              </FieldSet>
            ) : null}
            {destination ? <PlatformLinkFlow /> : null}
          </div>
          {destination ? <QrFormatSelector fixedCode={Boolean(destination.fixedCode)} /> : null}
        </div>
      )}
    </section>
  )
}

function DestinationLogo({ destination }: { destination: PosterDestination }) {
  const id = useId()
  const maskId = `destination-mask-${id}`
  const filterId = `destination-invert-${id}`
  const alphaFilterId = `destination-alpha-${id}`
  const clipId = `destination-clip-${id}`
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24" className="size-6 shrink-0 text-foreground">
      <defs>
        <filter id={filterId} colorInterpolationFilters="sRGB">
          <feColorMatrix type="matrix" values="-1 0 0 0 1  0 -1 0 0 1  0 0 -1 0 1  0 0 0 1 0" />
        </filter>
        <filter id={alphaFilterId}>
          <feComponentTransfer><feFuncA type="table" tableValues="1 0" /></feComponentTransfer>
        </filter>
        <clipPath id={clipId}><rect x="4.5" y="3.5" width="13.5" height="17" /></clipPath>
        <mask id={maskId} style={{ maskType: destination.logoWhiteBackground ? "luminance" : "alpha" }}>
          <g clipPath={destination.logoNegativeSymbol ? `url(#${clipId})` : undefined}>
            <image href={destination.logo} width="24" height="24" filter={destination.logoWhiteBackground ? `url(#${filterId})` : destination.logoNegativeSymbol ? `url(#${alphaFilterId})` : undefined} />
          </g>
        </mask>
      </defs>
      <rect width="24" height="24" fill="currentColor" mask={`url(#${maskId})`} />
    </svg>
  )
}

function QrFormatSelector({ fixedCode }: { fixedCode: boolean }) {
  const { t } = useTranslation()
  const qrFormat = usePosterStore((s) => s.qrFormat)
  const setQrFormat = usePosterStore((s) => s.setQrFormat)
  const [wechatAvailable, setWechatAvailable] = useState<boolean | null>(null)

  useEffect(() => {
    const controller = new AbortController()
    fetchCapabilities(controller.signal)
      .then((data) => setWechatAvailable(data.wechat_qr === true))
      .catch(() => { if (!controller.signal.aborted) setWechatAvailable(false) })
    return () => controller.abort()
  }, [])

  useEffect(() => {
    if (wechatAvailable === false && qrFormat === "wechat") setQrFormat("standard")
  }, [wechatAvailable, qrFormat, setQrFormat])

  if (!fixedCode && wechatAvailable !== true) return null

  return (
    <FieldSet>
      <FieldLegend>{t("poster.listenCodeType")}</FieldLegend>
      {fixedCode ? (
        <p className="text-sm text-muted-foreground">{t("poster.spotifyCodeHelp")}</p>
      ) : (
        <ToggleGroup
          value={[qrFormat]}
          onValueChange={(values) => { if (values[0]) setQrFormat(values[0] as QrFormat) }}
          variant="default"
          className="grid w-full grid-cols-2 items-stretch max-sm:grid-cols-1"
        >
          {([
            { value: "standard", title: t("poster.qrFormatStandard"), description: t("poster.qrFormatStandardHelp") },
            { value: "wechat", title: t("poster.qrFormatWechat"), description: t("poster.qrFormatWechatHelp") },
          ] as const).map((option) => (
            <ToggleGroupItem key={option.value} value={option.value} className="h-auto min-h-18 w-full items-start justify-start gap-3 px-3 py-3 text-left whitespace-normal">
              <span aria-hidden="true" className={qrFormat === option.value ? "mt-1 size-3.5 shrink-0 rounded-full border-4 border-primary" : "mt-1 size-3.5 shrink-0 rounded-full border border-muted-foreground"} />
              <span className="flex flex-col gap-1">
                <span>{option.title}</span>
                <span className="text-xs leading-relaxed font-normal text-muted-foreground">{option.description}</span>
              </span>
            </ToggleGroupItem>
          ))}
        </ToggleGroup>
      )}
    </FieldSet>
  )
}
