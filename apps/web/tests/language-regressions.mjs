import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { runInNewContext } from "node:vm"
import i18next from "i18next"
import LanguageDetector from "i18next-browser-languagedetector"
import { createServer } from "vite"

const server = await createServer({ server: { middlewareMode: true, ws: false }, appType: "custom" })
const originalWindow = Object.getOwnPropertyDescriptor(globalThis, "window")
const originalNavigator = Object.getOwnPropertyDescriptor(globalThis, "navigator")
const values = new Map()
const storage = {
  getItem: (key) => values.get(key) ?? null,
  setItem: (key, value) => values.set(key, String(value)),
  removeItem: (key) => values.delete(key),
}
try {
  Object.defineProperty(globalThis, "window", { configurable: true, value: { location: { pathname: "/" }, localStorage: storage } })
  const { languageDetection, languageStorageKey } = await server.ssrLoadModule("/src/i18n/detection.ts")
  const { defaultLanguage, supportedLanguages, resources } = await server.ssrLoadModule("/src/i18n/resources.ts")
  const { languageFromPath } = await server.ssrLoadModule("/src/i18n/home.ts")
  const { localizedReleaseNotes } = await server.ssrLoadModule("/src/features/poster/release-notes-content.ts")
  async function detect(path, languages, saved) {
    values.clear()
    if (saved) values.set(languageStorageKey, saved)
    window.location.pathname = path
    Object.defineProperty(globalThis, "navigator", { configurable: true, value: { languages, language: languages[0] } })
    const instance = i18next.createInstance()
    await instance.use(LanguageDetector).init({
      resources, supportedLngs: supportedLanguages, fallbackLng: defaultLanguage,
      load: "currentOnly", detection: languageDetection,
    })
    return instance.resolvedLanguage
  }
  assert.equal(await detect("/", ["zh-CN"]), "zh-CN")
  assert.equal(await detect("/", ["zh-Hant-HK"]), "zh-TW")
  assert.equal(await detect("/", ["zh-Hans-SG"]), "zh-CN")
  assert.equal(await detect("/", ["fr-FR"]), "en")
  assert.equal(await detect("/", ["fr-FR", "zh-TW"]), "zh-TW")
  assert.equal(await detect("/", ["ja-JP"]), "ja")
  assert.equal(await detect("/", ["ko-KR"]), "ko")
  assert.equal(await detect("/", ["fr-FR", "ja-JP"]), "ja")
  assert.equal(await detect("/", ["zh-CN"], "en"), "en")
  assert.equal(await detect("/en/", ["zh-CN"], "zh-TW"), "en")
  assert.equal(await detect("/zh-CN/", ["en-US"], "zh-TW"), "zh-CN")
  assert.equal(await detect("/zh-TW/", ["en-US"]), "zh-TW")
  assert.equal(await detect("/ja/", ["ko-KR"], "zh-TW"), "ja")
  assert.equal(await detect("/ko/", ["ja-JP"], "en"), "ko")
  for (const language of supportedLanguages) {
    assert.equal(languageFromPath(`/${language}`), language)
    assert.equal(languageFromPath(`/${language}/`), language)
  }
  assert.equal(languageFromPath("/unknown/"), undefined)
  const release = `<!-- release-summary:start -->
<!-- release-summary:zh-TW:start -->
## 繁體中文
- 新增功能
<!-- release-summary:zh-TW:end -->
<!-- release-summary:en:start -->
## English
- New feature
<!-- release-summary:en:end -->
<!-- release-summary:ja:start -->
## 日本語
- 新機能
<!-- release-summary:ja:end -->
<!-- release-summary:ko:start -->
## 한국어
- 새 기능
<!-- release-summary:ko:end -->
<!-- release-summary:end -->
## Technical changes
- Internal details`
  assert.equal(localizedReleaseNotes(release, "zh-TW"), "## 繁體中文\n- 新增功能")
  assert.equal(localizedReleaseNotes(release, "ja"), "## 日本語\n- 新機能")
  assert.equal(localizedReleaseNotes(release, "ko"), "## 한국어\n- 새 기능")
  assert.equal(localizedReleaseNotes(release, "zh-CN"), "## English\n- New feature")
  assert.equal(localizedReleaseNotes("## Old release\n- Details", "ja"), "## Old release\n- Details")
  assert.equal(localizedReleaseNotes("<!-- release-summary:start -->broken", "ja"), "<!-- release-summary:start -->broken")

  function flatten(object, prefix = "") {
    return Object.fromEntries(Object.entries(object).flatMap(([key, value]) => {
      const path = prefix ? `${prefix}.${key}` : key
      return typeof value === "string" ? [[path, value]] : Object.entries(flatten(value, path))
    }))
  }
  const english = flatten(resources.en.translation)
  for (const language of supportedLanguages) {
    const translations = flatten(resources[language].translation)
    assert.deepEqual(Object.keys(translations).sort(), Object.keys(english).sort(), `${language} must translate every key`)
    for (const [key, value] of Object.entries(english)) {
      const placeholders = (text) => [...text.matchAll(/{{\s*([^}]+?)\s*}}/g)].map((match) => match[1]).sort()
      assert.ok(translations[key].trim(), `${language}: ${key} must not be empty`)
      assert.deepEqual(placeholders(translations[key]), placeholders(value), `${language}: ${key} must preserve placeholders`)
    }
  }

  const source = readFileSync(new URL("../index.html", import.meta.url), "utf8")
  const bootstrap = source.match(/<script id="app-bootstrap">([\s\S]*?)<\/script>/)?.[1]
  assert.ok(bootstrap, "the pre-paint app guard must be present")
  function runBootstrap() {
    const attributes = new Set()
    const document = {
      documentElement: {
        setAttribute: (name) => attributes.add(name),
      },
    }
    runInNewContext(bootstrap, { document })
    return attributes
  }
  assert.equal(runBootstrap().has("data-app-pending"), true)
  assert.match(source, /html\[data-app-pending\] #root \{ display: none; \}/)
  assert.doesNotMatch(source, /id="app-fallback"/)
  console.log("Language detection regressions passed")
} finally {
  await server.close()
  if (originalWindow) Object.defineProperty(globalThis, "window", originalWindow)
  else delete globalThis.window
  if (originalNavigator) Object.defineProperty(globalThis, "navigator", originalNavigator)
  else delete globalThis.navigator
}
