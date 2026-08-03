// This is the complete frontend enablement list for source catalogs.
// Commenting one import removes it from the picker without changing the flow.
import "@/features/poster/catalogs/spotify"
import "@/features/poster/catalogs/deezer"

export {
  enabledCatalogSources,
  getCatalogSource,
} from "@/features/poster/catalogs/store"
