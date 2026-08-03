import { CheckIcon, Disc3Icon } from "lucide-react"
import { useTranslation } from "react-i18next"

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
import { getCatalogSource } from "@/features/poster/catalogs/registry"
import type { SearchResult } from "@/features/poster/types"
import { cn } from "@/lib/utils"

export function SearchSkeleton() {
  const { t } = useTranslation()
  return (
    <div
      className="flex flex-col gap-2.5"
      aria-label={t("poster.loadingSearchResults")}
    >
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
  const { t } = useTranslation()

  if (results.length === 0) {
    return (
      <Empty>
        <EmptyHeader>
          <EmptyMedia variant="icon">
            <Disc3Icon />
          </EmptyMedia>
          <EmptyTitle>{t("poster.noResultsTitle")}</EmptyTitle>
          <EmptyDescription>
            {t("poster.noResultsDescription")}
          </EmptyDescription>
        </EmptyHeader>
      </Empty>
    )
  }

  return (
    <ScrollArea
      className={cn(
        "editorial-scroll result-scroll overflow-hidden rounded-lg border bg-card/25 [&_[data-slot=scroll-area-viewport]]:overscroll-contain",
        results.length > 4 && "h-[400px]",
      )}
    >
      <ItemGroup
        className="gap-2.5 p-2.5 pr-4"
        aria-label={t("poster.searchResults")}
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
  const { t } = useTranslation()
  const details = [
    result.album?.title,
    result.release_year,
    result.duration,
    result.track_count
      ? `${result.track_count} ${t("poster.trackCountUnit")}`
      : undefined,
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
          {getCatalogSource(result.provider)?.label ?? result.provider}
        </Badge>
      </ItemActions>
    </Item>
  )
}
