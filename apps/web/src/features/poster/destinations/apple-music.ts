import { registerDestination } from "@/features/poster/destinations/store"

registerDestination({
  key: "apple_music",
  labelKey: "poster.integrationNames.appleMusic",
  default: false,
  domains: ["music.apple.com"],
  reusesSourceLink: () => false,
})
