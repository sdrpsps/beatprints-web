import type { IntegrationLabelKey } from "@/features/poster/integration-labels"

export type CatalogSource = {
  key: string
  labelKey: IntegrationLabelKey
  default: boolean
}
