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
import { getDestination } from "@/features/poster/destinations/registry"
import { usePosterStore } from "@/features/poster/poster-store"

export function ManualPlatformLink() {
  const { t } = useTranslation()
  const selected = usePosterStore((s) => s.selected)
  const qrPlatform = usePosterStore((s) => s.qrPlatform)
  const platformUrl = usePosterStore((s) => s.platformUrl)
  const setPlatformUrl = usePosterStore((s) => s.setPlatformUrl)
  const platformManualError = usePosterStore((s) => s.platformManualError)
  const platformManualState = usePosterStore((s) => s.platformManualState)
  const platformManualMatch = usePosterStore((s) => s.platformManualMatch)
  const resolveManualPlatformUrl = usePosterStore(
    (s) => s.resolveManualPlatformUrl,
  )
  const showPlatformCandidates = usePosterStore(
    (s) => s.showPlatformCandidates,
  )

  const destination = getDestination(qrPlatform)
  const label = destination ? t(destination.labelKey) : qrPlatform
  const error = platformManualError

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
            value={platformUrl}
            aria-invalid={Boolean(error)}
            placeholder={t("poster.platformUrlPlaceholder")}
            onChange={(event) => setPlatformUrl(event.target.value)}
          />
        </InputGroup>
        <FieldDescription>{t("poster.platformManualHelp")}</FieldDescription>
        <Button
          type="button"
          variant="outline"
          size="sm"
          disabled={platformManualState === "loading"}
          onClick={() => void resolveManualPlatformUrl(t)}
        >
          {platformManualState === "loading" ? (
            <Spinner data-icon="inline-start" aria-hidden="true" />
          ) : null}
          {t("poster.fetchPlatformInfo")}
        </Button>
        {error ? <FieldError>{error}</FieldError> : null}
      </Field>
      {platformManualState === "success" && platformManualMatch ? (
        <PlatformItemCard
          match={platformManualMatch}
          source={selected!}
          platform={label}
          actions={
            <Button
              render={
                <a
                  href={platformManualMatch.url}
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
        onClick={() => void showPlatformCandidates(t)}
      >
        {t("poster.choosePlatformVersion")}
      </Button>
    </>
  )
}
