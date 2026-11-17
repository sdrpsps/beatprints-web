import { en } from "@/i18n/locales/en"
import { ja } from "@/i18n/locales/ja"
import { ko } from "@/i18n/locales/ko"
import { zhCN } from "@/i18n/locales/zh-CN"
import { zhTW } from "@/i18n/locales/zh-TW"

export const defaultLanguage = "en"

export const supportedLanguages = ["zh-CN", "zh-TW", "en", "ja", "ko"] as const

export type SupportedLanguage = (typeof supportedLanguages)[number]

export const languageOptions = [
  { value: "zh-CN", label: "简体中文" },
  { value: "zh-TW", label: "繁體中文" },
  { value: "en", label: "English" },
  { value: "ja", label: "日本語" },
  { value: "ko", label: "한국어" },
] satisfies { value: SupportedLanguage; label: string }[]

export const resources = {
  "zh-CN": { translation: zhCN },
  "zh-TW": { translation: zhTW },
  en: { translation: en },
  ja: { translation: ja },
  ko: { translation: ko },
} as const

// Keep unknown languages intact so the detector can try the next browser preference.
export function convertDetectedLanguage(language: string): string {
  const normalized = language.toLowerCase().replaceAll("_", "-")
  if (/^zh-(tw|hk|mo|hant)(-|$)/.test(normalized)) return "zh-TW"
  if (normalized === "zh" || normalized.startsWith("zh-")) return "zh-CN"
  if (normalized === "en" || normalized.startsWith("en-")) return "en"
  if (normalized === "ja" || normalized.startsWith("ja-")) return "ja"
  if (normalized === "ko" || normalized.startsWith("ko-")) return "ko"
  return language
}

export function normalizeLanguage(language?: string): SupportedLanguage {
  const converted = convertDetectedLanguage(language ?? "")
  return supportedLanguages.find((supported) => supported === converted) ?? defaultLanguage
}
