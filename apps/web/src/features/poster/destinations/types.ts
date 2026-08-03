import type { CatalogProvider } from "@/features/poster/types"
import type { IntegrationLabelKey } from "@/features/poster/integration-labels"

export type PosterDestination = {
  key: string
  labelKey: IntegrationLabelKey
  order: number
  default: boolean
  domains: string[]
  reusesSourceLink: (provider: CatalogProvider) => boolean
}
