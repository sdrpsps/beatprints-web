import { ArrowDownIcon, Code2Icon } from "lucide-react"
import { useEffect } from "react"
import { useTranslation } from "react-i18next"

import { LanguageSwitcher } from "@/components/language-switcher"
import { buttonVariants } from "@/components/ui/button"
import { Toaster } from "@/components/ui/toast"
import { SiteFooter } from "@/features/poster/components/site-footer"
import { PosterStudio } from "@/features/poster/poster-studio"
import "./App.css"

function App() {
  const { t, i18n } = useTranslation()

  useEffect(() => {
    document.title = t("app.documentTitle")
  }, [i18n.resolvedLanguage, t])

  return (
    <div className="min-h-screen overflow-clip">
      <header className="mx-auto flex min-h-[76px] w-[calc(100%-40px)] max-w-[1440px] items-center justify-between gap-6 border-b max-sm:min-h-16 max-sm:w-[calc(100%-28px)]">
        <a
          className="inline-flex items-center gap-2.5 text-[15px] font-[720] tracking-[-0.025em] text-foreground no-underline"
          href="/"
          aria-label={t("app.homeLabel")}
        >
          <span
            className="grid size-[30px] place-items-center bg-primary font-[var(--font-utility)] text-[10px] tracking-[0.08em] text-primary-foreground"
            aria-hidden="true"
          >
            BP
          </span>
          {t("poster.brand")}
        </a>
        <nav
          className="flex items-center gap-[22px]"
          aria-label={t("app.primaryNavigationLabel")}
        >
          <a
            className="inline-flex items-center gap-[7px] text-[13px] text-muted-foreground no-underline transition-colors duration-150 hover:text-foreground motion-reduce:transition-none max-sm:hidden"
            href="#studio"
          >
            {t("app.startCreating")}
          </a>
          <a
            className="inline-flex items-center gap-[7px] text-[13px] text-muted-foreground no-underline transition-colors duration-150 hover:text-foreground motion-reduce:transition-none [&_svg]:size-3.5"
            href="https://github.com/sdrpsps/byteshare"
            target="_blank"
            rel="noreferrer"
          >
            <Code2Icon aria-hidden="true" />
            GitHub
          </a>
          <LanguageSwitcher />
        </nav>
      </header>

      <main>
        <section
          className="mx-auto grid min-h-[clamp(540px,76vh,780px)] w-[calc(100%-40px)] max-w-[1440px] grid-rows-[auto_1fr_auto] border-b pt-[clamp(42px,7vw,96px)] pb-[54px] max-[960px]:min-h-[600px] max-sm:min-h-[540px] max-sm:w-[calc(100%-28px)] max-sm:pt-[34px] max-sm:pb-8"
          aria-labelledby="hero-title"
        >
          <div className="flex justify-between gap-5 font-[var(--font-utility)] text-[10px] font-semibold tracking-[0.14em] text-muted-foreground">
            <span>{t("app.heroSubtitle")}</span>
            <span>{t("app.heroEst")}</span>
          </div>
          <h1
            className="my-[clamp(44px,8vh,88px)] max-w-[1120px] self-center text-[clamp(62px,8.5vw,132px)] leading-[0.96] font-[680] tracking-[-0.068em] [font-variation-settings:'wdth'_82] max-sm:my-12 max-sm:text-[10.8vw] max-sm:leading-none max-sm:tracking-[-0.065em]"
            id="hero-title"
          >
            <span>{t("app.heroTitleFirstLine")}</span>
            <span className="block whitespace-nowrap">
              {t("app.heroTitleSecondLine")}
            </span>
          </h1>
          <div className="grid grid-cols-[minmax(260px,480px)_auto] items-end justify-between gap-8 max-sm:grid-cols-1 max-sm:items-start max-sm:gap-6">
            <p className="m-0 text-[clamp(16px,1.6vw,21px)] leading-[1.62] text-muted-foreground [text-wrap:balance]">
              {t("poster.heroBody")}
            </p>
            <a
              className={buttonVariants({ size: "lg" })}
              href="#studio"
            >
              {t("app.startCreating")}
              <ArrowDownIcon data-icon="inline-end" />
            </a>
          </div>
        </section>
        <PosterStudio />
      </main>
      <SiteFooter />
      <Toaster />
    </div>
  )
}

export default App
