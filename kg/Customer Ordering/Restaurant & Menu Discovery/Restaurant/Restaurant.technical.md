---
id: 8orders/customer-ordering/restaurant-and-menu-discovery/restaurant-technical
note_type: technical
rule_count: 5
context: Customer Ordering
feature: Restaurant & Menu Discovery
entity: Restaurant
entity_type: child
sources:
  - path: Shared/TalabatkApplication/Commands/EditRestaurantCommand/EditRestaurantCommand.cs
    sha1: 6e197e03cafe
  - path: Shared/TalabatkApplication/Commands/MangeRestaurantWorkingDaysCommand/MangeRestaurantWorkingDaysCommand.cs
    sha1: decd196067f4
  - path: Shared/TalabatkApplication/Queries/RestaurantInfoByRestuarantId/RestaurantInfoByRestaurantIdQuery.cs
    sha1: dacf1684f300
  - path: Shared/TalabatkLogic/TalabatkModels/CartItem.cs
    sha1: 7048d48ce442
  - path: Shared/TalabatkLogic/TalabatkModels/Restaurant.cs
    sha1: 42514c8fb3e5
last_updated: 2026-08-23
tags: [customer-ordering, restaurant-menu-discovery, master, technical, backend-domain]
---
# Restaurant — Technical

> **Layer:** Domain — Legacy POCO   **Context:** Customer Ordering (read/browse) / Restaurant Portal (managed, not covered here)   **Feature:** Restaurant & Menu Discovery
> **Source Path:** `Shared/TalabatkLogic/TalabatkModels/Restaurant.cs` (1,055 lines — this note covers the customer-facing "is it open / is it new" logic, not full profile management)   **Last Updated:** 2026-08-02

