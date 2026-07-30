import { useState } from "react"
import { Music2Icon } from "lucide-react"

import type { SearchResult } from "@/features/poster/types"
import type { usePosterStudio } from "@/features/poster/use-poster-studio"

export type Studio = ReturnType<typeof usePosterStudio>

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
        className="font-[var(--font-utility)] text-[10px] font-semibold tracking-[0.1em] text-muted-foreground"
        aria-hidden="true"
      >
        {number}
      </span>
      <div>
        <h3 className="m-0 text-lg font-[650] tracking-[-0.025em]">{title}</h3>
        {description ? (
          <p className="mt-[5px] max-w-[520px] text-[13px] leading-[1.55] text-muted-foreground">
            {description}
          </p>
        ) : null}
      </div>
    </div>
  )
}

export function CoverArt({ result }: { result: SearchResult }) {
  const [failed, setFailed] = useState(false)

  if (failed) {
    return (
      <div
        className="cover-fallback grid size-full place-items-center text-muted-foreground [&_svg]:size-[18px]"
        aria-label={`${result.title} 封面加载失败`}
      >
        <Music2Icon aria-hidden="true" />
      </div>
    )
  }

  return (
    <img
      src={result.cover_url}
      alt={`${result.title} 封面`}
      loading="lazy"
      onError={() => setFailed(true)}
    />
  )
}
