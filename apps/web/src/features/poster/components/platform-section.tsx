import { ExternalLinkIcon, Music2Icon } from "lucide-react"
import { useTranslation } from "react-i18next"

import {
  Field,
  FieldDescription,
  FieldError,
  FieldLabel,
  FieldLegend,
  FieldSet,
} from "@/components/ui/field"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Spinner } from "@/components/ui/spinner"
import {
  Item,
  ItemActions,
  ItemContent,
  ItemDescription,
  ItemMedia,
  ItemTitle,
} from "@/components/ui/item"
import {
  InputGroup,
  InputGroupAddon,
  InputGroupInput,
} from "@/components/ui/input-group"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import {
  SectionHeading,
  studioSectionClass,
  type Studio,
  CoverArt,
} from "@/features/poster/components/studio-shared"
import type { PosterPlatform } from "@/features/poster/types"

export function PlatformSection({ studio }: { studio: Studio }) {
  const { t } = useTranslation()
  if (!studio.selected) return null

  const platformItems = [
    { value: "none", label: t("poster.platformNone") },
    { value: "spotify", label: "Spotify" },
    { value: "apple_music", label: "Apple Music" },
    { value: "qq_music", label: t("poster.qqMusic") },
    { value: "netease_music", label: t("poster.neteaseMusic") },
  ] as const

  return (
    <section className={studioSectionClass}>
      <SectionHeading
        number={studio.kind === "track" ? "03" : "02"}
        title={t("poster.platform")}
        description={t("poster.platformHelp")}
      />
      <FieldSet>
        <FieldLegend className="sr-only">{t("poster.qrPlatformLabel")}</FieldLegend>
        <ToggleGroup
          value={[studio.qrPlatform || "none"]}
          onValueChange={(values) => {
            const value = values[0]
            if (!value) return
            studio.setQrPlatform(
              value === "none" ? "" : (value as PosterPlatform),
            )
          }}
          variant="outline"
          size="sm"
          className="flex-wrap"
        >
          {platformItems.map((item) => (
            <ToggleGroupItem key={item.value} value={item.value}>
              {item.label}
            </ToggleGroupItem>
          ))}
        </ToggleGroup>
      </FieldSet>
      {studio.platformNeedsUrl && studio.qrPlatform ? (
        studio.qrPlatform === "apple_music" &&
        studio.appleMusicLinkMode === "automatic" ? (
          <AppleMusicMatch studio={studio} />
        ) : studio.qrPlatform === "spotify" && studio.selected.provider === "deezer" && studio.spotifyLinkMode === "automatic" ? (
          <SpotifyMatch studio={studio} />
        ) : studio.qrPlatform === "apple_music" ? (
          <ManualAppleMusicLink studio={studio} />
        ) : studio.qrPlatform === "spotify" && studio.selected.provider === "deezer" ? (
          <ManualSpotifyLink studio={studio} />
        ) : (
          <PlatformUrlField studio={studio} />
        )
      ) : null}
    </section>
  )
}

function ManualSpotifyLink({ studio }: { studio: Studio }) {
  const { t } = useTranslation()
  const error = studio.currentPlatformError ?? studio.spotifyManualError

  return (
    <>
      <Field data-invalid={Boolean(error) || undefined}>
        <FieldLabel htmlFor="spotify-url">
          Spotify {t("poster.platformLinkSuffix")}
        </FieldLabel>
        <InputGroup>
          <InputGroupAddon>
            <ExternalLinkIcon aria-hidden="true" />
          </InputGroupAddon>
          <InputGroupInput
            id="spotify-url"
            type="url"
            inputMode="url"
            value={studio.platformUrl}
            aria-invalid={Boolean(error)}
            placeholder={t("poster.platformUrlPlaceholder")}
            onChange={(event) => studio.setPlatformUrl(event.target.value)}
          />
        </InputGroup>
        <FieldDescription>{t("poster.spotifyManualHelp")}</FieldDescription>
        <Button
          type="button"
          variant="outline"
          size="sm"
          disabled={studio.spotifyManualState === "loading"}
          onClick={() => void studio.resolveManualSpotifyUrl()}
        >
          {studio.spotifyManualState === "loading" ? (
            <Spinner data-icon="inline-start" aria-hidden="true" />
          ) : null}
          {t("poster.fetchSpotifyInfo")}
        </Button>
        {error ? <FieldError>{error}</FieldError> : null}
      </Field>
      {studio.spotifyManualState === "success" && studio.spotifyManualMatch ? (
        <AppleMusicConfirmationCard
          match={studio.spotifyManualMatch}
          source={studio.selected!}
        />
      ) : null}
    </>
  )
}

