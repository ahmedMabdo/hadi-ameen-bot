---
id: 8orders/customer-ordering/restaurant-and-menu-discovery/search-technical
note_type: technical
rule_count: 14
context: Customer Ordering
feature: Restaurant & Menu Discovery
sources:
  - path: AdminUi/Controllers/ElasticSerach/ElasticSerachController.cs
    sha1: 78fd0dfb607e
  - path: Shared/TalabatkApplication/Commands/CreateElasticSerachIndiciesCommand/CreateElasticSerachIndiciesCommand.cs
    sha1: 001dc0cc9da3
  - path: Shared/TalabatkApplication/Feature/Search/Queries/SearchItemsWithFiltersAndSortingOptionsQuery.cs
    sha1: 8afd528ecc9c
  - path: Shared/TalabatkData/ElasticSerarchServices/CachingEmbeddingService.cs
    sha1: b5fff5480eea
  - path: Shared/TalabatkData/ElasticSerarchServices/ElasticHybridSearchOptions.cs
    sha1: a6501d8e15d1
  - path: Shared/TalabatkData/ElasticSerarchServices/ElasticSearchConfiguration.cs
    sha1: b4fdbc29d923
  - path: Shared/TalabatkData/ElasticSerarchServices/ElasticSearchServices.ItemHybrid.cs
    sha1: 0abb0deaa4c9
  - path: Shared/TalabatkData/ElasticSerarchServices/ElasticSearchServices.UnifiedSearchScoring.cs
    sha1: 1adebe317a59
  - path: Shared/TalabatkData/ElasticSerarchServices/ElasticSearchServices.cs
    sha1: 832f036aa0b8
  - path: Shared/TalabatkData/ElasticSerarchServices/ItemElasticModel.cs
    sha1: 6327f0eddbc8
  - path: Shared/TalabatkData/ElasticSerarchServices/ItemHybridRrfMerge.cs
    sha1: 0abb2b9c4cc2
  - path: Shared/TalabatkData/ElasticSerarchServices/MerchantSearchScoringService.cs
    sha1: 98dbbfa26bee
  - path: Shared/TalabatkData/ElasticSerarchServices/OllamaEmbeddingService.cs
    sha1: 622de76d6e44
  - path: Shared/TalabatkData/ElasticSerarchServices/RestaurantElasticModel.cs
    sha1: c4da8ed400e4
  - path: Shared/TalabatkLogic/Constants/Features.cs
    sha1: fa91c37f4d2c
  - path: TalabatkAPIs/Controllers/Search/SearchController.cs
    sha1: 261ea8084ed6
  - path: TalabatkAPIs/Controllers/SearchHistory/SearchHistoryController.cs
    sha1: 7dc36cb6c0bd
last_updated: 2026-08-23
tags: [customer-ordering, restaurant-menu-discovery, technical, backend-data, backend-application]
---
# Search — Technical

> **Layer:** Backend-Data (`TalabatkData.ElasticSerarchServices` — Elasticsearch client, scoring
> service, embedding services) + Backend-Application (MediatR query orchestration)
> **Context:** Customer Ordering   **Feature:** Restaurant & Menu Discovery
> **Source paths:** `Shared/TalabatkData/ElasticSerarchServices/` (folder name misspelled in the
> repo — path kept as-is), `Shared/TalabatkApplication/Feature/Search/Queries/SearchItemsWithFiltersAndSortingOptionsQuery.cs`
> **Canonical spec:** `Shared/TalabatkData/ElasticSerarchServices/SearchScoring.md` — this note
> bridges to it for scoring formulas, weights, rejected alternatives and test names; it is not
> restated here. **Last Updated:** 2026-08-21

Merchant/item search: Elasticsearch retrieval (literal + fuzzy) plus an optional Ollama-embedding
hybrid semantic layer, feeding a scoring service that ranks and filters merchants before menu items
are re-loaded from the relational database for display.

## Business Rules

### Rule 1: Two search-ranking code paths, gated by the `UnifiedSearchScoring` feature flag
- **Plain language:** whether a request uses the newer weighted-scoring ranking or the older
  Elasticsearch-order ranking depends on an Esquio flag, checked per request.
