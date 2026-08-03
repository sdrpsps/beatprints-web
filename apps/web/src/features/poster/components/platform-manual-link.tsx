import { ExternalLinkIcon } from "lucide-react"
import { useTranslation } from "react-i18next"

import { Button } from "@/components/ui/button"
import {
  Field,
  FieldDescription,
  FieldError,
  FieldLabel,
} from "@/components/ui/field"
import {
  InputGroup,
  InputGroupAddon,
  InputGroupInput,
} from "@/components/ui/input-group"
import { Spinner } from "@/components/ui/spinner"
import { PlatformItemCard } from "@/features/poster/components/platform-item-card"
import type { Studio } from "@/features/poster/components/studio-shared"
import { getDestination } from "@/features/poster/destinations/registry"

export function ManualPlatformLink({ studio }: { studio: Studio }) {
  const { t } = useTranslation()
  const destination = getDestination(studio.qrPlatform)
  const label = destination ? t(destination.labelKey) : studio.qrPlatform
  const error = studio.currentPlatformError ?? studio.platformManualError

  return (
    <>
      <Field data-invalid={Boolean(error) || undefined}>
        <FieldLabel htmlFor="platform-url">
          {label} {t("poster.platformLinkSuffix")}
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
            aria-invalid={Boolean(error)}
            placeholder={t("poster.platformUrlPlaceholder")}
            onChange={(event) => studio.setPlatformUrl(event.target.value)}
          />
        </InputGroup>
        <FieldDescription>{t("poster.platformManualHelp")}</FieldDescription>
        <Button
          type="button"
          variant="outline"
          size="sm"
          disabled={studio.platformManualState === "loading"}
          onClick={() => void studio.resolveManualPlatformUrl()}
        >
          {studio.platformManualState === "loading" ? (
            <Spinner data-icon="inline-start" aria-hidden="true" />
          ) : null}
          {t("poster.fetchPlatformInfo")}
        </Button>
        {error ? <FieldError>{error}</FieldError> : null}
      </Field>
      {studio.platformManualState === "success" &&
      studio.platformManualMatch ? (
        <PlatformItemCard
          match={studio.platformManualMatch}
          source={studio.selected!}
          platform={label}
          actions={
            <Button
              render={
                <a
                  href={studio.platformManualMatch.url}
                  target="_blank"
                  rel="noreferrer"
                />
              }
              variant="outline"
              size="sm"
            >
              {t("poster.openPlatform")}
            </Button>
          }
        />
      ) : null}
      <Button
        type="button"
        variant="ghost"
        size="sm"
        onClick={() => void studio.showPlatformCandidates()}
      >
        {t("poster.choosePlatformVersion")}
      </Button>
    </>
  )
}
