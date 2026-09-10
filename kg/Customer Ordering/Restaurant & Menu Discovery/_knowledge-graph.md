---
id: 8orders/customer-ordering/restaurant-and-menu-discovery/knowledge-graph
title: Restaurant & Menu Discovery — Knowledge Graph
note_type: knowledge-graph
context: Customer Ordering
feature: Restaurant & Menu Discovery
last_updated: 2026-08-24
sources:
  - path: TalabatkAPIs/Controllers/Resturant/ResturantController.cs
    sha1: 3423a44e924b
  - path: TalabatkAPIs/Controllers/MenuItem/ItemController.cs
    sha1: be53936a10f9
  - path: TalabatkAPIs/Controllers/MenuItem/CategoryController.cs
    sha1: 717fe626ecae
  - path: TalabatkAPIs/Controllers/Search/SearchController.cs
    sha1: 261ea8084ed6
  - path: TalabatkAPIs/Controllers/Mart/MartController.cs
    sha1: c3ed2983e8dc
  - path: TalabatkAPIs/Controllers/HomePage/HomePageController.cs
    sha1: 66ce350b1899
  - path: TalabatkAPIs/Controllers/Favourite/FavouriteController.cs
    sha1: 7a539caee621
  - path: TalabatkAPIs/Controllers/FoodTypes/FoodTypesController.cs
    sha1: 564bba454312
  - path: TalabatkAPIs/Controllers/StoreTypes/StoreTypesController.cs
    sha1: 5b8388d67804
  - path: TalabatkAPIs/Controllers/SearchHistory/SearchHistoryController.cs
    sha1: 7dc36cb6c0bd
  - path: TalabatkAPIs/Controllers/Mart/BrandsController.cs
    sha1: af0f7fc99978
  - path: Shared/TalabatkLogic/TalabatkModels/Restaurant.cs
    sha1: 42514c8fb3e5
  - path: Shared/TalabatkLogic/TalabatkModels/MenuItem.cs
    sha1: 41321a3dafe6
tags: [customer-ordering, restaurant-menu-discovery, technical, api-host]
---
# Restaurant & Menu Discovery — Knowledge Graph

> **Context:** Customer Ordering
> **Source Project:** `TalabatkAPIs` — 11 controllers, **69 endpoints**, the largest read surface in
> the platform
> **Entities:** [[Restaurant.technical|Restaurant]], [[MenuItem.technical|MenuItem]],
> [[MenuItemPrice.technical|MenuItemPrice]], [[Offers.technical|Offers]],
> [[Search.technical|Search]], [[RestaurantReview|RestaurantReview]], plus 33 folded utilities in
> [[Customer Ordering/Restaurant & Menu Discovery/Discovery-Utilities|Discovery Utilities]]
> **Register findings open here:** #636, #192, #325, #410, #423, #437, #29

Everything the customer sees before they add anything to a cart: the home screen, search, the store
list, one restaurant's menu, the grocery (mart) browse tree, and favourites. It is the feature a
customer touches most and the one with the most endpoints — and it is where the same question ("what can
I order?") is answered by four different code paths that do not agree.

## The four search paths, and why that matters

Search is not one thing here. Four controllers answer overlapping questions, and a change to one does
not change the others:

| Path | Endpoint | What it searches |
|---|---|---|
| Home search | `GET api/HomePage/SearchItem` and `/V2` (`TalabatkAPIs/Controllers/HomePage/HomePageController.cs:301`, `:330`) | Items across restaurants, from the home screen |
| Faceted search | `GET SearchWithFiltersAndSortingOptions` and `V2` (`TalabatkAPIs/Controllers/Search/SearchController.cs:71`, `:110`) | Restaurants, with filters and sort |
| In-restaurant search | `GET api/Item/SearchItemInRestaurnant` and `V2` (`TalabatkAPIs/Controllers/Resturant/ResturantController.cs:227`, `:259`) | Items inside one restaurant — **anonymous**, 🟡 #636 |
| Mart search | `GET api/Mart/SearchProducts`, `MartHomeSearch`, `SearchAutoComplete` (`TalabatkAPIs/Controllers/Mart/MartController.cs:114`, `:136`, `:285`) | Grocery products |

Each has a `V1`/`V2` pair on top of that, so the same question has up to eight live answers. Two
consequences are already in the register: **#325** (a confirmed high-severity regression in item
search) and **#192** (four post-materialisation bugs in `SearchItemsInRestaurantQuery`). The general
lesson for anyone changing search: fixing one path fixes one client.

