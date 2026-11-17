import type { IntegrationLabelKey } from "@/features/poster/integration-labels"

export type CatalogSource = {
  key: string
  labelKey: IntegrationLabelKey
  label?: string
  available?: boolean
  supportsRegions?: boolean
  regions?: string[]
}
