---
id: 8orders/identity-and-access/customer-identity/customer-technical
note_type: technical
context: Identity & Access
feature: Customer Identity
entity: Customer
entity_type: legacy-poco-root
rule_count: 15
covers: [CustomerActionsHistory, CustomerAds, CustomerCard, CustomerDeliveryInstruction, CustomerItemNotificationRequest, CustomerItemOrderStats, CustomerNotification, CustomerNotificationCustomersData, CustomerNotificationNewVersion, CustomerSavedTipsConfiguration, CustomerMultiSearchKeyword, CustomerTag, CustomerTipsConfig, UnRegesteredCustomers]
sources:
  - path: AdminUi/Controllers/CustomerController/CustomerController.cs
    sha1: 54a6cd2065b5
  - path: Shared/TalabatkApplication/Commands/DeleteCustomerCommand/DeleteCustomerCommand.cs
    sha1: 28d7576044f7
  - path: Shared/TalabatkApplication/Commands/EditCustomerTagsCommand/EditCustomerTagsCommand.cs
    sha1: 9245888cb497
  - path: Shared/TalabatkApplication/Commands/MergeGuestCartIntoCustomerCommand/MergeGuestCartIntoCustomerCommand.cs
    sha1: 08634d0387d9
  - path: Shared/TalabatkApplication/Commands/RemoveCustomerDevicesIdsCommand/RemoveCustomerDevicesIdsCommand.cs
    sha1: 5d9a12cee359
  - path: Shared/TalabatkApplication/Commands/RemoveDeliveryManDevicesQuery/RemoveDeliveryManDevicesQuery.cs
    sha1: 44d834e5f5eb
  - path: Shared/TalabatkApplication/Commands/RemoveRestaurantDevicesCommand/RemoveRestaurantDevicesIdsCommand.cs
    sha1: 96294f977127
  - path: Shared/TalabatkApplication/Commands/UpdateCustomerAddressFromAdminCommand/UpdateCustomerAddressFromAdminCommand.cs
    sha1: 6cc655d82bc9
  - path: Shared/TalabatkApplication/Commands/UpdateCustomerDataFromAdminCommand/UpdateCustomerDataFromAdminCommand.cs
    sha1: 8367f63c73da
  - path: Shared/TalabatkData/Mapping/CustomerMap.cs
    sha1: 5ec0075f81d7
  - path: Shared/TalabatkLogic/TalabatkModels/Customer.cs
    sha1: 312359030eb8
  - path: Talabatk.IDS/Application/Commands/RegisterCustomerV2Command/RegisterCustomerV2Command.cs
    sha1: f480da554257
  - path: Shared/TalabatkLogic/TalabatkModels/CustomerAds.cs
    sha1: 1e287dc4c2d7
  - path: Shared/TalabatkLogic/TalabatkModels/CustomerDeliveryInstruction.cs
    sha1: 703cef00edd8
  - path: Shared/TalabatkLogic/TalabatkModels/CustomerItemNotificationRequest.cs
    sha1: 5c3ba7e67793
  - path: Shared/TalabatkLogic/TalabatkModels/CustomerItemOrderStats.cs
    sha1: c89497c29351
  - path: Shared/TalabatkLogic/TalabatkModels/CustomerSearchKeyword.cs
    sha1: 315855a0984c
  - path: Shared/TalabatkLogic/TalabatkModels/CustomerNotification.cs
    sha1: 16940ee86722
  - path: Shared/TalabatkLogic/TalabatkModels/CustomerNotificationCustomersData.cs
    sha1: 7b7880c27a17
  - path: Shared/TalabatkLogic/TalabatkModels/CustomerNotificationNewVersion.cs
    sha1: 08927075d691
  - path: Shared/TalabatkLogic/TalabatkModels/CustomerSavedTipsConfiguration.cs
    sha1: 20a060b0f7c6
  - path: Shared/TalabatkLogic/TalabatkModels/CustomerTipsConfig.cs
    sha1: d61bd50b6e43
  - path: Shared/TalabatkLogic/TalabatkModels/UnRegesteredCustomers.cs
    sha1: 1203168f7464
  - path: Shared/TalabatkLogic/TalabatkModels/CustomerActionsHistory.cs
    sha1: 046d0fe1196f
  - path: Shared/TalabatkLogic/TalabatkModels/CustomerCard.cs
    sha1: 17874aefede8
  - path: Shared/TalabatkLogic/TalabatkModels/CustomerTag.cs
    sha1: b4c954000665
