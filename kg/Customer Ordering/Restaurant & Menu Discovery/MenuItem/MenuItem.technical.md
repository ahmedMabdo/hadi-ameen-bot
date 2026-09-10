---
id: 8orders/customer-ordering/restaurant-and-menu-discovery/menuitem-technical
note_type: technical
rule_count: 4
context: Customer Ordering
feature: Restaurant & Menu Discovery
entity: MenuItem
entity_type: child
covers: [MenuItemActivationHistory, MenuItemImage]
sources:
  - path: AdminUi/Controllers/MenuItemActivationTrackingController.cs
    sha1: 6d1ad7552b5e
  - path: Shared/TalabatkLogic/TalabatkModels/MenuItemActivationHistory.cs
    sha1: b5caba69af6f
  - path: Shared/TalabatkLogic/TalabatkModels/MenuItemImage.cs
    sha1: 0de8d73ee930
  - path: Shared/TalabatkLogic/DomainEvents/MenuItemEvents/MenuItemActivationChangedEvent.cs
    sha1: 0f1955a11b5b
  - path: Shared/TalabatkApplication/Commands/ConfirmUnRevisedItemCommand/ConfirmUnRevisedItemCommand.cs
    sha1: f95fecda6a51
  - path: Shared/TalabatkApplication/Commands/CopyMenuItemCommand/CopyMenuItemCommand.cs
    sha1: b0fcffb0f6e2
  - path: Shared/TalabatkApplication/Commands/EditMenuItem/EditMenuItemCommand.cs
    sha1: 56b19db7c7f5
  - path: Shared/TalabatkApplication/Commands/EditMenuItemPriceCommand/EditMenuItemPriceCommand.cs
    sha1: e183d5bc1c8d
  - path: Shared/TalabatkLogic/TalabatkModels/MenuItem.cs
    sha1: 41321a3dafe6
last_updated: 2026-08-23
tags: [customer-ordering, restaurant-menu-discovery, master, technical, backend-domain]
---
# MenuItem — Technical

> **Layer:** Domain — Legacy POCO, event-raising (`AddRecordPostDomainEvent`, `TrackChange` audit helper)   **Context:** Customer Ordering (read/browse) / Restaurant Portal (managed, not covered here)   **Feature:** Restaurant & Menu Discovery
> **Source Path:** `Shared/TalabatkLogic/TalabatkModels/MenuItem.cs` (1,202 lines — this note covers availability/stock and the activation-history/gallery children, not full catalog management)   **Last Updated:** 2026-09-09

## Business Rules

### Rule 1: Availability suspension has 4 durations, keyed by rejection reason
- **Plain language:** When a restaurant marks an item unavailable, how long it stays hidden depends
  on why: 1 hour, 2 hours, the rest of the working day, or a full year (effectively indefinite,
  used as a stand-in for "deactivate").
- **Source:** `MenuItem.cs:561-597` (`ChangeItemAvalibilty`) — keyed off
  `RestaurantOrderDetailsAvailability` enum values (`ItemNotAvalibleForOneHour`,
  `ItemNotAvalibleForTwoHour`, `ItemNotAvalibleAllDay`, `ItemNotAvalibleAtAllYear`); any other
  reason instead sets `Active = false` outright.

### Rule 2: Repeated rejections from the same shift compound the suspension exponentially
- **Plain language:** If a restaurant keeps deleting/rejecting the same item from orders within one
  shift, each successive rejection doubles how long the item stays unavailable (1h, 2h, 4h, 8h...).
- **Why this matters:** it's a real anti-flakiness mechanism — a restaurant that's unreliable about
  one item gets an escalating "cool-down," not just a flat penalty, unless the item was actually
  delivered since the last rejection (which resets to a flat 1-hour suspension instead).
- **Source:** `MenuItem.cs:651-677` (`ChangeItemAvalibiltyAfterDeletingOrderDetails`) —
  `totalItemUnAvalibleHours = Math.Pow(2, numberOfTimesThatItemHasBeenDeletedInOrderDetailsInShift)`.
  For Mart items specifically, the item is fully deactivated instead of time-suspended
  (`isMart` parameter short-circuits to `Deactivate()`).

### Rule 3: Stock hitting zero/recovering toggles availability automatically
- **Source:** `ApplyStockQuantity` (`MenuItem.cs:1122-1161`) — negative quantities clamp to zero
  (`:1126-1127`); reaching exactly zero calls `SetItemOutOfStock()` and returns (`:1137-1141`);
  recovering from zero calls `SetItemInStock(notifySubscribers: …)` (`:1148-1151`) and re-activates
  the item unless it is held closed deliberately (below).
