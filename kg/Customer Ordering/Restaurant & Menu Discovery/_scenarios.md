---
id: 8orders/customer-ordering/restaurant-and-menu-discovery/scenarios
title: Restaurant & Menu Discovery — Scenario Catalog
note_type: scenarios
context: Customer Ordering
feature: Restaurant & Menu Discovery
audience: Business · QA · Developer
last_updated: 2026-08-24
sources:
  - path: Shared/TalabatkLogic/TalabatkModels/MenuItem.cs
    sha1: 41321a3dafe6
  - path: Shared/TalabatkLogic/TalabatkModels/Restaurant.cs
    sha1: 42514c8fb3e5
  - path: TalabatkAPIs/Controllers/Resturant/ResturantController.cs
    sha1: 3423a44e924b
  - path: TalabatkAPIs/Controllers/MenuItem/ItemController.cs
    sha1: be53936a10f9
  - path: TalabatkAPIs/Controllers/Search/SearchController.cs
    sha1: 261ea8084ed6
  - path: TalabatkAPIs/Controllers/Mart/MartController.cs
    sha1: c3ed2983e8dc
  - path: TalabatkAPIs/Controllers/HomePage/HomePageController.cs
    sha1: 66ce350b1899
  - path: TalabatkAPIs/Controllers/Favourite/FavouriteController.cs
    sha1: 7a539caee621
tags: [customer-ordering, restaurant-menu-discovery, scenarios]
---
# Restaurant & Menu Discovery — Scenario Catalog

> The largest read surface in the platform: 69 endpoints across 11 controllers. What follows is what
> actually happens at each of them, including the cases where two endpoints answering the same question
> disagree.

## Happy path

| # | Precondition | Action | Expected outcome | Rule / source |
|---|---|---|---|---|
| H1 | Coordinates resolved to a serviceable area | `GET GetAllRestaurant` | The store list for that area | `TalabatkAPIs/Controllers/Resturant/ResturantController.cs:106` |
| H2 | Restaurant within its working hours | Customer views it | Shows as open | `Shared/TalabatkLogic/TalabatkModels/Restaurant.cs:330-343` |
| H3 | Customer opens a store | `GET GetRestaurantInfoByRestaurantId` | Detail page with its info | `TalabatkAPIs/Controllers/Resturant/ResturantController.cs:69` |
| H4 | Store open | `GET api/Category/GetCategoryByRestaurantId` | Its menu sections | `TalabatkAPIs/Controllers/MenuItem/CategoryController.cs:41` |
| H5 | Section chosen | `GET api/Item/GetItemsByCategoryId` | The items in it | `TalabatkAPIs/Controllers/MenuItem/ItemController.cs:77` |
| H6 | Item chosen | `GET api/Item/Details` | Options, option groups and prices | `TalabatkAPIs/Controllers/MenuItem/ItemController.cs:188` |
| H7 | Selection built | `POST api/Item/CheckSelectedItems` | Re-validated, then handed to Cart & Checkout | `TalabatkAPIs/Controllers/MenuItem/ItemController.cs:48` |
| H8 | Customer on the home screen | `GET api/HomePage/SliderHome` | The banner carousel | `TalabatkAPIs/Controllers/HomePage/HomePageController.cs:390` |
| H9 | Customer has ordered before | `GET api/HomePage/GetCustomerRecentMerchants` | The reorder rail | `TalabatkAPIs/Controllers/HomePage/HomePageController.cs:213` |
| H10 | ML model has scored this customer | `GET api/HomePage/GetPersonalizedRestaurantRecommendations` | The personalised rail | `TalabatkAPIs/Controllers/HomePage/HomePageController.cs:95` |
| H11 | Customer taps a recommendation | `POST api/HomePage/LogRecommendationClick` | An interaction event is written, so the rail is measurable | `TalabatkAPIs/Controllers/HomePage/HomePageController.cs:127` |
| H12 | Customer wants groceries | the mart browse chain: categories, then sub-categories, then products | The three-level tree | `TalabatkAPIs/Controllers/Mart/MartController.cs:73`, `:161`, `:92` |
| H13 | Customer likes a store | `POST api/Favourite/add` | Saved, and listed by the places endpoint | `TalabatkAPIs/Controllers/Favourite/FavouriteController.cs:41` |
| H14 | Customer finished an order | `POST AddResturantWithDeliveryReviews` | Rates the restaurant **and** the driver in one call | `TalabatkAPIs/Controllers/Resturant/ResturantController.cs:203` |
| H15 | Mart item stock recovers from 0 | ERP restock webhook | Item becomes available again automatically | `Shared/TalabatkLogic/TalabatkModels/MenuItem.cs:816-839` |

