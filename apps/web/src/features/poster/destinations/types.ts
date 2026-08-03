import type { CatalogProvider } from "@/features/poster/types"

export type PosterDestination = {
  key: string
  label: string
  default: boolean
  domains: string[]
  reusesSourceLink: (provider: CatalogProvider) => boolean
}
