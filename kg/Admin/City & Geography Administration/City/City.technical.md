---
id: 8orders/admin/city-and-geography-administration/city-technical
note_type: technical
context: Admin
feature: City & Geography Administration
entity: City
entity_type: legacy-poco-root
rule_count: 12
sources:
  - path: Shared/TalabatkLogic/TalabatkModels/City.cs
    sha1: dcb1e22e8f7e
last_updated: 2026-08-23
tags: [admin, master, technical, backend-domain]
---
# City — Technical

> **Layer:** Backend-Domain — legacy entity, richer than a typical POCO (`Result`-returning
> factory/update methods with a real guard), no private constructor though (`public City()`).
> **Context:** Admin — no single bounded context owns geographic/reference master data per
> `CONTEXT-MAP.md`; homed here since `AdminUi` is the back-office that administers it (see this
> repo's shared-entity homing convention in `_entity-index.md`'s notes). Read by every other context.
> **Source Path:** `Shared/TalabatkLogic/TalabatkModels/City.cs`   **Last Updated:** 2026-08-03

## Business Rules

### Rule 1: Delivery-man scoring weights must sum to exactly 1
- **Plain language:** A city's six delivery-man scoring weights (customer rating, working hours,
  delivered orders, acceptance rate, restaurant arrival time, customer arrival time) must add up to
  exactly 100% — the system won't let you save a city otherwise.
- **Source:** `City.cs:126-129` (`AddCity`, returns `Result.Failure`) and `City.cs:271-274`
  (`UpdateCity`, **throws** a raw `Exception` instead of returning a `Result.Failure`) — same rule,
  two different failure mechanisms depending on create vs. update. Worth flagging: `Update` isn't
  `Result`-returning at all (`void`), so this is the only way it can signal failure, which is
  inconsistent with the rest of the class's `Result` pattern.

### Rule 2: City-level financial defaults feed directly into `DeliveryMen`'s cash-limit math
- **Plain language:** The minimum deposit/equipment deduction amounts and percentages, and the
  default insurance limit, are configured per city and read when computing what a delivery man in
  that city owes.
- **Source:** `City.cs:71-76` (`RefundableDepositDeductionPercentage`, `AssetsDeductionPercentage`,
  `MinimumRefundableDepositAmount`, `MinimumAssetsDeductionAmount`, `DeliveryManInsuranceLimit`) — the
  parameter names on
  [[DeliveryMen.technical|DeliveryMen.UpdatePaidFromFinancialAmounts]]
  (`minimumRefundableDepositeAmount`, `minimumAssetsDeductionAmount`) match these fields exactly,
  confirming City is their source — the actual call site wasn't traced in this pass (Open Question).

### Rule 3: City owns its own delivery-man price-tier table, reconciled by ID on update
- **Plain language:** Updating a city's delivery-man price tiers is a full sync: tiers not present in
  the incoming list are removed, tiers with a real id are updated in place, and tiers with no id (or a
  non-positive one) are treated as new and added.
