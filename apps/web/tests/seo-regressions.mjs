import assert from "node:assert/strict"
import { readFileSync, existsSync } from "node:fs"

const dist = new URL("../dist/", import.meta.url)
const read = (name) => readFileSync(new URL(name, dist), "utf8")
const origin = "https://beatprints.bytespark.app"
const pages = [
  { file: "index.html", lang: "en", heading: "How to make a music poster", indexable: true },
  { file: "en/index.html", lang: "en", heading: "How to make a music poster" },
  { file: "zh-CN/index.html", lang: "zh-CN", heading: "如何制作音乐海报" },
  { file: "zh-TW/index.html", lang: "zh-TW", heading: "如何製作音樂海報" },
  { file: "ja/index.html", lang: "ja", heading: "音楽ポスターの作り方" },
  { file: "ko/index.html", lang: "ko", heading: "음악 포스터를 만드는 방법" },
]
const sitemap = read("sitemap.xml")
assert.match(read("robots.txt"), /Sitemap: https:\/\/beatprints\.bytespark\.app\/sitemap\.xml/)
assert.deepEqual([...sitemap.matchAll(/<loc>(.*?)<\/loc>/g)].map((match) => match[1]), [`${origin}/`])
for (const page of pages) {
  const html = read(page.file)
  assert.ok(html.includes(`<html lang="${page.lang}">`))
  assert.ok(html.includes(`<link rel="canonical" href="${origin}/" />`))
  assert.ok(html.includes(`<meta property="og:url" content="${origin}/" />`))
  assert.ok(html.includes(`<title>BeatPrints Web · Online Music Poster Maker</title>`))
  assert.ok(html.includes(page.heading))
  assert.ok(html.includes('src="/examples/track.webp"'))
  assert.ok(html.includes('src="/examples/album.webp"'))
  assert.ok(html.includes(`<meta property="og:image" content="${origin}/og-image.png" />`))
  assert.ok(html.includes(`<meta name="twitter:image" content="${origin}/og-image.png" />`))
  assert.match(html, page.indexable ? /<meta name="robots" content="index, follow/ : /<meta name="robots" content="noindex, follow/)
  assert.doesNotMatch(html, /hreflang=/)
  const json = JSON.parse(html.match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1])
  assert.equal(json.url, `${origin}/`)
  assert.equal(json.inLanguage, "en")
}
for (const file of ["examples/track.webp", "examples/album.webp", "og-image.png"]) {
  assert.ok(existsSync(new URL(file, dist)))
}
console.log("SEO prerender regressions passed")
