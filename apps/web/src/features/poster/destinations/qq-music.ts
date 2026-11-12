import { registerDestination } from "@/features/poster/destinations/store"
import logo from "@/features/poster/destinations/assets/qq-music-symbol.png"

registerDestination({
  key: "qq_music",
  logo,
  logoWhiteBackground: true,
  labelKey: "poster.integrationNames.qqMusic",
  order: 0,
  default: false,
  domains: ["y.qq.com", "qq.com"],
  reusesSourceLink: (provider) => provider === "qq_music",
})
