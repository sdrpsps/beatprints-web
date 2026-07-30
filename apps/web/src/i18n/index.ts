import i18n from "i18next"
import LanguageDetector from "i18next-browser-languagedetector"
import { initReactI18next } from "react-i18next"

import {
  defaultLanguage,
  normalizeLanguage,
  resources,
  supportedLanguages,
} from "@/i18n/resources"

export const languageStorageKey = "beatprints.language"

void i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources,
    supportedLngs: supportedLanguages,
    fallbackLng: defaultLanguage,
    load: "currentOnly",
    interpolation: {
      escapeValue: false,
    },
    detection: {
      order: ["localStorage", "navigator"],
      caches: ["localStorage"],
      lookupLocalStorage: languageStorageKey,
      convertDetectedLanguage: normalizeLanguage,
    },
    react: {
      useSuspense: false,
    },
  })

function syncDocumentLanguage(language: string) {
  document.documentElement.lang = normalizeLanguage(language)
}

syncDocumentLanguage(i18n.resolvedLanguage ?? i18n.language)
i18n.on("languageChanged", syncDocumentLanguage)

export default i18n