A restaurant or **Mart** (grocery/quick-commerce store) — `IsStore=true` marks the latter; there is
**no separate Mart entity**, "Mart" is a browsing/category layer over the same `Restaurant` +
`MenuItem` models (confirmed via `CreateOrderFromCartCommand`'s `r.IsStore` check and
`MartController`'s routes, which all read/search the same underlying data). See the Mart light note.

## Business Rules

### Rule 1: Two coexisting open-hours strategies
- **Plain language:** Whether a restaurant is "open right now" is computed one of two ways
  depending on a flag: a **legacy** single daily open/close window, or a **newer** full per-day
  working-hours schedule that supports overnight hours (open Monday 10pm, closes Tuesday 2am).
- **Source:** `Restaurant.cs:330-343` (`CheckResturantOpen`) branches on `ApplyWorkingDays`:
  `CheckRestaurantOpenWithNewWorkingDaysOn` (new, per-day schedule,
  `Restaurant.cs:449-` — not fully read in this pass) vs.
  `CheckRestaurantOpenWithNewWorkingDaysOff` (legacy, `Restaurant.cs:346-446`, single start/end
  time + a day-of-week bitmask string `OpenWeekDays`, with explicit overnight-wraparound handling).

### Rule 2: "New restaurant" badge is time-boxed
- **Source:** `Restaurant.cs:529-533` (`CheckResturantIsNew`) — a restaurant is only "new" for a
  configured period after some reference date; details of the window not fully read in this pass.

### Rule 3: Working-day changes require at least one open day
- **Source:** `Restaurant.cs:945-962` (`MangeRestaurantWorkingDays`) —
  `"Open Week Days Can Not Be Empty"` guards both the legacy and new working-day representations.

### Rule 4: Application layer — `EditRestaurantCommand`, 2 confirmed bugs
- **⚠️ Confirmed bug (copy-paste validation):** the background-image branch validates the wrong
  field — `_uploadImage.Validate(command.LogoimageBase64)` instead of
  `command.BackGroundimageBase64` — so an invalid background image is never actually rejected (and
  the error message, "Invalid Logo Image", is mislabeled too).
  **Source:** `EditRestaurantCommand.cs:206-213`.
- **⚠️ Confirmed bug (6th instance of the save-before-upload pattern):** saves changes (`:350`)
  before uploading the actual background/logo image bytes (`:359-392`) — same
  save-then-orphaned-record-on-upload-failure shape as `_conflicts.md` #54/#57/#75/#77.
  **Source:** `EditRestaurantCommand.cs:350-392`.

### Rule 4b: Application layer — main restaurant browse/search query has 3 unguarded dereferences
- **⚠️ Confirmed bugs, high-traffic path:** `GetAllActiveRestaurantWithReviewInfoQuery` (the current
  EF-based restaurant browse/search) dereferences `RestaurantName`/`CityName` from `FirstOrDefault()`
  translation lookups with no null-check, and `x.OpenFrom.Value.TimeOfDay`/`x.OpenTo.Value.TimeOfDay`
  with no `.HasValue` check. A restaurant/city missing a translation for the requested language, or a
  restaurant with unset working hours, throws. The deprecated sibling
  `GetAllRestaurantsWithActiveReviewsOldVersion` has the identical `OpenFrom.Value`/`OpenTo.Value` gap.
  The newer stored-procedure-based `SearchStoresQueryV2` does not have this issue.
  **Source:** `GetAllActiveRestaurantWithReviewInfoQuery.cs:156,182,198`.

### Rule 4c: `RestaurantInfoByRestaurantIdQuery` overrides `OpenFrom` while inside a busy period
- **Plain language:** if the restaurant is currently in a manually-set busy window
  (`RestaurantBusyHistory`), the displayed `OpenFrom` shows the busy period's end time instead of
  the configured opening time — added post-Phase-14, not present when this note's Rule 4b bug
  (#189) was documented. Properly `HasValue`-guarded, no new bug found. Rush-time busy (area-wide,
  no end time) is explicitly not considered here.
- **Source:** `RestaurantInfoByRestaurantIdQuery.cs:198-212`.

### Rule 5: Application layer — `MangeRestaurantWorkingDaysCommand` ignores `TryParseExact`'s result
- **⚠️ Confirmed bug:** `BuildOpenWOrkingDays` calls `DateTime.TryParseExact(workingDay.OpenTime, ...)`
  and the matching call for `CloseTime` as bare statements, never checking the returned `bool`. If a
  working-day's time string fails to parse, the `out` variable silently stays at `default(DateTime)`
  (midnight) instead of the command failing — a malformed time value silently becomes a
  midnight-to-midnight working window rather than being rejected with a clear validation error.
  **Source:** `MangeRestaurantWorkingDaysCommand.cs:132-152`.

| Field | Meaning |
|-------|---------|
| `IsStore` | Marks this row as a **Mart** (grocery/store) rather than a restaurant — same entity, different browsing category |
| `ApplyWorkingDays` | Switches between legacy single-window and new per-day schedule (Rule 1) |
| `OpenWeekDays` | Legacy day-of-week bitmask string |
| `Active` | Whether the restaurant/store can be ordered from at all |
| `UseMenuCategoryProfit` / `Profit` | Drives which profit percentage a `CartItem` snapshots (see `CartItem.md`) |
| `ApplyProfitDate` | The date a profit-percentage change takes effect — items added before this date keep the old rate (see `CartItem.cs:263-273`) |

## Dependencies & Integrations
| Depends on / integrates | Side/Context | Via | Notes |
|--------------------------|---------------|-----|-------|
| [[MenuItem.technical\|MenuItem]] | Backend-Domain | `TA_MenuCategory` → items | A restaurant's menu. |
| [[CartItem\|CartItem]] | Backend-Domain | Snapshotted at add-to-cart time | See `CartItem.technical.md`'s flagged staleness conflict — this is the source data that gets snapshotted. |
| Restaurant Portal | *(not covered here)* | Restaurant Portal manages its own profile/menu/hours | This note only covers the read-side "is it open/new" logic Customer Ordering consumes. |

## Open Questions
- [ ] Full restaurant profile management (creation, menu editing, working-hours editing UI) belongs
  to Restaurant Portal — not documented in this pass.
- [ ] The new per-day working-hours schedule (`CheckRestaurantOpenWithNewWorkingDaysOn` and its
  `IsRegularOpenToday`/`IsOvernightOpenToday` helpers) wasn't read in full — flagged for a future
  pass if working-hours logic needs a CR.

## Related
- Business view: [[Restaurant.business|Restaurant]]
- [[Mart|Mart]] — the store/grocery browsing layer over this same entity
- [[MenuItem.technical|MenuItem]]
