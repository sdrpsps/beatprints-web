import { useTranslation } from "react-i18next"

import { useAlbumOptions } from "@/features/poster/use-album-options"
import { useCatalogSelection } from "@/features/poster/use-catalog-selection"
import { useLyricsSelection } from "@/features/poster/use-lyrics-selection"
import { usePlatformLinkFlow } from "@/features/poster/use-platform-link-flow"
import { usePosterGeneration } from "@/features/poster/use-poster-generation"
import { usePosterPreferences } from "@/features/poster/use-poster-preferences"
import type {
  CatalogProvider,
  PosterKind,
  Theme,
} from "@/features/poster/types"

export function usePosterStudio() {
  const { t } = useTranslation()
  const preferences = usePosterPreferences()
  const generation = usePosterGeneration()
  const catalog = useCatalogSelection({
    kind: preferences.kind,
    t,
    markOutputStale: generation.markOutputStale,
  })
  const lyrics = useLyricsSelection({
    kind: preferences.kind,
    selected: catalog.selected,
    t,
    markOutputStale: generation.markOutputStale,
  })
  const platform = usePlatformLinkFlow({
    selected: catalog.selected,
    kind: preferences.kind,
    t,
    markOutputStale: generation.markOutputStale,
  })
  const album = useAlbumOptions(generation.markOutputStale)

  function setKind(value: PosterKind) {
    if (value === preferences.kind) return

    generation.markOutputStale()
    preferences.setKind(value)
    catalog.resetForKind()
    platform.clear()
  }

  function setProvider(value: CatalogProvider) {
    if (value === catalog.provider) return

    if (catalog.selected) platform.clear()
    catalog.setProvider(value)
  }

  function selectResult(result: NonNullable<typeof catalog.selected>) {
    platform.clear()
    catalog.selectResult(result)
  }

  function resetSelection() {
    catalog.resetSelection()
    platform.clear()
    generation.clearOutput()
  }

  const canGenerate =
    Boolean(catalog.selected) &&
    lyrics.lyricsReady &&
    !platform.currentPlatformError &&
    platform.platformChoiceMode !== "candidates" &&
    platform.platformReady &&
    generation.generationState !== "loading"

  function generate() {
    if (!catalog.selected || !canGenerate) return

    const request = {
      provider: catalog.selected.provider,
      catalog_id: catalog.selected.id,
      theme: preferences.theme,
      accent: preferences.accent,
      ...(preferences.kind === "track"
        ? lyrics.instrumental
          ? { instrumental_text: lyrics.instrumentalText.trim() }
          : { lyrics: lyrics.lyricsText }
        : { indexing: album.indexing, shuffle: album.shuffle }),
      ...(platform.qrPlatform
        ? {
            qr_platform: platform.qrPlatform,
            ...(platform.platformNeedsUrl
              ? {
                  platform_links: {
                    [platform.qrPlatform]: platform.platformUrl.trim(),
                  },
                }
              : {}),
          }
        : {}),
    }
    return generation.generate(
      preferences.kind,
      request,
      catalog.selected.title,
      t,
    )
  }

  return {
    ...preferences,
    ...catalog,
    ...lyrics,
    ...platform,
    ...album,
    ...generation,
    setKind,
    setTheme: (value: Theme) => {
      preferences.setTheme(value)
      generation.markOutputStale()
    },
    setAccent: (value: boolean) => {
      preferences.setAccent(value)
      generation.markOutputStale()
    },
    setProvider,
    selectResult,
    resetSelection,
    canGenerate,
    generate,
  }
}
