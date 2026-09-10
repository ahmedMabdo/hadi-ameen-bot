---
id: 8orders/customer-ordering/restaurant-and-menu-discovery/discovery-utilities
note_type: single
context: Customer Ordering
feature: Restaurant & Menu Discovery
group: Discovery-Utilities
covers: [Brand, BrandDescription, CookingTimeCategory, Favourites, FoodType, FoodTypesDescription, ItemDescription, MartMainCategory, MenuCategory, MenuCategoryDescription, MenuItemOptionCategoryDescription, MenuItemOptionGroup, MenuItemOptionGroupDescription, MenuItemOptionGroupItem, MenuItemOptionGroupItemDescription, MenuItemOptions, MenuItemOptionsCategories, MenuItemPriceDescription, MenuItemPriceSku, MenuItemReplacement, RecommendationInteractionEvent, RestaurantArea, RestaurantDescription, RestaurantFinalScoreRate, RestaurantJournalSubuscriptions, RestaurantPromoCode, RestaurantZone, RestaurantZoneArea, Restaurant_FoodTypes, ResturantBusyHistory, SearchHistory, SliderHome, StoreTypeCities, StoreTypesDescription, Tag]
last_updated: 2026-08-23
sources:
  - path: Shared/TalabatkLogic/TalabatkModels/Brand.cs
    sha1: e82e77d7480d
  - path: Shared/TalabatkLogic/TalabatkModels/BrandDescription.cs
    sha1: e664ed59b514
  - path: Shared/TalabatkLogic/TalabatkModels/CookingTimeCategory.cs
    sha1: ba698f139f37
  - path: Shared/TalabatkLogic/TalabatkModels/Favourites.cs
    sha1: 456585176416
  - path: Shared/TalabatkLogic/TalabatkModels/FoodType.cs
    sha1: 9449f07703cd
  - path: Shared/TalabatkLogic/TalabatkModels/FoodTypesDescription.cs
    sha1: 8ec3b6ab30ad
  - path: Shared/TalabatkLogic/TalabatkModels/ItemDescription.cs
    sha1: ac069fd3164c
  - path: Shared/TalabatkLogic/TalabatkModels/MartMainCategory.cs
    sha1: f55bcfa21eea
  - path: Shared/TalabatkLogic/TalabatkModels/MenuCategory.cs
    sha1: ebebb97f2cc6
  - path: Shared/TalabatkLogic/TalabatkModels/MenuCategoryDescription.cs
    sha1: 8ef7d974b848
  - path: Shared/TalabatkLogic/TalabatkModels/MenuItemOptionCategoryDescription.cs
    sha1: 55ddde3caf08
  - path: Shared/TalabatkLogic/TalabatkModels/MenuItemOptionGroup.cs
    sha1: 3bfa0e464b3b
  - path: Shared/TalabatkLogic/TalabatkModels/MenuItemOptionGroupDescription.cs
    sha1: 621f9aa101c4
  - path: Shared/TalabatkLogic/TalabatkModels/MenuItemOptionGroupItem.cs
    sha1: ebeacfc7c497
  - path: Shared/TalabatkLogic/TalabatkModels/MenuItemOptionGroupItemDescription.cs
    sha1: 9bbd7ea61ae6
  - path: Shared/TalabatkLogic/TalabatkModels/MenuItemOptions.cs
    sha1: 650cad02b126
  - path: Shared/TalabatkLogic/TalabatkModels/MenuItemOptionsCategories.cs
    sha1: 805d457345c8
  - path: Shared/TalabatkLogic/TalabatkModels/MenuItemPriceDescription.cs
    sha1: c30513972aaa
  - path: Shared/TalabatkLogic/TalabatkModels/MenuItemPriceSku.cs
    sha1: 9ab96ef9afef
  - path: Shared/TalabatkLogic/TalabatkModels/MenuItemReplacement.cs
    sha1: 6ad49d92e50b
  - path: Shared/TalabatkLogic/TalabatkModels/RecommendationInteractionEvent.cs
    sha1: 1758f9dd0441
  - path: Shared/TalabatkLogic/TalabatkModels/RestaurantArea.cs
    sha1: 936e8cde06d2
  - path: Shared/TalabatkLogic/TalabatkModels/RestaurantDescription.cs
    sha1: 85e0900caaa1
  - path: Shared/TalabatkLogic/TalabatkModels/RestaurantFinalScoreRate.cs
    sha1: b9c9bbcbc458
  - path: Shared/TalabatkLogic/TalabatkModels/RestaurantJournalSubuscriptions.cs
    sha1: b7fd9d261ce8
  - path: Shared/TalabatkLogic/TalabatkModels/RestaurantPromoCode.cs
    sha1: c8e747604abd
  - path: Shared/TalabatkLogic/TalabatkModels/RestaurantZone .cs
    sha1: f5bf5396ef54
  - path: Shared/TalabatkLogic/TalabatkModels/RestaurantZoneArea.cs
    sha1: 64669b28c955
  - path: Shared/TalabatkLogic/TalabatkModels/Restaurant_FoodTypes.cs
    sha1: c7323639c45c
  - path: Shared/TalabatkLogic/TalabatkModels/ResturantBusyHistory.cs
    sha1: 2f34f9a32a3b
  - path: Shared/TalabatkLogic/TalabatkModels/SearchHistory.cs
    sha1: 84a141eb6255
  - path: Shared/TalabatkLogic/TalabatkModels/SliderHome.cs
    sha1: 91be5e368b59
  - path: Shared/TalabatkLogic/TalabatkModels/StoreTypeCities.cs
    sha1: e7589d3addb8
  - path: Shared/TalabatkLogic/TalabatkModels/StoreTypesDescription.cs
    sha1: 48cbfa2189b7
  - path: Shared/TalabatkLogic/TalabatkModels/Tag.cs
    sha1: f573be01e1d1
