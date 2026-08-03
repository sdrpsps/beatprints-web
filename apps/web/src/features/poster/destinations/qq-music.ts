import { registerDestination } from "@/features/poster/destinations/store"

registerDestination({
  key: "qq_music",
  label: "QQ 音乐",
  default: false,
  domains: ["y.qq.com", "qq.com"],
  reusesSourceLink: () => false,
})
