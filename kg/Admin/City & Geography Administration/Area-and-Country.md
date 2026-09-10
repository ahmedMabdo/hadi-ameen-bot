---
id: 8orders/admin/city-and-geography-administration/area-and-country
note_type: single
context: Admin
feature: City & Geography Administration
group: Area-and-Country
covers: [Area, AreaDecription, CityDailyPickupTagCounter, CityDescription, CityRushTimeConfigHistory, CitySuggestions, Country, RushTimeAreaPriority, WorkingDay]
sources:
  - path: Shared/TalabatkLogic/TalabatkModels/AreaDecription.cs
    sha1: 2c081f0050c2
  - path: Shared/TalabatkLogic/TalabatkModels/CityDailyPickupTagCounter.cs
    sha1: a180b17f30f0
  - path: Shared/TalabatkLogic/TalabatkModels/CityDescription.cs
    sha1: b4b7376c974f
  - path: Shared/TalabatkLogic/TalabatkModels/CityRushTimeConfigHistory.cs
    sha1: afa6d590de13
  - path: Shared/TalabatkLogic/TalabatkModels/CitySuggestions.cs
    sha1: 25fcb76b8727
  - path: Shared/TalabatkLogic/TalabatkModels/WorkingDay.cs
    sha1: fe7cd69d1562
  - path: Shared/TalabatkLogic/TalabatkModels/Area.cs
    sha1: e94900c8a715
  - path: Shared/TalabatkLogic/TalabatkModels/Country.cs
    sha1: e2035c78c2fe
last_updated: 2026-08-23
tags: [admin, master, technical, backend-domain]
---
# Area (+ Country)

Two lighter geographic reference entities, both children in the same location hierarchy as
[[City.technical|City]]: `Country` → `City` → `Area`.
`Shared/TalabatkLogic/TalabatkModels/Area.cs` / `Country.cs`.

## Area
A city's sub-division — has a real geo border and one actual validation method, otherwise a thin
reference row.

- **`ValidateRestaurantArea(customerRestaurantIds)`** (`Area.cs:49-68`) — given a list of restaurant
  ids, returns the subset that do **not** cover this area (i.e. aren't linked via `TA_RestaurantArea`).
  An empty list back means every requested restaurant covers the area. Used, presumably, to validate
  a multi-restaurant cart/order against delivery coverage — the actual caller wasn't traced in this
  pass.
- **`AreaBorder`** (`Geometry`) is set separately via `UpdateBorder(Polygon)` (`Area.cs:93-96`), not
  part of the main `Instance`/`Update` factory pair — worth noting since a caller creating/updating an
  area's other fields won't touch its border unless it also calls this.
- No numeric/uniqueness validation in `Instance`/`Update` (`Area.cs:69-90`) beyond assigning fields —
  contrast `City`'s weight-sum guard (Rule 1 there).
- `RushTimeAreaPriorityId` field exists but isn't set anywhere in this class — likely configured
  elsewhere (ties to `CityRushTimeConfiguration`, not yet documented in this pass).

## Country
A trivial reference entity — name pair (Arabic/English) and a currency id, plus the payment methods
valid for that country.

- `Instance`/`UpdateCountry` (`Country.cs:17-30`) have no validation at all — plain field assignment.
- `MethodCountries` (`PaymentMethodCountries`, not yet documented) is the only relationship of note —
  which payment methods are available per country.

## Folded entities — the 6 further satellites documented here

| Entity | What it is | Rules |
|---|---|---|
| `AreaDecription` | An area's name in one language | Guards both paths, with the two messages **swapped relative to its own siblings**: `Instance` says "wrong Parameters" (`Shared/TalabatkLogic/TalabatkModels/AreaDecription.cs:30`) and `Update` says "Empty Parameters" (`:21`). Note the misspelt class and file name — `Decription` — which is the real one and has to be spelled that way in every query |
| `CityDescription` | A city's name in one language | The same two guards with the same two messages (`Shared/TalabatkLogic/TalabatkModels/CityDescription.cs:22`, `:31`), and a primary key named `AK_CityTranslationId` — the only `AK_`-prefixed key in the model, a leftover naming convention |
| `WorkingDay` | A restaurant's opening and closing time for one weekday | `Instance` only, **no guards** (`Shared/TalabatkLogic/TalabatkModels/WorkingDay.cs:26`), so nothing prevents a close time earlier than the open time, or two rows for the same day. This is the table that decides whether a customer sees a restaurant as open |
| `CitySuggestions` | A customer's suggestion of a city 8Orders does not yet serve | `Instance` only, no guards (`Shared/TalabatkLogic/TalabatkModels/CitySuggestions.cs:19`). It joins to `Customer`, and that join is what makes the admin listing a full name-and-phone dump — 🔴 `_conflicts.md` #414, where the `[Permission("SuggestionCity")]` attribute guarding it is commented out |
| `CityDailyPickupTagCounter` | The last pickup-tag number issued in a city on a business date | Private ctor, `Instance` only (`Shared/TalabatkLogic/TalabatkModels/CityDailyPickupTagCounter.cs:16`). A per-city, per-day sequence with `LastValue` mutated in place — so uniqueness of the customer-facing pickup tag depends entirely on how the incrementing caller handles concurrency, not on this entity |
| `CityRushTimeConfigHistory` | A closed period during which a city was in rush mode, and how many orders it saw | The only method is `CloseHistory` (`Shared/TalabatkLogic/TalabatkModels/CityRushTimeConfigHistory.cs:29`) — there is **no factory at all**, so rows are opened by the caller and only closed through the entity. Note `StratAt`, misspelt, alongside a correctly spelled `EndAt` |

Five of the six have no validation, and the one that matters most operationally — `WorkingDay` — is
among them. Three of the six carry a misspelling in a name that queries must reproduce exactly
(`AreaDecription`, `StratAt`, `AK_CityTranslationId`).

## Related
- [[City.technical|City]] — the parent in the location hierarchy; also where the bulk of
  geography-driven business rules actually live.

## Open Questions
- [ ] Who calls `Area.ValidateRestaurantArea` — not traced in this pass.
- [ ] What sets `RushTimeAreaPriorityId` — likely `CityRushTimeConfiguration`, not yet documented.
- [ ] `PaymentMethodCountries` not yet documented.