## Partial / incremental

| # | Precondition | Action | Expected outcome | Rule / source |
|---|---|---|---|---|
| P1 | Two app versions in the field | each calls its own variant | Four search paths, each with a `V1`/`V2` pair — up to **eight** live answers to "what can I order?" | `TalabatkAPIs/Controllers/Search/SearchController.cs:71`, `:110` |
| P2 | Customer types three letters | `GET HomeSearchAutoComplete` | Typeahead suggestions | `TalabatkAPIs/Controllers/Search/SearchController.cs:283` |
| P3 | Customer subscribes to an out-of-stock item | `POST api/Mart/ToggleItemAvailabilityNotification` | Notified when it returns; requires the `Customer` role | `TalabatkAPIs/Controllers/Mart/MartController.cs:230` |
| P4 | Customer saves a multi-item shopping list | the three multi-search-keyword actions | Stored per customer, role-gated | `TalabatkAPIs/Controllers/Mart/MartController.cs:325`, `:348`, `:371` |
| P5 | Item edited in Admin | `MenuItem` raises an index event | Elasticsearch is updated asynchronously, so search can lag the menu | `Shared/TalabatkLogic/TalabatkModels/MenuItem.cs:553-558` |
| P6 | Restaurant marks itself busy | store list read | Shown as busy for the configured minutes; the reason is recorded | `Shared/TalabatkLogic/TalabatkModels/ResturantBusyHistory.cs:34` |

## Negative / guard

| # | Precondition | Action | Expected outcome (rejection) | Rule / source |
|---|---|---|---|---|
| N1 | Outside working hours, including the overnight wrap | Customer views restaurant | Shows as closed | `Shared/TalabatkLogic/TalabatkModels/Restaurant.cs:346-446` |
| N2 | Item rejected from orders 3 times in one shift | 4th rejection | Unavailable for 8 hours — 2³, an exponential penalty, not a flat one | `Shared/TalabatkLogic/TalabatkModels/MenuItem.cs:651-677` |
| N3 | Working days saved with no day selected | Save | **Rejected** — "Open Week Days Can Not Be Empty" | `Shared/TalabatkLogic/TalabatkModels/Restaurant.cs:945-951` |
| N4 | No token | most endpoints in this feature | 401 — every controller carries a class-level `[Authorize]` | `TalabatkAPIs/Controllers/Search/SearchController.cs:33` |
| N5 | Token without the `Customer` role | any favourites endpoint | 403 — the whole controller is role-gated, unusually for this codebase | `TalabatkAPIs/Controllers/Favourite/FavouriteController.cs:21` |
| N6 | Token without the `Customer` role | `POST AddResturantWithDeliveryReviews` | 403 | `TalabatkAPIs/Controllers/Resturant/ResturantController.cs:199` |
| N7 | ERP webhook with a bad signature | `POST api/Item/ItemStockQuantityChangedInERP` | **Rejected** by HMAC verification before the handler runs | `TalabatkAPIs/Controllers/MenuItem/ItemController.cs:219` |

## Returns / cancellation / reversal

| # | Precondition | Action | Expected outcome | Rule / source |
|---|---|---|---|---|
| R1 | Favourite added in error | `POST api/Favourite/DeleteFavourite` | Removed; `DeleteFavouriteByType` clears a whole kind at once | `TalabatkAPIs/Controllers/Favourite/FavouriteController.cs:158`, `:181` |
| R2 | Review left in error | — | No customer-facing edit or delete path in this feature | `TalabatkAPIs/Controllers/Resturant/ResturantController.cs:203` |
| R3 | Item notification no longer wanted | `ToggleItemAvailabilityNotification` again | The same endpoint toggles both ways | `TalabatkAPIs/Controllers/Mart/MartController.cs:230` |
| R4 | Shopping-list keyword no longer wanted | `DELETE api/Mart/DeleteCustomerMultiSearchKeyword` | Removed | `TalabatkAPIs/Controllers/Mart/MartController.cs:348` |
| R5 | Item deactivated by the rejection penalty | 8 hours pass | Returns automatically; nothing needs to intervene | `Shared/TalabatkLogic/TalabatkModels/MenuItem.cs:651-677` |

