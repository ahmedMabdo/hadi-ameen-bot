---
id: 8orders/identity-and-access/customer-identity/customeraddress-technical
note_type: technical
rule_count: 8
context: Identity & Access
feature: Customer Identity
sources:
  - path: AdminUi/Controllers/CustomerController/CustomerController.cs
    sha1: 54a6cd2065b5
  - path: Shared/TalabatkApplication/Commands/AddNewAdressCommand/AddNewAddressCommand.cs
    sha1: d84e3b6defaf
  - path: Shared/TalabatkApplication/Commands/AddNewCartItemCommand/AddNewCartItemCommand.cs
    sha1: c3cb69f77a84
  - path: Shared/TalabatkApplication/Commands/AddNewCartItemCommand/ValidateItemOptionsCommand.cs
    sha1: c72c2ed43edc
  - path: Shared/TalabatkApplication/Commands/CalculateItemsReplacementTotalCommand/CalculateItemsReplacementTotalCommand.cs
    sha1: 094bc548ce3c
  - path: Shared/TalabatkApplication/Commands/ChangeAddressByCustomer/ChangeAddressByCustomerCommand.cs
    sha1: 9312a13d0710
  - path: Shared/TalabatkApplication/Commands/ChangeCustomerCartAddressCommand/ChangeCustomerCartAddressCommand.cs
    sha1: d5809b9874a0
  - path: Shared/TalabatkApplication/Commands/CreateOrderFromCartCommand/CreateOrderFromCartCommand.cs
    sha1: 26e07e2fc0b4
  - path: Shared/TalabatkApplication/Commands/DeleteCustomerAddressCommand/DeleteCustomerAddressCommand.cs
    sha1: d415010a9143
  - path: Shared/TalabatkApplication/Commands/DeleteRestaurantFromOrderCommand/DeleteRestaurantFromOrderCommand.cs
    sha1: 2464ca954b43
  - path: Shared/TalabatkApplication/Commands/EditCartItemCommand/EditCartItemCommand.cs
    sha1: 05f3af04a1f0
  - path: Shared/TalabatkApplication/Commands/MakeOrderCommand/MakeOrderCommand.cs
    sha1: 8632380200e6
  - path: Shared/TalabatkApplication/Commands/MergeGuestCartIntoCustomerCommand/MergeGuestCartIntoCustomerCommand.cs
    sha1: 08634d0387d9
  - path: Shared/TalabatkApplication/Commands/PurgeAbandonedGuestCustomersCommand/PurgeAbandonedGuestCustomersCommand.cs
    sha1: ab7070313d56
  - path: Shared/TalabatkApplication/Commands/ReorderCommand/ReorderCommand.cs
    sha1: eb5d0a8a1988
  - path: Shared/TalabatkApplication/Commands/UpdateCustomerAddressCommand/UpdateCustomerAddressCommand.cs
    sha1: 2df348aae4aa
  - path: Shared/TalabatkApplication/Commands/UpdateCustomerAddressFromAdminCommand/UpdateCustomerAddressFromAdminCommand.cs
    sha1: 6cc655d82bc9
  - path: Shared/TalabatkApplication/Commands/UpdateOrderCommand/UpdateOrderCommand.cs
    sha1: 1208d02f5f9e
  - path: Shared/TalabatkApplication/DTO/CustomerDTOS/CustomerAdressDto.cs
    sha1: 4f68685f7def
  - path: Shared/TalabatkApplication/ITalabatkContext.cs
    sha1: 5d8fb628ef5c
  - path: Shared/TalabatkApplication/OrderBuilder/OrderBuilder.cs
    sha1: fcdc8279337d
  - path: Shared/TalabatkApplication/Queries/GetAvalibleCustomerAddressQuery/GetAvalibleCustomerAddressQuery.cs
    sha1: 4bb1a2f1470d
  - path: Shared/TalabatkApplication/Queries/ValidateCustomerAddressQuery/ValidateOrderAddressChangeQuery.cs
    sha1: bc3770566db9
  - path: Shared/TalabatkApplication/Services/GuestCustomerResolver/ResolveGuestCustomerService.cs
    sha1: 03427d4e316d
  - path: Shared/TalabatkData/Mapping/CustomerAddressesMap.cs
    sha1: 254a427fd3f9
  - path: Shared/TalabatkLogic/TalabatkModels/Customer.cs
    sha1: 312359030eb8
  - path: Shared/TalabatkLogic/TalabatkModels/CustomerAddresses.cs
    sha1: 039d81d75d83
  - path: TalabatkAPIs/Controllers/CustomerUser/CustomerUserController.cs
    sha1: fc15a3e7f335
