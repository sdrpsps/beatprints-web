import { useTranslation } from "react-i18next"
import {
  Field,
  FieldDescription,
  FieldGroup,
  FieldLabel,
  FieldTitle,
} from "@/components/ui/field"
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Switch } from "@/components/ui/switch"
import {
  SectionHeading,
  studioSectionClass,
} from "@/features/poster/components/studio-shared"
import { usePosterStore } from "@/features/poster/poster-store"
import type { Theme } from "@/features/poster/types"

export function AppearanceSection() {
  const { t } = useTranslation()
  const kind = usePosterStore((s) => s.kind)
  const selected = usePosterStore((s) => s.selected)
  const accent = usePosterStore((s) => s.accent)
  const setAccent = usePosterStore((s) => s.setAccent)
  const indexing = usePosterStore((s) => s.indexing)
  const setIndexing = usePosterStore((s) => s.setIndexing)
  const shuffle = usePosterStore((s) => s.shuffle)
  const setShuffle = usePosterStore((s) => s.setShuffle)

  if (!selected) return null

  return (
    <section className={studioSectionClass}>
      <SectionHeading
        number={kind === "track" ? "04" : "03"}
        title={t("poster.appearance")}
        description={t("poster.appearanceHelp")}
      />
      <FieldGroup>
        <ThemeField />
        <OptionSwitch
          id="accent"
          title={t("poster.accentTitle")}
          description={t("poster.accentDescription")}
          checked={accent}
          onChange={setAccent}
        />
        {kind === "album" ? (
          <>
            <OptionSwitch
              id="indexing"
              title={t("poster.indexingTitle")}
              description={t("poster.indexingDescription")}
              checked={indexing}
              onChange={setIndexing}
            />
            <OptionSwitch
              id="shuffle"
              title={t("poster.shuffleTitle")}
              description={t("poster.shuffleDescription")}
              checked={shuffle}
              onChange={setShuffle}
            />
          </>
        ) : null}
      </FieldGroup>
    </section>
  )
}

function ThemeField() {
  const { t } = useTranslation()
  const theme = usePosterStore((s) => s.theme)
  const setTheme = usePosterStore((s) => s.setTheme)

  const themeItems = [
    { value: "Light", label: t("poster.themeLight") },
    { value: "Dark", label: t("poster.themeDark") },
    { value: "Catppuccin", label: "Catppuccin" },
    { value: "Gruvbox", label: "Gruvbox" },
    { value: "Nord", label: "Nord" },
    { value: "RosePine", label: "Rosé Pine" },
    { value: "Everforest", label: "Everforest" },
  ] satisfies { value: Theme; label: string }[]

  return (
    <Field orientation="responsive">
      <FieldTitle>{t("poster.posterTheme")}</FieldTitle>
      <Select
        items={themeItems}
        value={theme}
        onValueChange={(value) => value && setTheme(value as Theme)}
      >
        <SelectTrigger>
          <SelectValue />
        </SelectTrigger>
        <SelectContent alignItemWithTrigger={false}>
          <SelectGroup>
            {themeItems.map((item) => (
              <SelectItem key={item.value} value={item.value}>
                {item.label}
              </SelectItem>
            ))}
          </SelectGroup>
        </SelectContent>
      </Select>
    </Field>
  )
}

function OptionSwitch({
  id,
  title,
  description,
  checked,
  onChange,
}: {
  id: string
  title: string
  description: string
  checked: boolean
  onChange: (value: boolean) => void
}) {
  return (
    <Field orientation="horizontal">
      <FieldLabel htmlFor={id}>
        <FieldTitle>{title}</FieldTitle>
        <FieldDescription>{description}</FieldDescription>
      </FieldLabel>
      <Switch id={id} checked={checked} onCheckedChange={onChange} />
    </Field>
  )
}
