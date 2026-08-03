// This is the complete frontend enablement list. Comment one import to remove
// that destination from the picker and its generic matching flow.
import "@/features/poster/destinations/spotify"
import "@/features/poster/destinations/apple-music"
import "@/features/poster/destinations/qq-music"
import "@/features/poster/destinations/netease-music"

export {
  enabledDestinations,
  getDestination,
} from "@/features/poster/destinations/store"
