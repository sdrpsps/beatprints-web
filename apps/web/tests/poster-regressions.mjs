import assert from "node:assert/strict"
import { setImmediate } from "node:timers/promises"
import { createServer } from "vite"

const server = await createServer({ server: { middlewareMode: true }, appType: "custom" })
const originals = { fetch: globalThis.fetch, indexedDB: globalThis.indexedDB, create: URL.createObjectURL, revoke: URL.revokeObjectURL }
try {
  const { usePosterStore: store, selectCanGenerate } = await server.ssrLoadModule("/src/features/poster/poster-store.ts")
  const db = await server.ssrLoadModule("/src/lib/poster-history-db.ts")
  const t = (key) => key
  const selected = { id: "source-A", provider: "qq_music", type: "track", title: "Track A", artists: ["Artist"], cover_url: "https://example.com/cover.png", link: "https://y.qq.com/n/ryqq/songDetail/source-A" }
  const json = (data) => new Response(JSON.stringify({ code: 0, data, message: "success" }), { headers: { "Content-Type": "application/json" } })
  const reset = (state = {}) => {
    store.getState().resetSelection()
    store.setState({ ...store.getInitialState(), ...state }, true)
  }
  const pendingFetch = () => {
    let finish
    globalThis.fetch = (_url, options) => new Promise((resolve) => { finish = { resolve, options } })
    return () => finish
  }
  const revoked = []
  let serial = 0
  URL.createObjectURL = () => `blob:regression-${++serial}`
  URL.revokeObjectURL = (url) => revoked.push(url)
  globalThis.indexedDB = undefined

  // A late lyrics response must not resurrect the previous selection.
  reset({ selected })
  let current = pendingFetch()
  let pending = store.getState().loadLyrics(selected, "qq_music", t)
  store.getState().resetSelection()
  assert.equal(current().options.signal.aborted, true)
  current().resolve(json({ instrumental: false, lines: [{ index: 1, text: "Old lyrics" }] }))
  await pending
  assert.equal(store.getState().lyricsState, "idle")
  assert.deepEqual(store.getState().lyrics, [])

  // Only the active source search may update results, even with an empty query.
  reset({ query: "Track A" })
  current = pendingFetch()
  pending = store.getState().search(t)
  store.getState().setQuery("")
  store.getState().setProvider("netease_music", t)
  current().resolve(json([selected]))
  await pending
  assert.deepEqual(store.getState().searchResults, [])

  // Success frees the previous image and preserves an edit made while waiting.
  reset({ kind: "album", selected: { ...selected, type: "album" } })
  let posts = 0
  globalThis.fetch = async (_url, options) => {
    posts += 1
    const payload = JSON.parse(options.body)
    assert.equal(payload.provider, selected.provider)
    assert.equal(payload.catalog_id, selected.id)
    assert.equal(payload.qr_platform, undefined)
    assert.equal(payload.platform_links, undefined)
    return new Response("poster", { status: 200 })
  }
  await store.getState().generate(t)
  assert.equal(store.getState().generationState, "success", "storage unavailable must not fail PNG generation")
  const first = store.getState().output.url
  await store.getState().generate(t)
  assert.ok(revoked.includes(first))
  assert.equal(posts, 2)
  current = pendingFetch()
  pending = store.getState().generate(t)
  store.getState().setTheme("Dark")
  current().resolve(new Response("old-theme-poster"))
  await pending
  assert.equal(store.getState().outputStale, true)

  // Changing item kind cancels generation; duplicate submissions are ignored.
  current = pendingFetch()
  pending = store.getState().generate(t)
  const active = current()
  await store.getState().generate(t)
  assert.equal(current(), active)
  const previousOutput = store.getState().output
  store.getState().setKind("track")
  assert.equal(active.options.signal.aborted, true)
  active.resolve(new Response("old-album-poster"))
  await pending
  assert.equal(store.getState().output, previousOutput)
  assert.equal(store.getState().generationState, "success")
  assert.equal(store.getState().outputStale, true)

  // Viewing another image while generating must not be overwritten by a late response.
  reset({ kind: "album", selected: { ...selected, type: "album" } })
  current = pendingFetch()
  pending = store.getState().generate(t)
  const viewed = { url: "blob:history-view", title: "History", filename: "history.png" }
  store.getState().showOutput(viewed)
  current().resolve(new Response("late-poster"))
  await pending
  assert.equal(store.getState().output, viewed)

  // Every enabled QR destination supports the same track/album contract.
  const urls = { spotify: "https://open.spotify.com/track/4uLU6hMCjMI75M1A2tKUQC", apple_music: "https://music.apple.com/us/album/example/123?i=456", qq_music: "https://y.qq.com/n/ryqq/songDetail/current", netease_music: "https://music.163.com/song?id=123" }
  for (const kind of ["track", "album"]) {
    for (const [platform, url] of Object.entries(urls)) {
      reset({ kind, selected: { ...selected, type: kind }, lyricsMode: "manual" })
      const source = store.getState().selected
      const match = { url, type: kind, title: "Destination", artists: ["Artist"] }
      let searches = 0, resolutions = 0, payload
      globalThis.fetch = async (path, options) => {
        if (String(path).includes("/options?")) { searches += 1; return json({ match, candidates: [match] }) }
        if (String(path).includes("/resolve?")) { resolutions += 1; return json({ ...match, title: "Current destination" }) }
        payload = JSON.parse(options.body)
        return new Response("poster")
      }
      store.getState().setQrPlatform(platform, t)
      await setImmediate()
      assert.equal(store.getState().platformMatchState, "success")
      assert.equal(store.getState().platformMatch.title, "Destination")
      store.getState().showPlatformCandidates(t)
      assert.equal(searches, 1, "opening cached candidates must not repeat searches")
      assert.equal(selectCanGenerate(store.getState()), false)
      await store.getState().selectPlatformCandidate(match, t)
      assert.equal(resolutions, 1, "selected candidate must fetch current metadata")
      assert.equal(store.getState().platformMatch.title, "Current destination")
      assert.equal(store.getState().selected, source)
      store.getState().showManualPlatformLink()
      store.getState().setPlatformUrl(url)
      await store.getState().resolveManualPlatformUrl(t)
      assert.equal(store.getState().selected, source)
      assert.equal(selectCanGenerate(store.getState()), true)
      await store.getState().generate(t)
      assert.equal(payload.provider, selected.provider)
      assert.equal(payload.catalog_id, selected.id)
      assert.equal(payload.platform_links[platform], url)
      store.getState().showPlatformCandidates(t)
      assert.equal(searches, 1)
      store.getState().showManualPlatformLink()
      globalThis.fetch = async () => json({ ...match, type: kind === "track" ? "album" : "track" })
      await store.getState().resolveManualPlatformUrl(t)
      assert.equal(store.getState().platformManualState, "error")
      assert.equal(selectCanGenerate(store.getState()), false)
    }
  }

  // Editing a link cancels its resolution, and an invalid target cannot generate.
  reset({ kind: "album", selected, qrPlatform: "qq_music", platformChoiceMode: "manual", platformUrl: urls.qq_music })
  current = pendingFetch()
  pending = store.getState().resolveManualPlatformUrl(t)
  store.getState().setPlatformUrl("https://y.qq.com/n/ryqq/albumDetail/new")
  current().resolve(json({ type: "album", url: urls.qq_music, title: "Old link", artists: [] }))
  await pending
  assert.equal(store.getState().platformManualState, "idle")
  assert.equal(store.getState().platformManualMatch, undefined)
  store.setState({ qrPlatform: "disabled", platformChoiceMode: "automatic", platformMatchState: "success" })
  assert.equal(selectCanGenerate(store.getState()), false)

  // Empty lyrics and old snapshots must clear prior state; saved links are re-resolved.
  const history = { id: "saved", createdAt: 0, kind: "track", title: "Saved", artists: ["Artist"], theme: "Light", accent: false, filename: "saved.png", blob: new Blob(["saved"]), snapshot: { provider: selected.provider, catalogId: selected.id, selectedItem: selected, lyrics: "" } }
  reset({ selected, instrumental: true, instrumentalText: "Old text", manualLyrics: "Old lyrics", lyricEdits: { 1: "Old edit" }, platformChoiceMode: "manual" })
  store.getState().restoreFromHistory(history, t)
  assert.equal(store.getState().manualLyrics, "")
  assert.equal(store.getState().instrumental, false)
  assert.deepEqual(store.getState().lyricEdits, {})
  assert.equal(store.getState().qrPlatform, "")
  store.getState().restoreFromHistory({ ...history, snapshot: undefined }, t)
  assert.equal(store.getState().selected, undefined)
  store.getState().restoreFromHistory({ ...history, snapshot: { ...history.snapshot, instrumentalText: "" } }, t)
  assert.equal(store.getState().instrumental, true, "legacy instrumental snapshots include empty text")
  current = pendingFetch()
  store.getState().restoreFromHistory({ ...history, snapshot: { ...history.snapshot, qrPlatform: "qq_music", platformUrl: urls.qq_music } }, t)
  assert.equal(selectCanGenerate(store.getState()), false)
  current().resolve(json({ type: "track", url: urls.qq_music, title: "Current saved link", artists: [] }))
  await setImmediate()
  assert.equal(store.getState().platformManualMatch.title, "Current saved link")
  assert.equal(selectCanGenerate(store.getState()), true)

  // Storage rejection/abort is caught and all opened connections are closed.
  let closed = 0, outcome = "abort"
  globalThis.indexedDB = { open() {
    const request = {}
    queueMicrotask(() => {
      request.result = { close() { closed += 1 }, transaction() {
        const transaction = { error: new Error("quota"), objectStore() { return { put() {}, delete() {}, clear() {}, index() { return { count() { return {} }, openCursor() { return {} } } } } } }
        queueMicrotask(() => outcome === "success" ? transaction.oncomplete() : transaction.onabort())
        return transaction
      } }
      request.onsuccess()
    })
    return request
  } }
  assert.equal(await db.saveHistoryItem(history), false)
  assert.equal(await db.deleteHistoryItem("saved"), false)
  assert.equal(await db.clearAllHistory(), false)
  assert.deepEqual(await db.getAllHistory(), [])
  assert.equal(closed, 4)
  outcome = "success"
  assert.equal(await db.saveHistoryItem(history), true)
  assert.equal(closed, 5)
  reset()
  console.log("Poster regressions passed (state, resources, storage, four destinations × track/album).")
} finally {
  globalThis.fetch = originals.fetch
  globalThis.indexedDB = originals.indexedDB
  URL.createObjectURL = originals.create
  URL.revokeObjectURL = originals.revoke
  await server.close()
}
