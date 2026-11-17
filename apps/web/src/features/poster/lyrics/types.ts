import type { IntegrationLabelKey } from "@/features/poster/integration-labels"

export type LyricsSource = {
  key: string
  labelKey: IntegrationLabelKey
  label?: string
  available?: boolean
  default: boolean
}
