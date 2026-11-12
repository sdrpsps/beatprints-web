import { registerDestination } from "@/features/poster/destinations/store"
import logo from "@/features/poster/destinations/assets/spotify-symbol.png"

registerDestination({
  key: "spotify",
  logo,
  labelKey: "poster.integrationNames.spotify",
  order: 2,
  default: true,
  fixedCode: true,
  domains: ["spotify.com"],
  reusesSourceLink: (provider) => provider === "spotify",
})
