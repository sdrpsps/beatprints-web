import type { FormEvent } from "react"
import { AlertCircleIcon, SearchIcon } from "lucide-react"
import { useTranslation } from "react-i18next"

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
import type { CatalogProvider } from "@/features/poster/types"
import { cn } from "@/lib/utils"

const providerItems = [
  { value: "deezer", label: "Deezer" },
  { value: "spotify", label: "Spotify" },
] satisfies { value: CatalogProvider; label: string }[]

export function SearchSection({ studio }: { studio: Studio }) {
  const { t } = useTranslation()
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
        title={t("poster.selectWork")}
        description={
          studio.kind === "track"
            ? t("poster.searchTrackDescription")
            : t("poster.searchAlbumDescription")
        }
      />
      <form onSubmit={onSubmit}>
        <FieldGroup>
          <Field>
            <FieldLabel htmlFor="catalog-search" className="sr-only">
              {studio.kind === "track"
                ? t("poster.searchTrack")
                : t("poster.searchAlbum")}
            </FieldLabel>
            <InputGroup className="min-h-11">
              <InputGroupInput
                id="catalog-search"
                value={studio.query}
                onChange={(event) => studio.setQuery(event.target.value)}
                placeholder={
                  studio.kind === "track"
                    ? t("poster.searchTrackPlaceholder")
                    : t("poster.searchAlbumPlaceholder")
                }
                autoComplete="off"
              />
              <InputGroupAddon align="inline-start">
                <SearchIcon aria-hidden="true" />
              </InputGroupAddon>
              <InputGroupAddon align="inline-end">
                <InputGroupButton
                  type="submit"
                  variant="default"
                  size="sm"
                  disabled={!studio.query.trim() || studio.searchState === "loading"}
                >
                  {studio.searchState === "loading" ? (
                    <Spinner data-icon="inline-start" />
                  ) : null}
                  {studio.searchState === "loading"
                    ? t("poster.searching")
                    : t("poster.search")}
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
  const { t } = useTranslation()
  return (
    <Field orientation="horizontal" className="justify-end">
      <FieldTitle>{t("poster.source")}</FieldTitle>
      <ToggleGroup
        value={[studio.provider]}
        onValueChange={(values) => {
          const value = values[0]
          if (value) studio.setProvider(value as CatalogProvider)
        }}
        variant="outline"
        size="sm"
        aria-label={t("poster.source")}
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
  const { t } = useTranslation()
  if (studio.searchState === "loading") return <SearchSkeleton />
  if (studio.searchState === "error") {
    return (
      <Alert variant="destructive">
        <AlertCircleIcon />
        <AlertTitle>{t("poster.searchFailed")}</AlertTitle>
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