## Anonymous surface

The class-level `[Authorize(JwtBearer)]` on `ResturantController` (`TalabatkAPIs/Controllers/Resturant/ResturantController.cs:25`)
is opted out of by three actions, and one more elsewhere is anonymous **by design**:

| Endpoint | Attribute | Verdict |
|---|---|---|
| `api/Item/SearchItemInRestaurnant` | `[AllowAnonymous]` (`:222`) | 🟡 #636 — menu search for any restaurant id, no token |
| `api/Item/SearchItemInRestaurnantV2` | `[AllowAnonymous]` (`:254`) | 🟡 #636 |
| `TopSearchedItemsInRestaurants` | `[AllowAnonymous]` (`:287`) | 🟡 #636 — leaks aggregate customer *behaviour*, not just catalogue |
| `api/Item/ItemStockQuantityChangedInERP` | `[AllowAnonymous]` **+ `[WebHookHmacAuthorize]`** (`TalabatkAPIs/Controllers/MenuItem/ItemController.cs:218-219`) | ✅ correct — anonymous to ASP.NET, authenticated by HMAC signature |

That last row is the pattern worth carrying out of this feature: **the codebase already knows how to
authenticate a caller that cannot hold a token.** `_conflicts.md` #616 (the unauthenticated Centrifugo
proxy) is one attribute away from this.

## Endpoint index

### Restaurant and menu

| Endpoint | Auth | What it does |
|---|---|---|
| `GET GetAllRestaurant` | JWT | The store list for a location (`TalabatkAPIs/Controllers/Resturant/ResturantController.cs:106`) |
| `GET GetRestaurantInfoByRestaurantId` | JWT | One restaurant's detail page (`:69`) |
| `GET GetRestaurantReviews` | JWT | Its reviews (`:50`) |
| `POST AddResturantWithDeliveryReviews` | JWT + role `Customer` | Leave a review of the restaurant **and** the driver in one call (`:203`) |
| `GET GetAllStoresOffers` | JWT | Active offers across stores (`:155`) |
| `GET GetMartCategoryName` | JWT | Category label lookup (`:317`) |
| `GET api/Category/GetCategoryByRestaurantId` | JWT | A restaurant's menu sections (`TalabatkAPIs/Controllers/MenuItem/CategoryController.cs:41`) |
| `GET api/Item/GetItemsByCategoryId` | JWT | Items in one section (`TalabatkAPIs/Controllers/MenuItem/ItemController.cs:77`) |
| `GET api/Item/GetAllRestaurantItems` / `V2` | JWT | The whole menu; the V1 path is where **#410**'s incomplete offer window lives (`:128`, `:161`) |
| `GET api/Item/Details` | JWT | One item with its options and prices (`:188`) |
| `POST api/Item/CheckSelectedItems` | JWT | Re-validates a client's selection before checkout (`:48`) |
| `POST api/Item/ItemStockQuantityChangedInERP` | HMAC | The ERP stock webhook (`:223`) |

### Search and home screen

