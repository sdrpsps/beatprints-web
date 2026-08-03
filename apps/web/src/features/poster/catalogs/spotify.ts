import { registerCatalogSource } from "@/features/poster/catalogs/store"

registerCatalogSource({
  key: "spotify",
  labelKey: "poster.integrationNames.spotify",
  default: false,
})
