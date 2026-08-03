import { registerDestination } from "@/features/poster/destinations/store"

registerDestination({
  key: "spotify",
  labelKey: "poster.integrationNames.spotify",
  order: 2,
  default: true,
  domains: ["spotify.com"],
  reusesSourceLink: (provider) => provider === "spotify",
})