last_updated: 2026-08-23
tags: [identity-access, customer, child, technical, backend-domain]
---
# CustomerAddress — Technical

> **Layer:** Backend-Domain — legacy entity, not a full DDD aggregate: some behavior methods return
> `Result` (`SetIsDeleted`, `SetIsDefault`, `UpdateAddressDetails`, `UpateAddress`) but there's no
> private constructor/factory guard and a plain public constructor also exists.
> **Context:** Identity & Access — a child record of [[Customer.technical|Customer]]
> (`Shared/TalabatkApplication/ITalabatkContext.cs` exposes it as `CustomerAddresses` alongside
> `Customer`), per `CONTEXT-MAP.md`'s "Identity & Access ... owns the `Customer`, `DeliveryMen`, and
> ... identity records referenced elsewhere by ID" — but, like `Customer` itself, it is read/written
> just as heavily by Customer Ordering (`TalabatkAPIs`) for cart/checkout/order flows, and by Admin
> (`AdminUi`) for staff-assisted address management.
> **Source Path:** `Shared/TalabatkLogic/TalabatkModels/CustomerAddresses.cs`   **EF Mapping:**
> `Shared/TalabatkData/Mapping/CustomerAddressesMap.cs`   **Last Updated:** 2026-08-21

## Business Rules

### Rule 1: `AreaId` is nullable because a pin can fall outside every configured delivery zone
- **Plain language:** An address's area/zone is worked out by checking which configured zone's border
  contains the pin. If none does, the address is still saved, just with no zone attached.
- **Source:** `CustomerAddresses.cs:13` (`public int? AreaId`); `CustomerAddressesMap.cs:20`
  (`builder.Property(t => t.AreaId).HasColumnName("DistrictId")` — the DB column is literally named
  `DistrictId`, a naming mismatch worth flagging on its own) and `:29`
  (`builder.HasOne(t => t.TA_Area).WithMany().HasForeignKey(x => x.AreaId)` — an optional FK, matching
  the nullable property). The concrete reason is spelled out in guest-address creation:
  `ResolveGuestCustomerService.cs:339-360` (`ResolveAreaFromLocationAsync`) does a point-in-polygon
  lookup (`context.Area.Where(a => a.AreaBorder != null && a.AreaBorder.Intersects(location))`) and
  returns `(null, null)` when nothing matches; the in-line comment at `:362-364` states outright:
  "the pin is outside every configured area (which is allowed at creation time — `AreaId` is nullable
  on the address)".
- **Downstream effect:** `GetAvalibleCustomerAddressQuery.cs:30` filters
  `x.CustomerId == query.CustomerId && x.AreaId.HasValue` — an address with no resolved area is
  correctly excluded from the "available addresses" list this query serves (consumed by
  `AdminUi/Controllers/CustomerController/CustomerController.cs`), the one place in the codebase that
  handles a null `AreaId` defensively rather than crashing on it (contrast Rules 3-4 below).
- **Contrast — authenticated customers can't normally reach this state:** `AddNewAddressCommand.cs:72-79`
  rejects the whole save with `"this address is not covered"` if the pin isn't inside any area with
  matching `IsShortCutApp`, so a null `AreaId` is in practice a guest-creation-only outcome — except
  for the residual bug in Rule 2.

### Rule 2: `AddNewAddressCommand` dereferences its own nullable, client-supplied `AreaId` unguarded
- **Plain language:** The authenticated "add address" endpoint takes an optional area id straight from
  the client and unwraps it without checking it was actually sent.