| Endpoint | Auth | What it does |
|---|---|---|
| `GET GetSearchOptions` | JWT | The filter/sort vocabulary the client renders (`TalabatkAPIs/Controllers/Search/SearchController.cs:54`) |
| `GET SearchWithFiltersAndSortingOptions` / `V2` | JWT | Faceted restaurant search (`:71`, `:110`) |
| `GET MostSearchedKeywords` | JWT | Trending searches (`:240`) |
| `GET MostFamousRestaurants` | JWT | Popularity list (`:259`) |
| `GET HomeSearchAutoComplete` | JWT | Typeahead (`:283`) |
| `GET GetNearestByStoreType` | JWT | Nearest stores of a type (`:307`) |
| `GET HighestRatedRestaurants` | JWT | Rating leaderboard — reads the cached `RestaurantFinalScoreRate` (`:363`) |
| `GET api/HomePage/GetTheBestOffers` | JWT | Home-screen offer rail (`TalabatkAPIs/Controllers/HomePage/HomePageController.cs:47`) |
| `GET api/HomePage/GetTheNearest` | JWT | Nearest restaurants — takes a `userAddressId` that is **not** checked against the caller (`:75`, `_idor-instances.md` instance 26) |
| `GET api/HomePage/GetPersonalizedRestaurantRecommendations` | JWT | The ML recommendation rail (`:95`) |
| `POST api/HomePage/LogRecommendationClick` | JWT | Writes a `RecommendationInteractionEvent` (`:127`) |
| `GET api/HomePage/GetTheNewPlaces` / `V1` | JWT | New-on-8Orders rail (`:170`, `:278`) |
| `GET api/HomePage/GetCustomerRecentMerchants` / `ByStoreType` | JWT | Reorder rails (`:213`, `:234`) |
| `GET api/HomePage/SliderHome`, `GetSliderHomeByLocation` | JWT | The banner carousel (`:390`, `:413`) |

### Mart (grocery)

Twenty-one endpoints on one controller (`TalabatkAPIs/Controllers/Mart/MartController.cs`). The
browse tree is `GetMartCategories`/`V2` (`:57`, `:73`) → `GetSubCategories` (`:161`) →
`GetCategoryProducts` (`:92`). Six actions are role-gated to `Customer` because they write or read
personal data: `ToggleItemAvailabilityNotification` (`:230`), `GetMyItemsNotificationSubscriptions`
(`:257`), the three multi-search-keyword actions (`:325`, `:348`, `:371`) and `GetPreviousPurchases`
(`:450`). `CheckMartBusyOrNot` (`:273`) carries a **roleless** `[Authorize]` on top of the class
attribute, which adds nothing.

### Favourites and reference lookups

| Endpoint | Auth | What it does |
|---|---|---|
| `api/Favourite/*` — 7 actions | JWT + role `Customer` **on the class** (`TalabatkAPIs/Controllers/Favourite/FavouriteController.cs:21`) | Add, list and delete favourite items and places; the whole controller is correctly role-gated, unusually for this codebase |
| `GET api/FoodTypes/GetAllFoodTypes` | JWT | Cuisine filter vocabulary (`TalabatkAPIs/Controllers/FoodTypes/FoodTypesController.cs:39`) |
| `GET api/StoreTypes/GetAllStoreTypesForCityByLocation` | JWT | Store types available at a location (`TalabatkAPIs/Controllers/StoreTypes/StoreTypesController.cs:39`) |
| `api/SearchHistory/*` | JWT | The customer's own past searches (`TalabatkAPIs/Controllers/SearchHistory/SearchHistoryController.cs`) |
| `api/Brands/*` | JWT | Brand filter for mart (`TalabatkAPIs/Controllers/Mart/BrandsController.cs`) |

## Status / State

Read-only except three writes: a review (`ResturantController.cs:203`), a favourite
(`FavouriteController.cs:41`), and a recommendation click (`HomePageController.cs:127`). Everything
else is projection over `Restaurant`, `MenuItem` and the discovery utilities. The one piece of
derived state is `RestaurantFinalScoreRate`, written by a scoring job and read by
`HighestRatedRestaurants`.

## Entity Index

| Entity | Layer | Type | Responsibility |
|---|---|---|---|
| `Restaurant` | Domain | legacy-poco-root | The store — **and the mart**, via `IsStore`. See [[Restaurant.technical\|Restaurant]] |
| `MenuItem` | Domain | legacy-poco-root | A sellable item, event-raising for search indexing. See [[MenuItem.technical\|MenuItem]] |
| `MenuItemPrice` | Domain | child | Size/variant pricing. See [[MenuItemPrice.technical\|MenuItemPrice]] |
| `Offers` | Domain | legacy-poco-root | Item-level discounts. See [[Offers.technical\|Offers]] |
| `Search` | Application | — | Elasticsearch indexing and query. See [[Search.technical\|Search]] |
| `RestaurantReview` | Domain | child | Customer rating and comment. See [[RestaurantReview\|RestaurantReview]] |
| 33 more | Domain | child / lookup | Descriptions, option structures, geography, discovery signals — all in [[Customer Ordering/Restaurant & Menu Discovery/Discovery-Utilities\|Discovery Utilities]] |

