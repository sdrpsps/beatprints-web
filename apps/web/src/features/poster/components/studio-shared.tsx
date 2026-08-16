import { useState } from "react"
import { Music2Icon } from "lucide-react"
import { useTranslation } from "react-i18next"

import type { SearchResult } from "@/features/poster/types"

export const studioSectionClass =
  "flex flex-col gap-[22px] border-b py-8 first:pt-2"

export function SectionHeading({
  number,
  title,
  description,
}: {
  number: string
  title: string
  description?: string
}) {
  return (
    <div className="grid grid-cols-[34px_1fr] gap-3 max-sm:grid-cols-[28px_1fr]">
      <span
        className="font-utility text-[10px] font-semibold tracking-widest text-muted-foreground"
        aria-hidden="true"
      >
        {number}
      </span>
      <div>
        <h3 className="m-0 text-lg font-[650] tracking-tight">{title}</h3>
        {description ? (
          <p className="mt-1.25 max-w-130 text-[13px] leading-[1.55] text-muted-foreground">
            {description}
          </p>
        ) : null}
      </div>
    </div>
  )
}

export function CoverArt({ result }: { result: SearchResult }) {
  const { t } = useTranslation()
  const [failed, setFailed] = useState(false)

  if (failed) {
    return (
      <div
        className="cover-fallback grid size-full place-items-center text-muted-foreground [&_svg]:size-4.5"
        aria-label={t("poster.coverFailed", { title: result.title })}
      >
        <Music2Icon aria-hidden="true" />
      </div>
    )
  }

  return (
    <img
      src={result.cover_url}
      alt={t("poster.coverAlt", { title: result.title })}
      loading="lazy"
      onError={() => setFailed(true)}
    />
  )
}
