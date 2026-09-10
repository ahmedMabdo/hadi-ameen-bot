---
id: 8orders/delivery/driver-cash-and-compensation/driver-cash-cycle-technical
note_type: technical
context: Delivery
feature: Driver Cash & Compensation
group: Driver-Cash-Cycle
covers: [DeliveryBounsTier, JournalSubuscriptions]
sources:
  - path: AdminUi/Controllers/DeliverymanWallet/DeliverymanWalletController.cs
    sha1: 9714e0642f79
  - path: AdminUi/Helper/ERPIntegration/CashControllApiServices/CashControllApiServices.cs
    sha1: a6668ea790a5
  - path: AdminUi/Helper/ERPIntegration/CashControllApiServices/CashReceiptValidator.cs
    sha1: fc8fbdfb8ee5
  - path: Shared/TalabatkApplication/Commands/AddDeliverymanWalletTransactionCommand/AddDeliverymanWalletTransactionCommand.cs
    sha1: e20ba0617d0b
  - path: Shared/TalabatkApplication/DomainEventsHandlers/OrderEventsHandlers/OrderDeliveredEventHandler.cs
    sha1: 57f2b31cd7dd
  - path: Shared/TalabatkApplication/ForceAssignDeliverymenService.cs
    sha1: c558c63dd0a2
  - path: Shared/TalabatkApplication/Queries/GetDeliveryManShiftDeliveryBounsQuery/GetDeliveryManShiftDeliveryBounsQuery.cs
    sha1: 798a3e8cb23f
  - path: Shared/TalabatkData/CalculateDeliveryBounsService/DeliveryBounsCalculationService.cs
    sha1: f6eefb3f7b77
  - path: Shared/TalabatkData/FawryCashCollectionService/FawryCashCollectionService.cs
    sha1: fb2c3d4c4d3d
  - path: Shared/TalabatkLogic/TalabatkModels/DeliveryMen.cs
    sha1: e592516c13f2
  - path: Shared/TalabatkLogic/TalabatkModels/DeliverymanTransaction.cs
    sha1: ad9f630f0b02
  - path: Talabatk.IDS/Helper/HangFire/DailyDeductionFromDeliveryManFinance.cs
    sha1: d563163f7f2e
last_updated: 2026-08-23
tags: [flow, technical]
---
# Driver Cash and Settlement Cycle — Technical

> **Bridges:** [[DeliveryMen.technical|DeliveryMen]] (Rules 3-5: cash-limit
> formula, insurance/assets deduction bounds), [[City.technical|City]] (Rule 2: per-city
> financial defaults), [[DeliverymanTransaction.technical|DeliverymanTransaction]] (the
> ledger every step below writes to), [[DeliveryBouns.technical|DeliveryBouns]] (bonus tier
> config), [[OrderDelivery.technical|OrderDelivery]] (source of the collected/profit amounts),
> [[Fawry.technical|Fawry]] (the customer-payment side of the same
> partner integration used here for cash deposits). This note does not restate any of their formulas —
> only where each fires within the cash cycle.

## Trigger
Four independent triggers feed the same per-driver running balance and the same
`ExceededCashLimit` gate, and there is no single "cash cycle" entry point:
1. An order reaches `Delivered` status → `OrderDeliveredEvent` → `OrderDeliveredEventHandler`.
2. Fawry's servers call back after a rider deposits cash at a Fawry point of sale → webhook.
3. A back-office cashier posts a cash receipt/payment in `AdminUi`'s ERP-integration screen.
4. A nightly Hangfire job runs unconditionally for every driver who delivered that working day.

## Step-by-step

### A. Cash collection at delivery (per order)
1. `OrderDeliveredEvent` fires; `OrderDeliveredEventHandler.Handle` branches on the
   `MultipleDeliveries` feature flag into `HandleSingleDelivery` or `HandleMultiDelivery`
   (`OrderDeliveredEventHandler.cs:47-59`).