function SpotifyMatch({ studio }: { studio: Studio }) {
  const { t } = useTranslation()
  if (studio.spotifyMatchState === "loading") {
    return (
      <Alert>
        <Spinner aria-hidden="true" />
        <AlertTitle>{t("poster.spotifyMatching")}</AlertTitle>
      </Alert>
    )
  }
  if (studio.spotifyMatchState === "success" && studio.spotifyMatch) {
    return (
      <AppleMusicConfirmationCard
        match={studio.spotifyMatch}
        source={studio.selected!}
        manualAction={() => studio.setSpotifyLinkMode("manual")}
        manualLabel={t("poster.manualSpotifyLink")}
      />
    )
  }
  if (studio.spotifyMatchState === "error") {
    return (
      <Alert variant="destructive">
        <Music2Icon aria-hidden="true" />
        <AlertTitle>{t("poster.spotifyNotMatched")}</AlertTitle>
        <AlertDescription>{studio.currentPlatformError}</AlertDescription>
        <Button
          variant="outline"
          size="sm"
          onClick={() => studio.setSpotifyLinkMode("manual")}
        >
          {t("poster.manualSpotifyLink")}
        </Button>
      </Alert>
    )
  }
  return null
}

function AppleMusicMatch({ studio }: { studio: Studio }) {
  const { t } = useTranslation()

  if (studio.appleMusicState === "loading") {
    return (
      <Alert>
        <Spinner aria-hidden="true" />
        <AlertTitle>{t("poster.appleMusicMatching")}</AlertTitle>
        <AlertDescription>{t("poster.appleMusicMatchingHelp")}</AlertDescription>
      </Alert>
    )
  }

  if (studio.appleMusicState === "success" && studio.appleMusicMatch) {
    return (
      <AppleMusicConfirmationCard
        match={studio.appleMusicMatch}
        source={studio.selected!}
        manualAction={() => studio.setAppleMusicLinkMode("manual")}
        manualLabel={t("poster.manualAppleMusicLink")}
      />
    )
  }

  if (studio.appleMusicState === "error") {
    return (
      <Alert variant="destructive">
        <Music2Icon aria-hidden="true" />
        <AlertTitle>{t("poster.appleMusicNotMatched")}</AlertTitle>
        <AlertDescription>{studio.currentPlatformError}</AlertDescription>
        <Button
          variant="outline"
          size="sm"
          onClick={() => studio.setAppleMusicLinkMode("manual")}
        >
          {t("poster.manualAppleMusicLink")}
        </Button>
      </Alert>
    )
  }

  return null
}

function ManualAppleMusicLink({ studio }: { studio: Studio }) {
  const { t } = useTranslation()
  const error = studio.currentPlatformError ?? studio.appleMusicManualError

  return (
    <>
      <Field data-invalid={Boolean(error) || undefined}>
        <FieldLabel htmlFor="apple-music-url">Apple Music {t("poster.platformLinkSuffix")}</FieldLabel>
        <InputGroup>
          <InputGroupAddon>
            <ExternalLinkIcon aria-hidden="true" />
          </InputGroupAddon>
          <InputGroupInput
            id="apple-music-url"
            type="url"
            inputMode="url"
            value={studio.platformUrl}
            aria-invalid={Boolean(error)}
            placeholder={t("poster.platformUrlPlaceholder")}
            onChange={(event) => studio.setPlatformUrl(event.target.value)}
          />
        </InputGroup>
        <FieldDescription>{t("poster.appleMusicManualHelp")}</FieldDescription>
        <Button
          type="button"
          variant="outline"
          size="sm"
          disabled={studio.appleMusicManualState === "loading"}
          onClick={() => void studio.resolveManualAppleMusicUrl()}
        >
          {studio.appleMusicManualState === "loading" ? (
            <Spinner data-icon="inline-start" aria-hidden="true" />
          ) : null}
          {t("poster.fetchAppleMusicInfo")}
        </Button>
        {error ? <FieldError>{error}</FieldError> : null}
      </Field>
      {studio.appleMusicManualState === "success" && studio.appleMusicManualMatch ? (
        <AppleMusicConfirmationCard
          match={studio.appleMusicManualMatch}
          source={studio.selected!}
        />
      ) : null}
    </>
  )
}