- **Source:** `AddNewAddressCommand.cs:21` (`public int? AreaId { get; init; }`, populated directly
  from the request body at `TalabatkAPIs/Controllers/CustomerUser/CustomerUserController.cs:216`,
  `newAdress.AreaId`) — then `AddNewAddressCommand.cs:89` calls
  `customer.AddNewAddress(command.AreaId.Value, ...)` with no `.HasValue` guard. The area-coverage
  check just above it (`:72-79`) validates the **pin's location** against `Area.AreaBorder`, not the
  client-supplied `AreaId` value itself, so a request with a covered lat/long but an omitted/null
  `AreaId` throws `InvalidOperationException` instead of failing cleanly. Not previously logged in
  `_conflicts.md` — traced directly in this pass.

### Rule 3: Unguarded null dereference of `customerAddress` across multiple order-write paths (confirmed, established finding)
- **Plain language:** Several handlers load the customer's address only when an address id was
  supplied, then read a field off it unconditionally a few lines later — an order with no address
  (e.g. pickup, or a client that omits the field) crashes those handlers instead of failing cleanly.
- **Source (already verified, see `_conflicts.md` for full detail):**
  - `#352` — `MakeOrderCommand.cs:219-226` (`customerAddress` initialized to `null`, assigned only
    `if (command.UserAdressId.HasValue)`, then `supportedAreaIds.Contains(customerAddress.AreaId.Value)`
    dereferences both the object and its nullable `AreaId` unguarded) and
    `UpdateOrderCommand.cs:582-589` (same shape, `x.AreaId == customerAddress.AreaId`).
  - `#61` — `CalculateItemsReplacementTotalCommand.cs:660-669` and its copy-pasted twin
    `DeleteRestaurantFromOrderCommand.cs:148-158` (`customerAddress.AreaId` dereferenced when
    `order.UserAddressId` was null).
  - `#101` — `ReorderCommand.cs:98,109` (`customerAddressId.Value` / `customerData.CurrentAreaId.Value`
    dereferenced without `.HasValue`).
  - `#116` — `UpdateCustomerAddressFromAdminCommand.cs:40-66` (`customerAddress` from
    `FirstOrDefaultAsync` dereferenced with no null check).
  - `#269` — `OrderBuilder.cs:77` dereferences `customerAddress.TA_Area.AreaReferenceName` and
    `.AddressDescription` unconditionally, **before** the defensive `customerAddress == null` checks
    later in the same method (`:79-80`, `:92-94`) ever run — making that later defense dead code.
- I did not re-verify these line-by-line beyond what's already recorded in `_conflicts.md`; they are
  cited here, not re-investigated, because they are this entity's most consequential defects.

### Rule 4: `CustomerAddresses` rows are routinely looked up by id alone, with no ownership check (confirmed IDOR cluster)
- **Plain language:** Several handlers fetch an address (or an order tied to one) using only the id the
  caller supplied, never checking it belongs to the caller. Any authenticated user can act on someone
  else's address by guessing/incrementing the id.
- **Source (already verified, see `_conflicts.md` `#227`, `#366`, `#365`, `#350` for full detail):**
  - `#227` — `DeleteCustomerAddressCommand.cs:27`
    (`ctx.CustomerAddresses.Where(x => x.UserAddressId == command.AddressId)`, no `CustomerId` filter),
    reachable via `TalabatkAPIs/Controllers/CustomerUser/CustomerUserController.cs:282-286` which — unlike every sibling address action in
    the same controller — carries no `[Authorize(Roles = "Customer")]`, only the class-level
    "any authenticated JWT" check.
  - `#366` — names this as the shared root cause: 7 Application-layer files fetch `CustomerAddresses`
    by id alone (representative instances: `ValidateOrderAddressChangeQuery.cs:38`,
    `MakeOrderCommand.cs:221`, `UpdateOrderCommand.cs:584`); two of the seven files have the correct
    ownership-scoped pattern immediately adjacent, so the fix template already exists in-repo.
  - `#365` — `ValidateOrderAddressChangeQuery.cs:38,66`, the read-side twin of the
    `ChangeAddressByCustomerCommand` defect below.
  - `#350` (item 1 and item 3 of its five-handler cluster) — `ChangeAddressByCustomerCommand.cs:28-30,74`
    loads the target order by `OrderId` alone (no customer id on the command at all) and can redirect
    another customer's in-flight order to an address the caller controls;
    `DeleteCustomerAddressCommand.cs:12,27` is the same handler as `#227` above.
