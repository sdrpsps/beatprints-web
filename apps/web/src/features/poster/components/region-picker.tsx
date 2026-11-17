import { useMemo, useRef, useState } from "react"
import { SearchIcon } from "lucide-react"
import { useTranslation } from "react-i18next"

import { Button } from "@/components/ui/button"
import {
  Combobox,
  ComboboxContent,
  ComboboxEmpty,
  ComboboxInput,
  ComboboxTrigger,
} from "@/components/ui/combobox"
import { InputGroupAddon } from "@/components/ui/input-group"
import { Separator } from "@/components/ui/separator"
import { RegionList, type Region, type RegionVirtualizer } from "@/features/poster/components/region-list"

export function RegionPicker({ value, onChange, disabled, platform, className, regionCodes }: {
  value: string
  regionCodes: string[]
  onChange: (region: string) => void
  disabled?: boolean
  platform: string
  className?: string
}) {
  const { t, i18n } = useTranslation()
  const [open, setOpen] = useState(false)
  const virtualizerRef = useRef<RegionVirtualizer | null>(null)
  const regions = useMemo(() => {
    const locale = i18n.resolvedLanguage || "en"
    const names = new Intl.DisplayNames([locale], { type: "region" })
    const english = new Intl.DisplayNames(["en"], { type: "region" })
    return regionCodes.map((code) => {
      const flag = String.fromCodePoint(...[...code].map((char) => char.charCodeAt(0) + 127397))
      const name = names.of(code) ?? code
      return { code, flag, name, label: `${flag} ${name} (${code})`, search: `${name} ${english.of(code)} ${code}` }
    }).sort((a, b) => a.name.localeCompare(b.name, locale))
  }, [i18n.resolvedLanguage, regionCodes])
  const selected = regions.find((region) => region.code === value) ?? null

  return (
    <Combobox virtualized items={regions} open={open} onOpenChange={setOpen} value={selected} onValueChange={(region: Region | null) => { if (region) onChange(region.code) }}
      onItemHighlighted={(region, { reason, index }) => {
        const virtualizer = virtualizerRef.current
        if (!region || !virtualizer) return
        const isEnd = index === virtualizer.options.count - 1
        if (reason === "none" || (reason === "keyboard" && (index === 0 || isEnd))) {
          queueMicrotask(() => virtualizer.scrollToIndex(index, { align: isEnd ? "start" : "end" }))
        }
      }}
      itemToStringLabel={(region: Region) => region.label}
      isItemEqualToValue={(a: Region, b: Region) => a.code === b.code}
      filter={(region, query) => region.search.toLocaleLowerCase().includes(query.trim().toLocaleLowerCase())}>
      <ComboboxTrigger
        render={<Button type="button" variant="outline" size="sm" className={className} />}
        aria-label={`${t("poster.regionFor", { platform })}: ${selected?.label ?? value}`}
        disabled={disabled}
        title={`${t("poster.regionFor", { platform })}: ${selected?.name ?? value}`}
        className="[&>svg]:hidden"
      >
        <span aria-hidden="true" className="text-base leading-none">{selected?.flag}</span>
      </ComboboxTrigger>
      <ComboboxContent className="flex w-72 flex-col rounded-xl shadow-lg" align="end" sideOffset={8}>
        <div className="shrink-0 px-4 pt-4 pb-3">
          <span className="text-sm font-medium">{t("poster.regionChoose")}</span>
        </div>
        <div className="shrink-0 px-3 pb-3">
          <ComboboxInput aria-label={t("poster.regionFor", { platform })} placeholder={t("poster.regionSearch")} showTrigger={false} className="w-full">
            <InputGroupAddon align="inline-start"><SearchIcon aria-hidden="true" /></InputGroupAddon>
          </ComboboxInput>
        </div>
        <Separator />
        <ComboboxEmpty className="px-4 py-6 text-center text-sm text-muted-foreground">{t("poster.regionEmpty")}</ComboboxEmpty>
        <RegionList open={open} virtualizerRef={virtualizerRef} />
      </ComboboxContent>
    </Combobox>
  )
}
