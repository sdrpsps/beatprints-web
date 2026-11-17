import type { CatalogProvider } from "@/features/poster/types"
import type { IntegrationLabelKey } from "@/features/poster/integration-labels"

export type PosterDestination = {
  key: string
  labelKey: IntegrationLabelKey
  label?: string
  available?: boolean
  supportsRegions?: boolean
  regions?: string[]
  reusesSourceLink?: (provider: CatalogProvider) => boolean
  fixedCode?: boolean
  logo?: string
  logoWhiteBackground?: boolean
  logoNegativeSymbol?: boolean
}