- **Source:** `SearchItemsWithFiltersAndSortingOptionsQuery.cs:380-408` (`SearchForItemsWithElasticSearch`
  branches on `Features.UnifiedSearchScoring` into `SearchForItemsWithUnifiedScoringAsync` at `:410`
  or `SearchForItemsWithLegacyUnifiedAsync` at `:564`); flag constant at `Features.cs:19`.

### Rule 2: Merchant ranking formula, weights and rejected alternatives — see `SearchScoring.md` (authority)
- **Plain language:** each merchant's final score combines a restaurant-name signal and a menu-item
  signal (literal + fuzzy Elasticsearch scores), each multiplied by its own configurable weight, then
  added — restaurant and item sides are **not** independently normalized to 0–1 before weighting
  (`SearchScoring.md` explains why, with the rejected normalize-per-side alternative).
- **Source:** Implementation in `MerchantSearchScoringService.RankMerchants`
  (`MerchantSearchScoringService.cs:25-297`); options bound from `ElasticSearch:SearchScoring` at
  `ElasticSearchConfiguration.cs:97`. Formulas/weights/examples/test names: `SearchScoring.md`.

### Rule 3: Below-threshold merchants are excluded, not just deprioritized
- **Source:** `MerchantSearchScoringService.cs:182-224` (`PassesScoreThreshold` applied via
  `MinResultThresholdPercent`/`MinMerchantFinalScore`/`MaxPercentCutoffScore`, options declared at
  `SearchScoringOptions.cs:11,16,22`). `MinMerchantFinalScore` and `MaxPercentCutoffScore` exist in
  code but are **not** documented in `SearchScoring.md`'s "Top-level keys" section — flagged as a
  gap in the canonical spec's coverage, not a contradiction of it.

### Rule 4: Final sort is availability tier, then score, then restaurant rate
- **Source:** `MerchantSearchScoringService.cs:223-230`
  (`OrderBy(GetAvailabilitySortTier).ThenByDescending(MerchantFinalScore).ThenByDescending(rate)`);
  tiers defined at `:387-395` (`0`=open & not busy, `1`=open & busy, `2`=closed).

### Rule 5: Semantic (Ollama-embedding) expansion is gated by index version, feature flag and query length
- **Plain language:** the kNN/RRF semantic expansion of item search only runs when the v2 item index
  is configured, the `HybridSearch` feature is on, and the search text is at least
  `MinQueryLengthForSemantic` characters (default 2).
- **Source:** `ElasticSearchServices.UnifiedSearchScoring.cs:122-132` (`ExpandItemHitsWithHybridAsync`
  early-return gate); kNN query + client-side RRF merge at `:151-210`; rank constant/K/candidates from
  `ElasticHybridSearchOptions.cs:9-13` (`MinQueryLengthForSemantic` default `2` at `:13`); merge math
  in `ItemHybridRrfMerge.cs:73-109`. A failure anywhere in this path (embedding call or ES kNN query)
  is caught and logged as a warning, silently falling back to lexical-only item signals
  (`ElasticSearchServices.UnifiedSearchScoring.cs:212-215`).

### Rule 6: Ollama vs. HTTP embedding backend is one boolean switch — confirmed prod/dev divergence
- **Source:** `ElasticSearchConfiguration.cs:77-82` (`ElasticSearch:UseOllamaEmbeddings` selects
  `OllamaEmbeddingService` vs `HttpEmbeddingService`); default model `nomic-embed-text` (768 dims),
  `OllamaEmbeddingService.cs:15,48`. **Per conflict #361** (authoritative, not re-verified here):
  `true` in every `appsettings.Development.json`, `false` in every production `appsettings.json` —
  the Ollama path this note and `SearchScoring.md` describe is not the one production runs, and
  prod's `ElasticSearch:Ollama:BaseUrl` still points at `http://127.0.0.1:11434`.

