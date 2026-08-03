import { registerDestination } from "@/features/poster/destinations/store"

registerDestination({
  key: "qq_music",
  labelKey: "poster.integrationNames.qqMusic",
  order: 0,
  default: false,
  domains: ["y.qq.com", "qq.com"],
  reusesSourceLink: (provider) => provider === "qq_music",
})
