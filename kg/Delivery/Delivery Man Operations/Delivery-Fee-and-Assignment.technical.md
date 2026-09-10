---
id: 8orders/delivery/delivery-man-operations/delivery-fee-and-assignment-technical
note_type: technical
context: Delivery
feature: Delivery Man Operations
sources:
  - path: Shared/TalabatkApplication/Commands/AcceptAutoAssignRequestCommand/AcceptAutoAssignRequestCommand.cs
    sha1: d87f0060da64
  - path: Shared/TalabatkApplication/Commands/AssignDeliveryManToDeliveryRequestCommand/AssignDeliveryManToDeliveryRequestCommand.cs
    sha1: c164400fb4a6
  - path: Shared/TalabatkApplication/Commands/AssignOrderDeliveryToDeliveryManFromMapCommand/AssignOrderDeliveryToDeliveryManFromMapCommand.cs
    sha1: 272f6783bf1f
  - path: Shared/TalabatkApplication/Commands/AssignOrdertoDeliveryManCommand/AssignOrdertoDeliveryManCommand.cs
    sha1: 90ce68a43a2d
  - path: Shared/TalabatkApplication/Commands/AssigneOrderToDeliveryManCommand/AssignOrderToDeliveryManByHimselfCommand.cs
    sha1: 67da09da960e
  - path: Shared/TalabatkApplication/Commands/CreateOrderFromCartCommand/CreateOrderFromCartCommand.cs
    sha1: 26e07e2fc0b4
  - path: Shared/TalabatkApplication/Commands/RejectAutoAssignRequestCommand/RejectAutoAssignRequestCommand.cs
    sha1: d023d9880262
  - path: Shared/TalabatkApplication/ForceAssignDeliverymenService.cs
    sha1: c558c63dd0a2
  - path: Shared/TalabatkApplication/Helper/DeliveryFeesCalculator/DeliveryManPricingCalculatorAdapter.cs
    sha1: 6c845eb647aa
  - path: Shared/TalabatkApplication/Helper/DeliveryFeesCalculator/IOrderDeliveryFeesCalculator.cs
    sha1: 23f1b1882aef
  - path: Shared/TalabatkApplication/Helper/DeliveryFeesCalculator/OrderDeleveryFeesCalculator.cs
    sha1: 79d4864f0833
  - path: Shared/TalabatkApplication/Helper/DeliveryManRatingCalculator.cs
    sha1: e67c20c5b909
  - path: Shared/TalabatkApplication/OrderBuilder/CalculateCustomerDeliveryFeesForCurrentAddress.cs
    sha1: 37cf1b81170c
  - path: Shared/TalabatkApplication/Queries/GetAllDeliveryZoneAreaQuery/GetAllDeliveryZoneAreaQuery.cs
    sha1: 546a7cb29ca3
  - path: Shared/TalabatkApplication/Queries/GetCustomerCartSummaryQuery/GetCustomerCartSummaryQuery.cs
    sha1: f6bb6edfa97a
  - path: Shared/TalabatkLogic/TalabatkModels/AutoAssignRequest.cs
    sha1: 9126e401d976
  - path: Shared/TalabatkLogic/TalabatkModels/DeliveryManPrice.cs
    sha1: 4c7143355396
  - path: Shared/TalabatkLogic/TalabatkModels/DeliveryZoneArea.cs
    sha1: 1a5481a9679b
  - path: Shared/TalabatkLogic/TalabatkModels/Order.cs
    sha1: a8504688c441
  - path: Shared/TalabatkLogic/TalabatkModels/OrderDelivery.cs
    sha1: f86d116d0efc
  - path: Talabatk.IDS/Application/Commands/AssigneOrderToDeliveryManTasksDistributionCommand/AssigneOrderToDeliveryManTasksDistributionCommand.cs
    sha1: 37f8b92a0bf9
  - path: Talabatk.IDS/Helper/HangFire/AutoAssignJob.cs
    sha1: 116ead595090
  - path: Talabatk.IDS/Helper/HangFire/Automaions.cs
    sha1: 47b7403410c4