### Rule 7: Query embeddings are cached two-tier (memory + Redis), ~12h default TTL
- **Source:** `CachingEmbeddingService.cs:39-40` (`DefaultCacheMinutes=720`,
  `MemoryTierSlidingMinutes=30`); cache key includes model, dimensions, role and normalized text
  (`:120-131`); Redis is optional/best-effort, failures logged and swallowed (`:151-192`). Only
  `Query`-role embeddings are cached — indexing/passage embeddings are not (`:69-71`).

### Rule 8: `OutOfStock` in search results now ignores the mart-only guard — confirmed regression
- **Per conflict #325** (authoritative, very high severity, not re-investigated here). Directly
  verified in the current file: all three item-projection sites compute
  `OutOfStock = x.CurrentStockQuantity <= 0` with no `IsStore` guard, at
  `SearchItemsWithFiltersAndSortingOptionsQuery.cs:491` (unified-scoring path), `:628` (legacy path)
  and `:930` (backfill path) — matching the conflict's own citation. Non-mart restaurant items, which
  never populate `CurrentStockQuantity`, now report `OutOfStock=true` in search; the dedicated
  `MenuItem.OutOfStock` column is no longer read by any of the three paths.

### Rule 9: A restaurant with no description row for the request's language throws instead of degrading
- **Per conflict #199** (authoritative, not re-investigated here). Directly verified: the plain
  dictionary indexer `restaurantDescriptionsDict[x.TA_MenuCategory.RestaurantId ?? 0]` is used at
  `SearchItemsWithFiltersAndSortingOptionsQuery.cs:492`, `:629` and `:931` in the current file (the
  conflict cites `:450`,`:587`,`:866` — the discrepancy looks like line drift from the 2026-08-20
  rebase noted in conflict #325, not a different finding). A restaurant missing a `RestaurantDescription`
  row for the requested `LanguageId` throws `KeyNotFoundException`; the sibling `TryGetValue` pattern
  used correctly elsewhere in the same file (e.g. `merchantIsOpen.TryGetValue`, `:1101`) is not used
  here.

### Rule 10: Legacy `SearchUnifiedAsync` has no null-guard on `storeTypeIds`/`foodTypeIds`
- **Per conflict #215** (authoritative, high confidence, not re-investigated here). Directly
  verified: `ConvertToFieldValues(List<int> ids) => ids.ConvertAll(...)`
  (`ElasticSearchServices.cs:1275-1277`) is called on `storeTypeIds`/`foodTypeIds` at
  `ElasticSearchServices.cs:1301,1304` inside `SearchUnifiedAsync` (declared `:1279`) with no
  null-check — a null list throws `NullReferenceException`. Reachable because
  `SearchItemsWithFiltersAndSortingOptionsQuery.StoreTypes` (`:32`) has no default initializer, unlike
  sibling `FoodTypes` (`:31`, `= new List<int>()`).

### Rule 11: Item index (legacy vs. v2/vector) is chosen dynamically, independent of the embedding-write flag
- **Source:** `ElasticSearchServices.ItemHybrid.cs:45-48` (`ShouldUseItemIndexV2Async` = v2 index
  name configured **and** `Features.HybridSearch` enabled), effective name resolved at `:136-144`.
  A third, independent flag, `Features.ItemEmbeddingIndexing` (`Features.cs:17`), controls whether
  embeddings are actually computed/persisted during indexing jobs — `HybridSearch` alone can route
  search reads to the v2 index without any vectors ever having been written to it
  (`ElasticSearchServices.ItemHybrid.cs:84-89`).

### Rule 12: Search-index rebuild endpoint is anonymous and currently a no-op
- **Per conflicts #46 / #70 / #374** (authoritative, not re-investigated here). Directly verified:
  `GET api/ElasticSerach/CreateIndecies` (`AdminUi/Controllers/ElasticSerach/ElasticSerachController.cs`
  — `[AllowAnonymous]` at class level `:15`, `[HttpGet]` action `:26-32`) sends
  `CreateElasticSerachIndiciesCommand`; per conflict #70, that handler's body is fully commented out
  and unconditionally returns `Result.Success()` (`CreateElasticSerachIndiciesCommand.cs:24-39`, not
  re-read in this pass). Net effect: an unauthenticated `GET` that claims to rebuild the search index
  and currently does nothing.

### Rule 13: Deleting a saved search-history entry has no ownership check (IDOR)
- **Per conflict #350** (authoritative, part of a 5-IDOR cluster, not re-investigated here):
  `DeleteSearchHistoryCommand` matches on `Where(x => x.Id == request.SearchId)` with no customer-id
  filter (`DeleteSearchHistoryCommand.cs:13,28`, not re-read in this pass). Directly verified the
  endpoint: `SearchHistoryController.cs:61-71` (`POST api/SearchHistory/DeleteSearchHistory`),
  gated only by the controller's class-level `[Authorize(AuthenticationSchemes = JwtBearerDefaults.AuthenticationScheme)]`
  (`:18` — any authenticated bearer, not further role-scoped) — any authenticated customer can delete
  another customer's search-history row by id.

### Rule 14: Elasticsearch transport trusts every certificate, on a bare production IP
- **Per conflict #357** (authoritative, high severity, not re-investigated here). Directly verified:
  `.ServerCertificateValidationCallback((sender, certificate, chain, sslPolicyErrors) => true)`
  (`ElasticSearchConfiguration.cs:26-27`) has no environment guard, unlike the API-key branch
  immediately below it which is correctly conditional (`:30-33`).

## Key Fields
| Field / Setting | Meaning | Constraints |
|---|---|---|
| `ElasticSearch:SearchScoring.*` (`SearchScoringOptions`) | Merchant-ranking weights, window size, cutoff thresholds | Canonical: `SearchScoring.md`; bound at `ElasticSearchConfiguration.cs:97` |
| `ElasticSearch:UseOllamaEmbeddings` | Ollama vs. plain-HTTP embedding backend switch | `false` in prod, `true` in dev (Rule 6, #361) |
| `ElasticSearch:HybridSearch.*` (`ElasticHybridSearchOptions`) | kNN + RRF hybrid semantic expansion tuning | `MinQueryLengthForSemantic` default `2` (`ElasticHybridSearchOptions.cs:13`) |
| `SearchItemDto.OutOfStock` | Out-of-stock flag surfaced per item in search results | Currently `CurrentStockQuantity<=0` only, no mart guard (Rule 8, #325) |
| `RestaurantElasticModel` | ES document shape for restaurant retrieval | `RestaruantId` (sic, `RestaurantElasticModel.cs:17`), `RestaurantAreaIds`, `FoodTypeIds` |
| `ItemElasticModel` | ES document shape for item retrieval | `ItemNameEmbedding float[768]` populated only when indexed to the v2 index (`ItemElasticModel.cs:22`) |
| `Features.UnifiedSearchScoring` / `HybridSearch` / `ItemEmbeddingIndexing` | Esquio flags gating the three independent axes of search behavior | Rules 1, 5/11 |

## Dependencies & Integrations
| Depends on / integrates | Side/Context | Via | Notes |
|---|---|---|---|
| Elasticsearch 8.15.6 cluster | External infra (Backend-Data) | `ElasticsearchClient` (`Elastic.Clients.Elasticsearch`) | Local dev stack: `docker-compose.elasticsearch-local.yml` (ES 8.15.6 + Kibana 8.15.6, no TLS/security, `discovery.type=single-node`); prod connects to a bare IP with cert validation disabled (Rule 14) |
| Ollama (`nomic-embed-text`, 768 dims) | External infra | `OllamaEmbeddingService` (`OllamaEmbeddingService.cs`), HTTP client, `/api/embed` with legacy `/api/embeddings` fallback | Only active when `UseOllamaEmbeddings=true` — currently false in prod (Rule 6); local Ollama container in `docker-compose.elasticsearch-local.yml` |
| Redis | Backend-Data (Cross-cutting) | `CachingEmbeddingService` L2 cache, optional via `IConnectionMultiplexer` | Best-effort; a Redis outage degrades to memory-only caching, never fails a search (Rule 7) |
| [[Restaurant.technical\|Restaurant]] | Backend-Domain | `LoadEligibleRestaurantSearchItemsAsync` (`SearchItemsWithFiltersAndSortingOptionsQuery.cs:1025-1056`) | Restaurant open/busy/rate feed merchant ranking (Rule 4) and eligibility filtering |
| [[MenuItem.technical\|MenuItem]] | Backend-Domain | Item projection into `SearchItemDto` | Source of `CurrentStockQuantity`/`OutOfStock` (Rule 8) and item price/availability |
| [[Offers.technical\|Offers]] | Backend-Domain | `LoadActiveOffersAsync` (`SearchItemsWithFiltersAndSortingOptionsQuery.cs:259-276`) | Per-item discount applied to search results |
| Search History (`SearchHistoryController`, `AddSearchHistoryRecordCommand`, `DeleteSearchHistoryCommand`, `GetMostSearchedQuery` — no dedicated note) | Backend-Application | Adjacent feature sharing the search surface | IDOR gap, Rule 13 / #350 |
| Esquio feature management | Cross-cutting | `IFeatureManager` | Gates Rules 1, 5, 11 |
| `TalabatkAPIs/Controllers/Search/SearchController.cs` | API host (Customer-facing) | `SearchWithFiltersAndSortingOptions` (`:66-103`) / `...V2` (`:105-143`) send `SearchItemsWithFiltersAndSortingOptionsQuery` | Class-level `[Authorize(AuthenticationSchemes = JwtBearerDefaults.AuthenticationScheme)]` (`:33`) |
| `AdminUi/Controllers/ElasticSerach/ElasticSerachController.cs` | API host (Admin) | `CreateIndecies` (`:26-32`) | Anonymous, currently a no-op (Rule 12) |

## Change Surface
| Signal | Value | Notes |
|--------|-------|-------|
| Direct dependents (Ring 1) | Restaurant, MenuItem, Offers, RestaurantReview (review counts), StoreTypes | Read-only consumption; Search does not write back to any of these |
| Sides touched | 3 confirmed | Backend-Data (`TalabatkData.ElasticSerarchServices`), Backend-Application (`SearchItemsWithFiltersAndSortingOptionsQuery` and siblings), API host (`TalabatkAPIs`, `AdminUi`) |
| Cross-context integrations | 0 confirmed | Purely a Customer Ordering read path over its own domain data plus external ES/Ollama/Redis infra |
| Domain events involved | 0 | No events raised by this subsystem |
| Hub? | Medium | Feeds home search, filters/sorting, and (not traced in this pass) in-restaurant search and autocomplete; nothing else reads Search's own outputs |
| Known confirmed defects (this pass) | 6 high/critical + 2 unconfirmed-risk | #325 (OutOfStock regression, very high severity), #357 (TLS bypass), #361 (prod/dev embedding divergence), #46/#374 (anonymous rebuild endpoint), #70 (rebuild handler no-op), #350 (search-history IDOR); plus #199/#215 (unguarded null/lookup risk, not yet confirmed as triggered in production) |

## Related
- Business view: [[Search.business|Search]]
- [[Restaurant.technical|Restaurant]]
- [[MenuItem.technical|MenuItem]]
- [[Offers.technical|Offers]]
- Canonical scoring spec: `Shared/TalabatkData/ElasticSerarchServices/SearchScoring.md`

## Open Questions
- [ ] In-restaurant item search (`GetTopSearchedItemsInRestaurantQuery`, referenced by conflict #192)
  is a separate query path in the same subsystem — not traced in this pass.
- [ ] Whether `MinMerchantFinalScore`/`MaxPercentCutoffScore` (code-only, undocumented in
  `SearchScoring.md`) are configured anywhere beyond their zero/default values — not traced.
- [ ] Whether flipping `UseOllamaEmbeddings=true` in production (to match dev) would actually work
  given prod's `Ollama:BaseUrl` still points at `127.0.0.1` per #361 — not traced beyond the
  conflict's own note.
- [ ] `CreateElasticSerachIndiciesCommand`'s commented-out handler body (#70) wasn't re-read in this
  pass — only its cited line range was trusted from the existing conflict.
