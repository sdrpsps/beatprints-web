import { registerDestination } from "@/features/poster/destinations/store"

registerDestination({
  key: "spotify",
  label: "Spotify",
  default: true,
  domains: ["spotify.com"],
  reusesSourceLink: (provider) => provider === "spotify",
})
