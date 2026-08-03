# Changelog

## [1.2.0](https://github.com/sdrpsps/beatprints-web/compare/v1.1.2...v1.2.0) (2026-08-03)


### Features

* add QQ and NetEase catalog sources ([7b0d264](https://github.com/sdrpsps/beatprints-web/commit/7b0d264f4fca3482b80e827ffd8f78e92fc46a66))
* add QQ and NetEase music sources ([9ceb1fc](https://github.com/sdrpsps/beatprints-web/commit/9ceb1fcdf929e0175d17d4dc8d8b83699087c5a1))
* **api:** add NetEase and QQ Music lyrics sources ([f9b50eb](https://github.com/sdrpsps/beatprints-web/commit/f9b50ebfe1f246f2a1b597ce43573aa7d9237257))


### Bug Fixes

* enrich missing poster labels ([2ba55df](https://github.com/sdrpsps/beatprints-web/commit/2ba55df415faabb07f10a74d3cc9f1b4a6edf31f))
* localize integration display names ([08012fc](https://github.com/sdrpsps/beatprints-web/commit/08012fc38e02b01df57d286d539e27e5489c4796))
* match QQ albums without empty queries ([3a5f67a](https://github.com/sdrpsps/beatprints-web/commit/3a5f67a099ef994a57c16da559c490305304fdbe))
* preserve all album tracks in posters ([23f6fe2](https://github.com/sdrpsps/beatprints-web/commit/23f6fe2b05f0e203ff4b96b552a846fd8ab8416b))
* retain partial album title candidates ([5c4fd28](https://github.com/sdrpsps/beatprints-web/commit/5c4fd288c17e6c0f7e4ecb000ed2e9419f1f1815))
* **web:** order poster destinations explicitly ([07b3d65](https://github.com/sdrpsps/beatprints-web/commit/07b3d65559371f23a264f2f4b69ce9cd03ce6ea2))


### Code Refactoring

* **web:** manage integration sources with static registries ([3ed07dc](https://github.com/sdrpsps/beatprints-web/commit/3ed07dcce57979cc5d295b6d316606c18ee0a6c6))

## [1.1.2](https://github.com/sdrpsps/beatprints-web/compare/v1.1.1...v1.1.2) (2026-08-03)


### Bug Fixes

* initialize palette compatibility before integrations ([330171e](https://github.com/sdrpsps/beatprints-web/commit/330171e7371e8b3805d0fa91a32c5f84118c3dd7))
* initialize palette compatibility before integrations ([baf9418](https://github.com/sdrpsps/beatprints-web/commit/baf9418a07dee407a1d0615043c5de26c9f775d5))

## [1.1.1](https://github.com/sdrpsps/beatprints-web/compare/v1.1.0...v1.1.1) (2026-08-03)


### Bug Fixes

* remove unavailable lrcapi lyrics source ([80b6e58](https://github.com/sdrpsps/beatprints-web/commit/80b6e585fdab3ce72353dd8826a202f1f34d65fe))


### Code Refactoring

* make frontend music integrations pluggable ([054562c](https://github.com/sdrpsps/beatprints-web/commit/054562cddc106ed867ddd4f02217d87261df5383))
* make music integrations pluggable ([dbeab48](https://github.com/sdrpsps/beatprints-web/commit/dbeab487457753db22660155ef109812e598f213))
* modularize catalog integrations ([622ed11](https://github.com/sdrpsps/beatprints-web/commit/622ed11425062ee2d7050a8d87c2fe65910e990b))
* remove legacy rendering duplication ([f185577](https://github.com/sdrpsps/beatprints-web/commit/f185577c2ff13f39c19d699b58e17051f1d2697b))
* separate music integrations from services ([1f37ee4](https://github.com/sdrpsps/beatprints-web/commit/1f37ee40bd6ee3296a3e372b551c3cb94f3d9f7c))
* split backend orchestration and DTOs ([d5aee9c](https://github.com/sdrpsps/beatprints-web/commit/d5aee9cc0c23dc95fc23d9206721e9ad3020fd89))
* unify platform matching ([562c9eb](https://github.com/sdrpsps/beatprints-web/commit/562c9eb2828ce9437cbbb6c706c79f6071d162e5))

## [1.1.0](https://github.com/sdrpsps/beatprints-web/compare/v1.0.1...v1.1.0) (2026-07-31)


### Features

* **api:** add structured access logging ([23ed061](https://github.com/sdrpsps/beatprints-web/commit/23ed06122e717066a381353c272901babd370f2a))
* make track lyrics optional ([b186316](https://github.com/sdrpsps/beatprints-web/commit/b186316de676eb00179948917851f2e069c74cf8))

## [1.0.1](https://github.com/sdrpsps/beatprints-web/compare/v1.0.0...v1.0.1) (2026-07-31)


### Miscellaneous Chores

* release 1.0.1 ([b891bfc](https://github.com/sdrpsps/beatprints-web/commit/b891bfc4a8cdfac27e552732ad7dbdaabfc3ccb8))

## 1.0.0 (2026-07-31)


### Features

* add cross-platform music matching ([f68dccf](https://github.com/sdrpsps/beatprints-web/commit/f68dccf3e5d8d62670bec5b343dc80f0e177017b))
* add public music poster studio ([08bc309](https://github.com/sdrpsps/beatprints-web/commit/08bc3094a7f26275bd80b29a794809f19d77b126))
* add selectable platform QR codes to posters ([274f200](https://github.com/sdrpsps/beatprints-web/commit/274f2003864caca34034fa0a13da70d5df291bbf))
* auto-match Apple Music links ([dc40c9c](https://github.com/sdrpsps/beatprints-web/commit/dc40c9c13682fa43858218064b9dd8482b9f7823))
* initialize BeatPrints API monorepo ([c30a824](https://github.com/sdrpsps/beatprints-web/commit/c30a824ab845bdb0707c97d66c19ca1d9ef6390a))
* match Deezer releases to Spotify ([2ddbbc1](https://github.com/sdrpsps/beatprints-web/commit/2ddbbc1e0ca4c132bc5d67545c7f74b085c3dd93))
* render native Spotify Codes on posters ([5b706b1](https://github.com/sdrpsps/beatprints-web/commit/5b706b134dfec8238b38f439291cfece0b31fc5d))
* show album details in match cards ([c7982d1](https://github.com/sdrpsps/beatprints-web/commit/c7982d1d22384632667be54007d41188b9c4af4f))
* **web:** add multilingual interface ([78d86c9](https://github.com/sdrpsps/beatprints-web/commit/78d86c9b0b522a0ea17d8b91f6c35cb62aea16fa))
* **web:** initialize frontend design workflow ([03d0681](https://github.com/sdrpsps/beatprints-web/commit/03d06813d5da483916eb26b1d7d0136ff35cd1dc))


### Bug Fixes

* align Apple Music QR colors with Spotify ([e5faf8e](https://github.com/sdrpsps/beatprints-web/commit/e5faf8e23d3e135092bdcd9d25dd069bebd16ab9))
* **ci:** publish Docker images only from release tags ([5d894f3](https://github.com/sdrpsps/beatprints-web/commit/5d894f353bf1d73d0cda95661aa8601c66a98cbe))
* reduce container image size ([afd4eca](https://github.com/sdrpsps/beatprints-web/commit/afd4ecaedb25b6dd8c2e8eea6e4724ed6f76e8a1))
* slim runtime image and remove OpenCV dependency ([0a0e082](https://github.com/sdrpsps/beatprints-web/commit/0a0e0823faf2114b4f0f4ff15f95ab36c84ccef9))
* support unicode poster filenames ([25d99ee](https://github.com/sdrpsps/beatprints-web/commit/25d99ee2fc3a53e901329c1709ab292b95446e79))
* use BeatPrints logo in header ([2aaf442](https://github.com/sdrpsps/beatprints-web/commit/2aaf442b0eddbef423822bfd3b0406f9993a0d07))
* use official PyPI for Docker builds ([4099779](https://github.com/sdrpsps/beatprints-web/commit/40997798ded8709f94bd4dd8d73f08f1fa2ab81c))
* **web:** preserve scroll position when switching poster type ([64bc263](https://github.com/sdrpsps/beatprints-web/commit/64bc263909e5c1119b18088efb43504ee332d541))
* **web:** smooth poster loading transition ([449c6d3](https://github.com/sdrpsps/beatprints-web/commit/449c6d308c374156f15a145ed75fd68185810404))


### Performance Improvements

* speed up poster generation ([2a390d1](https://github.com/sdrpsps/beatprints-web/commit/2a390d12bff7977d691ea14a18a9401aa92eabc1))