- Not re-investigated; cited from the established findings.

### Rule 5: `UpdateCustomerAddressCommand` has the same unscoped lookup, and it is exercised with the caller's own id (self-traced, extends the pattern behind Rule 4)
- **Plain language:** The "edit my address" handler also fetches the target address by id alone, with
  no check that it belongs to the caller — and then overwrites that row's owning-customer field with
  the caller's own id. Aimed at another customer's address id, an authenticated caller can silently
  re-home that address onto their own account.
- **Source:** `UpdateCustomerAddressCommand.cs:47`
  (`ctx.CustomerAddresses.AsTracking().Where(x => x.UserAddressId == command.UserAddressId).FirstOrDefaultAsync()`
  — no `CustomerId` predicate), then `:63-67` calls
  `customeraddress.UpateAddress(command.UserAddressId, command.CustomerId, ...)`, which per
  `CustomerAddresses.cs:83-102` reassigns both `UserAddressId` and `CustomerId` on the loaded row. The
  endpoint confirms `command.CustomerId` is always the caller's own session id, not attacker-controlled:
  `TalabatkAPIs/Controllers/CustomerUser/CustomerUserController.cs:254-257` (`UpdateAddress` action) sets
  `CustomerId = sessionInfo.CusomerId`. Net effect: supplying any other customer's `UserAddressId` in
  the request body reassigns that address's ownership to the caller. The pre-existing entity-level
  note `../Customer/CustomerAddresses.md` had flagged `UpateAddress`'s reassignment capability as an
  open question ("not confirmed whether any caller actually changes these values") — this traces the
  concrete call site that does.

### Rule 6: A newly added address is always created as the default, regardless of the caller's `IsDefault` flag (self-traced)
- **Plain language:** Adding a new address only clears the customer's previous default if the request
  said the new one should be default — but the new address itself is always saved as the default
  either way, so requesting a non-default address can leave two rows both flagged default.
- **Source:** `Customer.cs:307-313` (`AddNewAddress`) only clears existing defaults
  `if (isDefault)`, but the address it constructs a few lines later is unconditional:
  `Customer.cs:319` passes the named argument `isDefault: true` as a literal, not the method's
  `isDefault` parameter, into `new CustomerAddresses(...)` (constructor signature at
  `CustomerAddresses.cs:35-44`, parameter `isDefault`). This runs directly against the one-default
  invariant [[Customer.technical|Customer]] documents as Rule 6 on that note — the guard
  clears the old default only sometimes, but the new row is always the default.

### Rule 7: Guest-to-existing-account migration re-homes the address as a new row, not a rename (confirmed via code, cross-referencing Customer Rule 5)
- **Plain language:** When a guest logs into an account that already exists, their saved address isn't
  relabeled onto the real account — a brand-new address row is created with the same content, and the
  guest's original row is deleted. The address keeps its data but gets a new id.
- **Source:** `MergeGuestCartIntoCustomerCommand.cs:296-371` — loads the guest's addresses
  (`:296-298`), clears the real customer's existing default first if the guest had one (`:309-328`,
  explicitly to preserve the one-default invariant), then for each guest address with a non-null
  location calls `CustomerAddresses.Instance(...)` to build a fresh row owned by
  `request.RealCustomerId` (`:342-353`) and finally `context.CustomerAddresses.RemoveRange(guestAddresses)`
  (`:370`) deletes the originals. A guest address with a null `location` is skipped from the copy
  entirely (`:332-340`) but still removed. See [[Customer.technical|Customer]] Rule 5 for
  the overall guest-merge policy this is one part of.