## Integration (cross-side / cross-context)

| # | Precondition | Action | Expected outcome | Rule / source |
|---|---|---|---|---|
| I1 | Any coordinate | area resolution first | Nothing in this feature can answer until an area resolves | [[Customer Ordering/Ops & Infra/_knowledge-graph\|Ops & Infra]] |
| I2 | Item or restaurant changed | index event raised | Elasticsearch updated out of band | [[Search.technical\|Search]] |
| I3 | ERP stock changes | HMAC webhook | `MenuItem` availability flips | `_integrations.md` row 19 |
| I4 | Admin edits a brand, food type or slider | next read | Customer-facing filters change | [[Admin/Catalog & Content Administration/_knowledge-graph\|Catalog & Content Administration]] |
| I5 | Offer active on an item | menu read | The discounted price is shown — from the offer rules, not this feature | [[Customer Ordering/Discounts & Coupons/_knowledge-graph\|Discounts & Coupons]] |
| I6 | Selection validated | hand-off | `CheckSelectedItems` is the boundary to Cart & Checkout | `TalabatkAPIs/Controllers/MenuItem/ItemController.cs:48` |
| I7 | Review written | merchant KPI | Feeds the merchant score and the rejection-rate weight | [[Restaurant Portal/Merchant Finance & Reporting/_knowledge-graph\|Merchant Finance & Reporting]] |

## Correctness and exposure scenarios — current behaviour

| # | Precondition | Action | Actual outcome today | Finding |
|---|---|---|---|---|
| X1 | **No token** | `GET api/Item/SearchItemInRestaurnant?restaurantId=N` | A restaurant's matching menu items, for any id | 🟡 **#636** · `TalabatkAPIs/Controllers/Resturant/ResturantController.cs:222` |
| X2 | **No token** | `GET TopSearchedItemsInRestaurants?restaurantId=N` | What that restaurant's customers most search for — aggregate behaviour, not catalogue | 🟡 **#636** · `TalabatkAPIs/Controllers/Resturant/ResturantController.cs:287` |
| X3 | Offer active only between certain hours | `GET api/Item/GetAllRestaurantItems` (V1) | The discount is shown outside its hour window — the weekday and date range are checked, the time of day is not | 🔴 **#410** |
| X4 | Item search across restaurants | the affected path | A confirmed high-severity regression in item search results | 🔴 **#325** |
| X5 | In-restaurant item search | `SearchItemsInRestaurantQuery` | Four post-materialisation bugs in one query | 🔴 **#192** |
| X6 | Another customer's `userAddressId` | `GET api/HomePage/GetTheNearest` | Nearest-restaurant results computed from that address; no ownership check | 🔴 `_idor-instances.md` instance 26 |
| X7 | Campaign targeted "exactly N days" | ad rails on the home screen | Reaches a wider audience than intended | 🔴 **#423** |
| X8 | Merchant reads its ad cards | portal | The response can contain literal `null` entries | 🔴 **#437** |
| X9 | Customer sorts by rating | `GET HighestRatedRestaurants` | Reads the cached `RestaurantFinalScoreRate`; if the scoring job is behind, the order is stale and nothing says so | ⚠️ `Shared/TalabatkLogic/TalabatkModels/RestaurantFinalScoreRate.cs` |

## Open Questions

- [ ] Which of the four search paths does the shipped app call? Eight live answers to one question is
      the root of both #325 and #192, and retiring the dead ones is cheaper than fixing all of them.
- [ ] Are the three anonymous search endpoints (#636) a deliberate preview feature? If so,
      `TopSearchedItemsInRestaurants` still stands out — it returns behaviour rather than catalogue.
- [ ] Is `RestaurantFinalScoreRate` recomputed on a schedule or on review write (X9)?
- [ ] Does the exponential rejection penalty (N2) reset at shift end, or accumulate across shifts?
- [ ] Scenarios for the 33 folded discovery utilities live in their own note rather than here — see
      [[Customer Ordering/Restaurant & Menu Discovery/Discovery-Utilities|Discovery Utilities]].
