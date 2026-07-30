import "i18next"

import type { defaultLanguage, resources } from "@/i18n/resources"

declare module "i18next" {
  interface CustomTypeOptions {
    defaultNS: "translation"
    fallbackNS: "translation"
    resources: (typeof resources)[typeof defaultLanguage]
  }
}