last_updated: 2026-08-23
tags: [flow, technical]
---
# Delivery Fee Calculation & Driver Assignment — Technical

> **Bridges:** [[City.technical|City]] (Rule 1: the six driver-scoring weights sum to
> 1 — treated as this flow's input set, not re-derived), [[Driver-Cash-Cycle.technical|Driver Cash and
> Settlement Cycle]] (the cash-limit formula and Redis `ExceededCashLimit` gate — cited by step number
> here, not restated), [[Delivery-Assignment-Strategies|Delivery Assignment Strategies]]
> (`DeliverymenProfitCalculator.Calculate`'s best-zone-profit pick, tip-splitting, and
> `ExtraRestaurantDeliveryFees`-only-if-one-delivery rule — not restated), [[DeliveryZone|DeliveryZone]]
> (the `AutoAssign` flag this flow branches on), [[DeliveryMen.technical|DeliveryMen]],
> [[OrderDelivery.technical|OrderDelivery]].

## Trigger
No single trigger — two chained sub-flows, each with multiple entry points:
1. **Fee calculation**: (a) customer opens/refreshes the cart summary; (b) customer places the order
   (server recomputes, does not trust the client).
2. **Driver assignment**: (a) Hangfire `AutoAssignJob.AssignOrders`, polling continuously, for zones
   with `AutoAssign = true`; (b) Hangfire `Automaions.DistrubiteOrdersToActiveDeliveryMen`, for zones
   with `AutoAssign = false`; (c) a driver tapping an order on the map (self-assign); (d) a driver
   plain self-assigning by id; (e) an admin manually assigning from the back office; (f) a driver
   accepting/rejecting a system-generated offer.

## Step-by-step

### A. Customer-facing fee — computed at cart time, re-computed at order time
1. `GetCustomerCartSummaryQuery.Handle` calls `CalculateCustomerDeliveryFeesForCurrentAddress.CalculateCustomerDeliveryFees`
   (`Shared/TalabatkApplication/Queries/GetCustomerCartSummaryQuery/GetCustomerCartSummaryQuery.cs:48`).
