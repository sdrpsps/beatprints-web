import { CheckIcon, Disc3Icon } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import {
  Empty,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty"
import {
  Item,
  ItemActions,
  ItemContent,
  ItemDescription,
  ItemGroup,
  ItemMedia,
  ItemTitle,
} from "@/components/ui/item"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Skeleton } from "@/components/ui/skeleton"
import { CoverArt } from "@/features/poster/components/studio-shared"
import type { SearchResult } from "@/features/poster/types"
import { cn } from "@/lib/utils"

export function SearchSkeleton() {
  return (
    <div className="flex flex-col gap-2.5" aria-label="正在加载搜索结果">
      {[0, 1, 2].map((value) => (
        <div
          className="flex items-center gap-3 rounded-lg border p-2.5"
          key={value}
        >
          <Skeleton className="size-16" />
          <div className="flex flex-1 flex-col gap-[9px]">
            <Skeleton className="h-4 w-2/3" />
            <Skeleton className="h-3 w-1/2" />
          </div>
        </div>
      ))}
    </div>
  )
}

export function CatalogResultList({
  results,
  selected,
  onSelect,
}: {
  results: SearchResult[]
  selected?: SearchResult
  onSelect: (result: SearchResult) => void
}) {
  if (results.length === 0) {
    return (
      <Empty>
        <EmptyHeader>
          <EmptyMedia variant="icon">
            <Disc3Icon />
          </EmptyMedia>
          <EmptyTitle>没有找到匹配的作品</EmptyTitle>
          <EmptyDescription>
            试试“歌名 + 歌手”，或切换搜索来源。
          </EmptyDescription>
        </EmptyHeader>
      </Empty>
    )
  }

  return (
    <ScrollArea
      className={cn(
        "result-scroll [&_[data-slot=scroll-area-viewport]]:overscroll-contain",
        results.length > 4 && "h-[400px]",
      )}
    >
      <ItemGroup
        className={cn(results.length > 4 && "pr-3")}
        aria-label="搜索结果"
      >
        {results.map((result) => (
          <CatalogResult
            key={`${result.provider}-${result.id}`}
            result={result}
            selected={
              selected?.id === result.id &&
              selected.provider === result.provider
            }
            onSelect={onSelect}
          />
        ))}
      </ItemGroup>
    </ScrollArea>
  )
}

function CatalogResult({
  result,
  selected,
  onSelect,
}: {
  result: SearchResult
  selected: boolean
  onSelect: (result: SearchResult) => void
}) {
  const details = [
    result.album?.title,
    result.release_year,
    result.duration,
    result.track_count ? `${result.track_count} 首` : undefined,
  ]
    .filter(Boolean)
    .join(" · ")

  return (
    <Item
      render={
        <button
          className="cursor-pointer text-start"
          type="button"
          aria-pressed={selected}
          onClick={() => onSelect(result)}
        />
      }
      variant={selected ? "muted" : "outline"}
    >
      <ItemMedia variant="image" className="size-16">
        <CoverArt result={result} />
      </ItemMedia>
      <ItemContent>
        <ItemTitle>
          {result.title}
          {result.explicit ? <Badge variant="outline">E</Badge> : null}
        </ItemTitle>
        <ItemDescription>{result.artists.join("、")}</ItemDescription>
        <ItemDescription>{details}</ItemDescription>
      </ItemContent>
      <ItemActions className="max-sm:basis-full max-sm:justify-end">
        <Badge variant={selected ? "default" : "secondary"}>
          {selected ? <CheckIcon data-icon="inline-start" /> : null}
          {result.provider === "spotify" ? "Spotify" : "Deezer"}
        </Badge>
      </ItemActions>
    </Item>
  )
}
