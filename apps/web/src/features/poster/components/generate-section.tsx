import { AlertCircleIcon, ImageIcon } from "lucide-react"

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Spinner } from "@/components/ui/spinner"
import type { Studio } from "@/features/poster/components/studio-shared"
import { zhCN } from "@/features/poster/copy"

export function GenerateSection({ studio }: { studio: Studio }) {
  if (!studio.selected) return null
  return (
    <div className="flex flex-col gap-3 pt-7">
      {studio.generationError ? (
        <Alert variant="destructive">
          <AlertCircleIcon />
          <AlertTitle>海报没有生成</AlertTitle>
          <AlertDescription>
            {studio.generationError.message}
            {studio.generationError.requestId ? (
              <span className="mt-2 block font-[var(--font-utility)] text-[10px]">
                请求编号：{studio.generationError.requestId}
              </span>
            ) : null}
          </AlertDescription>
        </Alert>
      ) : null}
      <Button
        className="w-full"
        size="lg"
        disabled={!studio.canGenerate}
        onClick={() => void studio.generate()}
      >
        {studio.generationState === "loading" ? (
          <Spinner data-icon="inline-start" />
        ) : (
          <ImageIcon data-icon="inline-start" />
        )}
        {studio.generationState === "loading"
          ? zhCN.generating
          : studio.outputStale
            ? "应用修改并重新生成"
            : zhCN.generate}
      </Button>
      {!studio.canGenerate && studio.generationState !== "loading" ? (
        <p className="m-0 text-center text-xs text-muted-foreground">
          完成上方必填内容后即可生成。
        </p>
      ) : null}
    </div>
  )
}
