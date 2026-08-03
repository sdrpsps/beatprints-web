import { registerDestination } from "@/features/poster/destinations/store"

registerDestination({
  key: "spotify",
  label: "Spotify",
  domains: ["spotify.com"],
  reusesSourceLink: (provider) => provider === "spotify",
})
