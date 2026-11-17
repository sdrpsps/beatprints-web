import type { HomeContent } from "../i18n/home.ts"

export function HomeHero({ content, buttonClass }: { content: HomeContent; buttonClass?: string }) {
  return (
    <section className="mx-auto grid min-h-[clamp(540px,76vh,780px)] w-[calc(100%-40px)] max-w-360 grid-rows-[auto_1fr_auto] border-b pt-[clamp(42px,7vw,96px)] pb-13.5 max-[960px]:min-h-150 max-sm:min-h-135 max-sm:w-[calc(100%-28px)] max-sm:pt-8.5 max-sm:pb-8" aria-labelledby="hero-title">
      <div className="flex justify-between gap-5 font-utility text-[10px] font-semibold tracking-[0.14em] text-muted-foreground"><span>MUSIC POSTER MAKER</span><span>EST. 2026</span></div>
      <h1 className="my-[clamp(44px,8vh,88px)] max-w-280 self-center text-[clamp(62px,8.5vw,132px)] leading-[0.96] font-[680] tracking-[-0.068em] [font-variation-settings:'wdth'_82] max-sm:my-12 max-sm:text-[10.8vw] max-sm:leading-none max-sm:tracking-[-0.065em]" id="hero-title">
        <span>{content.heroFirst}</span><span className="block">{content.heroSecond}</span>
      </h1>
      <div className="grid grid-cols-[minmax(260px,480px)_auto] items-end justify-between gap-8 max-sm:grid-cols-1 max-sm:items-start max-sm:gap-6">
        <p className="m-0 text-[clamp(16px,1.6vw,21px)] leading-[1.62] text-muted-foreground text-balance">{content.heroBody}</p>
        <a className={buttonClass} href="#studio">{content.start}<span aria-hidden="true">↓</span></a>
      </div>
    </section>
  )
}

export function HomeGuide({ content }: { content: HomeContent }) {
  return (
    <div className="mx-auto w-[calc(100%-40px)] max-w-360 border-t pb-24 max-sm:w-[calc(100%-28px)] max-sm:pb-16">
      <section className="grid grid-cols-[1fr_1.25fr] gap-10 py-20 max-md:grid-cols-1 max-md:gap-5 max-sm:py-14" aria-labelledby="intro-title">
        <h2 id="intro-title" className="m-0 max-w-120 text-3xl font-semibold tracking-tight sm:text-4xl">{content.introTitle}</h2>
        <p className="m-0 max-w-175 text-lg leading-relaxed text-muted-foreground">{content.intro}</p>
      </section>
      <section className="border-t py-20 max-sm:py-14" aria-labelledby="guide-title">
        <h2 id="guide-title" className="m-0 text-3xl font-semibold tracking-tight sm:text-4xl">{content.guideTitle}</h2>
        <ol className="mt-10 grid list-none grid-cols-3 gap-8 p-0 max-md:grid-cols-1">
          {content.steps.map(([title, body], index) => <li key={title} className="border-t pt-4"><span className="font-utility text-xs text-muted-foreground">0{index + 1}</span><h3 className="mt-4 mb-2 text-lg font-semibold">{title}</h3><p className="m-0 max-w-100 leading-relaxed text-muted-foreground">{body}</p></li>)}
        </ol>
      </section>
      <section className="grid grid-cols-[minmax(0,1fr)_minmax(0,1.4fr)] gap-12 border-t pt-20 max-md:grid-cols-1 max-sm:gap-8 max-sm:pt-14" aria-labelledby="examples-title">
        <div><h2 id="examples-title" className="m-0 text-3xl font-semibold tracking-tight sm:text-4xl">{content.examplesTitle}</h2><p className="mt-5 max-w-100 leading-relaxed text-muted-foreground">{content.examplesIntro}</p></div>
        <div className="grid grid-cols-2 items-start gap-5 max-sm:gap-3">
          <figure className="m-0"><img className="w-full shadow-md" src="/examples/track.webp" alt={content.trackExample} width="760" height="1160" loading="lazy" /><figcaption className="mt-3 text-sm text-muted-foreground">{content.trackCaption}</figcaption></figure>
          <figure className="m-0 pt-10"><img className="w-full shadow-md" src="/examples/album.webp" alt={content.albumExample} width="760" height="1160" loading="lazy" /><figcaption className="mt-3 text-sm text-muted-foreground">{content.albumCaption}</figcaption></figure>
        </div>
      </section>
    </div>
  )
}
