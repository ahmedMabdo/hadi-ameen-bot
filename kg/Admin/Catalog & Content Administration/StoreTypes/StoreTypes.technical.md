---
id: 8orders/admin/catalog-and-content-administration/storetypes-technical
note_type: technical
rule_count: 9
context: Admin
feature: Catalog & Content Administration
entity: StoreTypes
entity_type: child
sources:
  - path: Shared/TalabatkApplication/Commands/AddStoreTypeCommand/AddstoreTypeCommand.cs
    sha1: 81610dffa6ef
  - path: Shared/TalabatkApplication/Commands/EditStoreTypeCommand/EditStoreTypeCommand.cs
    sha1: 46e31a648301
  - path: Shared/TalabatkLogic/TalabatkModels/StoreTypes.cs
    sha1: 6d1e1c29b45c
  - path: Shared/TalabatkLogic/TalabatkModels/StoreTypesDescription.cs
    sha1: 48cbfa2189b7
last_updated: 2026-08-23
tags: [admin, master, technical, backend-domain]
---
# StoreTypes (+ StoreTypesDescription)

The merchant-category taxonomy (e.g. Restaurant, Mart, Store) — every `Restaurant` row belongs to a
`StoreTypes`. `Shared/TalabatkLogic/TalabatkModels/StoreTypes.cs` /
`StoreTypesDescription.cs`.

## Business rules — two confirmed bugs, both previously flagged informally, now cited directly

### ⚠️ Confirmed bug: `UpdateStoreType`'s guard uses `&&` where its sibling `AddStoreType` correctly uses `||`
- **Plain language:** Creating a store type correctly rejects the request if *any* required field is
  bad. Updating one only rejects if *both* the order number is negative *and* the name is empty at
  the same time — so you can update a store type with a blank name (as long as the order number is
  non-negative) or a negative order number (as long as the name isn't blank), neither of which the
  create path would ever allow.
- **Source:** `StoreTypes.cs:40-54` (`UpdateStoreType`) —
  `if (OrderNumber < 0 && string.IsNullOrEmpty(ReferenceName)) return Result.Failure(...)`. Contrast
  `StoreTypes.cs:56-75` (`AddStoreType`) —
  `if (OrderNumber < 0 || string.IsNullOrEmpty(ReferenceName) || descriptions == null || ImageBank == null)`.

### ⚠️ Confirmed bug: `StoreTypesDescription.AddDescription` validates the wrong field
- **Plain language:** The guard meant to check the incoming language id instead checks the
  description's own already-stored (and, for a new description, still-null) language id — so the
  check almost never actually rejects anything based on the language id being invalid.
- **Source:** `StoreTypesDescription.cs:27-36` —
  `if (string.IsNullOrEmpty(Description) || LanguageId<0) ...` — `LanguageId` (capital L, the
  **existing field**, nullable `int?`, starts `null`) is checked instead of the method's own
  parameter `languageId` (lowercase, the **incoming value**). In C#, a nullable-int `<` comparison
  against `null` evaluates to `false`, so this half of the guard is effectively dead for a
  newly-constructed description. This is the same shape as a bug independently found and confirmed
  earlier in this pass on `Customer.UpdateInfo` (guards the existing field instead of the incoming
  parameter) — worth flagging to the team as a recurring copy-paste mistake pattern across the
  codebase, not two unrelated one-offs.

### ⚠️ Confirmed bug (Application layer): `AddstoreTypeCommand` saves before uploading its images
- **Plain language:** the store type row (with image/icon IDs already assigned) is committed to the
  database first; the actual image/icon file upload happens afterward. If either upload fails, the
  command returns failure but the store type row is already saved — left referencing image files
  that were never written. Same shape as the `SliderHome` finding in
  [[Admin/Admin Back-Office/_knowledge-graph|Admin Back-Office]] (`_conflicts.md` #54) — now a confirmed
  repo-wide pattern, not a one-off.
- **Source:** `AddstoreTypeCommand.cs:82-108`.
- **⚠️ Same bug, sibling `EditStoreTypeCommand` (7th instance repo-wide):** saves at `:140` before
  uploading the image/icon bytes at `:145-168`.
  **Source:** `EditStoreTypeCommand.cs:126-154`.

## Other notes
- `StoreTypes` has no per-city uniqueness/name-conflict validation — `AddStoreType` sets
  `CityId = 0` unconditionally (`:65`), and city assignment happens separately via
  `TA_StoreTypesCities`/`AddCities` (`:89-95`) — the meaning of the `CityId` field itself vs. the
  `StoreTypeCities` join collection wasn't fully reconciled in this pass (Open Question).

## Rule / Decision Matrix

The store-type taxonomy — Restaurant, Mart and so on — with per-city availability, images and a set of behavioural flags that quietly decide what a store type can do.

| # | Rule | Where | Notes |
|---|---|---|---|
| 1 | `AddStoreType` rejects blank parameters | `Shared/TalabatkLogic/TalabatkModels/StoreTypes.cs:61` | "Empty Parameters" — the only guard on creation |
| 2 | `UpdateStoreType` rejects blank parameters | `Shared/TalabatkLogic/TalabatkModels/StoreTypes.cs:44` | Same message, so create and update agree |
| 3 | `IsStore` is what makes a store type a mart rather than a restaurant | `Shared/TalabatkLogic/TalabatkModels/StoreTypes.cs:56` | The flag the whole mart browse surface keys off |
| 4 | `AcceptRoundOrders` decides whether orders can be rounded | `Shared/TalabatkLogic/TalabatkModels/StoreTypes.cs:40` | Set through `UpdateStoreType`, unvalidated |
| 5 | `IsRestaurantSearch` controls inclusion in restaurant search | `Shared/TalabatkLogic/TalabatkModels/StoreTypes.cs:40` | So a store type can exist and be unsearchable |
| 6 | `IsShortCutApp` scopes the type to the shortcut app | `Shared/TalabatkLogic/TalabatkModels/StoreTypes.cs:40` |  |
| 7 | `HidFoodType` hides the cuisine filter for this type | `Shared/TalabatkLogic/TalabatkModels/StoreTypes.cs:40` | Misspelt; it is the real name |
| 8 | Images are attached by dedicated unguarded setters | `Shared/TalabatkLogic/TalabatkModels/StoreTypes.cs:78-83` | `AddImage`, `AddIcon` — `void`, no null check, unlike `Brand` which rejects a null image |
| 9 | City availability is replace-then-add, not a diff | `Shared/TalabatkLogic/TalabatkModels/StoreTypes.cs:89-96` | `AddCities` and `ClearCities` are separate, so the caller owns correctness |

> Its Admin controller saves **before** uploading the image bytes, so a failed upload leaves a saved
> store type with no image — 🔴 `_conflicts.md` #80, and the 7th instance of that pattern.

## Related
- [[Restaurant.technical|Restaurant]] — every restaurant belongs to a `StoreTypes`

## Open Questions
- [ ] What `StoreTypes.CityId` (single FK, always `0` at creation) means relative to
  `TA_StoreTypesCities` (a full list of cities) — possibly a legacy field superseded by the join
  table, not confirmed.
- [ ] Whether the `UpdateStoreType`/`AddDescription` bugs above have caused real bad data in
  production — flagged as high-confidence code-reading findings, not verified incidents.
