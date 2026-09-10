---
id: 8orders/customer-ordering/order-and-fulfilment/order-externaldelivery
note_type: single
rule_count: 6
context: Customer Ordering
feature: Order & Fulfilment
group: Order.ExternalDelivery
covers: [ExternalCustomer, ExternalCustomerAdress, ExternalDeliveryRequests]
sources:
  - path: Shared/TalabatkApplication/Commands/ExternalDeliveryRequests/CreateExternalDeliveryRequestCommand.cs
    sha1: 28086fae6938
  - path: Shared/TalabatkApplication/Commands/MakeOutGoingDeliveryCommand/MakeOutGoingDeliveryCommand.cs
    sha1: 65b56faed089
  - path: Shared/TalabatkLogic/TalabatkModels/Order.Partial.cs
    sha1: 0ee58f302d71
last_updated: 2026-08-23
tags: [customer-ordering, order-fulfilment, transactional, technical, backend-domain]
---
# Order — External Delivery Extension (`Order.Partial.cs`)

> Confirms a gap flagged (but never verified) by an earlier, unpersisted research pass: `Order.Partial.cs`
> is a **separate physical file** extending the `Order` partial class with a whole parallel
> order-creation path that [[Order.technical|Order.technical.md]] does not cover (that note only
> documents the cart-checkout-created path via `CreateOrderFromCartCommand`). This file closes that
> gap rather than re-documenting `Order.technical.md` from scratch.

## What this path is
A **third order-creation path**, alongside cart-checkout (`CreateOrderFromCartCommand`) and reorder —
for merchants who ask the platform to fulfil delivery for an order that originated **outside** the
app entirely (no customer cart, no checkout). Ties directly to
[[Delivery-Requests-and-Suppliers|ExternalDeliveryRequests]] (already documented) and
`OrderDetails.CreateOutGoingDeliveryOrderDetail` (see `OrderDetails.technical.md`'s construction-path
list).

## Business Rules

