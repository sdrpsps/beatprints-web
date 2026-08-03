import { registerDestination } from "@/features/poster/destinations/store"

registerDestination({
  key: "netease_music",
  label: "网易云",
  domains: ["music.163.com", "163.com"],
  reusesSourceLink: () => false,
})
