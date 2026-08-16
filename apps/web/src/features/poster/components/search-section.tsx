import type { FormEvent } from "react"
import { AlertCircleIcon, SearchIcon } from "lucide-react"
import { useTranslation } from "react-i18next"

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import {
  Field,
  FieldGroup,
  FieldLabel,
  FieldTitle,
} from "@/components/ui/field"
import {
  InputGroup,
  InputGroupAddon,
  InputGroupButton,
  InputGroupInput,
} from "@/components/ui/input-group"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import { Spinner } from "@/components/ui/spinner"
import {
  CatalogResultList,
  SearchSkeleton,
} from "@/features/poster/components/catalog-result-list"
import {
  SectionHeading,
  studioSectionClass,
} from "@/features/poster/components/studio-shared"
import { enabledCatalogSources } from "@/features/poster/catalogs/registry"
import { usePosterStore } from "@/features/poster/poster-store"
import type { CatalogProvider } from "@/features/poster/types"
import { cn } from "@/lib/utils"

export function SearchSection() {
  const { t } = useTranslation()
  const kind = usePosterStore((s) => s.kind)
  const query = usePosterStore((s) => s.query)
  const setQuery = usePosterStore((s) => s.setQuery)
  const provider = usePosterStore((s) => s.provider)
  const searchState = usePosterStore((s) => s.searchState)
  const selected = usePosterStore((s) => s.selected)
  const search = usePosterStore((s) => s.search)

  const onSubmit = (event: FormEvent) => {
    event.preventDefault()
    void search(t)
  }

  return (
    <section
      className={cn(studioSectionClass, !selected && "border-b-0 pb-0")}
    >
      <SectionHeading
        number="01"
        title={t("poster.selectWork")}
        description={
          kind === "track"
            ? t("poster.searchTrackDescription")
            : t("poster.searchAlbumDescription")
        }
      />
      <form onSubmit={onSubmit}>
        <FieldGroup>
          <Field>
            <FieldLabel htmlFor="catalog-search" className="sr-only">
              {kind === "track"
                ? t("poster.searchTrack")
                : t("poster.searchAlbum")}
            </FieldLabel>
            <InputGroup className="min-h-11">
              <InputGroupInput
                id="catalog-search"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder={
                  kind === "track"
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
                  disabled={
                    !query.trim() ||
                    !provider ||
                    searchState === "loading"
                  }
                >
                  {searchState === "loading" ? (
                    <Spinner data-icon="inline-start" />
                  ) : null}
                  {searchState === "loading"
                    ? t("poster.searching")
                    : t("poster.search")}
                </InputGroupButton>
              </InputGroupAddon>
            </InputGroup>
          </Field>
          {searchState !== "idle" ? <SourceFilter /> : null}
        </FieldGroup>
      </form>
      <SearchFeedback />
    </section>
  )
}

function SourceFilter() {
  const { t } = useTranslation()
  const provider = usePosterStore((s) => s.provider)
  const setProvider = usePosterStore((s) => s.setProvider)

  return (
    <Field orientation="horizontal" className="justify-end">
      <FieldTitle>{t("poster.source")}</FieldTitle>
      <ToggleGroup
        value={[provider]}
        onValueChange={(values) => {
          const value = values[0]
          if (value) setProvider(value as CatalogProvider, t)
        }}
        variant="outline"
        size="sm"
        aria-label={t("poster.source")}
      >
        {enabledCatalogSources().map((item) => (
          <ToggleGroupItem key={item.key} value={item.key}>
            {t(item.labelKey)}
          </ToggleGroupItem>
        ))}
      </ToggleGroup>
    </Field>
  )
}

function SearchFeedback() {
  const { t } = useTranslation()
  const searchState = usePosterStore((s) => s.searchState)
  const searchError = usePosterStore((s) => s.searchError)
  const searchResults = usePosterStore((s) => s.searchResults)
  const selected = usePosterStore((s) => s.selected)
  const selectResult = usePosterStore((s) => s.selectResult)

  if (searchState === "loading") return <SearchSkeleton />
  if (searchState === "error") {
    return (
      <Alert variant="destructive">
        <AlertCircleIcon />
        <AlertTitle>{t("poster.searchFailed")}</AlertTitle>
        <AlertDescription>{searchError}</AlertDescription>
      </Alert>
    )
  }
  if (searchState !== "success") return null
  return (
    <CatalogResultList
      results={searchResults}
      selected={selected}
      onSelect={(result) => void selectResult(result, t)}
    />
  )
}
