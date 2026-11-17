import { convertDetectedLanguage } from "@/i18n/resources"

export const languageStorageKey = "beatprints.language"

// Explicit URLs and saved choices take precedence over browser preferences.
// Cache only explicit choices, so automatic detection follows the browser.
export const languageDetection = {
  order: ["path", "localStorage", "navigator"],
  lookupFromPathIndex: 0,
  lookupLocalStorage: languageStorageKey,
  caches: [],
  convertDetectedLanguage,
}
