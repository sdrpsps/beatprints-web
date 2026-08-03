import { registerDestination } from "@/features/poster/destinations/store"

registerDestination({
  key: "netease_music",
  labelKey: "poster.integrationNames.neteaseMusic",
  default: false,
  domains: ["music.163.com", "163.com"],
  reusesSourceLink: () => false,
})
