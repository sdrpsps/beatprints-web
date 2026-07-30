import { Disc3Icon, Music2Icon } from "lucide-react"

import { Separator } from "@/components/ui/separator"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { AppearanceSection } from "@/features/poster/components/appearance-section"
import { GenerateSection } from "@/features/poster/components/generate-section"
import { LyricsSection } from "@/features/poster/components/lyrics-section"
import { OutputStage } from "@/features/poster/components/output-stage"
import { PlatformSection } from "@/features/poster/components/platform-section"
import { SearchSection } from "@/features/poster/components/search-section"
import type { Studio } from "@/features/poster/components/studio-shared"
import { zhCN } from "@/features/poster/copy"
import type { PosterKind } from "@/features/poster/types"
import { usePosterStudio } from "@/features/poster/use-poster-studio"

function Editor({ studio }: { studio: Studio }) {
  return (
    <div className="min-w-0">
      <SearchSection studio={studio} />
      <LyricsSection studio={studio} />
      <PlatformSection studio={studio} />
      <AppearanceSection studio={studio} />
      <GenerateSection studio={studio} />
    </div>
  )
}

function StudioContent({ studio }: { studio: Studio }) {
  return (
    <div className="grid grid-cols-[minmax(0,0.86fr)_minmax(430px,1.14fr)] items-start gap-[clamp(32px,5vw,76px)] max-[960px]:grid-cols-1 max-sm:gap-[42px]">
      <Editor studio={studio} />
      <OutputStage studio={studio} />
    </div>
  )
}

export function PosterStudio() {
  const studio = usePosterStudio()
  return (
    <section
      id="studio"
      className="mx-auto w-[calc(100%-40px)] max-w-[1440px] py-20 pb-28 max-sm:w-[calc(100%-28px)] max-sm:py-14 max-sm:pb-[72px]"
      aria-labelledby="studio-title"
    >
      <div className="flex items-end justify-between gap-8 pb-7 max-sm:flex-col max-sm:items-start">
        <div>
          <span className="font-[var(--font-utility)] text-[10px] font-semibold tracking-[0.14em] text-muted-foreground">
            COMPOSE / PRINT / KEEP
          </span>
          <h2
            className="mt-[7px] mb-0 text-[clamp(42px,5vw,72px)] leading-[0.95] font-[670] tracking-[-0.055em] [font-variation-settings:'wdth'_86]"
            id="studio-title"
          >
            开始制作
          </h2>
        </div>
        <p className="m-0 max-w-[360px] text-right text-[13px] text-muted-foreground max-sm:text-left">
          无需登录。生成结果只存在于这次浏览器会话中。
        </p>
      </div>
      <Separator />
      <Tabs
        value={studio.kind}
        onValueChange={(value) => studio.setKind(value as PosterKind)}
      >
        <TabsList className="mt-5 mb-6" variant="line" aria-label="海报类型">
          <TabsTrigger value="track">
            <Music2Icon data-icon="inline-start" />
            {zhCN.track}
          </TabsTrigger>
          <TabsTrigger value="album">
            <Disc3Icon data-icon="inline-start" />
            {zhCN.album}
          </TabsTrigger>
        </TabsList>
        <TabsContent value="track">
          <StudioContent studio={studio} />
        </TabsContent>
        <TabsContent value="album">
          <StudioContent studio={studio} />
        </TabsContent>
      </Tabs>
    </section>
  )
}