last_updated: 2026-08-23
tags: [identity-access, customer, transactional, technical, backend-domain]
---
# Customer — Technical

> **Layer:** Backend-Domain — legacy entity, richer than a typical anemic POCO (private setters +
> behavior methods) but not a full DDD aggregate (no private constructor / static `Create` factory
> returning `Result`; extends ASP.NET Identity's `IdentityUser<int>`).
> **Context:** Identity & Access (per `CONTEXT-MAP.md`: "Identity & Access ... owns the `Customer`,
> `DeliveryMen`, and restaurant-user identity records referenced elsewhere by ID") — but this is one
> of the most cross-context entities in the system: read/written directly by Customer Ordering
> (`TalabatkAPIs`) for cart/order/loyalty flows just as heavily as by Identity & Access itself for
> registration/login.
> **Source Path:** `Shared/TalabatkLogic/TalabatkModels/Customer.cs`   **Last Updated:** 2026-08-03

## Business Rules

### Rule 1: Guest creation is a placeholder identity
- **Plain language:** A Guest row has no phone number — it's keyed by device id, starts unverified,
  and has notifications disabled.
- **Source:** `Customer.cs:238-259` (`Guest(...)` factory) — sets `IsGuest=true`, `Active=false`,
  `NotificationEnable=false`, `ReferenceCode` random.

### Rule 2: Registered creation starts unverified
- **Plain language:** A freshly registered customer starts `Active=false` (pending OTP verification)
  and `IsNewCustomer=true`.
- **Source:** `Customer.cs:189-236` (`Instance(...)` factory).

### Rule 3: One guest row per device (DB-enforced)
- **Plain language:** Two different guest sessions on the same device can't both exist as separate
  rows — but a registered customer legitimately can share a device id with others (e.g. reinstall).
- **Trigger:** Insert/update of `Customer.DeviceId`.
- **Source:** `Shared/TalabatkData/Mapping/CustomerMap.cs:57-60` — filtered unique index
  `HasFilter("[IsGuest] = 1 AND [DeviceId] IS NOT NULL")`. Flipping `IsGuest` to `false` on promotion
  (Rule 4) drops the row out of the filter, freeing the device id for a future guest.

### Rule 4: Guest promotion — same-device registration reuses the row in place
- **Plain language:** When the **same device's** guest registers with a phone number, the guest row
  itself becomes the real account (same primary key, so cart/addresses stay attached) — this is
  distinct from Rule 5.
- **Trigger:** Registration where a guest row exists for `GuestDeviceId`.
- **Source:** `Customer.cs:267-287` (`PromoteFromGuest(...)`), called from
  `Talabatk.IDS/Application/Commands/RegisterCustomerV2Command/RegisterCustomerV2Command.cs:106-137`
  (looked up by `IsGuest && DeviceId == request.GuestDeviceId`, loaded `AsTracking`). Sets
  `IsGuest=false` and activates via `MangeCustomerActivation(active: true)`.
- **Cross-context integration:** this is a second confirmed instance of the "shared
  Application/Data library invoked independently by two hosts against the same DB, no network call"
  pattern already on record in `_system/_conflicts.md` (originally found for another feature) —
  `Talabatk.IDS` mutates a `Shared/TalabatkLogic` entity directly, in-process, not via HTTP.

### Rule 5: Guest-into-existing-account is a separate "replace" merge, not a promotion
- **Plain language:** If a guest instead logs into an account that **already exists** (a different
  customer row), the guest row is **not** promoted — its cart/address/discount are copied onto the
  real row and the guest row is deleted. Full rule detail (guest-replaces policy, address/discount
  carryover, preference carryover) is documented once, on the cart entity, not duplicated here.
- **Source:** `Shared/TalabatkApplication/Commands/MergeGuestCartIntoCustomerCommand/MergeGuestCartIntoCustomerCommand.cs`
  (whole file) — see
  [[CustomerCart.technical|CustomerCart.technical]]
  Rules 6-8 for the merge policy itself.
- **Customer-specific detail not on the cart note:** the guest's `UnavailableItemsPreference` is
  carried over too, but **only if non-default** — every guest starts at `SuggestAlternatives` (never
  set explicitly by `Guest(...)`), so an unconditional copy would silently reset a returning
  customer's own preference on every guest login. `MergeGuestCartIntoCustomerCommand.cs:401-445`
  (`CarryOverUnavailableItemsPreferenceAsync`).

### Rule 6: One-default-address invariant is enforced on Customer, not on the address itself
- **Plain language:** Adding a new default address automatically un-defaults whichever address was
  previously the default — a customer can never end up with two defaults from this path.
- **Source:** `Customer.cs:289-329` (`AddNewAddress(...)`) — iterates
  `TA_CustomerAddresses.Where(a => a.IsDefault)` and calls `SetIsDefault(false)` on each before adding
  the new one. The in-code comment explicitly ties this to preventing "the same symptom the guest
  cart merge produced" (see Rule 5) — i.e. this guard and the merge's own default-clearing
  (`CustomerCart.technical` Rule 8) are two independent enforcement points for the same invariant,
  not one shared mechanism.
- **Caveat:** requires the caller to have loaded `TA_CustomerAddresses` tracked (`AsTracking` +
  `Include`) for the clear to reach the database — noted in-line at `Customer.cs:300-306`.

### Rule 7: Soft delete frees the phone number for reuse
- **Plain language:** Deleting an account doesn't remove the row — it's flagged deleted and its
  phone number/username get a numeric suffix appended so the original value is free for a future
  registration.
- **Source:** `Customer.cs:608-617` (`DeleteAccount(index)`) — sets `Deleted=true`,
  `UserName`/`NormalizedUserName`/`PhoneNumber` all become `"{phone}_Delete{index}"`.
- **⚠️ Possible bug — suffix count uses substring match, not exact equality:** the caller
  (`Shared/TalabatkApplication/Commands/DeleteCustomerCommand/DeleteCustomerCommand.cs:38`) computes
  the suffix index as `Customer.Where(x => x.PhoneNumber.Contains(customerValue.PhoneNumber) &&
  x.IsShortCutApp == customerValue.IsShortCutApp).Count() + 1` — `.Contains` is a **substring** test,
  so a customer with phone `"123"` would also match a stored phone `"1234567"`, inflating the count
  (or, less likely, colliding on the suffix if two unrelated numbers happen to be substrings of each
  other). Flagged for the team, not silently changed to exact-match.

### Rule 8: Two activation paths diverge on `IsNewCustomer` — resolved, appears intentional
- **Plain language:** There are two different ways a customer gets marked "active", and only one of
  them also clears the "is this a brand-new customer" flag.
- **Source:** `Customer.cs:405-409` (`MangeCustomerActivation(active)` — sets `Active` +
  `PhoneNumberConfirmed` to the same bool, used by `PromoteFromGuest`, Rule 4) vs.
  `Customer.cs:503-509` (`ActivateUser()` — sets `Active=true`, `PhoneNumberConfirmed=true`, **and**
  `IsNewCustomer=false`).
- **Resolved (2026-08-03):** `MangeCustomerActivation` is also the method behind **Admin's manual
  activate/deactivate toggle** — `AdminUi/Controllers/CustomerController/CustomerController.cs:216-232`
  (`MangeCustomerActivation` route) dispatches `MangeCustomerActivationFromAdminCommand`, which reaches
  this same entity method. This reframes the divergence as sensible rather than an oversight: an admin
  toggling a customer's active status for unrelated reasons (support action, reversing a block, etc.)
  shouldn't retroactively mark a long-standing customer as "new" — only completing the OTP/registration
  flow for the first time (`ActivateUser`) should. Not yet confirmed whether `PromoteFromGuest`'s use
  of the same method was intentionally reasoned this way or is incidental reuse of a convenient
  existing method — the Admin-toggle use case is the one clearly justifying the split.

### Rule 9: `UpdateInfo`'s guard checks the wrong value
- **Plain language:** the update-profile-info method's only validation checks the customer's
  **current, already-stored** name instead of the **new name being submitted** — so it can never
  actually reject a blank incoming name (the check is checking data that's about to be overwritten
  anyway), while a customer who already has a name can have it overwritten with an empty string
  without being stopped.
- **Source:** `Customer.cs:540-555` (`UpdateInfo(firstName, male, dateOfBirth)`) —
  `if (string.IsNullOrEmpty(FirstName)) return Result.Failure(...)` reads the field `FirstName`
  (existing value) rather than the parameter `firstName` (incoming value) before assigning
  `this.FirstName = firstName`.
- This matches the same shape as a previously-confirmed bug elsewhere in the repo
  (`StoreTypesDescription.AddDescription` checking the existing field instead of the incoming
  parameter) — worth a team conversation about whether this is a recurring copy-paste mistake.
- **Contrast:** the sibling method `UpdateCustomerData` (`Customer.cs:557-580`) has no such bug —
  it guards `email` correctly (`if (!string.IsNullOrEmpty(email))`) before conditionally assigning it.

### Rule 10: Loyalty point math
- **Plain language:** Points earned on an order are proportional to money spent, using a
  points-per-currency-unit ratio; expiring and redeeming points are separate ledger entries.
- **Formula:** `totalEarningPoints = earningMoney != 0 ? (orderTotal * earningPoints / earningMoney) : 0`
- **Source:** `Customer.cs:331-357` (`AddEarnedLoyaltyPoints`), `:359-368`
  (`AddExpirationLoyaltyPoints`), `:370-390` (`AddRedeemedLoyaltyPoints`) — all three delegate to
  `LoyaltyPoints`'s own factory methods (`AddEarnedPointsInstance`/`ExpiryPointsInstance`/
  `RedeemedPointsInstance`), which can themselves fail (`Result<T>`). **`LoyaltyPoints` itself is not
  yet documented** (see Open Questions / `_entity-index.md`'s "not yet in the registry" list).

### Rule 11: Payment card add replaces same-PAN card rather than duplicating
- **Plain language:** Adding a card that shares a masked PAN with one already saved silently drops
  the old one first — a customer never ends up with two cards showing the same masked number.
- **Source:** `Customer.cs:146-176` (`AddNewCard(...)`) — finds and removes any existing
  `Cards.Any(x => x.MaskedPan == maskedPan)` before adding the new `CustomerCard.Instance(...)`.

### Rule 12: Tag update is a full replace-with-diff
- **Plain language:** Updating a customer's tags adds any new ones and removes any that are no
  longer in the submitted list — it's a full sync, not an additive-only operation.
- **Source:** `Customer.cs:583-605` (`UpdateTags(tagIds)`).
- **⚠️ Confirmed bug, Application layer — duplicated logic that introduces a new bug:**
  `EditCustomerTagsCommand.cs` does **not** call this existing `Customer.UpdateTags` domain method —
  it reimplements the identical add/remove diff logic inline (`:41-69`), but wraps each branch in an
  **async lambda passed to `List<T>.ForEach`** (`request.TagIds.ForEach(async tag => {...})` and the
  same for `currentTagIds`). `ForEach` takes a plain `Action<T>`, so the async lambdas run
  fire-and-forget — `context.CustomerActionsHistory.AddAsync(...)` calls inside them are not awaited
  before the method proceeds to `context.SaveChangesAsync()` on the same `DbContext`. This risks
  losing audit-history rows for a race the domain method's synchronous version can't have, and (EF
  Core `DbContext` not being safe for concurrent operations) can throw
  `InvalidOperationException: A second operation was started on this context before a previous
  operation completed` if a customer has multiple tag changes in one call.
  **Source:** `EditCustomerTagsCommand.cs:41-69`.

### Rule 13: Device-token "Add" methods actually overwrite, not append
- **Plain language:** Despite the names, `AddAndroidDevice`/`AddIOSDevice`/`SaveSingleAndroidDevice`
  all just overwrite the single stored device-token string — there is no multi-device list here,
  just guarded (non-empty, trimmed) single-value assignment.
- **Source:** `Customer.cs:446-473`. Worth noting for anyone assuming "Add" means additive.

### Rule 14: Application layer — "remove one device" wipes every device, repo-wide across 3 actor types
- **⚠️ Confirmed bug, high severity:** `RemoveCustomerDevicesIdsCommand`'s device-removal filter is
  `list.Where(x => !list.Contains(command.DeviceId))` — the predicate tests whether the **whole
  list** contains the target id (a constant, the same for every `x`), not whether the current item
  `x` equals it. So if the device id being removed is actually present (the normal case — that's the
  whole point of calling this), the condition evaluates `false` for every item and the **entire
  device list is wiped**, not just the targeted one; if the id isn't present at all, the filter is a
  harmless no-op. Hits on essentially every real invocation of the intended use case.
- **Same exact bug, 2 sibling commands in other bounded contexts:** `RemoveDeliveryManDevicesQuery`
  (Delivery, Android only) and `RemoveRestaurantDevicesIdsCommand` (Restaurant Portal, Android + iOS)
  — same copy-pasted `list.Where(x => !list.Contains(target))` shape.
- **Source:** `RemoveCustomerDevicesIdsCommand.cs:41-50`, `RemoveDeliveryManDevicesQuery.cs:37-39`,
  `RemoveRestaurantDevicesIdsCommand.cs:49-65`.

### Rule 15: Application layer — 2 more confirmed bugs (address update, admin data update)
- **`UpdateCustomerAddressFromAdminCommand`:** dereferences `customerAddress` (`FirstOrDefaultAsync`)
  with no null-check, and its `SaveChangesAsync()` result is captured but never checked before
  unconditionally returning success. **Source:** `UpdateCustomerAddressFromAdminCommand.cs:40-66`.
- **`UpdateCustomerDataFromAdminCommand`:** ignores `DateTime.TryParseExact`'s `bool` return for
  `DateOfBirth` — a malformed date silently saves as `DateTime.MinValue`. **Source:**
  `UpdateCustomerDataFromAdminCommand.cs:64`.

## Key Fields
| Field | Meaning | Constraints |
|-------|---------|-------------|
| `Id` (→ `CustomerId` column) | Primary key | `TA_Customer` table |
| `PhoneNumber` (→ `MobileNumber`) | Identity for registered customers | max 20 chars; suffixed on delete (Rule 7) |
| `DeviceId` | Single device identifier, guest or registered | max 450 chars; filtered unique index — one guest row per device (Rule 3) |
| `IsGuest` | Guest vs. registered | default `false` |
| `Active` | OTP-verified | see Rule 8 for the two paths that set it |
| `IsBlocked` / `BlockReason` | Blocking, independent of `Deleted` | — |
| `Deleted` | Soft-delete flag | see Rule 7 |
| `ReferenceId` → `TA_CustomerReference` | Self-referencing FK — "referred by" customer | nullable |
| `CityId` → `CurrentCity` | Customer's city | FK to `City` (own note, this same batch) |
| `UnavailableItemsPreference` | What to do if an ordered item is unavailable | enum, default `SuggestAlternatives` — see Rule 5 |
| `OnlinePaymentRefundPreference` | Refund routing preference | enum, default `Bank` |

## Status / State
No single status enum — an implicit lifecycle from independent booleans:
```
IsGuest=true (device-keyed, Active=false)
   │  same-device registers (Rule 4)          logs into existing account (Rule 5)
   ▼                                           ▼
IsGuest=false, Active=true (via                (guest row deleted, its data merged
MangeCustomerActivation)                        onto the pre-existing real row)
   │
   │  ActivateUser() elsewhere also clears IsNewCustomer (Rule 8 — divergence noted)
   ▼
Active=true, IsNewCustomer=false  ── IsBlocked=true/false (independent) ── Deleted=true (terminal, Rule 7)
```

## Dependencies & Integrations
| Depends on / integrates | Side/Context | Via | Notes |
|--------------------------|---------------|-----|-------|
| `CustomerCart` | Backend-Domain, Customer Ordering | 1:1 FK (`Cart`) | Guest-replaces merge, see [[CustomerCart.technical\|CustomerCart]] |
| `CustomerAddresses` | Backend-Domain | 1:many, default invariant (Rule 6) | |
| `LoyaltyPoints` | Backend-Domain | 1:many (`Points`) | Not yet documented — flagged dependency |
| `CustomerCard` | Backend-Domain | 1:many (`Cards`) | Dedup-by-PAN (Rule 11) |
| `CustomerTag` | Backend-Domain | 1:many | Full replace-with-diff (Rule 12) |
| `Order` (`TA_Orders`) | Backend-Domain, Customer Ordering | 1:many | High fan-out — Order is itself a partially-documented hub |
| `City` | Backend-Domain (master data) | FK (`CurrentCity`) | Own note, this same shared-layer batch |
| `Talabatk.IDS` registration/OTP commands | API host, Identity & Access | In-process call into this Shared entity (no HTTP) | Rules 4-5 |

## Cross-Context Integrations
| Direction | Other context | Via | Mechanism | Risk if changed |
|-----------|-----------------|-----|-----------|------------------|
| inbound | Identity & Access (`Talabatk.IDS`) | Registration/OTP promotes or creates this row directly | In-process Shared-layer call, not HTTP | High — `Talabatk.IDS` and `TalabatkAPIs` must agree on `Customer`'s shape/rules since both mutate it directly |
| inbound | Customer Ordering (`TalabatkAPIs`) | Cart, checkout, loyalty, address, device-token flows | In-process Shared-layer call | High — same reasoning |

## Change Surface
| Signal | Value | Notes |
|--------|-------|-------|
| Direct dependents (Ring 1) | 6+ | CustomerCart, CustomerAddresses, LoyaltyPoints, CustomerCard, CustomerTag, Order |
| Sides touched | 4/5 | Backend-Domain, Backend-Application, Backend-Data, API host (both `TalabatkAPIs` and `Talabatk.IDS`) — Frontend touch not yet confirmed |
| Cross-context integrations | 2 | Identity & Access (registration/promotion), Customer Ordering (everything else) |
| Domain events involved | 1 confirmed | `NewRegistrationEvent` (`Customer.cs:398-403`) |
| Hub? | yes | One of the most heavily cross-referenced entities in the system |

## Folded entities — the 14 satellites documented here

`_entity-classes.tsv` assigns these to this note (`covered-by:Customer`), so this is where they are
enumerated. All live in `Shared/TalabatkLogic/TalabatkModels/`. "Factory" names the creation method,
because in this codebase whether a factory returns `Result` is what decides if the type has invariants
at all.

| Entity | Type | Factory | Key fields | What it is for |
|---|---|---|---|---|
| `CustomerCard` | child | — | saved-card reference fields | A customer's stored payment card reference for repeat checkout |
| `CustomerAds` | root | `Instance` (**`Result` guards**) | 17 fields: `ArabicTitle`/`EnglishTitle`, `Active`, `StartDate`/`EndDate`, `StartHour`/`EndHour`, `Type` (`CustomerAdsType`), `RestaurantId`, `EntityId`, `CityId`, `IsMart`, Arabic/English image ids | A customer-targeted in-app ad or message: bilingual, city-scoped, with both a date range **and** an hour-of-day window, and separate images per language (`SetArabicImage` / `SetEnglishImage`). Filed here by name, but its behaviour belongs to [[Customer Ordering/Marketing & Content/_knowledge-graph\|Marketing & Content]] — read that feature for how it is scheduled and delivered |
| `CustomerAddresses` | child | — | address, coordinates, city | Delivery addresses; has its own note — [[CustomerAddresses\|CustomerAddresses]] |
| `CustomerActionsHistory` | child | — | customer, action, timestamp | Audit trail of what the customer did — the basis for support investigations |
| `CustomerTag` | child | — | customer, tag | Free-form labelling of a customer (segmentation, ops flags) |
| `CustomerDeliveryInstruction` | child | `Instance` (infallible) | `CustomerId`, `DeliveryInstructionId`, `CreatedAt`, `ModifiedAt` | Links a customer to a standing delivery instruction ("leave at door"); `UpdateModifiedAt` is its only behaviour |
| `CustomerItemNotificationRequest` | root | `Instance` (**`Result` guards**) | `CustomerId`, `MenuItemId`, `RequestDate` | "Tell me when this item is back" — the request that `SendNotificationJob` later fans out (`_integrations.md` row 22) |
| `CustomerItemOrderStats` | child | `Instance` (infallible) | `CustomerId`, `ItemId`, `OrderCount`, `LastOrderDate` | Per-customer per-item ordering counters, maintained by `UpdateOrderStats`; feeds recommendations and re-order prompts |
| `CustomerMultiSearchKeyword` | root | `Instance` | `CustomerId`, `Keyword`, `CreatedDate` | Search history. **Note the file/class mismatch:** the class is `CustomerMultiSearchKeyword` but the file is `CustomerSearchKeyword.cs` |
| `CustomerSavedTipsConfiguration` | root | `Instance` | `CustomerId`, `SaveTips`, `LastSavedTipsAmount` | Whether to remember the customer's tip, and the last amount |
| `CustomerTipsConfig` | root | `Create` | `CustomerId`, `SaveLastTipsValue`, `TipsAmount` | **A duplicate of the row above** — same concept, own table, and unreachable. Registered as a confirmed finding; do not extend it |
| `CustomerNotification` | child | `Instance` (**`Result` guards**) | 16 fields incl. `NotificationType`, `EntityId`, `Title`/`Body`, `MarkAsRead`, `IsSent`, `SendToIOS`, `SendToAndroid` | The **original** notification row: one record per customer, single-language, with `MarkNotificationAsRead`, `SetUnRegisteredCustomer`, `Sent` |
| `CustomerNotificationNewVersion` | root | `Create` | 27 fields incl. `ArabicBody`/`EnglishBody`, `ArabicTitle`/`EnglishTitle`, `ToBeSendDate`, `Processing`, `Sent` | The **replacement**: one master notification, bilingual, with an explicit `Processing` → `Sent` progression |
| `CustomerNotificationCustomersData` | child | `CreateForRegisteredCustomer` / `CreateForUnregisteredCustomer` | `CustomerNotificationId`, `CustomerId?`, `UnRegisteredCustomerId?`, `IsCustomerRegistered`, `MarkAsRead`, `IsSent` | The per-recipient row of the new model. Its `CustomerNotification` navigation points at **`CustomerNotificationNewVersion`**, not at `CustomerNotification` — the two generations are separate graphs sharing a name |
| `UnRegesteredCustomers` | root | `Create` | `DeviceId`, `DeviceToken`, `CityId?`, `CreatedAt` | The guest/provisional customer (ADR 0001). Keyed by **device**, not by phone — which is why a guest is identified before any account exists, and why the merge at registration matters |

### Two notification generations coexist

Worth stating explicitly, because a CR that "changes notifications" has to pick a side:

- **Old model** — `CustomerNotification`, one row per customer per notification, single language,
  read/sent flags on the same row.
- **New model** — `CustomerNotificationNewVersion` (the master, bilingual, with a `Processing` state)
  plus `CustomerNotificationCustomersData` (one row per recipient, handling **registered and
  unregistered** customers via two nullable ids and two distinct factories).

Both are live types with mappings. The new model is the only one that can address a guest, which is the
functional reason it exists. The old model's `SetUnRegisteredCustomer` method suggests guest support was
retrofitted there first.

### The tips duplicate

`CustomerSavedTipsConfiguration` and `CustomerTipsConfig` model the same thing — "remember this
customer's tip and how much" — in two tables with two different factory conventions (`Instance` vs.
`Create`). The duplicate is recorded as confirmed and unreachable in
`_inbox/pathA-A-models-batch03.md` and carried in the conflict register. Any tips work should target
`CustomerSavedTipsConfiguration` and treat the other as dead.

## Related
- Business view: [[Customer.business|Customer]]
- [[CustomerCart.technical|CustomerCart]] — guest-replaces merge (Rules 5-8 there)
- [[CartItem|CartItem]]

## Open Questions
- [x] ~~`LoyaltyPoints` itself is not yet documented~~ — **Resolved**, see [[LoyaltyPoints|LoyaltyPoints]].
- [x] ~~Whether `MangeCustomerActivation` intentionally leaves `IsNewCustomer` untouched~~ —
  **Resolved 2026-08-03**, see Rule 8 above (Admin's manual activation toggle also uses this method).
- [x] ~~Whether `AdminUi` has a customer-management screen~~ — **Confirmed yes**,
  `AdminUi/Controllers/CustomerController/CustomerController.cs` (~30 routes: activation, blocking,
  COD-ban management via [[BlockedUsersFromCOD\|BlockedUsersFromCOD]],
  tags, address management, wallet transactions) — not read handler-by-handler beyond confirming
  `MangeCustomerActivation`'s connection above.
- [ ] The `DeleteCustomerCommand` substring-match suffix-count issue (Rule 7) — not confirmed whether
  it has caused a real collision in production, only that the logic is fragile.
