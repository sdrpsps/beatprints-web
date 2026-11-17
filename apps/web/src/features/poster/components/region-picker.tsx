import { useMemo } from "react"
import { SearchIcon } from "lucide-react"
import { useTranslation } from "react-i18next"

import { Button } from "@/components/ui/button"
import {
  Combobox,
  ComboboxContent,
  ComboboxEmpty,
  ComboboxInput,
  ComboboxItem,
  ComboboxList,
  ComboboxTrigger,
} from "@/components/ui/combobox"
import { InputGroupAddon } from "@/components/ui/input-group"
import { Separator } from "@/components/ui/separator"

type Region = { code: string; flag: string; name: string; label: string; search: string }

export function RegionPicker({ value, onChange, disabled, platform, className, regionCodes }: {
  value: string
  regionCodes: string[]
  onChange: (region: string) => void
  disabled?: boolean
  platform: string
  className?: string
}) {
  const { t, i18n } = useTranslation()
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
    <Combobox items={regions} value={selected} onValueChange={(region: Region | null) => { if (region) onChange(region.code) }}
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
        <ComboboxList className="min-h-0 max-h-64 p-2 [scrollbar-width:thin]! [scrollbar-color:var(--muted-foreground)_transparent] [&::-webkit-scrollbar]:block! [&::-webkit-scrollbar]:w-2 [&::-webkit-scrollbar-thumb]:rounded-full [&::-webkit-scrollbar-thumb]:border-2 [&::-webkit-scrollbar-thumb]:border-solid [&::-webkit-scrollbar-thumb]:border-transparent [&::-webkit-scrollbar-thumb]:bg-muted-foreground/50 [&::-webkit-scrollbar-thumb]:bg-clip-padding">
          {(region: Region) => (
            <ComboboxItem key={region.code} value={region} className="min-h-10 gap-3 py-2 pr-9 pl-2.5 data-selected:bg-secondary/60">
              <span aria-hidden="true" className="w-6 shrink-0 text-center text-lg leading-none">{region.flag}</span>
              <span className="min-w-0 flex-1 truncate">{region.name}</span>
              <span className="font-utility text-[0.65rem] tracking-wide text-muted-foreground">{region.code}</span>
            </ComboboxItem>
          )}
        </ComboboxList>
      </ComboboxContent>
    </Combobox>
  )
}
