import { en } from "@/i18n/locales/en"
import { zhCN } from "@/i18n/locales/zh-CN"
import { zhTW } from "@/i18n/locales/zh-TW"

export const defaultLanguage = "zh-CN"

export const supportedLanguages = ["zh-CN", "zh-TW", "en"] as const

export type SupportedLanguage = (typeof supportedLanguages)[number]

export const languageOptions = [
  { value: "zh-CN", label: "简体中文" },
  { value: "zh-TW", label: "繁體中文" },
  { value: "en", label: "English" },
] satisfies { value: SupportedLanguage; label: string }[]

export const resources = {
  "zh-CN": { translation: zhCN },
  "zh-TW": { translation: zhTW },
  en: { translation: en },
} as const

export function normalizeLanguage(language?: string): SupportedLanguage {
  const normalized = language?.toLowerCase().replace("_", "-")

  if (normalized === "zh-tw" || normalized === "zh-hk" || normalized === "zh-hant") {
    return "zh-TW"
  }
  if (normalized?.startsWith("en")) {
    return "en"
  }
  return defaultLanguage
}