2. For the single-driver path (`HandleSingleDelivery`, `OrderDeliveredEventHandler.cs:107-209`):
   dedup flags are pre-computed by querying for an existing `Order_Collection` /
   `Delivery_Profit` row for this `OrderCode` (`:138-146`), then passed into
   `DeliverymanTransaction.AddCashOrderTransaction` (`:148-156`).
3. `AddCashOrderTransaction` (`DeliverymanTransaction.cs:87-172`) writes, if not already present:
   - `Order_Collection` (debit) for `orderDelivery.TotalCollectedFromCustomer` (`:117-134`) — the
     cash the rider now owes the company.
   - `Delivery_Profit` (credit) for `orderDelivery.DeliveryManProfit` (`:150-168`) — the rider's
     earned fee. `TotalCollectedFromCustomer`/`DeliveryManProfit` themselves are `OrderDelivery`
     fields, not re-derived here — not traced further in this pass (see
     [[OrderDelivery.technical|OrderDelivery]]).
   Both go through the shared `Instance` factory gate (`:31-84`), which for these two types adds no
   side effect beyond the `IsCredit` classification (Rule 1/Rule 2 of the `DeliverymanTransaction`
   note only fire side effects for `Equipment_Deduction`/`Deposit_Settlement`).
4. `context.SaveChangesAsyncWithResult()` (`OrderDeliveredEventHandler.cs:173`).
5. The rider's full balance is recomputed by summing every `DeliveryMenTransactions` row for that
   driver (`:176-179`, `IsCredit ? -Amount : Amount`), then
   `deliveryman.UpdateRequiredPaymentAndExceededCashLimit(balance)` is called (`:183`) — the formula
   itself is `DeliveryMen.cs:96-129`, documented in [[DeliveryMen.technical|DeliveryMen]]
   Rule 3; not restated here.
6. The resulting `exceededCashLimit` bool is written to the Redis cache field
   `DeliverymenRedisAttribute.ExceededCashLimit` for that driver id (`:185`), then a second
   `SaveChangesAsyncWithResult()` persists the entity-side flag (`:194`).
7. The multi-driver path (`HandleMultiDelivery`, `:211-331`) does the same three things
   (transaction write, balance recompute, cache write) per leg of a split delivery, batching the
   balance query across all involved drivers (`:279-287`) rather than the per-driver query used in
   the single path.
8. Separately, a domain event `CalculateDeliveryShiftBounsEvent` (raised elsewhere — not traced in
   this pass which order-state transition fires it) drives
   `CalculateDeliveryShiftBounsEventHandler.Handle` (`:32-73`): for each `OrderDelivery` on the
   order, `IDeliveryBounsCalculationService.CalculateDeliveryBounsAsync(deliveryManId)` (`:55`)
   returns a bonus value and tier id; if non-zero,
   `DeliverymanTransaction.AddDeliveryShiftBounsTransaction` writes a `Shift_Bouns` credit
   (`:63-67`), and `context.SaveChangesAsyncWithResult()` closes the handler (`:71`). **#411**
   applies directly inside `CalculateDeliveryBounsAsync`'s counting query (see Failure modes).

### B. Cash limit exceeded — what it blocks
9. Auto-assignment (`ForceAssignDeliverymenService.TryCompleteAutoAssignForDeliverymanAsync`,
   `ForceAssignDeliverymenService.cs:554-730`) only evaluates cash exposure for cash-only orders
   (`isOrderPaidInCashOnly`, computed at `:296-307` in the caller `AssignOrderToDeliveryman`).
10. Inside that check (`:658-691`): the driver's current balance is summed fresh from
    `DeliveryMenTransactions` (`:660-663`), the combined cash limit is read directly off the entity
    (`CashLimit + ExternalDeliveryCashLimit`, `:665-668`) — **not** the cached value — but the actual
    gate is the Redis flag: `exceedCashLimit == "True"` → the candidate driver is rejected outright
    for this order and the loop moves to the next driver in queue (`:670-680`).
