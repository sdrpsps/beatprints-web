import type { IntegrationLabelKey } from "@/features/poster/integration-labels"

type Presentation = {
  key: string
  labelKey: IntegrationLabelKey
  logo?: string
  logoWhiteBackground?: boolean
  logoNegativeSymbol?: boolean
}

// These modules supply presentation only; the backend decides which keys exist.
const catalogs = import.meta.glob<Presentation>(["./catalogs/*.ts", "!./catalogs/types.ts"], { eager: true, import: "default" })
const lyrics = import.meta.glob<Presentation>(["./lyrics/*.ts", "!./lyrics/types.ts"], { eager: true, import: "default" })
const destinations = import.meta.glob<Presentation>(["./destinations/*.ts", "!./destinations/types.ts"], { eager: true, import: "default" })

function find(modules: Record<string, Presentation>, key: string) {
  return Object.values(modules).find((item) => item?.key === key)
}

export const catalogPresentation = (key: string) => find(catalogs, key)
export const lyricsPresentation = (key: string) => find(lyrics, key)
export const destinationPresentation = (key: string) => find(destinations, key)
