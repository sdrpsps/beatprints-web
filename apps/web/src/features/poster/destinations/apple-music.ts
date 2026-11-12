import { registerDestination } from "@/features/poster/destinations/store"
import logo from "@/features/poster/destinations/assets/apple-music-symbol.png"

registerDestination({
  key: "apple_music",
  logo,
  logoNegativeSymbol: true,
  labelKey: "poster.integrationNames.appleMusic",
  order: 3,
  default: false,
  domains: ["music.apple.com"],
  reusesSourceLink: () => false,
})