- **One implementation, two entry points.** `UpdateStockQuantity` (`:1065-1069`) and `MaintainStock`
  (`:1164-1170`) are now three-line wrappers that both delegate to `ApplyStockQuantity`. This note
  previously recorded them as two independent copies of the rule (`_conflicts.md` #10, a drift risk);
  that duplication was **resolved upstream on `master`** and #10 is closed.
- **`IgnoreErpStockActivation` overrides re-activation.** An item switched to manual control stays
  inactive even when stock arrives (`:1153-1154`), and the "in stock now" push to subscribers is
  withheld in that case rather than spent on an item nobody can order (`:1144-1146`) — so the
  customer's notification request survives until the real re-opening.
- **The quantity is assigned before anything can activate** (`:1134`), so the activation-history
  snapshot records the quantity that *drove* the decision. Assigning last, as this method used to,
  stamped every ERP re-activation with the previous quantity — almost always zero for an item being
  re-opened.

### Rule 4: Application layer — two confirmed bugs in item-management commands
- **⚠️ Confirmed bug, `CopyMenuItemCommand`:** fetches `menuItem` via `FirstOrDefaultAsync()` with
  **no null-check** before passing it straight into `new MenuItem(menuItem)` (a copy constructor) —
  an invalid `MenuItemId` throws inside the constructor instead of a graceful failure. Separately, the
  save result is captured but never checked — the handler always returns `Success = true` regardless
  of whether the copy actually persisted.
  **Source:** `CopyMenuItemCommand.cs:31-55`.
- **⚠️ Confirmed bug, `ConfirmUnRevisedItemCommand.HandleAddStatus`:** captures `saveResult`/`isSucess`
  correctly and gates the image-upload/Elastic-index step on it (`:249-251`), but the method's final
  `return Result.Success()` (`:260`) is unconditional — unlike its sibling `HandleUpdateStatus`
  (`:336-348`, correctly `return isSucess ? Success : Failure`) and `HandleDeleteStatus` (`:154-155`,
  same correct pattern). A failed save in the "Add" path is reported as success.
  **Source:** `ConfirmUnRevisedItemCommand.cs:249-260`.
- **⚠️ Confirmed bug (5th instance of the save-before-upload pattern), `EditMenuItemCommand`:** saves
  changes (`:197`) before uploading the actual image bytes (`:201-210`) — same
  save-then-orphaned-record-on-upload-failure shape as `_conflicts.md` #54/#57/#75.
  **Source:** `EditMenuItemCommand.cs:197-210`.
- **⚠️ Confirmed bug, `EditMenuItemPriceCommand`:** the not-found branch returns
  `CQRSResponse { Success = true, ErrorMessage = "Not Found" }` — `Success` is `true` on a failure to
  find the price row, same contradictory shape as `_conflicts.md` #56/#60.
  **Source:** `EditMenuItemPriceCommand.cs:55-58`.

## Folded entities: activation history and the image gallery

Two children added upstream are documented here rather than in notes of their own, because neither
carries a rule an operator can act on independently of `MenuItem` (registered as
`covered-by:MenuItem` in `_entity-classes.tsv`).

### `MenuItemActivationHistory` — one row per activation change, with the stock behind it

`Shared/TalabatkLogic/TalabatkModels/MenuItemActivationHistory.cs`, mapped by
`Shared/TalabatkData/Mapping/MenuItemActivationHistoryMap.cs`, table added by migration
`20260901120000_AddMenuItemActivationHistory`.

- **Append-only.** Private constructor, private setters, one `Create` factory (`:73`), and no
  mutator. `StockQuantityAtChange` (`:47`) is a **snapshot**, so a later sync dropping the quantity
  to zero must not disturb an event that happened while it was five.
- **Who and through what, as two separate columns.** `ActorType` (`:54`,
  `MenuItemActivationActorType`) answers *who* — `System`, `AdminUser`, `RestaurantUser`, or the ERP;
  `Source` (`:56`, `MenuItemActivationSource`) answers *through what mechanism*. The entity's own
  reasoning is that `System` alone tells an operator nothing about where to look, and that an
  activation is rarely a human action — the ERP stock sync, the nightly Hangfire job and the
  order-rejection flow all close and re-open items on their own.
- **Deliberately not `EntityChangeHistory`.** The generic change log records one row per changed
  property as strings, so it cannot express "status and quantity as one event"; it tracks no
  quantity; its actor is a user name plus an `IsAdmin` bool with no way to name the ERP or a job;
  and its read query hides every `IsAdmin` row from merchants — which is every system-driven row,
  precisely the ones this table exists to show them. The generic log keeps writing unchanged
  alongside this one.
- **Written through a pre-event, on purpose.** `MenuItemActivationChangedEvent`
  (`Shared/TalabatkLogic/DomainEvents/MenuItemEvents/MenuItemActivationChangedEvent.cs:21`) is a
  `PreEvent`, published before `base.SaveChangesAsync()`, so its handler adds rows without saving and
  they are inserted by that same save — the activation and its history row commit or roll back
  together. The stock figures travel *on* the event rather than being re-read by the handler, which
  runs once per save and would otherwise stamp the final value of the whole save onto every item in
  the nightly job's batches.
- **`RestaurantId` is denormalised** from `MenuCategory.RestaurantId` (`:34`) because item→restaurant
  is a two-hop nullable join.

### `MenuItemImage` — an ordered gallery over the existing `ImageBank`

`Shared/TalabatkLogic/TalabatkModels/MenuItemImage.cs`, mapped by
`Shared/TalabatkData/Mapping/MenuItemImageMap.cs`.

- A **join over `ImageBank`**, not a second image store: the file still lives in the same Items
  folder, is written by the same `IUploadImage`, gets the same `_low` companion, and is addressed by
  the same URL shape. Only "an item may have more than one" is new.
- **The primary image stays on `TA_MenuItem.ImageId`.** Every existing read path — customer item
  detail, the mart grid, Elasticsearch indexing, the Excel export, AdminUi — keeps reading that
  column untouched, which is what makes the table additive rather than a migration of the
  single-image model. The primary is *also* carried as a gallery row so the ordered list is
  complete; `MenuItem.AdoptPrimaryImageIntoGallery` brings older items into that shape.
- Ordered by `SortOrder` (`:32`), resettable via `SetSortOrder` (`:79`); two `Instance` factories
  (`:53`, `:69`) cover the id-only and the loaded-`ImageBank` cases.

### Reading it back — and a confirmed authorization gap

`AdminUi/Controllers/MenuItemActivationTrackingController.cs` exposes `GET api/…/current` (`:39`)
and `GET api/…/history` (`:77`). Both are **unguarded beyond bare authentication** and both trust a
caller-supplied `restaurantId` — see `_conflicts.md` **#653**.

## Key Fields
| Field | Meaning |
|-------|---------|
| `Available` | Temporarily hidden (vs. `Active` — permanently off) |
| `NotAvailableFrom` / `NotAvailableTo` | The suspension window (Rules 1-2) |
| `CurrentStockQuantity` / `OutOfStock` | Stock-driven availability (Rule 3), primarily relevant to Mart items |
| `MenuCategoryId` | Menu grouping |

## Dependencies & Integrations
| Depends on / integrates | Side/Context | Via | Notes |
|--------------------------|---------------|-----|-------|
| [[Restaurant.technical\|Restaurant]] | Backend-Domain | Owning restaurant/store | |
| [[CartItem\|CartItem]] | Backend-Domain | Snapshotted at add-to-cart | |
| `OrderDetails` | Backend-Domain (not documented) | Rejection tracking drives Rule 2 | |

> ⚠️ **NOTE — Duplicated stock-update logic**
> `UpdateStockQuantity` and `MaintainStock` (`MenuItem.cs:774-817`) implement the identical
> zero-crossing availability toggle independently. A future change to one (e.g. a new threshold
> instead of exactly zero) is very likely to be applied to only one of the two call sites.

## Open Questions
- [x] ~~Which of `UpdateStockQuantity` / `MaintainStock` is the "live" one~~ — answered by the
  upstream refactor: both are live, and both run the same body via `ApplyStockQuantity`. See Rule 3.
- [ ] Which `MenuItemActivationSource` values are actually reached in production, and whether any
  activation path still leaves `Unknown` behind, is not traced in this pass.
- [ ] Full menu/catalog management (creation, pricing, categories, options) is a Restaurant Portal
  concern, out of scope here.

## Related
- Business view: [[MenuItem.business|MenuItem]]
- [[Restaurant.technical|Restaurant]]
