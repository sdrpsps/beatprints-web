import type { ReactNode } from "react"
import { useTranslation } from "react-i18next"

import {
  Item,
  ItemActions,
  ItemContent,
  ItemDescription,
  ItemMedia,
  ItemTitle,
} from "@/components/ui/item"
import { CoverArt } from "@/features/poster/components/studio-shared"
import type { PlatformLinkMatch, SearchResult } from "@/features/poster/types"

type PlatformItemCardProps = {
  match: PlatformLinkMatch
  source: SearchResult
  platform: string
  actions: ReactNode
}

export function PlatformItemCard({
  match,
  source,
  platform,
  actions,
}: PlatformItemCardProps) {
  const { t } = useTranslation()
  const context = formatPlatformContext(match, t)

  return (
    <Item variant="outline">
      <ItemMedia variant="image" className="size-16">
        {match.cover_url ? (
          <img
            src={match.cover_url}
            alt={t("poster.platformCoverAlt", { title: match.title, platform })}
          />
        ) : (
          <CoverArt result={source} />
        )}
      </ItemMedia>
      <ItemContent>
        <ItemTitle>{match.title}</ItemTitle>
        <ItemDescription>{match.artists.join("、")}</ItemDescription>
        {context ? <ItemDescription>{context}</ItemDescription> : null}
      </ItemContent>
      <ItemActions className="max-sm:basis-full max-sm:justify-end">
        {actions}
      </ItemActions>
    </Item>
  )
}

function formatPlatformContext(
  match: PlatformLinkMatch,
  t: ReturnType<typeof useTranslation>["t"],
) {
  return (
    match.type === "album"
      ? [
          match.release_year,
          match.track_count
            ? `${match.track_count} ${t("poster.trackCountUnit")}`
            : undefined,
        ]
      : [
          match.album,
          match.release_year,
          formatDuration(match.duration_seconds),
        ]
  )
    .filter(Boolean)
    .join(" · ")
}

function formatDuration(seconds?: number) {
  if (!seconds) return undefined
  return `${Math.floor(seconds / 60)}:${(seconds % 60)
    .toString()
    .padStart(2, "0")}`
}