function AppleMusicConfirmationCard({
  match,
  source,
  manualAction,
  manualLabel,
}: {
  match: NonNullable<Studio["appleMusicMatch"]>
  source: NonNullable<Studio["selected"]>
  manualAction?: () => void
  manualLabel?: string
}) {
  const { t } = useTranslation()
  const albumDetails = [
    match.release_year,
    match.track_count ? `${match.track_count} ${t("poster.trackCountUnit")}` : undefined,
  ]
    .filter(Boolean)
    .join(" · ")

  return (
    <Item variant="outline">
      <ItemMedia variant="image" className="size-16">
        {match.cover_url ? (
          <img src={match.cover_url} alt={t("poster.appleMusicCoverAlt", { title: match.title })} />
        ) : (
          <CoverArt result={source} />
        )}
      </ItemMedia>
        <ItemContent>
          <ItemTitle>{match.title}</ItemTitle>
          <ItemDescription>{match.artists.join("、")}</ItemDescription>
          {match.type === "album" && albumDetails ? (
            <ItemDescription>{albumDetails}</ItemDescription>
          ) : null}
          {match.type === "track" && match.album ? (
            <ItemDescription>{match.album}</ItemDescription>
          ) : null}
        </ItemContent>
      <ItemActions className="max-sm:basis-full max-sm:justify-end">
        <Button render={<a href={match.url} target="_blank" rel="noreferrer" />} variant="outline" size="sm">
          <ExternalLinkIcon data-icon="inline-start" aria-hidden="true" />
          {t("poster.openAppleMusic")}
        </Button>
        {manualAction ? (
          <Button variant="ghost" size="sm" onClick={manualAction}>
            {manualLabel}
          </Button>
        ) : null}
      </ItemActions>
    </Item>
  )
}

function PlatformUrlField({ studio }: { studio: Studio }) {
  const { t } = useTranslation()
  const platform = studio.qrPlatform as PosterPlatform

  const platformLabels: Record<PosterPlatform, string> = {
    spotify: "Spotify",
    apple_music: "Apple Music",
    qq_music: t("poster.qqMusic"),
    netease_music: t("poster.neteaseMusic"),
  }

  return (
    <Field data-invalid={Boolean(studio.currentPlatformError) || undefined}>
      <FieldLabel htmlFor="platform-url">
        {platformLabels[platform]} {t("poster.platformLinkSuffix")}
      </FieldLabel>
      <InputGroup>
        <InputGroupAddon>
          <ExternalLinkIcon aria-hidden="true" />
        </InputGroupAddon>
        <InputGroupInput
          id="platform-url"
          type="url"
          inputMode="url"
          value={studio.platformUrl}
          aria-invalid={Boolean(studio.currentPlatformError)}
          placeholder={t("poster.platformUrlPlaceholder")}
          onChange={(event) => studio.setPlatformUrl(event.target.value)}
        />
      </InputGroup>
      <FieldDescription>
        {platform === "apple_music"
          ? t("poster.appleMusicManualHelp")
          : t("poster.platformUrlHelp")}
      </FieldDescription>
      {studio.currentPlatformError ? (
        <FieldError>{studio.currentPlatformError}</FieldError>
      ) : null}
    </Field>
  )
}
