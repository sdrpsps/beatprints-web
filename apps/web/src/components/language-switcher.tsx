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
import { homeContent } from "@/i18n/home"
import { languageStorageKey } from "@/i18n/detection"
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
        if (value) {
          const next = value as SupportedLanguage
          try {
            window.localStorage.setItem(languageStorageKey, next)
          } catch {
            // The selected URL still preserves the choice when storage is unavailable.
          }
          window.history.pushState(null, "", `${homeContent[next].path}${window.location.search}${window.location.hash}`)
          void i18n.changeLanguage(next)
        }
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
