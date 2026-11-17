import i18n from "i18next"
import LanguageDetector from "i18next-browser-languagedetector"
import { initReactI18next } from "react-i18next"

import { languageDetection } from "@/i18n/detection"
import { homeContent, languageFromPath } from "@/i18n/home"
import {
  defaultLanguage,
  normalizeLanguage,
  resources,
  supportedLanguages,
} from "@/i18n/resources"

void i18n.use(LanguageDetector).use(initReactI18next).init({
  resources,
  supportedLngs: supportedLanguages,
  fallbackLng: defaultLanguage,
  load: "currentOnly",
  detection: languageDetection,
  interpolation: { escapeValue: false },
  react: { useSuspense: false },
})

function syncDocumentLanguage(language: string) {
  const locale = normalizeLanguage(language)
  document.documentElement.lang = locale
  const robots = document.querySelector('meta[name="robots"]')
  robots?.setAttribute("content", window.location.pathname === "/"
    ? "index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1"
    : "noindex, follow")
}

// The unprefixed English homepage remains the crawlable entry point. Visitors
// with another preference get an address that matches the language they see.
const initialLanguage = normalizeLanguage(i18n.resolvedLanguage ?? i18n.language)
if (window.location.pathname === "/" && initialLanguage !== "en") {
  window.history.replaceState(null, "", `${homeContent[initialLanguage].path}${window.location.search}${window.location.hash}`)
}
syncDocumentLanguage(initialLanguage)
i18n.on("languageChanged", syncDocumentLanguage)
window.addEventListener("popstate", () => {
  const locale = languageFromPath(window.location.pathname)
  void i18n.changeLanguage(locale ?? defaultLanguage)
})

export default i18n
