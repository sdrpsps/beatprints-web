import { registerDestination } from "@/features/poster/destinations/store"

registerDestination({
  key: "apple_music",
  label: "Apple Music",
  default: false,
  domains: ["music.apple.com"],
  reusesSourceLink: () => false,
})
