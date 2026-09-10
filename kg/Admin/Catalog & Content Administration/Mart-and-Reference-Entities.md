---
id: 8orders/admin/catalog-and-content-administration/mart-and-reference-entities
note_type: single
context: Admin
feature: Catalog & Content Administration
group: Mart-and-Reference-Entities
covers: [ImageBank]
sources:
  - path: Shared/TalabatkLogic/TalabatkModels/ImageBank.cs
    sha1: 809d295f787a
  - path: Shared/TalabatkLogic/TalabatkModels/JournalSubuscriptions.cs
    sha1: 6ae43eaa31b4
  - path: Shared/TalabatkLogic/TalabatkModels/MartMainCategory.cs
    sha1: f55bcfa21eea
  - path: Shared/TalabatkLogic/TalabatkModels/RestaurantFinalScoreRate.cs
    sha1: b9c9bbcbc458
  - path: Shared/TalabatkLogic/TalabatkModels/RestaurantZoneArea.cs
    sha1: 64669b28c955
  - path: Shared/TalabatkLogic/TalabatkModels/Tag.cs
    sha1: f573be01e1d1
  - path: Shared/TalabatkLogic/TalabatkModels/UnRegesteredCustomers.cs
    sha1: 1203168f7464
last_updated: 2026-08-23
tags: [admin, master, technical, backend-domain]
---
# MartMainCategory, RestaurantFinalScoreRate, Tag, UnRegesteredCustomers, RestaurantZoneArea, JournalSubuscriptions

Grouped lighter-touch coverage of remaining reference/config entities.

## MartMainCategory
`Shared/TalabatkLogic/TalabatkModels/MartMainCategory.cs`. Mart product category hierarchy
(parent/sub-category tree), extends the existing light `Mart.md` note in Customer Ordering.
`Instance` validates Arabic/English name, logo, landscape image, and ≥1 sub-category; a lighter
`InstanceAsSubCategory` skips the image/subcategory requirements (correctly, since a sub-category has
neither).

- **⚠️ Likely bug — `Update` appends instead of replacing sub-categories:**
  `Update(...)` (`:107-126`) does `this._SubCategories.AddRange(subCategories)` — **adds** the
  incoming list to whatever's already there, rather than syncing/replacing it (unlike this
  codebase's more careful sync methods, e.g. `PaymentMethod.UpdateCountries`,
  `DeliveryMen.Update`'s zone reconciliation). Calling `Update` more than once with the same or
  overlapping sub-category list would duplicate entries.
- `ChangeActiveStatus(active)` (`:178-186`) cascades the activation flag to every sub-category —
  a real, deliberate cascading rule, same shape as `MenuCategory.Update`'s tax cascade to its items.

## RestaurantFinalScoreRate
`RestaurantFinalScoreRate.cs`. Purely a cached/computed score row — no methods at all. Presumably
written by a background job using `City`'s scoring-weight formula (already documented, `City.technical.md`
Rule 1) — the actual computation wasn't traced to this pass.

## Tag, UnRegesteredCustomers, RestaurantZoneArea
Trivial reference/light entities: `Tag` (name holder, `Tag.cs`), `UnRegesteredCustomers`
(device-id/token tracking for never-registered app installs, presumably push-notification targeting,
`UnRegesteredCustomers.cs`, create-only), `RestaurantZoneArea` (per-area customer delivery fee for a
restaurant-specific zone, `RestaurantZoneArea.cs`, one guard: `areaId` required).

## JournalSubuscriptions
`JournalSubuscriptions.cs`. Recurring accounting-journal subscription tied to a set of restaurants —
**a clean, positive example, and a real one**: both live paths validate, and they validate the same
things. `Instance` requires a non-empty name and at least one restaurant
(`Shared/TalabatkLogic/TalabatkModels/JournalSubuscriptions.cs:64`, `:74`); `Update` requires at least
one restaurant, a name and a description (`:100`, `:108`, `:112`); and `AddExcutionHistory` rejects a
null history (`:126`). Both return `Result`.

Worth stating precisely, because an earlier version of this note called it "matching
`PaymentMethod`/`Audiance`'s well-behaved shape". `PaymentMethod`'s create and update are indeed
identical — but only because its `Instance` is **never called** (🟡 `_conflicts.md` #632), so there is no
pair being kept in sync there. `JournalSubuscriptions` is the genuine article: two live methods that
agree. The one asymmetry is that `Update` requires a description and `Instance` does not.

## ImageBank

`ImageBank.cs` — the image-path holder every image-bearing entity in the platform points at
(`Brand.LogoId`, `MartMainCategory.LandscapeId`, `Ads.ArabicImageId`, `SliderHome.ImageId`,
`MenuCategory.ImageId`, and more). Three properties — `ImageId`, `imagePath`, `Extension` — and the usual
asymmetry: `Instance` assigns without checking (`Shared/TalabatkLogic/TalabatkModels/ImageBank.cs:17`)
while `UpdateImage` rejects blanks with "Empty Parameters" (`:33`).

Two things make it worth more than its three fields suggest. It is the single most widely referenced
lookup in the model, so a row deleted here breaks images across unrelated features; and the low-quality
companion files written beside each original are **not represented in this table at all** — clients build
the `_low` URL by convention and a fallback middleware resolves it, so the database has no record of
which companions exist.

Note the lower-case `imagePath` property, which is the real name.

## Related
- [[Mart|Mart]] (light note, Customer Ordering)
- [[City.technical|City]] — `RestaurantFinalScoreRate`'s presumed scoring source

## Open Questions
- [ ] Whether `MartMainCategory.Update`'s append-not-replace behavior (above) has caused duplicate
  sub-categories in practice.
- [ ] What actually computes `RestaurantFinalScoreRate` — not traced (likely a Hangfire job).
