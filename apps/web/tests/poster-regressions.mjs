import assert from "node:assert/strict"
import { setImmediate } from "node:timers/promises"
import { createServer } from "vite"

const server = await createServer({ server: { middlewareMode: true, ws: false }, appType: "custom" })
const originals = { fetch: globalThis.fetch, indexedDB: globalThis.indexedDB, create: URL.createObjectURL, revoke: URL.revokeObjectURL }
try {
  const { usePosterStore: store, selectCanGenerate } = await server.ssrLoadModule("/src/features/poster/poster-store.ts")
  const { friendlyError } = await server.ssrLoadModule("/src/features/poster/poster-errors.ts")
  const { ApiError, parseCapabilities, fetchCapabilities } = await server.ssrLoadModule("/src/features/poster/api.ts")
  const db = await server.ssrLoadModule("/src/lib/poster-history-db.ts")
  const t = (key) => key
  assert.equal(friendlyError(new ApiError("Apple Music search is unavailable for the selected region", 502), "fallback", t).message, "poster.errors.appleRegionSearchUnavailable")
  assert.equal(friendlyError(new ApiError("cover_url must resolve only to public Internet addresses", 422, "cover-request"), "fallback", t).message, "poster.errors.coverAddressError")
  const selected = { id: "source-A", provider: "qq_music", type: "track", title: "Track A", artists: ["Artist"], cover_url: "https://example.com/cover.png", link: "https://y.qq.com/n/ryqq/songDetail/source-A" }
  const json = (data) => new Response(JSON.stringify({ code: 0, data, message: "success" }), { headers: { "Content-Type": "application/json" } })
  const capability = (key, label = key, available = true) => ({ key, label, available, reason: available ? null : "not_configured", default: false, fixed_code: false, reuses_source_links: [] })
  const capabilities = {
    wechat_qr: false,
    catalogs: [capability("qq_music"), capability("netease_music"), capability("spotify", "Spotify", false)],
    lyrics: [{ ...capability("qq_music"), default: true }, capability("lrclib")],
    destinations: [{ ...capability("qq_music"), reuses_source_links: ["qq_music"] }, capability("spotify"), capability("apple_music"), capability("netease_music")],
  }
  const reset = (state = {}) => {
    store.getState().resetSelection()
    store.setState(store.getInitialState(), true)
    store.getState().setCapabilities(capabilities)
    store.setState(state)
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

  globalThis.fetch = async (path, options) => {
    assert.equal(options.cache, "no-store")
    assert.equal(path, "/v1/capabilities")
    return new Response(JSON.stringify({ code: 0, data: capabilities, message: "success" }))
  }
  assert.deepEqual(await fetchCapabilities(), capabilities)
  assert.deepEqual(parseCapabilities(capabilities), capabilities)
  assert.throws(() => parseCapabilities({ wechat_qr: true }), /capabilities/i)
  assert.throws(() => parseCapabilities({ ...capabilities, destinations: [{ ...capability("old"), reuses_source_links: undefined }] }), /capabilities/i)
  assert.throws(() => parseCapabilities({ ...capabilities, catalogs: [capability("duplicate"), capability("duplicate")] }), /capabilities/i)
  assert.doesNotThrow(() => parseCapabilities({ ...capabilities, future_field: true }))
  assert.throws(() => parseCapabilities({ ...capabilities, catalogs: [{ ...capability("x"), supports_regions: true, regions: [] }] }), /capabilities/i)
  assert.throws(() => parseCapabilities({ ...capabilities, catalogs: [{ ...capability("x"), supports_regions: true, regions: ["us"] }] }), /capabilities/i)
  reset()
  assert.equal(store.getState().provider, "qq_music")
  assert.deepEqual(store.getState().catalogSources.map((item) => item.key), ["qq_music", "netease_music", "spotify"])
  assert.equal(store.getState().catalogSources[2].available, false)
  assert.deepEqual(store.getState().lyricsSources.map((item) => item.key), ["qq_music", "lrclib"])
  store.getState().setCapabilities({ ...capabilities, catalogs: [capability("future", "Future Music")], lyrics: [], destinations: [capability("future", "Future Music")] })
  assert.equal(store.getState().provider, "future")
  assert.equal(store.getState().destinations[0].label, "Future Music")
  assert.equal(store.getState().lyricsSources.length, 0)

  // Search providers follow the backend registry order and retain an active choice.
  const orderedCatalogs = [capability("apple_music"), capability("spotify", "Spotify", false), capability("qq_music"), capability("netease_music")]
  store.setState(store.getInitialState(), true)
  store.getState().setCapabilities({ ...capabilities, catalogs: orderedCatalogs })
  assert.deepEqual(store.getState().catalogSources.map((item) => item.key), ["apple_music", "spotify", "qq_music", "netease_music"])
  assert.equal(store.getState().provider, "apple_music")
  store.getState().setCapabilities({ ...capabilities, catalogs: orderedCatalogs, destinations: orderedCatalogs })
  assert.deepEqual(store.getState().destinations.map((item) => item.key), ["apple_music", "spotify", "qq_music", "netease_music"])
  store.setState({ provider: "qq_music" })
  store.getState().setCapabilities({ ...capabilities, catalogs: orderedCatalogs })
  assert.equal(store.getState().provider, "qq_music")
  store.setState(store.getInitialState(), true)
  store.getState().setCapabilities({ ...capabilities, catalogs: [{ ...orderedCatalogs[0], available: false }, ...orderedCatalogs.slice(1)] })
  assert.equal(store.getState().provider, "qq_music")

  // A removed destination cannot be restored or used to generate through stale state.
  reset({ kind: "album", selected: { ...selected, type: "album" }, qrPlatform: "spotify", platformMatchState: "success" })
  store.getState().setCapabilities({ ...capabilities, destinations: capabilities.destinations.filter((item) => item.key !== "spotify") })
  assert.equal(store.getState().qrPlatform, "")
  store.getState().setQrPlatform("spotify", t)
  assert.equal(store.getState().qrPlatform, "")
  store.setState({ qrPlatform: "spotify", platformMatchState: "success" })
  assert.equal(selectCanGenerate(store.getState()), false)
  store.getState().setCapabilities({ ...capabilities, catalogs: [capability("qq_music", "QQ", false)] })
  assert.equal(selectCanGenerate(store.getState()), false)
  assert.equal(store.getState().provider, "")

  reset({ kind: "album", selected: { ...selected, type: "album" }, qrPlatform: "qq_music", platformMatchState: "success" })
  assert.equal(selectCanGenerate(store.getState()), true)
  store.getState().clearCapabilities()
  assert.equal(store.getState().qrPlatform, "")
  assert.equal(selectCanGenerate(store.getState()), false)
  reset({ selected, lyricsSource: "qq_music", lyricsMode: "manual", manualLyrics: "Keep this line" })
  store.getState().setCapabilities({ ...capabilities, lyrics: [] })
  assert.equal(store.getState().manualLyrics, "Keep this line")
  assert.equal(store.getState().lyricsMode, "manual")

  reset({ kind: "album", selected: { ...selected, type: "album" }, generationState: "loading", qrPlatform: "spotify" })
  store.getState().setCapabilities({ ...capabilities, destinations: capabilities.destinations.filter((item) => item.key !== "spotify") })
  assert.equal(store.getState().generationState, "idle")
  reset({ selected, lyricsState: "success", lyricsMode: "catalog" })
  store.getState().clearCapabilities()
  assert.equal(store.getState().lyricsState, "success")

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
      store.getState().setQrFormat("wechat")
      assert.equal(searches, 1, "changing code type must not repeat matching")
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
      assert.equal(payload.qr_format, "wechat")
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

  // Restoring a disabled source keeps it selected but leaves search on an available source.
  reset()
  store.getState().restoreFromHistory({ id: "disabled-source", kind: "album", title: "Old", artists: [], theme: "Light", accent: false, filename: "old.png", blob: new Blob(["old"]), snapshot: { selectedItem: { ...selected, provider: "disabled", type: "album" } } }, t)
  assert.equal(store.getState().provider, "qq_music")
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

  // Reselecting the current region must preserve the current work and destination.
  reset({ selected, provider: "qq_music", query: "Song", qrPlatform: "spotify", platformMatchState: "success", platformUrl: urls.spotify })
  let unexpectedRequests = 0
  globalThis.fetch = async () => { unexpectedRequests += 1; throw new Error("Unexpected request") }
  store.getState().setSourceRegion("qq_music", "US", t)
  store.getState().setDestinationRegion("spotify", "US", t)
  assert.equal(store.getState().selected, selected)
  assert.equal(store.getState().platformUrl, urls.spotify)
  assert.equal(store.getState().platformMatchState, "success")
  assert.equal(unexpectedRequests, 0)

  // Region choices travel independently with the exact source identity.
  const regional = { ...capabilities, catalogs: [{ ...capability("apple_music"), supports_regions: true, regions: ["US", "JP", "CN"] }], destinations: [{ ...capability("spotify"), supports_regions: true, regions: ["US", "GB"] }] }
  store.setState(store.getInitialState(), true)
  store.getState().setCapabilities(regional)
  store.setState({ provider: "apple_music", query: "Song", sourceRegions: { apple_music: "JP" }, destinationRegions: { spotify: "GB" }, kind: "album" })
  assert.deepEqual(store.getState().catalogSources[0].regions, ["US", "JP", "CN"])
  assert.deepEqual(store.getState().destinations[0].regions, ["US", "GB"])
  store.getState().setSourceRegion("apple_music", "AQ", t)
  store.getState().setDestinationRegion("spotify", "CN", t)
  assert.equal(store.getState().sourceRegions.apple_music, "JP")
  assert.equal(store.getState().destinationRegions.spotify, "GB")
  const requests = []
  globalThis.fetch = async (path, options) => {
    requests.push({ path: String(path), options })
    if (String(path).startsWith("/v1/search")) return json([{ ...selected, provider: "apple_music", type: "album" }])
    if (String(path).includes("/options")) return json({ candidates: [], match: { type: "album", url: urls.spotify, title: "Match", artists: [] } })
    if (String(path).includes("/resolve")) return json({ type: "album", url: urls.spotify, title: "Match", artists: [] })
    return new Response("poster", { status: 200 })
  }
  await store.getState().search(t)
  assert.match(requests[0].path, /region=JP/)
  const regionalSelected = store.getState().searchResults[0]
  assert.equal(regionalSelected.source_region, "JP")
  store.getState().selectResult(regionalSelected, t)
  store.getState().setQrPlatform("spotify", t)
  await setImmediate()
  assert.match(requests[1].path, /source_region=JP/)
  assert.match(requests[1].path, /destination_region=GB/)
  await store.getState().generate(t)
  const body = JSON.parse(requests.at(-1).options.body)
  assert.equal(body.source_region, "JP")
  assert.equal(body.destination_region, "GB")
  assert.equal(body.catalog_id, regionalSelected.id)
  store.getState().showManualPlatformLink()
  store.getState().setPlatformUrl(urls.spotify)
  await store.getState().resolveManualPlatformUrl(t)
  assert.match(requests.at(-1).path, /region=GB/)

  // Removed regions cannot be restored from history or survive a capability refresh.
  store.getState().restoreFromHistory({ ...history, snapshot: { ...history.snapshot, selectedItem: { ...regionalSelected, source_region: "AQ" }, qrPlatform: "spotify", destinationRegion: "GB", platformUrl: urls.spotify } }, t)
  assert.equal(store.getState().selected, undefined)
  assert.equal(store.getState().qrPlatform, "")
  store.getState().restoreFromHistory({ ...history, snapshot: { ...history.snapshot, selectedItem: regionalSelected, qrPlatform: "spotify", destinationRegion: "CN", platformUrl: urls.spotify } }, t)
  assert.equal(store.getState().selected, regionalSelected)
  assert.equal(store.getState().qrPlatform, "")
  store.setState({ selected: regionalSelected, sourceRegions: { apple_music: "JP" } })
  store.getState().setCapabilities({ ...regional, catalogs: [{ ...regional.catalogs[0], regions: ["US", "CN"] }] })
  assert.equal(store.getState().selected, undefined)
  assert.equal(store.getState().sourceRegions.apple_music, "US")

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
