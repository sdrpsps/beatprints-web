import { registerDestination } from "@/features/poster/destinations/store"
import logo from "@/features/poster/destinations/assets/netease-music-symbol.png"

registerDestination({
  key: "netease_music",
  logo,
  logoWhiteBackground: true,
  labelKey: "poster.integrationNames.neteaseMusic",
  order: 1,
  default: false,
  domains: ["music.163.com", "163.com"],
  reusesSourceLink: (provider) => provider === "netease_music",
})
