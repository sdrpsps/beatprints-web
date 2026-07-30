import { Code2Icon, ExternalLinkIcon } from "lucide-react"

export function SiteFooter() {
  return (
    <footer className="mx-auto flex min-h-[190px] w-[calc(100%-40px)] max-w-[1440px] items-start justify-between gap-8 border-t py-[42px] max-sm:w-[calc(100%-28px)] max-sm:flex-col">
      <div>
        <strong className="text-[15px]">BeatPrints</strong>
        <p className="mt-[7px] text-xs text-muted-foreground">
          为非商业音乐收藏与个人表达而制作。
        </p>
      </div>
      <div className="flex items-center gap-[22px] max-sm:flex-col max-sm:items-start max-sm:gap-3">
        <a
          className="inline-flex items-center gap-[7px] text-[13px] text-muted-foreground no-underline transition-colors duration-150 hover:text-foreground motion-reduce:transition-none [&_svg]:size-3.5"
          href="https://github.com/sdrpsps/byteshare"
          target="_blank"
          rel="noreferrer"
        >
          <Code2Icon aria-hidden="true" />
          项目源码
        </a>
        <a
          className="inline-flex items-center gap-[7px] text-[13px] text-muted-foreground no-underline transition-colors duration-150 hover:text-foreground motion-reduce:transition-none [&_svg]:size-3.5"
          href="https://github.com/TrueMyst/BeatPrints"
          target="_blank"
          rel="noreferrer"
        >
          <ExternalLinkIcon aria-hidden="true" />
          上游生成器
        </a>
        <a
          className="inline-flex items-center gap-[7px] text-[13px] text-muted-foreground no-underline transition-colors duration-150 hover:text-foreground motion-reduce:transition-none"
          href="https://creativecommons.org/licenses/by-nc-sa/4.0/"
          target="_blank"
          rel="noreferrer"
        >
          CC BY-NC-SA 4.0
        </a>
      </div>
    </footer>
  )
}
