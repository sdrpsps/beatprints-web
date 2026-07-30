import type { FormEvent } from "react"
import { AlertCircleIcon, SearchIcon } from "lucide-react"

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Field, FieldGroup, FieldLabel, FieldTitle } from "@/components/ui/field"
import {
  InputGroup,
  InputGroupAddon,
  InputGroupButton,
  InputGroupInput,
} from "@/components/ui/input-group"
import {
  ToggleGroup,
  ToggleGroupItem,
} from "@/components/ui/toggle-group"
import { Spinner } from "@/components/ui/spinner"
import {
  CatalogResultList,
  SearchSkeleton,
} from "@/features/poster/components/catalog-result-list"
import {
  SectionHeading,
  studioSectionClass,
  type Studio,
} from "@/features/poster/components/studio-shared"
import { zhCN } from "@/features/poster/copy"
import type { CatalogProvider } from "@/features/poster/types"
import { cn } from "@/lib/utils"

const providerItems = [
  { value: "deezer", label: "Deezer" },
  { value: "spotify", label: "Spotify" },
] satisfies { value: CatalogProvider; label: string }[]

export function SearchSection({ studio }: { studio: Studio }) {
  const onSubmit = (event: FormEvent) => {
    event.preventDefault()
    void studio.search()
  }

  return (
    <section
      className={cn(
        studioSectionClass,
        !studio.selected && "border-b-0 pb-0",
      )}
    >
      <SectionHeading
        number="01"
        title={zhCN.selectWork}
        description={
          studio.kind === "track"
            ? "输入歌名、歌手或专辑，找到准确的录音版本。"
            : "输入专辑名或歌手，确认发行版本。"
        }
      />
      <form onSubmit={onSubmit}>
        <FieldGroup>
          <Field>
            <FieldLabel htmlFor="catalog-search" className="sr-only">
              {studio.kind === "track" ? zhCN.searchTrack : zhCN.searchAlbum}
            </FieldLabel>
            <InputGroup className="min-h-11">
              <InputGroupAddon>
                <SearchIcon aria-hidden="true" />
              </InputGroupAddon>
              <InputGroupInput
                id="catalog-search"
                value={studio.query}
                onChange={(event) => studio.setQuery(event.target.value)}
                placeholder={
                  studio.kind === "track"
                    ? "例如：Best Things in Life The Dreamliners"
                    : "例如：Summer Breeze Piper"
                }
                autoComplete="off"
              />
              <InputGroupAddon align="inline-end">
                <InputGroupButton
                  type="submit"
                  variant="default"
                  size="sm"
                  disabled={!studio.query.trim() || studio.searchState === "loading"}
                >
                  {studio.searchState === "loading" ? (
                    <Spinner data-icon="inline-start" />
                  ) : (
                    <SearchIcon data-icon="inline-start" />
                  )}
                  {studio.searchState === "loading" ? zhCN.searching : zhCN.search}
                </InputGroupButton>
              </InputGroupAddon>
            </InputGroup>
          </Field>
          {studio.searchState !== "idle" ? (
            <SourceFilter studio={studio} />
          ) : null}
        </FieldGroup>
      </form>
      <SearchFeedback studio={studio} />
    </section>
  )
}

function SourceFilter({ studio }: { studio: Studio }) {
  return (
    <Field orientation="horizontal" className="justify-end">
      <FieldTitle>{zhCN.source}</FieldTitle>
      <ToggleGroup
        value={[studio.provider]}
        onValueChange={(values) => {
          const value = values[0]
          if (value) studio.setProvider(value as CatalogProvider)
        }}
        variant="outline"
        size="sm"
        aria-label="搜索来源"
      >
        {providerItems.map((item) => (
          <ToggleGroupItem key={item.value} value={item.value}>
            {item.label}
          </ToggleGroupItem>
        ))}
      </ToggleGroup>
    </Field>
  )
}

function SearchFeedback({ studio }: { studio: Studio }) {
  if (studio.searchState === "loading") return <SearchSkeleton />
  if (studio.searchState === "error") {
    return (
      <Alert variant="destructive">
        <AlertCircleIcon />
        <AlertTitle>没有完成搜索</AlertTitle>
        <AlertDescription>{studio.searchError}</AlertDescription>
      </Alert>
    )
  }
  if (studio.searchState !== "success") return null
  return (
    <CatalogResultList
      results={studio.searchResults}
      selected={studio.selected}
      onSelect={(result) => void studio.selectResult(result)}
    />
  )
}