2. The base fee is the **maximum** `RestaurantZoneArea.CustomerDeliveryFees` across every restaurant in
   the cart whose `RestaurantZoneId` covers the customer's current `AreaId`
   (`CalculateCustomerDeliveryFeesForCurrentAddress.cs:26-35`) — not a sum, not an average, the
   highest single zone's price wins when a multi-restaurant cart spans zones. If no restaurant-zone
   row matches the customer's area at all, the fee silently comes out as `0` (`:43-45`, `Count > 0 ? Max
   : 0`) — there is no "no delivery available here" failure, just a free delivery.
3. A flat multi-restaurant surcharge is added: `(restaurantCount - 1) × Configuration.ExtraRestaurantDeliveryFees`
   (`:47-48`) — one global config value city-wide, not zone- or distance-scaled.
4. These two numbers (`DeliveryFees`, `ExtraDeliveryFees`) are folded into `CustomerCartTotal`
   alongside item subtotal and service fees (`GetCustomerCartSummaryQuery.cs:60-68`) — this is what the
   customer sees before confirming.
5. At actual order placement, `CreateOrderFromCartCommand` calls the **same** helper again
   server-side (`CreateOrderFromCartCommand.cs:328`) rather than trusting whatever the client last
   displayed, and passes both figures into `Order.CreateOrderFromCustomerCart(...)`
   (`:451-452`) — this is what lands on the persisted `Order.DeliveryFees` /
   `Order.ExtraRestaurantDeliveryFees`.

### B. Driver's payout — a second, independent fee table
6. The customer's fee (step 2) and the driver's payout are **not the same number and do not come from
   the same table.** The driver-facing figure — `ZoneProfit` — is the **maximum**
   `DeliveryZoneArea.DeliverymanDeliveryFees` among the zones covering the restaurant(s) on this
   delivery and the customer's area (`OrderDeleveryFeesCalculator.CalculateDeliveryManProfit`,
   `Shared/TalabatkApplication/Helper/DeliveryFeesCalculator/OrderDeleveryFeesCalculator.cs:23-47`) —
   `DeliveryZoneArea` (keyed by `DeliveryZoneId`, off the **restaurant's** zone), not `RestaurantZoneArea`
   (keyed by `RestaurantZoneId`, used in step 2 for the customer). Two independently admin-configured
   tables, reconciled nowhere in code — see Failure modes.
   `DeliveryManProfitBreakdown.TotalProfit = ZoneProfit + ExtraRestaurantDeliveryFees + Tips`
   (`IOrderDeliveryFeesCalculator.cs:7-12`); the "pick the best-paying zone among candidates,
   `ExtraRestaurantDeliveryFees` only if exactly one delivery, tips split evenly across concurrent
   deliveries" refinements on top of this are `DeliverymenProfitCalculator.Calculate`'s job, already
   documented in [[Delivery-Assignment-Strategies|Delivery Assignment Strategies]] — not restated.
7. `DeliveryZoneArea` also carries a `CustomerDeliveryFees` field (`Shared/TalabatkLogic/TalabatkModels/DeliveryZoneArea.cs:11`),
   read at one call site (`AssignOrderDeliveryToDeliveryManFromMapCommand.cs:157`, the
   "outgoing-delivery, not flagged" branch) — but **neither** `DeliveryZoneArea.Instance` (`:27-39`) nor
   `.Update` (`:17-25`) ever sets it, and a DTO query hardcodes it to `0`
   (`GetAllDeliveryZoneAreaQuery.cs:29`). See Failure modes.
8. External-delivery orders skip zone math and split by config instead:
   `Configuration.ExternalDeliveryProfitPrecentage` (company share), remainder to the driver —
   `DeliverymenProfitCalculator.GetInitialCompanyAndDeliveryManProfitForOrderDelivery`, already
   documented in [[Delivery-Assignment-Strategies|Delivery Assignment Strategies]].

### C. The driver's rating-tier bonus — two divergent formulas
9. A city defines a table of driver-rating bands (`DeliveryManPrice`: `CityId`, `FromRate`, `ToRate`,
   `Percentage`, `RateCode` — `Shared/TalabatkLogic/TalabatkModels/DeliveryManPrice.cs:12-17`; creation
   validates `FromRate ≤ ToRate` and non-negative rates, `:21-63`). At assignment time the driver's
   `CurrentRating` is matched into this table and the row's `Percentage` becomes a bonus/penalty on top
   of `ZoneProfit`.
10. **Two different implementations exist for the same concept, and they compute different numbers
    for the same driver/city/rating:**
    - `DeliveryManPricingCalculatorAdapter.CalculatePricingAsync` (the `IDeliveryManPricingCalculator`
      injected into the domain layer) returns `matchingPrice.Percentage / 100m`
      (`Shared/TalabatkApplication/Helper/DeliveryFeesCalculator/DeliveryManPricingCalculatorAdapter.cs:69`)
      — a flat percentage, independent of how high the rating actually is within its band.
    - `OrderDeleveryFeesCalculator.CalculateDeliveryManPricing` (the `IOrderDeliveryFeesCalculator`
      used directly by the admin-assign handler) returns `currentRating * matchingPrice.Percentage / 100m`
      (`OrderDeleveryFeesCalculator.cs:90`) — scaled by the rating's own magnitude, so a driver with
      `CurrentRating = 4.5` gets 4.5× the adjustment a `CurrentRating = 1.0` driver would get from the
      identical table row.
    - Which formula a driver's payout actually uses depends entirely on **which command performed the
      assignment** (see step 17 vs. steps 13/15) — not on any business rule about the driver or order.
      Not confirmed as a live discrepancy in production values (the two could coincidentally agree at
      `CurrentRating ≈ 1`), but the formulas are provably different in general and no test or comment
      in either file acknowledges the other's existence.
11. `CurrentRating` itself is the output of `DeliveryManRatingCalculator.CalculateRatingForPeriod`
    (`Shared/TalabatkApplication/Helper/DeliveryManRatingCalculator.cs:123-132`): a weighted sum of six
    `(result + ConstantOfNonZeroRate) × weight` terms — customer rating, working hours, delivered
    orders, acceptance rate, restaurant arrival time, customer arrival time — multiplied by a rate
    multiplier and capped at that multiplier (`:131-132`). The six weights are the exact fields City
    Rule 1 requires to sum to 1, documented in [[City.technical|City]] — not re-derived
    here; this is simply where they get consumed.

### D. Assignment — auto-assign zones
12. `DeliveryZone.AutoAssign` (toggled via `UpdateDeliveryZone`, raising `DeliveryZoneModeChangedEvent`
    only on change — documented in [[DeliveryZone|DeliveryZone]]) is the fork point. For `AutoAssign =
    true` zones, Hangfire `AutoAssignJob.AssignOrders` (`Talabatk.IDS/Helper/HangFire/AutoAssignJob.cs:31-91`)
    selects `Initialize`-status, `Approved`, non-`Rejected` `OrderDelivery` rows in such zones once
    `now > ResponseDate + CookingTime − RemainingTimeToPickupInMinutes` (`:50-63,75-76`), and calls
    `ForceAssignDeliverymenService.AssignOrderToDeliveryman`.
13. That method builds a per-zone, per-delivery-method (Motorcycle/Bicycle/Walking) candidate queue
    (`ForceAssignDeliverymenService.cs:199-216`) and round-robins through it (`:353-405`): each
    candidate is dequeued and re-enqueued with a fresh timestamp score before being tested — the
    *initial* queue score at login is `lastLogin.epoch − CurrentRating` (`:84-93`), so among drivers
    who came online around the same moment a higher rating sorts as if they'd logged in earlier. Each
    candidate is tested by `TryCompleteAutoAssignForDeliverymanAsync` (`:554-730`):
    - Not already rejected this order (`:570-574`).
    - Passes `IOrderDeliveryMethodEligibilityValidator.ValidateDistanceOnlyAsync` (`:576-589`).
    - Flagged `IsInternalDelivery` for a non-external order (`:607-615`).
    - Active, online (Redis last-location timestamp within `OfflineTimeInSeconds`), in the order's
      zone, has no open order, not already mid-assignment-cooldown (`:617-656`).
    - **Cash gate** (cash-only orders only): hard-blocked if Redis `ExceededCashLimit == "True"`
      (`:670-680`); otherwise a non-blocking ~70%-of-limit warning is appended to the offer text
      (`:682-691`, `GetDescription`, `:761-763`) — this is the one enforcement point documented in
      [[Driver-Cash-Cycle.technical|Driver Cash and Settlement Cycle]] step 12; not restated here.
    - First candidate to pass gets an `AutoAssignRequest` (`Pending`) via `OrderDelivery.AutoAssign`
      (`OrderDelivery.cs:373-378`) and a push notification; the loop returns immediately (`:694-720`).
14. External-delivery orders skip the round-robin and instead **rank** every external driver in the
    candidate pool by a composite score: `0.6 × normalized_pickup_distance + 0.4 × (1 −
    normalized_rating)` (`ForceAssignDeliverymenService.cs:29-30, 500-551`), lowest score first, drivers
    with no resolvable last-location sorted last (`:534-537`); each ranked candidate is tried the same
    way as step 13 (`:311-338`).
15. **What happens when nobody accepts / no candidate qualifies:** `SendToManualAssign`
    (`ForceAssignDeliverymenService.cs:768-792`) marks the `OrderDelivery` `Timeout`
    (`OrderDelivery.MarkAsTimeout`, `OrderDelivery.cs:367-371`) and notifies admin via
    `iDSClientHandler.SendNewTimeOutRequets`. This fires when: too many prior offers timed out or were
    rejected (`≥ Configuration.NumberOfDeliverymenBeforeManualAssign`, `:138-163`); the auto-assign
    window has closed (too close to food-ready time, `:165-195`); the candidate queue is empty
    (`:262-283`); or an external order has no external drivers configured/available (`:224-260`). Not
    traced in this pass: what creates the ops-staff `Tasks` row (`TaskTypes.AssignOrdertoDeliveryMan`)
    that a `Timeout`'d delivery presumably becomes, or whether `Timeout` deliveries are ever retried
    automatically.
16. **#432** sits downstream of step 15's manual hand-off: the background job that redistributes
    pending `AssignOrdertoDeliveryMan` ops-staff tasks away from off-shift users and onto on-shift ones
    (`AssigneOrderToDeliveryManTasksDistributionCommand.cs:52-54`) uses the same unsatisfiable
    hour-only overnight-shift comparison as five sibling consumers. A shift crossing midnight (e.g.
    22:00–06:00) never matches any hour, so `operationusers` comes back empty for every overnight run
    (`:52-65`), and a delivery `Timeout`'d overnight sits with no on-shift staff eligible to be handed
    the manual-assignment task until the day shift's condition happens to match again — night staff
    are invisible to this redistribution exactly as they are to the five other consumers #432
    describes. **#430** (overnight delivery-man attendance never recorded, reported as success) is the
    sibling defect on the driver side of the shift system, not directly wired into this
    assignment-eligibility code (the online/active checks here read Redis, populated by a
    location/heartbeat ping — not the `DeliveryMenShifts`/attendance rows #430 concerns); whether
    attendance data feeds any assignment gate elsewhere was not traced in this pass.

### E. Assignment — non-auto-assign zones (manual broadcast)
17. For `AutoAssign = false` zones, Hangfire `Automaions.DistrubiteOrdersToActiveDeliveryMen`
    (`Talabatk.IDS/Helper/HangFire/Automaions.cs:41-100`, gated by a separate feature flag
    `Configuration.AutomaticOrderDistribution`, `:46-50`) finds every online + active driver assigned
    to a non-auto-assign zone with a pending confirmed order (`:52-89`) and pushes a broadcast
    notification to all of them at once — not a targeted single-driver pick. Whichever driver acts
    first (via the self-assign paths below) gets the order. Not traced further: how a race between two
    drivers accepting the same broadcast is resolved (likely by the "already has a delivery man"
    check in step 20, but not confirmed here).

### F. Assignment — driver self-assign from map
18. `AssignDeliveryManToDeliveryRequestCommand` (driver taps an order, submitting own lon/lat) checks:
    driver `Active` (`:73-77`); a hard cash gate — blocked if `RequiredPaymentTOLockExceedCashLimit >
    0`, or balance ≥ 70% of `CashLimit + ExternalDeliveryCashLimit` (`:79-110`) — a DB-direct
    reimplementation of the same limit-percentage idea alongside the ones already catalogued in
    [[Driver-Cash-Cycle.technical|Driver Cash and Settlement Cycle]]'s Failure modes (not restated,
    just noted as one more site); and a concurrent-order cap against
    `Configuration.MaximumDeliveryOrderCount` (`:113-136`).
19. **#389** fires here: the "does this driver already have an order on the way" lookup
    (`AssignDeliveryManToDeliveryRequestCommand.cs:155-172`) has no per-driver filter and projects the
    outer `order` (the one being assigned) instead of the joined `onWayOrder`. Concretely, this means
    `hasOnWayOrders` is `true` almost system-wide (any driver's on-way order anywhere satisfies it),
    which routes nearly every call into
    `Order.ValidateDeliveryManDistanceFromOrder`'s (`Order.cs:817-875`) **"has on-way order"** branch —
    blocked only if `> 15` minutes since the order's response and `> 3 km` from `customerOnWayLocation`
    (which is actually the *new* order's own delivery location, per #389's projection bug, `:845-853`)
    — while the branches actually meant for a driver with no other order (block if within 5 minutes and
    `> 3 km` from the restaurant, or after 5 minutes and `> 5 km`, `:857-872`) essentially never
    execute. The proximity gate this method exists to enforce is not applying as designed for most
    assignments.
20. `Order.AssignDeliveryManToOrderDeliveryRequest` (`Order.cs:613-688`) then runs the full path:
    rejects if the parent delivery (for split orders) is already `OnWay` (`:633-637`); `hasALreadyDeliveryMan`
    / same-driver-twice / delayed-order / cash-limit / distance checks in
    `ValidateAssignOrderDelivery` (`:729-811`, cash check `:792-797` via `CanDeliverymanTakeOrder`,
    `Order.cs:6024-6041`); on success, picks the assignment strategy via
    `DeliveryAssignementStrategyFactory` (documented in
    [[Delivery-Assignment-Strategies|Delivery Assignment Strategies]]) and calls
    `DeliverymenProfitCalculator.Calculate` (step 6/step 10's adapter formula flows in here via the
    `pricingCalculator` parameter, `:675`).

### G. Assignment — driver plain self-assign (no map, no gates)
21. **#390** fires here: `AssignOrderToDeliveryManByHimselfCommand`
    (`Shared/TalabatkApplication/Commands/AssigneOrderToDeliveryManCommand/AssignOrderToDeliveryManByHimselfCommand.cs:34-79`)
    performs **no** `Active` check at all before calling `Order.AssignOrderToDeliveryMan`
    (`:61-63`) — contrast the admin path's `if (deliveryMan is null || !deliveryMan.Active)`
    (`AssignOrdertoDeliveryManCommand.cs:63-64`). A deactivated driver can self-assign through this
    command.
22. `Order.AssignOrderToDeliveryMan` (`Order.cs:3467-3489`) is the thin legacy path: requires
    `StatusId == Confirmed` (`:3471-3474`), runs only the single hard cash check
    `CanDeliverymanTakeOrder` (`:3476-3479`, `:6024-6041` — blocks if cash-only order and balance ≥
    total cash limit or a required payment is locked), then flips status and stamps
    `DeliveryManId`/`AssignDeliveryManDate` (`:3481-3485`). **No fee/profit calculation happens on this
    path at all** — no `DeliverymenProfitCalculator`, no `OrderDelivery` row touched — unlike every
    other assignment route in this note.

### H. Assignment — admin manual assign
23. `AssignOrdertoDeliveryManCommand` (`Shared/TalabatkApplication/Commands/AssignOrdertoDeliveryManCommand/AssignOrdertoDeliveryManCommand.cs:55-90`)
    checks `Active` correctly (`:63-64`, the correct sibling #390 cites), calls the same thin
    `Order.AssignOrderToDeliveryMan` (`:77`), but the **handler itself** — not the domain method —
    does the fee math inline in `HandleOrderDelivery` (`:92-154`): fetches `ZoneProfit`/breakdown via
    `IOrderDeliveryFeesCalculator.CalculateDeliveryManProfit` (`:98`), fetches the rating-tier
    adjustment via `CalculateDeliveryManPricing` — the `currentRating × percentage` formula from step
    10 (`:101`) — applies it only to `ZoneProfit`, not to extras or tips (`:104-110`), then either
    updates the existing `OrderDelivery` (`:119-130`, `OrderDelivery.UpdateAccruals`, `OrderDelivery.cs:239-244`)
    or creates a new one (`:132-152`, `OrderDelivery.Instance`, `OrderDelivery.cs:72-90`) — both branches
    stamp `CompanyProfit = order.DeliveryFees` (the full customer fee, unnetted against the driver's
    cut — see Failure modes).

### I. Accepting or rejecting a system-generated offer
24. `AcceptAutoAssignRequestCommand` (`Shared/TalabatkApplication/Commands/AcceptAutoAssignRequestCommand/AcceptAutoAssignRequestCommand.cs:34-87`)
    validates the offer hasn't expired (`:47-50`) and belongs to this driver (`:52-55`), marks it
    `Accepted` (`AutoAssignRequest.MarkAsAccepted`, `AutoAssignRequest.cs:32-36`), then re-invokes the
    real assignment writer — `AssignOrderDeliveryToDeliveryManFromMapCommand`
    (`AssignOrderDeliveryToDeliveryManFromMapCommand.cs:56-247`) — with `SkipCashLimitValidation = true`
    (cash was already gated when the offer was created, step 13) and
    `skipDisanceValidation: true` hardcoded inside that command (`:204`, `hasOnWayOrder: false` at
    `:198`, meaning #389's bug cannot reach this particular call site — it only affects step 19's map
    path). `RejectAutoAssignRequestCommand` (`RejectAutoAssignRequestCommand.cs:27-59`) is the mirror:
    validates expiry/ownership, marks `Rejected` (`AutoAssignRequest.cs:38-42`) — this is what makes
    the driver ineligible for the *same* offer again in step 13's `assignedBefore` check, but does not
    by itself trigger the next candidate; the next `AutoAssignJob` tick does that.

## Data written
In the order they occur across the flow above:
1. `Order.DeliveryFees`, `Order.ExtraRestaurantDeliveryFees` — written once at order creation (step 5),
   read but not overwritten by every downstream assignment path except step 23 (admin path re-derives
   `ZoneProfit` fresh from `DeliveryZoneArea`, independent of the customer-facing figure already on the
   order).
2. `AutoAssignRequest` — one row per offer made (`Pending` at creation, step 13/14; `Accepted`/
   `Rejected` at step 24).
3. `OrderDelivery` — `DeliveryManId`, `DeliveryManProfit`, `CompanyProfit`, `DeliveryFees`, `Tips`,
   `OrderDeliveryStatusId` (`New` on assign, `Timeout` on step 15's manual hand-off) — written by
   whichever of steps 20/22/23 completes the assignment; step 22's path (plain self-assign) notably
   does **not** write any `OrderDelivery` fields.
4. `Order.DeliveryManId`, `.DeliveryManName`, `.StatusId`, `.AssignDeliveryManDate`,
   `.DeliveryManViewedDate` — set by `AddDeliveryManOwnerToOrder` (`Order.cs:714-727`, step 20 path) or
   directly by `AssignOrderToDeliveryMan` (step 22 path).
5. `Order.DeliveryManPricing` — the rating-tier adjustment value itself, written via
   `order.SetDeliveryManPricing` when the admin path computes it (`AssignOrdertoDeliveryManCommand.cs:106`)
   or when `DeliverymenProfitCalculator.Calculate`'s pricing-calculator branch runs (documented in
   [[Delivery-Assignment-Strategies|Delivery Assignment Strategies]]).
6. Redis (`DeliverymenRedisAttribute`) — `HasOrders`, `Orders`, `LastAssigningRequest`,
   `LastAssigningDate` written on every successful auto-assign offer (step 13) and on every successful
   accept/manual/admin assignment (steps 20, 23, 24) so the next eligibility check sees an up-to-date
   picture.

## External calls
- None directly in this flow beyond internal push notifications
  (`iDSClientHandler.SendNewTimeOutRequets`, `IAndroidGCMPushNotification`/`IVendorAppNotificationProvider`
  for offers and rejections) and the Redis cache reads/writes above. Payment/ERP integrations belong to
  [[Driver-Cash-Cycle.technical|Driver Cash and Settlement Cycle]], not this flow.

## Failure modes
- **#389** (step 19) — `AssignDeliveryManToDeliveryRequestCommand.cs:155-172`'s on-way-order lookup has
  no delivery-man filter and projects the wrong order's location, so the map self-assign path's
  distance gate is judged almost every time by the wrong branch and the wrong location (steps 20/24
  hardcode `hasOnWayOrder: false` and so are unaffected — see step 19 for the mechanism).
- **#390** (step 21) — `AssignOrderToDeliveryManByHimselfCommand.cs:39-58` has no `Active` check, unlike
  its admin-path sibling (`AssignOrdertoDeliveryManCommand.cs:63-64`) or the map-based self-assign
  (step 18, which does check `Active`) — see step 21 for the mechanism.
- **#430** / **#432** (step 16) — night-shift ops staff are invisible to the pending-task
  redistribution that follows a `Timeout`'d auto-assign delivery (#432), and night-shift drivers'
  attendance is never recorded (#430), though the latter is not confirmed to feed any gate in this
  flow specifically — see step 16 for the mechanism.
- **Two divergent rating-tier pricing formulas** (step 10) — `DeliveryManPricingCalculatorAdapter.cs:69`
  (`percentage / 100`) vs. `OrderDeleveryFeesCalculator.cs:90` (`currentRating × percentage / 100`).
  Not assigned a conflict number in this pass (newly observed here, not previously catalogued); flagged
  with the same "not confirmed as a live bug, but provably different formulas for the same concept"
  shape as the three cash-limit reimplementations in
  [[Driver-Cash-Cycle.technical|Driver Cash and Settlement Cycle]]'s Failure modes.
- **`DeliveryZoneArea.CustomerDeliveryFees` is a dead field** (step 7) — declared
  (`DeliveryZoneArea.cs:11`) but never set by either factory method, and one query explicitly
  hardcodes it to `0` (`GetAllDeliveryZoneAreaQuery.cs:29`). The one call site that reads it
  (`AssignOrderDeliveryToDeliveryManFromMapCommand.cs:157`) is therefore reading a column that is
  always its CLR default of `0` unless something outside the traced application code (a migration
  seed, a direct SQL update) has ever populated it. Not confirmed as reachable in practice — depends on
  how often the `OutGoingDeliveryOrder` branch that reads it is hit — but concrete and citable as-is.
- **Customer fee and driver payout are structurally unreconciled** (steps 2 vs. 6) — `RestaurantZoneArea.CustomerDeliveryFees`
  and `DeliveryZoneArea.DeliverymanDeliveryFees` are independent admin-configured tables (different
  zone concepts: `RestaurantZoneId` vs. `DeliveryZoneId`). No code path compares them or computes an
  explicit "company margin" figure; `OrderDelivery.CompanyProfit` is set to the full customer fee, not
  fee-minus-driver-payout (`AssignOrdertoDeliveryManCommand.cs:97,140-149`). Nothing in this codebase
  would catch a city admin configuring a driver payout that exceeds the customer's fee for the same
  route.

## Open Questions
- [ ] What creates the ops-staff `Tasks` row (`TaskTypes.AssignOrdertoDeliveryMan`) that a `Timeout`'d
  `OrderDelivery` (step 15) presumably becomes, and whether `Timeout` deliveries are ever retried by a
  later `AutoAssignJob` tick or require a human to act. Not traced in this pass.
- [ ] How a race between two drivers accepting the same zone-wide broadcast (step 17, non-auto-assign
  zones) is resolved — presumably the "already has a delivery man" checks inside step 20/22's domain
  methods, but not confirmed by tracing an actual concurrent-write scenario. Not traced in this pass.
- [ ] Whether `DeliveryMenShifts`/attendance data (the subject of #430) feeds any assignment
  eligibility check anywhere in this flow, beyond the Redis-based online/active flags traced here. Not
  traced in this pass.
- [ ] Whether `DeliveryZoneArea.CustomerDeliveryFees` (Failure modes) is simply unused legacy
  scaffolding, or whether some external process outside application code populates it. Not traced in
  this pass.
- [ ] Whether the two rating-tier pricing formulas (step 10) were ever meant to be identical — no git
  history or comment was consulted to determine which, if either, is "correct." Not traced in this
  pass.
- [ ] `MaxWalkingDistanceMeters`/`MaxBicycleDistanceMeters` (City fields) and whether/where they gate
  `DeliveryMethodType` selection feeding into step 12's queue-key selection. Not traced in this pass.
- [ ] The exact internal contract of `IOrderDeliveryMethodEligibilityValidator.ValidateAsync` /
  `.ValidateDistanceOnlyAsync` (used at steps 13, 18, 20) — only call sites were traced. Not traced in
  this pass.
