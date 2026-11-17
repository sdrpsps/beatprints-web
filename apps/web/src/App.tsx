import { Code2Icon } from "lucide-react"
import { useEffect, useLayoutEffect } from "react"
import { useTranslation } from "react-i18next"

import { HomeGuide, HomeHero } from "@/components/home-content"
import { homeContent } from "@/i18n/home"
import { normalizeLanguage } from "@/i18n/resources"
import { HistoryNavButton } from "@/components/history-nav-button"
import { LanguageSwitcher } from "@/components/language-switcher"
import { buttonVariants } from "@/components/ui/button"
import { Toaster } from "@/components/ui/toast"
import { SiteFooter } from "@/features/poster/components/site-footer"
import { PosterStudio } from "@/features/poster/poster-studio"
import { usePosterStore } from "@/features/poster/poster-store"
import "./App.css"

function App() {
  const { t, i18n } = useTranslation()

  const content = homeContent[normalizeLanguage(i18n.resolvedLanguage ?? i18n.language)]

  useLayoutEffect(() => {
    document.documentElement.removeAttribute("data-app-pending")
  }, [])

  useEffect(() => {
    void usePosterStore.getState().loadHistory()
  }, [])

  return (
    <div className="min-h-screen overflow-clip">
      <header className="mx-auto flex min-h-19 w-[calc(100%-40px)] max-w-360 items-center justify-between gap-6 border-b max-sm:gap-2 max-sm:min-h-16 max-sm:w-[calc(100%-28px)]">
        <a
          className="inline-flex shrink-0 items-center gap-2.5 whitespace-nowrap text-[15px] font-[720] tracking-tight text-foreground no-underline"
          href={content.path}
          aria-label={t("app.homeLabel")}
        >
          <img
            className="size-9 object-contain"
            src="/favicon.png"
            alt=""
            aria-hidden="true"
          />
          {t("poster.brand")}
        </a>
        <nav
          className="flex items-center gap-3 max-sm:gap-2"
          aria-label={t("app.primaryNavigationLabel")}
        >
          <HistoryNavButton />
          <a
            className="inline-flex items-center gap-1.75 text-[13px] text-muted-foreground no-underline transition-colors duration-150 hover:text-foreground motion-reduce:transition-none [&_svg]:size-3.5"
            href="https://github.com/sdrpsps/beatprints-web"
            target="_blank"
            rel="noreferrer"
          >
            <Code2Icon aria-hidden="true" />
            <span className="max-sm:sr-only">GitHub</span>
          </a>
          <LanguageSwitcher />
        </nav>
      </header>

      <main>
        <HomeHero content={content} buttonClass={buttonVariants({ size: "lg" })} />
        <PosterStudio />
        <HomeGuide content={content} />
      </main>
      <SiteFooter />
      <Toaster />
    </div>
  )
}

export default App
