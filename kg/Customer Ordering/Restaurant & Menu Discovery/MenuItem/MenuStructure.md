---
id: 8orders/customer-ordering/restaurant-and-menu-discovery/menustructure
note_type: single
context: Customer Ordering
feature: Restaurant & Menu Discovery
group: MenuStructure
covers: [MainCategory]
sources:
  - path: Shared/TalabatkLogic/TalabatkModels/MainCategory.cs
    sha1: 1ab71e46ed1b
  - path: Shared/TalabatkLogic/TalabatkModels/ImageBank.cs
    sha1: 809d295f787a
  - path: Shared/TalabatkApplication/Commands/MangeCatgoriesFromExcelSheetCommand/MangeCatgoriesFromExcelSheetCommand.cs
    sha1: 3dcc0abbe365
  - path: Shared/TalabatkApplication/Commands/MoveMenuItemsToAnotherCategoryCommand/MoveMenuItemsToAnotherCategoryCommand.cs
    sha1: c85add809f1f
  - path: Shared/TalabatkLogic/TalabatkModels/ImageBank.cs
    sha1: 809d295f787a
  - path: Shared/TalabatkLogic/TalabatkModels/MenuCategory.cs
    sha1: ebebb97f2cc6
  - path: Shared/TalabatkLogic/TalabatkModels/MenuItemOptions.cs
    sha1: 650cad02b126
  - path: Shared/TalabatkLogic/TalabatkModels/MenuItemOptionsCategories.cs
    sha1: 805d457345c8
last_updated: 2026-08-23
tags: [customer-ordering, restaurant-menu-discovery, child, technical, backend-domain]
---
# Menu Structure — MenuCategory, MenuItemOptions, MenuItemOptionsCategories, ImageBank

Lighter-touch coverage of the remaining menu-structure entities, grouped for efficiency rather than
given full separate notes — no standout bugs found, but a few points worth recording.

## MenuCategory
`Shared/TalabatkLogic/TalabatkModels/MenuCategory.cs`. A restaurant's menu section (e.g.
"Appetizers"). Has its own real open-hours check, `IsOpen(nowDate)` (`:47-78`) — overnight-aware,
same shape as `Restaurant`'s own open-hours logic (already documented) and `Offers.CheckOfferIsValid`
— a fourth independent implementation of "is this open right now" time-window logic in the codebase
(not adding as a new numbered conflict — the pattern is already well-established via #8/#10/#18/#22/#23/#25;
noted here for completeness). `Update` (`:150-183`) cascades a tax-percentage change to every child
`MenuItem` via `item.ApplyTax(...)` — a real, notable side effect: changing a category's tax setting
retroactively reapplies it to every item in that category.

- **Application layer, `EditMenuCategoryCommand`:** saves the category (`:143`) **before** uploading
  the actual category image (`:148-154`) — same save-before-upload-then-orphaned-record shape as
  `_conflicts.md` #54 (`SliderHome`)/#57 (`StoreTypes`); now a 3rd confirmed instance of this pattern
  (a 4th, `EditAdCommand`, is even worse — see `_conflicts.md`).
- **⚠️ Confirmed bug, `MoveMenuItemsToAnotherCategoryCommand`:** awaits `SaveChangesAsyncWithResult()`
  and captures it, but returns `Success = true` unconditionally regardless of `result.IsSuccess` —
  same shape as `_conflicts.md` #56/#60/#78. **Source:** `MoveMenuItemsToAnotherCategoryCommand.cs:38-40`.
- **⚠️ Confirmed bug, `MangeCatgoriesFromExcelSheetCommand` (bulk Excel category/item/price import):**
  the post-save stage that copies category/item images and re-indexes Elastic Search is wrapped in a
  `try/catch` whose `catch` silently swallows **any** exception (unlogged) and unconditionally returns
  `Result.Success(...)` — so the category/item rows can be created successfully in the DB while their
  images or search-index entries silently fail, with no signal to the caller or the logs at all.
  **Source:** `MangeCatgoriesFromExcelSheetCommand.cs:152-200`.

## MenuItemOptions (+ MenuItemOptionsCategories)
`MenuItemOptions.cs` / `MenuItemOptionsCategories.cs`. Both extend `AuditableEntity` like
`MenuItemPrice`, but — unlike `MenuItemPrice`'s mislabeled `TrackChange` calls (see
`MenuItemPrice.technical.md` Rule 2) — these two correctly use their own distinct
`EntityChangeType.Option`/`EntityChangeType.MenuCategoryOption` values, so no mislabeling issue here.
Both validate a non-blank reference name in `Update` (not in the constructor/`Instance` — same
create/update asymmetry already established elsewhere in this pass). `MenuItemOptions` has three
different update entry points (`Update`, `PartialUpdate`, `ActiveUpdate`) with different field
coverage — not confirmed which callers use which.

## ImageBank
`ImageBank.cs`. Trivial image-path/extension holder. `UpdateImage` validates both fields non-empty
(`Shared/TalabatkLogic/TalabatkModels/ImageBank.cs:33`); `Instance` (creation) does not
(`:17`) — same asymmetry pattern, noted without adding a new register row.

## MainCategory

`MainCategory.cs` — the top level above `MenuCategory`, and the smallest entity in the menu tree: a
private constructor, `Id`, `NameEn`, `NameAr` and the `MenuCategories` collection, with **no methods at
all** (`Shared/TalabatkLogic/TalabatkModels/MainCategory.cs`). No factory, so rows are seeded or built by
EF; no `Update`, so a main category's name cannot be changed through the domain.

Worth keeping straight because three similar names coexist in this feature and they are different tables:

| Name | What it is |
|---|---|
| `MainCategory` | The food-menu top level; `MenuCategory.MainCategoryId` points here |
| `MartMainCategory` | The **grocery** taxonomy, self-parenting for sub-categories, and heavily validated — see [[Customer Ordering/Restaurant & Menu Discovery/Discovery-Utilities\|Discovery Utilities]] |
| `MenuCategory` | A section of one restaurant's menu, which carries **both** `MainCategoryId` and `MartMainCategoryId` |

So `MenuCategory` is the join point between the food and grocery taxonomies, and nothing in the entity
prevents a row from being filed under both at once.

## Related
- [[MenuItem.technical|MenuItem]], [[MenuItemPrice.technical|MenuItemPrice]]

## Open Questions
- [ ] Which callers use `MenuItemOptions.Update` vs. `PartialUpdate` vs. `ActiveUpdate`.
