import type { CatalogProvider } from "@/features/poster/types"

export type PosterDestination = {
  key: string
  label: string
  domains: string[]
  reusesSourceLink: (provider: CatalogProvider) => boolean
}