### Rule 8: Guest address creation has no rate limit despite an ADR requiring one (confirmed, established finding)
- **Plain language:** Anyone, unauthenticated, can create an unlimited number of guest customers (each
  with its own default `CustomerAddresses` row) just by varying a client-supplied device id — the
  design doc that approved this flow explicitly called for a rate limit, and it was never built.
- **Source:** `_conflicts.md` `#341` — `ResolveGuestCustomerService.cs:96,103-148` creates a guest keyed
  only on a client-supplied `guestDeviceId` with no per-device/per-IP count check; the only bound is the
  24h abandoned-guest purge (`PurgeAbandonedGuestCustomersCommand.cs:30`). Required by
  `TalabatkAPIs/docs/adr/0001-guest-mode-provisional-customer.md`. Not re-investigated here.

## Key Fields
| Field | Meaning | Constraints |
|-------|---------|-------------|
| `UserAddressId` | Primary key | `CustomerAddressesMap.cs:14` |
| `CustomerId` | Owning customer | Nullable on the entity (`CustomerAddresses.cs:12`); not confirmed why a row could exist with no customer |
| `AreaId` (DB column `DistrictId`) | Geographic zone, resolves `TA_Area` | Nullable — Rule 1; DB column name diverges from the C#/FK property name (`CustomerAddressesMap.cs:20`) |
| `location` (`Geometry`) | Map pin | NetTopologySuite point, built via `GeomeryFactoryCustom` |
| `LocationName` | Display label ("Home", "Work", or the resolved area name for guests) | Max length 500 (`CustomerAddressesMap.cs:16`) |
| `AddressDescription` | Free-text address detail | |
| `IsDefault` | Default-address flag | One-default invariant enforced on `Customer`, not here — see Rule 6 for where that guard has a gap |
| `IsDelete` | Soft-delete flag | Nullable `bool?` |
| `BuildingName` / `BuildingNumber` / `ApartmentFLoorNumber` / `ApartmentNumber` | Address detail fields | Plain strings, no validation in the entity |
| `CreationDate` | Row creation timestamp | Nullable |
| `TA_Area` | Navigation to the resolved `Area` | Null whenever `AreaId` is null |

## Dependencies & Integrations
| Depends on / integrates | Side/Context | Via | Notes |
|--------------------------|---------------|-----|-------|
| [[Customer.technical\|Customer]] | Backend-Domain, Identity & Access | 1:many, `TA_CustomerAddresses` collection | Owns the one-default invariant (`Customer.cs:289-329`, Rule 6); Rule 6 above shows a gap in how that guard is applied |
| [[Area-and-Country\|Area]] | Backend-Domain, Admin (master data) | Optional FK `AreaId`→`DistrictId` column | Point-in-polygon resolution, Rule 1 |
| [[Order.technical\|Order]] | Backend-Application, Customer Ordering | Read via `UserAdressId`/`UserAddressId` at create/update/reorder/remove-restaurant/change-address time | Heaviest consumer; Rules 3-4's bug and IDOR cluster live here (`MakeOrderCommand.cs`, `UpdateOrderCommand.cs`, `ReorderCommand.cs`, `CalculateItemsReplacementTotalCommand.cs`, `DeleteRestaurantFromOrderCommand.cs`, `ChangeAddressByCustomerCommand.cs`, `ValidateOrderAddressChangeQuery.cs`, `CreateOrderFromCartCommand.cs:1087`) |
| [[CustomerCart.technical\|CustomerCart]] | Backend-Application, Customer Ordering | Read to resolve area/delivery-fee for the selected address | `AddNewCartItemCommand.cs:54`, `EditCartItemCommand.cs:109`, `ChangeCustomerCartAddressCommand.cs`, `ValidateItemOptionsCommand.cs:55` |
| Guest-mode flow | Backend-Application, Customer Ordering (Guest Mode) | Created on guest provisioning; re-homed on guest→real merge | `ResolveGuestCustomerService.cs:160-180` (creation), `:296-371` in `MergeGuestCartIntoCustomerCommand.cs` (merge, Rule 7) |
| AdminUi | Backend-Application, Admin | Staff-assisted address create/update; available-address listing | `AddCustomerNewAddressForAdminCommand.cs:54,71`; `UpdateCustomerAddressFromAdminCommand.cs:40-66`; `GetAvalibleCustomerAddressQuery.cs:30` |
| `CustomerAdressDto` / `AvalibleCustomerAddressDto` (AutoMapper) | Backend-Application | DTO projection for API responses | `Shared/TalabatkApplication/DTO/CustomerDTOS/CustomerAdressDto.cs:52-83` maps `TA_Area.AreaReferenceName` / `TA_Area.TA_City.TA_CityDescription` — not verified in this pass whether AutoMapper's null-propagation covers a null `TA_Area` (i.e. Rule 1's uncovered-address case) safely |