tags: [customer-ordering, restaurant-menu-discovery, technical, backend-domain]
---
# Discovery Utilities

The browsing side's supporting cast: the lookups a customer filters by, the description rows that make
the catalogue bilingual, the option structures that make a menu item configurable, and the geography
that decides which restaurants a customer can see at all. Thirty-five entities, none of which owns a
feature of its own — which is why they are documented together rather than in thirty-five notes.

The controllers that read them:

| Controller | Purpose |
|------------|---------|
| `Search` | Restaurant/item search |
| `SearchHistory` | Tracks a customer's past search terms |
| `Favourite` | Customer's favourited restaurants |
| `FoodTypes` | Cuisine-type lookup (used for filtering) |
| `StoreTypes` | Store/mart-type lookup (also referenced by [[TieredDiscount.technical\|TieredDiscount]]'s optional `StoreTypeId` scoping) |
| `City` | City lookup (delivery-area hierarchy root) |
| `AreaController` | Delivery-area lookup within a city |
| `HomePage` | Aggregates sliders/banners/sections for the app's landing screen |

## What this group tells you about the codebase

Read together, these thirty-five entities are the clearest sample of how validation is distributed in
8Orders, because they cover the whole range within one layer and one folder:

- **Three tiers of rigour.** `Brand` and `MartMainCategory` return `Result<T>` from a private-ctor
  factory and guard every field. `MenuCategory` and `ItemDescription` are equally central and have
  **no guards at all** — plain assignment through `void` methods. `MenuItemPriceSku` and
  `RestaurantFinalScoreRate` have no methods whatsoever.
- **The `*Description` pattern is inconsistent in a way that matters.** Ten of these entities are
  per-language description rows for a parent. `BrandDescription`, `FoodTypesDescription`,
  `RestaurantDescription` and `StoreTypesDescription` require a non-blank name;
  `MenuCategoryDescription`, `MenuItemOptionCategoryDescription`, `MenuItemOptionGroupDescription`,
  `MenuItemOptionGroupItemDescription` and `ItemDescription` accept anything. So whether a customer can
  end up looking at a blank name depends on which description table it came from.
- **Three near-identical option structures coexist.** `MenuItemOptions`, `MenuItemOptionGroupItem` and
  `MenuItemOptionsCategories` all carry a reference name, a price or ordering, an active flag, and an
  `Update` that guards only the reference name — with the error text spelled three different ways,
  including two spellings of "Reference" (`Refernce`).

## Folded entities

Every entity this note covers, what it is, and its real rules with line numbers.

### Classification and branding

| Entity | What it is | Rules |
|---|---|---|
| `Brand` | Product brand with a logo, a landscape image and a display order | The strictest entity in the group. `Instance` requires at least one description (`Shared/TalabatkLogic/TalabatkModels/Brand.cs:44`) and a landscape image (`:49`); `UpdateOrder` rejects a negative order (`:72`); `UpdateLogo` and `UpdateLandscape` each reject a null image (`:82`, `:92`); `UpdateBrandDescription` fails when the language row is absent (`:106`). Starts inactive, toggled by `ChangeActiveStatus` (`:63`) |
| `BrandDescription` | A brand's name in one language | Name required on both create (`Shared/TalabatkLogic/TalabatkModels/BrandDescription.cs:25`) and `Update` (`:39`) — one of the four description types that actually checks |
| `FoodType` | Cuisine type used for filtering | Its own rules are documented with the restaurant catalogue; the description row below is where the per-language text lives |
| `FoodTypesDescription` | A cuisine type's name in one language | `AddDescription` rejects blanks with "wrong Parameters" (`Shared/TalabatkLogic/TalabatkModels/FoodTypesDescription.cs:22`), `UpdateDescription` with "Empty Parameters" (`:32`) — same check, two messages |
| `StoreTypesDescription` | A store type's name in one language | Mirror image of the above, with the two messages **swapped**: `UpdateDescription` says "Empty Parameters" (`Shared/TalabatkLogic/TalabatkModels/StoreTypesDescription.cs:22`) and `AddDescription` says "wrong Parameters" (`:31`) |
| `StoreTypeCities` | Which cities a store type is offered in | Join row, no validation (`Shared/TalabatkLogic/TalabatkModels/StoreTypeCities.cs:12`) |
| `MartMainCategory` | Grocery taxonomy, self-parenting for sub-categories | Second-strictest here. `Instance` requires both names, both images, and at least one sub-category (`Shared/TalabatkLogic/TalabatkModels/MartMainCategory.cs:53-70`); `InstanceAsSubCategory` requires only the two names (`:91`, `:95`) — so a sub-category needs no imagery while its parent does. Separate `Update`, `UpdateSubCategory`, `DeleteSubCategory`, `UpdateLogo`, `UpdateLandscape`, and **two** active-status methods, `ChangeActiveStatus` (`:178`) and `MangeActiveStatus` (`:188`) |
| `Tag` | A free-text tag | `TagId` plus `tag`, and one `UpdateTag` that assigns without checking (`Shared/TalabatkLogic/TalabatkModels/Tag.cs:17`) |
| `CookingTimeCategory` | Named band of cooking-time values | Both `Instance` and `Update` require a name and a non-empty value list, with identical messages in both — a properly symmetric pair (`Shared/TalabatkLogic/TalabatkModels/CookingTimeCategory.cs:39-44`, `:62-67`). Its admin screen is gated only by a roleless `[Authorize]` — 🔴 `_conflicts.md` #560 |

### Menu structure

| Entity | What it is | Rules |
|---|---|---|
| `MenuCategory` | A section of a restaurant's menu, optionally time-limited, with its own tax and profit settings | **No guards anywhere**, despite being one of the busiest entities here: `Instance` (`Shared/TalabatkLogic/TalabatkModels/MenuCategory.cs:91`), `Update` (`:150`), `ApplyCategoryProfit` (`:139`), `AddNewItemtoCategory` (`:133`) and six state setters all assign directly. `IsOpen()` (`:47`) is where the `HasTime`/`StartTime`/`EndTime` window is evaluated — the same three-field shape whose unguarded twin is 🔴 #625 |
| `MenuCategoryDescription` | A category's name and description in one language | Private ctor, `Instance` only, no validation (`Shared/TalabatkLogic/TalabatkModels/MenuCategoryDescription.cs:23`) |
| `ItemDescription` | An item's name and description in one language, plus its search embedding | No validation on any of its seven mutators (`Shared/TalabatkLogic/TalabatkModels/ItemDescription.cs:28-57`). Carries `ItemNameEmbedding` with `SetItemNameEmbedding`/`ClearItemNameEmbedding` (`:48`, `:53`) — this is the row semantic search reads |
| `MenuItemPriceDescription` | A price variant's name in one language | `Update` returns a failure literally called "Fail Update" (`Shared/TalabatkLogic/TalabatkModels/MenuItemPriceDescription.cs:40`) — a guard whose message says nothing about what was wrong |
| `MenuItemPriceSku` | The SKU string for a price variant | Four properties, **no methods at all** (`Shared/TalabatkLogic/TalabatkModels/MenuItemPriceSku.cs`). The ERP stock sync matches on this value |
| `MenuItemReplacement` | Which item may substitute for another | Private ctor, one `Instance`, no rules (`Shared/TalabatkLogic/TalabatkModels/MenuItemReplacement.cs:16`). The replacement *flow* is where the logic lives — see [[Customer Ordering/Order & Fulfilment/_knowledge-graph\|Order & Fulfilment]] |

### Item options — the three parallel structures

| Entity | What it is | Rules |
|---|---|---|
| `MenuItemOptionGroup` | Reusable option group owned by a restaurant, with min/max selection | `Update` requires the names — "Arabic and English names are required" (`Shared/TalabatkLogic/TalabatkModels/MenuItemOptionGroup.cs:97`). `CreateWithFilteredItems` (`:34`) builds a projection carrying only the items a caller asked for; `Instance` (`:65`) has no guard, so the invariant holds only on update |
| `MenuItemOptionGroupItem` | One choice inside a group, with a price and a countable flag | `Update` guards only the reference name — "Reference Name Can't be Empty" (`Shared/TalabatkLogic/TalabatkModels/MenuItemOptionGroupItem.cs:65`). `ToggleActive` (`:128`) returns `Result` but cannot fail |
| `MenuItemOptions` | The per-item option row — the older shape the group structure replaces | Same single guard, spelled "Refernce Name Can't be Empty" (`Shared/TalabatkLogic/TalabatkModels/MenuItemOptions.cs:65`). Has three mutators where its sibling has one: `Update` (`:54`), `PartialUpdate` (`:135`) and `ActiveUpdate` (`:177`) |
| `MenuItemOptionsCategories` | Groups options under a price variant, with min/max | `Update` carries the same single guard with the same misspelling (`Shared/TalabatkLogic/TalabatkModels/MenuItemOptionsCategories.cs:69`), plus a separate `UpdateState` (`:120`). Carries **both** `OptionsGroupId` and its own `PriceId`, which is what makes the old and new option models coexist on one row |
| `MenuItemOptionGroupDescription` | A group's name in one language | `Instance` only, no validation (`Shared/TalabatkLogic/TalabatkModels/MenuItemOptionGroupDescription.cs:16`) |
| `MenuItemOptionGroupItemDescription` | A group item's name in one language | `Instance` and a `void Update`, neither validating (`Shared/TalabatkLogic/TalabatkModels/MenuItemOptionGroupItemDescription.cs:17`, `:26`) |
| `MenuItemOptionCategoryDescription` | An option category's name and description in one language | Six properties, only a `ToString` (`Shared/TalabatkLogic/TalabatkModels/MenuItemOptionCategoryDescription.cs:14`) — no factory, so rows are built by EF or by the caller directly |

### Restaurant attributes and geography

| Entity | What it is | Rules |
|---|---|---|
| `RestaurantDescription` | A restaurant's name and description in one language | `Instance` rejects blanks ("wrong Parameters", `Shared/TalabatkLogic/TalabatkModels/RestaurantDescription.cs:62`) and `UpdateDescription` rejects blanks ("Empty Parameters", `:25`). Overrides `Equals` (`:38`), so descriptions compare by value — relevant to the diff-based update paths |
| `Restaurant_FoodTypes` | Which cuisines a restaurant is listed under | `Instance` returns `Result` but never fails (`Shared/TalabatkLogic/TalabatkModels/Restaurant_FoodTypes.cs:14`) |
| `RestaurantArea` | Which delivery areas a restaurant serves | Same shape: `Result<RestaurantArea>` with no failure path (`Shared/TalabatkLogic/TalabatkModels/RestaurantArea.cs:17`). This row is what makes a restaurant visible to a customer's resolved area |
| `RestaurantZone` | Named group of areas within a city | `Instance` requires both names and a city (`Shared/TalabatkLogic/TalabatkModels/RestaurantZone .cs:60-70`); `Update` requires the two names but **cannot change the city** (`:94`, `:99`). ⚠️ Its filename contains a **space before the extension** — `RestaurantZone .cs` — which breaks any tooling that assumes a normal path |
| `RestaurantZoneArea` | An area inside a zone, with the customer delivery fee for it | Guards that the area is present (`Shared/TalabatkLogic/TalabatkModels/RestaurantZoneArea.cs:21`) and carries `CustomerDeliveryFees` — so the fee a customer pays is a property of this join row, not of the restaurant |
| `ResturantBusyHistory` | A period when a restaurant marked itself busy, with reason and who ended it | No validation. `Instance` (`Shared/TalabatkLogic/TalabatkModels/ResturantBusyHistory.cs:34`), `EndRestaurantBusy` (`:25`) and `UpdateRestaurantBusy` (`:58`); tracks `CreatedBy`, `IsAdmin`, `TerminatedBy` and `Reason`, which is the data an IDOR exposes cross-tenant — 🔴 `_idor-instances.md` instance 11. Note the misspelt type name, kept as-is because it is the real one |
| `RestaurantFinalScoreRate` | A restaurant's cached final rating and when it was computed | Five properties, **no methods** (`Shared/TalabatkLogic/TalabatkModels/RestaurantFinalScoreRate.cs`) — written by the scoring job, read by ranking |
| `RestaurantPromoCode` | Links a promo code to a restaurant | `Instance` only, no rules (`Shared/TalabatkLogic/TalabatkModels/RestaurantPromoCode.cs:17`); the rules live in [[Customer Ordering/Discounts & Coupons/_knowledge-graph\|Discounts & Coupons]] |
| `RestaurantJournalSubuscriptions` | A recurring accounting charge against a restaurant | Rejects a non-positive restaurant id (`Shared/TalabatkLogic/TalabatkModels/RestaurantJournalSubuscriptions.cs:25`) and a negative amount (`:30`) — the only money-bearing entity in this group, and it does validate. Soft-deleted via `IsDeleted`. Misspelling again preserved |

### Discovery signals

| Entity | What it is | Rules |
|---|---|---|
| `Favourites` | A customer's favourited restaurant or item | `Instance` assigns, no validation (`Shared/TalabatkLogic/TalabatkModels/Favourites.cs:19`). `FavouriteTypeId` plus `Type` is what makes one table serve both kinds |
| `SearchHistory` | A customer's past search terms | Feeds autocomplete; the multi-keyword variant is folded into [[Customer.technical\|Customer]] |
| `RecommendationInteractionEvent` | One impression, click or conversion on a recommendation | Private ctor with three named factories — `CreateImpression` (`Shared/TalabatkLogic/TalabatkModels/RecommendationInteractionEvent.cs:25`), `CreateClick` (`:53`), `CreateConversion` (`:79`) — and no validation in any of them. Records `MlScore`, `Position`, `RecommendationSource` and `AppVersion`, so recommendation quality is measurable from this table alone. The clearest example in the group of *intent* expressed through factory names rather than through guards |
| `SliderHome` | A home-screen slider with per-language images, an optional time window and a navigation target | `Instance` (`Shared/TalabatkLogic/TalabatkModels/SliderHome.cs:35`) has no guard; four narrow updaters (`UpdateShourtCut`, `UpdateSliderOrder`, `UpdateHasTime`, `UpdateSliderTime`) each return `Result` and none can fail; only the full `Update` guards, with "Text Can't be Empty" (`:103`). Carries the same `HasTime`/`StartTime`/`EndTime` triple as `Ads` and `Announcement` — a **third** copy of that shape, and like `Announcement` it is unguarded (🔴 #625). Note `UpdateShourtCut`, misspelt |

## Related

- [[Customer Ordering/Restaurant & Menu Discovery/_knowledge-graph|Restaurant & Menu Discovery]] — the
  feature these entities serve.
- [[Customer Ordering/Restaurant & Menu Discovery/MenuItem/MenuStructure|MenuStructure]] — the menu-item
  core these option entities hang off.
- [[Admin/City & Geography Administration/_knowledge-graph|City & Geography Administration]] — where
  areas, zones and cities are administered.
- [[Admin/Catalog & Content Administration/_knowledge-graph|Catalog & Content Administration]] — where
  brands, food types, store types and sliders are authored.

## Open Questions

- [ ] Are `MenuItemOptions` (with `MenuItemOptionsCategories`) and `MenuItemOptionGroup` (with
      `MenuItemOptionGroupItem`) both live, or is one a migration in progress? `MenuItemOptionsCategories`
      carries keys for both, which suggests a transition that never finished.
- [ ] Should the five unguarded `*Description` types require a non-blank name, as the other four do? A
      blank name reaches the customer's screen.
- [ ] `MenuCategory` has no guards at all and owns tax, profit and a time window. Is that deliberate,
      given `Brand` and `MartMainCategory` in the same folder guard everything?
- [ ] `SliderHome` is the third entity with the `HasTime`/`StartTime`/`EndTime` triple and the second
      without a guard. Is a shared value object warranted?
- [ ] Can `RestaurantZone .cs` be renamed to drop the space? It is a latent break for any path-based
      tooling, including this knowledge graph's own verifiers.
- [ ] `RestaurantZoneArea.CustomerDeliveryFees` sets the fee per area-in-zone. Which wins when an area
      belongs to a zone whose restaurant also has its own fee? Not traced.
