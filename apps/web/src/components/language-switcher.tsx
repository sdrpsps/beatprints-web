import { LanguagesIcon } from "lucide-react"
import { useTranslation } from "react-i18next"

import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  languageOptions,
  normalizeLanguage,
  type SupportedLanguage,
} from "@/i18n/resources"

export function LanguageSwitcher() {
  const { i18n, t } = useTranslation()
  const language = normalizeLanguage(i18n.resolvedLanguage ?? i18n.language)

  return (
    <Select
      items={languageOptions}
      value={language}
      onValueChange={(value) => {
        if (value) void i18n.changeLanguage(value as SupportedLanguage)
      }}
    >
      <SelectTrigger
        size="sm"
        aria-label={t("language.selectorLabel")}
      >
        <LanguagesIcon aria-hidden="true" />
        <SelectValue />
      </SelectTrigger>
      <SelectContent align="end" alignItemWithTrigger={false}>
        <SelectGroup>
          {languageOptions.map((option) => (
            <SelectItem key={option.value} value={option.value}>
              {option.label}
            </SelectItem>
          ))}
        </SelectGroup>
      </SelectContent>
    </Select>
  )
}