### Rule 1: External orders skip straight past the approval gate
- **Plain language:** A normal cart-checkout order goes through a pending/auto-approve gate (already
  documented as duplicated twice — `Order.technical.md`'s conflict callout,
  `_system/_conflicts.md` #8). An external delivery order does not go through either of those gates —
  it's created with `StatusId = Pending` and then **immediately** confirmed in the same factory call.
- **Source:** `CreateExternalDeliveryOrder(...)` (`Order.Partial.cs:39-93`) — sets
  `StatusId = (int)OrderStatus.Pending` at construction (`:73`), then unconditionally calls
  `order.ConfirmOrder(dateTime)` (`:89`) before returning. This is a **third** independent code path
  deciding an order's initial approval state, on top of the two already flagged as duplicated with
  each other — worth folding into that same conflict entry's scope rather than treating as unrelated.

### Rule 2: External delivery fee becomes a cash payment, only if positive
- **Source:** `AddExternalDeliveryOrderPayment()` (`:12-27`) — no-ops if `!IsExternalDeliveryOrder` or
  if `DeliveryFees <= 0`; otherwise calls `AddCashPayment(DeliveryFees)`.

### Rule 3: Rejection cancels any still-new delivery requests and records history
- **Source:** `RejectExternalDeliveryOrder(createdBy, nowDate, comment, actionId)` (`:114-134`) —
  no-ops if not an external order; sets `StatusId = Rejected`, records status history (attributing
  `"Merchant"` if no actor name given, `:121`), optionally records an action-comment, and cancels
  every `OrderDelivery` still in `New` status for this order.

### Rule 4: Creation timeline attribution defaults to "Merchant"
- **Source:** `AddExternalDeliveryOrderCreationTimeline(createdBy, nowDate)` (`:28-37`) — same
  `createdBy` fallback pattern as Rule 3.

### Rule 5: Application layer — `CreateExternalDeliveryRequestCommand.GetOutGoingRestaurantData` has an unguarded null
- **⚠️ Confirmed bug:** `selectedRestaurantData` is explicitly set to `null` when
  `selectedRestaurantId == 0` (`:213`, a deliberate ternary), and the two name fields correctly
  fall back with `outGoingRestaruantData?...` (`:234-237`) — but `RestaurantLocation` is assigned
  directly from `selectedRestaurantData.Location` (`:238`) with no null-check or fallback. Any call
  with `selectedRestaurantId == 0` throws `NullReferenceException` at that line instead of using the
  same `outGoingRestaruantData` fallback its sibling fields use.
- **Source:** `CreateExternalDeliveryRequestCommand.cs:213-238`.

### Rule 6: A separate, admin/CS-initiated "outgoing delivery" command has the same bug as Rule 5, plus two more
- **Plain language:** `MakeOutGoingDeliveryCommand` is a **different, fourth order-creation path** —
  not the merchant-originated `CreateExternalDeliveryOrder` this file otherwise documents, and not
  cart-checkout or reorder either. It builds an order via the domain factory
  `Order.MakeOutGoingDeliveryOrder(...)` from an existing customer + optionally a specific restaurant.
  Its own `GetOutGoingRestaurantData` helper (confusingly, the exact same method name as the one
  documented in Rule 5) shares that method's unguarded-null bug, and adds two more of its own.
- **⚠️ Confirmed bugs:**
  1. Same shape as Rule 5/#82: `selectedRestaurantData` is `null` when `selectedRestaurantId == 0`, and
     when it isn't, `RestatruantNameAr`, `RestatruantNameEn`, and the `location` local all dereference
     it directly with no guard.
  2. **New gap not present in Rule 5:** `outGoingRestaruantData` (a fallback/default restaurant looked
     up separately, filtered to `restaurant.OutGoingDelivery == true` with menu items) is dereferenced
     completely unconditionally — `.MenuItemId`/`.PriceId` are read regardless of which branch was
     taken. If no restaurant is configured with `OutGoingDelivery = true` and menu items, **every** call
     to this command throws, even ones that pass an explicit `selectedRestaurantId`.
  3. **New gap:** the two lookup queries handle EF Core's global query filters inconsistently — the
     fallback `outGoingRestaruantData` query explicitly calls `.IgnoreQueryFilters()`, but the
     `selectedRestaurantData` query (the one used when a specific restaurant *is* explicitly chosen)
     does not. A soft-deleted or otherwise filtered-out restaurant ID crashes this command instead of
     being found, unlike the fallback path which deliberately looks past those same filters.
- **Source:** `MakeOutGoingDeliveryCommand.cs:142-218` (`GetOutGoingRestaurantData`).

## Folded entities — the 2 satellites documented here

The merchant's own customer book: when a restaurant sends 8Orders a delivery job for one of *its* walk-in
or phone customers, that person is an `ExternalCustomer`, not a `Customer`.

| Entity | What it is | Rules |
|---|---|---|
| `ExternalCustomer` | A merchant's own customer, scoped to that restaurant | Six guards across three methods, and they are substantive: `Instance` requires a mobile number **and at least one address** (`Shared/TalabatkLogic/TalabatkModels/ExternalCustomer.cs:47`, `:52`); `AddNewAdress` refuses a duplicate — "Adress is Already exist" (`:85`); `Update` requires a name, a mobile number and at least one address (`:105`, `:108`, `:111`). Requiring an address at construction is unusual in this codebase and correct here: an external delivery job with no destination is not a job. `RestaurantId` is the tenancy key, and it is what `_idor-instances.md` instances 4 and 10 bypass — the external-customer read endpoints resolve by id without checking it belongs to the calling merchant, so a merchant can read another merchant's customer names, phones and addresses |
| `ExternalCustomerAdress` | One address of such a customer, tied to a delivery zone area | `Instance` requires a description and a positive `deliveryZoneAreaId` (`Shared/TalabatkLogic/TalabatkModels/ExternalCustomerAdress.cs:31`, `:36`) — and then **silently drops the `deliveryZoneId` it was given**, leaving that column zero on every row (🟡 `_conflicts.md` #635). There are no other methods, so an address is immutable once created: correcting one means adding another. Note the misspelt class name, `Adress`, which every query must reproduce |

## Related
- [[Order.technical|Order]] — the main technical note; this file extends rather than duplicates it
- [[Delivery-Requests-and-Suppliers|ExternalDeliveryRequests]]
- [[OrderDetails.technical|OrderDetails]] — `CreateOutGoingDeliveryOrderDetail`, the matching line-item construction path

## Open Questions
- [ ] Whether skipping both known approval-gate implementations (Rule 1) is a deliberate design
  choice for merchant-originated orders (trusted source, no need to gate) or an overlooked
  inconsistency — not confirmed against the team's intent.
- [ ] Which controller/command actually calls `CreateExternalDeliveryOrder` — not traced in this pass
  (likely in `TalabatkRestaurants`, given `ExternalDeliveryRequests`' merchant-facing nature).