## Change Surface
| Signal | Value | Notes |
|--------|-------|-------|
| Direct dependents (Ring 1) | 5+ | Customer, Order, CustomerCart, Guest-mode flow, AdminUi |
| Sides touched | 3 confirmed | Backend-Domain (entity), Backend-Application (Commands/Queries), API host (`TalabatkAPIs`, `AdminUi`) — Frontend touched indirectly (see Open Questions, `#378`) |
| Cross-context integrations | 2 confirmed | Identity & Access (owner) ↔ Customer Ordering (heaviest consumer, order/cart write paths); ↔ Admin (staff-assisted management) |
| Domain events involved | 0 confirmed | Plain CRUD via MediatR commands/queries; no event dispatch traced on this entity |
| Hub? | yes | Highest confirmed-defect density of any entity in this graph so far: 2 distinct bug families (unguarded null-deref, unscoped-lookup IDOR) recur across 8+ separate handlers |

## Related
- Business view: [[CustomerAddress.business|CustomerAddress]]
- [[Customer.technical|Customer]] — owning record; one-default invariant (Rule 6 there, Rule 6 here)
- [[CustomerAddresses|CustomerAddresses (entity detail)]] — an earlier, narrower note on
  the same underlying class, written before this pair existed; documents the `UpateAddress`/
  `SetAsDefault`/`SetIsDefault` duplication and naming oddities at the code level
- [[Area-and-Country|Area]] — geographic zone an address resolves to (Rule 1)
- [[Order.technical|Order]] — heaviest consumer;
  Rules 3-4's confirmed bugs and IDORs
- [[CustomerCart.technical|CustomerCart]] — guest
  merge policy (Rule 7)

## Open Questions
- [ ] Whether AutoMapper's null-propagation actually protects `CustomerAdressDto`'s
  `src.TA_Area.AreaReferenceName` / `src.TA_Area.TA_City...` chains when `TA_Area` is null (Rule 1's
  uncovered-address case) — not traced in this pass, flagged rather than guessed.
  `Shared/TalabatkApplication/DTO/CustomerDTOS/CustomerAdressDto.cs:61-64`.
- [ ] `#378` (frontend, `edit-customer.component.ts:198,319`) — AdminUi's customer-edit form declares a
  required `area` form control with no template field to populate it, and the address save calls never
  check form validity at all; not re-investigated here, but it means AdminUi's address-editing UI for
  this entity is guided only by "was a pin placed," not by form validation. Logged against `Customer`,
  relevant here too since it concerns address editing specifically.
- [ ] Why `CustomerId` is nullable on the entity (`CustomerAddresses.cs:12`) when every creation path
  traced in this pass (`AddNewAddressCommand`, `ResolveGuestCustomerService`, admin creation, guest
  merge) always supplies one — no code path producing a genuinely ownerless address was found, but the
  full write-surface wasn't exhaustively checked.
- [ ] Whether `Rule 6`'s always-default bug is masked in practice by every real caller always sending
  `IsDefault: true` for a customer's first address (the common case) — not confirmed either way.