## Feature Flow (Business Narrative)

```
1. LOCATION            GET api/Area/GetAreaByCoordinates      (Ops & Infra — gates everything)
2. HOME                GET api/HomePage/SliderHome            banners
                       GET .../GetTheBestOffers               offer rail
                       GET .../GetPersonalizedRestaurantRecommendations   ML rail
                       GET .../GetCustomerRecentMerchants     reorder rail
3. BROWSE or SEARCH    GET GetAllRestaurant                   the store list
                       GET SearchWithFiltersAndSortingOptions faceted search
                       GET api/Mart/GetMartCategories         grocery tree
4. ONE STORE           GET GetRestaurantInfoByRestaurantId
                       GET api/Category/GetCategoryByRestaurantId
                       GET api/Item/GetAllRestaurantItemsV2   the menu  (#410 on the V1 path)
                       GET api/Item/SearchItemInRestaurnant   in-store search  (ANONYMOUS, #636)
5. ONE ITEM            GET api/Item/Details                   options and prices
6. HAND OFF TO CART    POST api/Item/CheckSelectedItems       re-validate, then Cart & Checkout
```

## Key Cross-Cutting Relationships

| From | To | Relationship | Notes |
|---|---|---|---|
| This feature | [[Customer Ordering/Cart & Checkout/_knowledge-graph\|Cart & Checkout]] | hands off a validated selection | `CheckSelectedItems` is the boundary |
| This feature | [[Customer Ordering/Ops & Infra/_knowledge-graph\|Ops & Infra]] | depends on area resolution | Nothing here can answer before a coordinate resolves |
| `MenuItem` | Elasticsearch | raises index events on change | See [[Search.technical\|Search]] |
| ERP | `MenuItem` | HMAC webhook sets stock | `_integrations.md` row 19 |
| This feature | [[Admin/Catalog & Content Administration/_knowledge-graph\|Catalog & Content Administration]] | reads what Admin authors | Brands, food types, store types, sliders |
| This feature | [[Customer Ordering/Discounts & Coupons/_knowledge-graph\|Discounts & Coupons]] | shows the discounted price | The offer window bug #410 is on this side |
| `RecommendationInteractionEvent` | recommendation quality | records impression, click, conversion | Measurable from one table |

## Change Surface

| Signal | Value | Notes |
|---|---|---|
| Direct dependents (Ring 1) | the customer mobile app; every downstream ordering step | |
| Endpoints | **69** across 11 controllers | The largest surface in the platform |
| Sides touched | 3/5 | API host · Application · Domain |
| Cross-context integrations | 4 | Elasticsearch, ERP stock, Admin catalogue, area geography |
| Register findings open | 7 (#636, #192, #325, #410, #423, #437, #29) | |
| Hub? | **yes** — nothing can be ordered that was not first discovered here | |
| Risk flags | four independent search paths with `V1`/`V2` pairs on each; three unregistered anonymous endpoints; an offer window evaluated without its time component on the V1 menu path |

## Open Questions

- [ ] Which of the four search paths does the shipped app actually call, and can the others be retired?
      Eight live answers to one question is the root of both #325 and #192.
- [ ] Should the three `[AllowAnonymous]` search endpoints (#636) be gated, or is anonymous menu search
      a deliberate SEO/preview feature? If deliberate, `TopSearchedItemsInRestaurants` is still the odd
      one out — it returns behaviour, not catalogue.
- [ ] `CheckMartBusyOrNot` has a roleless `[Authorize]` over a class that already requires JWT. Dead
      attribute, or was a role intended?
- [ ] Is `RestaurantFinalScoreRate` recomputed on a schedule or on review write? `HighestRatedRestaurants`
      reads it directly, so staleness there is invisible to the caller.
- [ ] `GetTheNearest` takes a `userAddressId` from the request without checking ownership
      (`_idor-instances.md` instance 26). Is that reachable with another customer's address id in
      practice, and does the response reveal anything address-specific?