- **Source:** `City.cs:283-349` (`UpdateCity`'s price-tier handling) — `DeliveryManPriceId <= 0` ⇒
  new; `> 0` ⇒ update existing; anything not in the incoming id list ⇒ removed. If no incoming price
  data is provided at all, **every existing price tier is deleted** (`City.cs:345-349`) — worth
  flagging: there's no way to distinguish "don't touch prices" from "clear all prices" in this API,
  since an empty/null list means the latter.

### Rule 4: `OneRestaurantPerOrder` is a public settable field, not behind a factory/update method
- **Plain language:** Unlike almost every other field on this entity, whether a city restricts orders
  to one restaurant can be toggled directly, with no validation path.
- **Source:** `City.cs:26` (`public bool OneRestaurantPerOrder { get; set; }` — the only field with a
  public setter on an otherwise private-setter class).

## Key Fields
| Field | Meaning | Constraints |
|-------|---------|-------------|
| `CityId` | Primary key | |
| `NumberOfRestaurantPerOrder` / `DistanceBetweenRestaurantsInMeter` / `EnableMultiRestriction` | Multi-restaurant-order rules | Read by Cart & Checkout's multi-restaurant distance validation (not re-derived here — see [[CustomerCart.technical\|CustomerCart]]) |
| `CityMinTax` / `CityMaxTax` / `CityTaxPercentage` | Tax config | Interacts with `CartItem`'s per-item tax computation (category vs. restaurant/city rate — not fully reconciled in this pass) |
| `CustomerRateWeight` + 5 siblings | Delivery-man scoring formula inputs | Must sum to 1 (Rule 1) |
| `RefundableDepositDeductionPercentage`, `AssetsDeductionPercentage`, `MinimumRefundableDepositAmount`, `MinimumAssetsDeductionAmount`, `DeliveryManInsuranceLimit` | Delivery-man financial defaults | Feed `DeliveryMen` cash-limit math (Rule 2) |
| `MaxWalkingDistanceMeters` / `MaxBicycleDistanceMeters` | Delivery-method distance caps | Presumably gate `DeliveryMethodType` selection — not traced |
| `EightOrdersOpenTime` / `EightOrdersCloseTime` | A city-level operating window | **Traced 2026-08-24:** the working hours for **general admin chat** — a customer opening a chat with no order attached must be inside this window (`docs/CHAT_FEATURE_REFERENCE.md:162`). Set from a `DateTime` and stored as a `TimeSpan` at `Shared/TalabatkLogic/TalabatkModels/City.cs:151`-152 on create and `:255`-256 on update. Nothing to do with rush hours, despite the name |
| `MandatoryDailyDepositPercentage` | City-level default, mirrored per-delivery-man on `DeliveryMen.MandatoryDailyDepositPercentage` | Not confirmed whether the per-delivery-man value can diverge from the city default once set |

## Dependencies & Integrations
| Depends on / integrates | Side/Context | Via | Notes |
|--------------------------|---------------|-----|-------|
| `Country` | Backend-Domain (master) | FK (`CountryId`) | Own note, this same batch — trivial entity |
| `DeliveryManPrice` | Backend-Domain | 1:many, full-sync-on-update (Rule 3) | Not yet documented as its own note |
| `DeliveryMen` | Backend-Domain, Identity & Access | Financial defaults consumed (Rule 2) | |
| `Customer`, `Order`, `Restaurant`(`StoreTypes`), `DeliverySupplier` | Backend-Domain, multiple contexts | FK collections | High fan-in — City is read by nearly every context |

## Change Surface
| Signal | Value | Notes |
|--------|-------|-------|
| Direct dependents (Ring 1) | 8+ | Customer, DeliveryMen, Order, DeliveryZone, StoreTypes, DeliverySupplier, DeliveryManPrice, Area |
| Sides touched | 2/5 confirmed | Backend-Domain, Backend-Application (AddCity/UpdateCity callers not traced) |
| Cross-context integrations | 0 confirmed directly, but read by every context | Master/reference data, not an event-raiser |
| Domain events involved | 0 | No events on this class |
| Hub? | yes | One of the most widely-referenced master entities in the system |

## Related
- Business view: [[City.business|City]]
- [[Area-and-Country|Area]] — a city's sub-divisions
- [[DeliveryMen.technical|DeliveryMen]] — consumes financial defaults (Rule 2)

## Open Questions
- [ ] The actual call site(s) that read City's financial defaults into `DeliveryMen`'s deduction math
  weren't traced — confirmed only by matching parameter names.
- [ ] Whether `UpdateCity`'s "no price data ⇒ delete all prices" behavior (Rule 3) is intentional API
  design or a footgun for a caller that forgets to pass the existing list back.
- [ ] What `EightOrdersOpenTime`/`EightOrdersCloseTime` actually gate — not traced.
- [ ] Whether `CityTaxPercentage`/`CityMinTax`/`CityMaxTax` and `CartItem`'s category/restaurant tax
  fields (`CartItem.technical.md`, Cart & Checkout) are reconciled anywhere, or represent two
  independent tax mechanisms.
- [ ] `DeliveryManPrice` itself not yet documented.