11. If not blocked, a softer check runs: if the driver's balance *would* reach 70% of their limit
    once this order's cash is added (`deliverymanBalance + orderTotal - toBePaidToMerchant >=
    deliverymanCashLimit * 70 / 100`, `:682-691`), the assignment still proceeds but
    `aboutToExceededCashLimit` is set, which appends an Arabic "please settle your cash soon" line
    to the assignment-notification description (`GetDescription`, `:761-763`) — a warning, not a
    block.
12. So "limit exceeded" has exactly one enforcement point in this codebase: the Redis
    `ExceededCashLimit` field consulted at `ForceAssignDeliverymenService.cs:670`. Every write path
    in this note (steps 6, 16, 24, 28, 34 below) exists to keep that one field current.

### C. Settlement path 1 — Fawry deposit
13. Fawry calls the webhook backing `FawryCashCollectionService.FawryPaymentNotify`
    (`FawryCashCollectionService.cs:95-223`) — the HTTP entry point/route itself is not opened in
    this pass (not traced); the DTO signature is SHA-256, checked against the incoming `signature`
    field before anything else (`:104-125`).
14. The driver is looked up by `FawryProfileId` (`:127-129`); on a new (non-retry) transaction, a
    `FawryCashCollectionTransaction` row is created and saved (`CreateTransaction`, `:295-317`),
    then a Hangfire job `CreateDeliveryStatementTransaction` is enqueued (`:153-154`) — the ledger
    write happens **out of band**, in the background job, not synchronously in the webhook handler.
15. `CreateDeliveryStatementTransaction` (`:321-391`, retried up to 4 times on failure,
    `[AutomaticRetry(Attempts = 4)]`) computes `requiredPayment` using the same
    over-limit-percentage-vs-under-limit-percentage branching as the cash-limit formula (`:338-348`,
    mirrors `DeliveryMen.cs:96-129` inline rather than calling it), then writes a `Fawry_Payment`
    credit via `DeliverymanTransaction.AddFawryTransaction` (`:350-354`) and saves (`:358-360`).
16. Balance is recomputed (`:362-365`) and compared against `requiredPayment`: paid-enough clears
    `ExceededCashLimit` to `false` and zeros `RequiredPaymentTOLockExceedCashLimit` (`:367-372`);
    under-paying sets the cache flag `true` and stores the shortfall (`:373-379`); an exact-equal
    edge case is handled separately, flooring the recorded shortfall at 1 (`:380-388`,
    `requiredPayment - amount == 0 ? 1 : …`). Final `SaveChangesAsync()` at `:389` (unchecked,
    fire-and-forget — no `IsSuccess` branch, unlike every other save in this file).

### D. Settlement path 2 — office cash handover
17. Back office posts through `AdminUi`'s `CashControllApiServices.CashReceiptPost`
    (`CashControllApiServices.cs:88-179`), shared by both driver and merchant cash receipts via
    `request.Type`.
18. `CashReceiptValidator.Validate` runs first (`:98-102`; validator at `CashReceiptValidator.cs:10-48`):
    common checks (description, configuration, treasury account, `:12-35`), then type-specific —
    `ValidateDeliverymanReceivement` (`:50-63`) rejects a declared amount that misses the driver's
    expected balance by more than `configuration.MoneyCollectionTolerance` (`:52-55`).
19. On success, the request is posted to the external AccFlex ERP's `api/CashReceipt` endpoint
    (`CashControllApiServices.cs:113-145`); only on an ERP-side success response does the local
    ledger write happen (`HandleDeliverymanReceivement`, `:181-273`).
20. A `DeliveryManDaily` row is created first and saved standalone (`:184-198`) — this is the
    office's record of "this much cash was physically handed over today", distinct from the
    `DeliverymanTransaction` ledger.
21. `requiredPayment` is computed inline (`:204-224`) using the same limit-percentage branching a
    third time (compare step 15) — here reading `deliveryman.CashLimit` alone, **not** `CashLimit +
    ExternalDeliveryCashLimit` as steps 10/15 do (`:211`, `deliverymanCashLimit = deliveryman.CashLimit`)
    — a third independent reimplementation of the same formula, each slightly different in scope. Not
    confirmed whether this divergence (external limit included vs. not) is deliberate.
22. `DeliverymanTransaction.AddCashRecievementTransaction` writes a `Delivery_Receivement` credit
    (`:226-231`) and saves (`:238-242`).
23. Balance is recomputed post-write (`:244-247`) and compared against `requiredPayment` and
    `deliverymanCashLimit`: fully caught up clears the cache flag and
    `UpdatePartialPaymentBlocked(false)` (`:249-255`); underpaid sets the flag `true`,
    `UpdatePartialPaymentBlocked(true)`, and records the shortfall via
    `UpdateRequiredPaymentToLockExceedCashLimit` (`:256-262`); the exact-equal branch again floors
    the shortfall at a minimum of 1 unit if it would otherwise compute to 0 (`:263-270`). Final
    `SaveChangesAsync()` at `:271` — again unchecked.
24. `IsPartialPaymentBlocked` (set at `:252/259/266`) is the flag the cash-limit formula documented
    in [[DeliveryMen.technical|DeliveryMen]] Rule 3 reads to decide whether a
    balance under the limit still requires zero payment — this is the write side of that read; the
    read site itself is `DeliveryMen.cs:96-129`, already documented there.
25. Merchant cash receipts share steps 17-19 (`request.Type == Merchant`) but branch into
    `HandleMerchantReceivement` (`:275-312`) instead — unrelated to the driver's own balance, called
    out here only because **#417** sits on this shared entry point (see Failure modes).

### E. Settlement path 3 — dismissal / final settlement
26. Not driven by a Hangfire job or webhook in this pass — `DeliveryMen.Dismiss(netSettlement)`
    (`DeliveryMen.cs:479-501`, documented in that entity's Rule 11) zeroes
    `PaidFromInsuranceLimit`/`PaidFromAssets` and records `NetSettlementAmount` directly on the
    entity. The caller (an Admin command) that invokes `Dismiss` and decides `netSettlement` was
    not traced in this pass.
27. Manual insurance/equipment settlement outside of dismissal goes through
    `AddDeliverymanWalletTransactionCommand` (below, step 33) with `TransactionType ==
    Deposit_Settlement` or `Equipment_Deduction` — this is the same command back office uses for
    ad-hoc bonuses/penalties.

### F. Daily automatic deductions (insurance + equipment, nightly)
28. Hangfire job `DailyDeductionFromDeliveryManFinance.DailyFinanceDeduction`
    (`Talabatk.IDS/Helper/HangFire/DailyDeductionFromDeliveryManFinance.cs:48-182`,
    `[RetryInQueue("ids")]`) selects every driver with at least one `Delivered` order inside the
    configured working-time window (`StartOffset`/`EndOffset` appsettings, `:51-63`).
29. Per driver, city defaults are read (`RefundableDepositDeductionPercentage`,
    `AssetsDeductionPercentage`, `MinimumRefundableDepositAmount`, `MinimumAssetsDeductionAmount` —
    all documented in [[City.technical|City]] Rule 2, not restated) and the raw deduction
    amounts computed (`:84-95`).
30. `deliveryMan.UpdatePaidFromFinancialAmounts(...)` (`DeliveryMen.cs:236-271`, documented in
    [[DeliveryMen.technical|DeliveryMen]] Rule 5) applies the
    minimum-floor/remaining-balance-ceiling bounding and returns the actual amounts deducted
    (`:97-102`).
31. If either actual deduction is positive, `AddInsuranceDailyDeductionTransaction`
    (`Insurance_Deposit`-style debit — wraps `Deposit_Deduction`) or
    `AddAssetsDailyDeductionTransaction` (wraps `Equipment_Deduction`) writes the ledger row
    (`:105-132`); a per-driver failure is logged and skipped, not fatal to the batch (`:113-116`,
    `:128-131`).
32. `SaveChangesAsyncWithResult()` for all drivers' transactions at once (`:135-141`) — if this
    fails, the job **returns early** (`:139-141`) and never reaches the cache-update loop below,
    leaving the Redis flag stale for every driver in the batch.
33. Balances are recomputed in one grouped query (`:143-151`), then for each driver
    `UpdateRequiredPaymentAndExceededCashLimit` is called (`:160`) and the result written to Redis
    (`:162`) — **before** the second `SaveChangesAsyncWithResult()` at `:174` that actually persists
    the entity-side `ExceededCashLimit`/`RequiredPayment` fields. **This ordering is #419's eighth
    instance** (see Failure modes).

### G. Manual back-office wallet adjustments (bonus/penalty/settlement)
34. `AddDeliverymanWalletTransactionCommand` (`Shared/TalabatkApplication/Commands/AddDeliverymanWalletTransactionCommand/AddDeliverymanWalletTransactionCommand.cs:28-158`),
    exposed via `AdminUi/Controllers/DeliverymanWallet/DeliverymanWalletController.cs` (route/authorization
    not opened in this pass).
35. For `Equipment_Deduction`/`Deposit_Settlement`, the account id is overridden from
    `Configuration.DeliverymenAssetsDeductionAccountId` /
    `Configuration.DeliverymenInsuranceAccountId` regardless of what the caller supplied (`:65-82`).
36. Only `Equipment_Deduction` is validated against actual holdings —
    `deliveryMan.ValidateEquipmentDeduction(request.Amount, totalAssetsValue)` (`:84-93`),
    documented in [[DeliveryMen.technical|DeliveryMen]] Rule 5. `Deposit_Settlement`
    falls straight through to `DeliverymanTransaction.Instance` with no equivalent check (`:78-81`
    vs. `:95-102`) — **this is #392**.
37. The transaction is saved (`:109-115`); if the type is one of `Penalty`/`Bonus`/
    `Equipment_Deduction`/`Deposit_Settlement` (`:117-121`), balance is recomputed and
    `UpdateRequiredPaymentAndExceededCashLimit` + Redis write happen exactly as in every other path
    (`:130-153`); other transaction types skip this and return immediately (`:123-126`).

## Data written
In trigger order as they occur through the cycle above:
1. `TA_DeliveryMenTransactions` (`DeliverymanTransaction`) — one row per event: `Order_Collection`
   (debit), `Delivery_Profit` (credit) per delivered cash order (step 3); `Shift_Bouns` (credit) per
   qualifying order (step 8); `Fawry_Payment` (credit) per Fawry deposit (step 15);
   `Delivery_Receivement` (credit) per office handover (step 22); `Deposit_Deduction`/
   `Equipment_Deduction` (debit) nightly (step 31); `Penalty`/`Bonus`/`Equipment_Deduction`/
   `Deposit_Settlement` on manual adjustment (step 36).
2. `DeliveryMen` entity fields — `RequiredPayment`, `ExceededCashLimit`,
   `RequiredPaymentTOLockExceedCashLimit`, `IsPartialPaymentBlocked`, and (for `Equipment_Deduction`/
   `Deposit_Settlement` only, as a side effect of `DeliverymanTransaction.Instance` itself)
   `PaidFromAssets`/`PaidFromInsuranceLimit` — updated at nearly every step above.
3. Redis — `DeliverymenRedisAttribute.ExceededCashLimit` per-driver hash field, read exclusively by
   `ForceAssignDeliverymenService` (step 12); written at steps 6, 16, 23, 33, 37.
4. `DeliveryManDaily` — one row per office cash handover (step 20), independent of the ledger.
5. `FawryCashCollectionTransaction` — one row per Fawry webhook notification (step 14).
6. External AccFlex ERP `CashReceipt`/`CashPayment` records — created via HTTP POST before the local
   ledger write in the office-handover path (steps 19, and the separate `DeliveryManPaymentPost`/
   `AddDeliveryManTransaction` payout path at `CashControllApiServices.cs:415-618`, not walked in
   detail in this pass — it mirrors the receipt path but pays the driver out via `Cash_Delivery_Payment`).

## External calls
- **Fawry webhook** (`FawryCashCollectionService.FawryPaymentNotify`) — inbound only; SHA-256
  signature check against `FawryCashCollection:SecurityKey` (name only, not the value) before any
  processing (`FawryCashCollectionService.cs:104-125`).
- **AccFlex ERP** (`AccFlexAccessControl:CashControlApiBaseUrl`, config key named only) — outbound
  HTTP POST to `api/CashReceipt` (driver/merchant cash receipts, `CashControllApiServices.cs:145`)
  and `api/CashPayment`/`api/PayableBankTransfer` (driver/merchant payouts, `:392-404`, `:441`).
  Local ledger writes only occur after a successful ERP response — see step 19.

## Failure modes
- **#392** — `AddDeliverymanWalletTransactionCommand.cs:78-81` skips amount validation for
  `Deposit_Settlement` while the sibling `Equipment_Deduction` branch is bounds-checked
  (`:84-93`). Sits at step 36 of this note (manual back-office insurance settlement) — a
  financial-control gap on money leaving the security-deposit fund specifically.
- **#411** — `GetDeliveryManShiftDeliveryBounsQuery.cs:113-114` and, independently,
  `DeliveryBounsCalculationService.cs:101-102` (reached from step 8's
  `CalculateDeliveryBounsAsync` call) both compare the bonus window's upper bound against
  `.Value.Date` instead of `.Value`, truncating it to midnight — so the upper bound behaves as
  "delivered on the same calendar day" rather than "before the window closes", and orders
  delivered after the bonus period ends still count toward the payout. Affects both the count a
  driver is shown and the count actually paid.
- **#417** — `CashReceiptValidator.cs:65-73` (`ValidateMerchantReceivement`) cannot validate the
  declared amount because its signature never receives `PostCashReceiptDto` at all, unlike
  `ValidateDeliverymanReceivement` (`:52-55`), which is tolerance-checked. Sits at step 25 — the
  same `CashReceiptPost` entry point used for driver receipts (step 17) has no equivalent guard on
  the merchant branch, confirmed unguarded all the way through `HandleMerchantReceivement`
  (`CashControllApiServices.cs:275-279`).
- **#419** (eighth instance in that finding's family) —
  `DailyDeductionFromDeliveryManFinance.cs:154-178` writes the `ExceededCashLimit` Redis cache
  field (`:162`) **before** the `SaveChangesAsyncWithResult()` that persists the corresponding
  entity fields (`:174`). If that save fails, `ForceAssignDeliverymenService`'s block/allow decision
  (step 10, which reads only the Redis field) has already diverged from what the database records —
  a driver could be blocked from assignment (or, conversely, let through) based on a required-payment
  calculation the database never confirmed. The same handler's *first* save (`:135`, saving the
  deduction transactions themselves) is checked and returns early on failure, but that early return
  happens before the cache write, not after it — the risk is specifically in the *second* save/cache
  pair.
- **Three independent reimplementations of the cash-limit-percentage formula** — step 15
  (`FawryCashCollectionService.cs:338-348`), step 21 (`CashControllApiServices.cs:211-224`, using
  `CashLimit` alone), and the canonical `DeliveryMen.UpdateRequiredPaymentAndExceededCashLimit`
  (`DeliveryMen.cs:96-129`, used by steps 5, 16 [indirectly, same formula], 33, 37) all compute
  "how much must the driver pay to clear the limit" independently rather than sharing one method.
  Not confirmed as a live bug — the values may agree in practice — but three call sites are one
  more than zero for a formula this financially sensitive, and step 21's narrower scope
  (`CashLimit` vs. `CashLimit + ExternalDeliveryCashLimit`) is a concrete divergence in what's
  being compared, not just duplicated logic.
- **Two unchecked final saves** — `FawryCashCollectionService.cs:389` and
  `CashControllApiServices.cs:271` both call `SaveChangesAsync()` (not the `...WithResult()`
  variant) as their last statement, with no success check — a failure here would leave the ledger
  transaction (already saved earlier in the same method) out of sync with the cache/entity flags
  the same method just tried to update. Not confirmed as a reachable production incident in this
  pass; flagged as the same shape as #419's family but not cross-referenced into that finding since
  the original investigation didn't cite these two lines specifically.

## Folded entities — the 2 satellites documented here

| Entity | What it is | Rules |
|---|---|---|
| `DeliveryBounsTier` | One band of a driver bonus scheme: an order-count range and the bonus it pays | Two guards, and both are the right ones: the bonus value must be greater than zero (`Shared/TalabatkLogic/TalabatkModels/DeliveryBounsTier.cs:39`) and the **minimum order count cannot exceed the maximum** (`:42`). `Create` returns `Result` and there is no update method at all, so a tier is immutable once made — which is the safest possible shape for a pay rule. Contrast `DeliveryManPrice`, the commission-band table in [[Delivery/Delivery Man Operations/Driver-Operations.technical\|Driver Operations]], which models the same idea and validates nothing. Note the misspelling, which is the real one, and that nothing prevents two tiers from overlapping or leaving a gap |
| `JournalSubuscriptions` | A recurring accounting-journal charge tied to a set of restaurants | Guards on both live paths: `Instance` requires a non-empty name and at least one restaurant (`Shared/TalabatkLogic/TalabatkModels/JournalSubuscriptions.cs:64`, `:74`); `Update` requires at least one restaurant, a name and a description (`:100`, `:108`, `:112`); `AddExcutionHistory` rejects a null history (`:126`). `IsStoped` is the pause switch and `SubuscriptionRepetion` the interval. Documented in full in [[Admin/Catalog & Content Administration/Mart-and-Reference-Entities\|Mart and Reference Entities]]; it appears here because its charges land on the merchant statement, and its run outcomes are recorded in `ExcutionHistory` |

## Open Questions
- [ ] `DeliveryBounsTier` validates its own range but nothing checks tiers against each other. Can two
      tiers overlap, and which wins?
- [ ] What raises `CalculateDeliveryShiftBounsEvent` (step 8) — not traced in this pass; presumably
  a domain method on `Order`/`OrderDelivery` fired alongside or near `OrderDeliveredEvent`, but the
  raise site itself was not located.
- [ ] Whether `HandleDeliverymanReceivement`'s use of `deliveryman.CashLimit` alone (step 21,
  `CashControllApiServices.cs:211`) versus every other site's `CashLimit + ExternalDeliveryCashLimit`
  is deliberate (e.g. external-delivery drivers settle differently at the office) or a bug.
  Not traced further given the budget for this pass.
- [ ] The caller/command that invokes `DeliveryMen.Dismiss(netSettlement)` (step 26) and how
  `netSettlement` itself is calculated — not traced in this pass.
- [ ] `AdminUi/Controllers/DeliverymanWallet/DeliverymanWalletController.cs`'s route and
  authorization for `AddDeliverymanWalletTransactionCommand` (step 34) — not opened in this pass.
- [ ] The Fawry webhook's actual route/controller (step 13) — only the service method was traced,
  not the HTTP entry point or its authentication model beyond the payload signature check.
- [ ] `CashControllApiServices.DeliveryManPaymentPost`/`AddDeliveryManTransaction`
  (`CashControllApiServices.cs:415-618`) — the driver *payout* path (company pays the driver, e.g.
  their earned profit in cash) shares the ERP integration but was not walked step-by-step in this
  pass; noted only in "Data written" as a sibling of the receipt path.
- [ ] Whether `OrderDelivery.TotalCollectedFromCustomer`/`DeliveryManProfit` (consumed at step 3)
  have their own validation — not traced in this pass; flagged in
  [[DeliverymanTransaction.technical|DeliverymanTransaction]]'s own Rule 3 as an
  "trusts the caller" case for `AddCashOrderTransaction`.
