import { BotIcon, Code2Icon, ExternalLinkIcon } from "lucide-react"
import { useTranslation } from "react-i18next"

import { ReleaseNotes } from "@/features/poster/components/release-notes"
import { buildInfo } from "@/lib/build-info"

const footerLinkClass = "inline-flex items-center gap-[7px] rounded-sm text-[13px] text-muted-foreground no-underline outline-offset-4 transition-colors duration-150 hover:text-foreground focus-visible:outline-2 focus-visible:outline-ring motion-reduce:transition-none [&_svg]:size-3.5"

export function SiteFooter() {
  const { t } = useTranslation()
  return (
    <footer className="mx-auto flex min-h-[190px] w-[calc(100%-40px)] max-w-[1440px] items-start justify-between gap-8 border-t py-[42px] max-sm:w-[calc(100%-28px)] max-sm:flex-col">
      <div>
        <strong className="text-[15px]">{t("poster.brand")}</strong>
        <p className="mt-[7px] text-xs text-muted-foreground">
          {t("app.footerDisclaimer")}
        </p>
        <p className="mt-2 font-mono text-[11px] tracking-[-0.01em] text-muted-foreground">
          {buildInfo.version} · {buildInfo.shortGitSha}
        </p>
      </div>
      <div className="flex flex-wrap items-center justify-end gap-[22px] [&>a]:whitespace-nowrap max-sm:flex-col max-sm:items-start max-sm:gap-3">
        <ReleaseNotes triggerClassName={footerLinkClass} />
        <a
          className={footerLinkClass}
          href="/llms.txt"
          target="_blank"
          rel="noreferrer"
        >
          <BotIcon aria-hidden="true" />
          {t("app.footerAgentGuide")}
        </a>
        <a
          className={footerLinkClass}
          href="https://github.com/sdrpsps/beatprints-web"
          target="_blank"
          rel="noreferrer"
        >
          <Code2Icon aria-hidden="true" />
          {t("app.footerSourceCode")}
        </a>
        <a
          className={footerLinkClass}
          href="https://github.com/TrueMyst/BeatPrints"
          target="_blank"
          rel="noreferrer"
        >
          <ExternalLinkIcon aria-hidden="true" />
          {t("app.footerUpstreamGenerator")}
        </a>
        <a
          className={footerLinkClass}
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
