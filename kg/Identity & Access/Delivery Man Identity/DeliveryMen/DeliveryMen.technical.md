---
id: 8orders/identity-and-access/delivery-man-identity/deliverymen-technical
note_type: technical
rule_count: 12
context: Identity & Access
feature: Delivery Man Identity
entity: DeliveryMen
entity_type: child
sources:
  - path: Shared/TalabatkApplication/Commands/ChangeDeliveryManActivationCommand.cs
    sha1: 50997f8b8f8c
  - path: Shared/TalabatkData/Mapping/DeliveryMenMap.cs
    sha1: b94b33c2dab5
  - path: Shared/TalabatkLogic/TalabatkModels/DeliveryMen.cs
    sha1: e592516c13f2
last_updated: 2026-08-23
tags: [identity-access, delivery-man, transactional, technical, backend-domain]
---
# DeliveryMen — Technical

> **Layer:** Backend-Domain — legacy entity, richer than a typical anemic POCO (private setters +
> substantial behavior methods, `Result`-returning), extends ASP.NET Identity's `IdentityUser<int>`.
> **Context:** Identity & Access (per `CONTEXT-MAP.md`) — but, like `Customer`, this is a hub touched
> directly by Delivery (`TalabatkDelivery`) and Admin (`AdminUi`) as much as by Identity & Access.
> **Source Path:** `Shared/TalabatkLogic/TalabatkModels/DeliveryMen.cs`   **Last Updated:** 2026-08-03

## Business Rules

### Rule 1: Created already active — no OTP-style verification gate
- **Plain language:** Unlike `Customer` (starts `Active=false` pending OTP), a delivery man row
  starts `Active=true`, `IsAttend=true` immediately on creation.
- **Source:** `DeliveryMen.cs:179-235` (`Instance(...)`). Confirms provisioning is operator-driven,
  not self-service registration+OTP like Customer — consistent with there being no equivalent
  `PromoteFromGuest`/guest concept for delivery men.

### Rule 2: `UserName` is a computed alias for `PhoneNumber`, not an independent field
- **Plain language:** Setting the username also sets the phone number and vice versa — they're
  always the same value.
- **Source:** `DeliveryMen.cs:77-89` (`override UserName` getter/setter).
- **⚠️ Conflict — DB does not enforce uniqueness on this identity value:**
  `Shared/TalabatkData/Mapping/DeliveryMenMap.cs:51` has `HasIndex(x => x.UserName)` with **no**
  `.IsUnique()` (contrast `FawryProfileId` at `DeliveryMenMap.cs:59`, which explicitly is
  `.IsUnique()`). This is a second, independent instance of the repo-wide "app-level-only uniqueness
  assumption with no DB constraint" pattern already on record in `_system/_conflicts.md` for
  `CustomerCart.CustomerId` / `PromoCodes.Promo` — add this as a third occurrence, not a new pattern.

### Rule 3: Cash-limit exceedance and required top-up payment
- **Plain language:** A delivery man's effective cash limit is their base limit plus their external
  limit. If their running cash balance is under that combined limit (and partial payments aren't
  blocked), no payment is required. Once it's at or over the limit, a mandatory percentage of the
  balance becomes due — calculated differently depending on whether the balance is above or below
  the limit.
- **Formula:** `deliverymanCashLimit = CashLimit + ExternalDeliveryCashLimit`;
  `cashLimitMandatoryPercentage = round((MandatoryDailyDepositPercentage/100) * deliverymanCashLimit, 2)`.
  If `deliverymanCashLimit > balance && !IsPartialPaymentBlocked` → `requiredPayment = 0`. Else if
  `balance >= deliverymanCashLimit` → `requiredPayment = cashLimitMandatoryPercentage + (balance -
  deliverymanCashLimit)`. Else → `requiredPayment = (MandatoryDailyDepositPercentage/100) * balance`.
- **Source:** `DeliveryMen.cs:96-129` (`UpdateRequiredPaymentAndExceededCashLimit`).

### Rule 4: Combined cash limit depends on which delivery types are enabled — and the "neither" case is unclear
- **Plain language:** When both internal and external delivery are enabled, the combined limit sums
  both; when only internal is enabled, it's just the internal limit. When only external is enabled,
  it's the external limit — same as the "neither enabled" case, since the logic doesn't distinguish
  them.
- **Source:** `DeliveryMen.cs:444-465` (`GetNewFinancialValues`) — `if (internal && external) → sum;
  else if (internal) → CashLimit; else → ExternalDeliveryCashLimit`. The `else` branch is reached both
  when only external is true AND when both are false — a delivery man with neither flag set still
  gets `ExternalDeliveryCashLimit` as their effective limit rather than `0`. Not confirmed whether
  "neither enabled" is a state that actually occurs in practice — flagged as an Open Question rather
  than a confirmed bug.
- Used by `Update(...)` (`DeliveryMen.cs:344-442`) to detect a real financial-settings change and
  emit exactly one `DeliveryManFinancialSettingsChangedEvent` if either the combined cash limit or
  the mandatory deposit percentage actually changed — avoids firing the event on unrelated profile
  edits.

### Rule 5: Insurance/assets deduction is bounded by minimums and remaining balance
- **Plain language:** When deducting from a delivery man's refundable deposit or equipment-assets
  balance, the system takes at least a configured minimum (if any deduction applies at all) but never
  more than what's actually left in that balance.
- **Source:** `DeliveryMen.cs:236-271` (`UpdatePaidFromFinancialAmounts`) — for each of the two
  balances: `actualDeduction = max(requestedDeduction, minimum)`, then
  `deducted = min(actualDeduction, remainingBalance)`.
- Equipment deduction is separately guarded: `ValidateEquipmentDeduction` (`DeliveryMen.cs:145-156`)
  rejects a non-positive amount or one exceeding `GetRemainingEquipmentBalance` (`totalAssetsValue -
  PaidFromAssets`).

### Rule 6: Two independent, differently-scoped rating calculations coexist
- **Plain language:** There are two separate ways this entity computes "the" delivery man's rating,
  and it's not obvious from the code alone which callers use which.
- `DeliveryManRate` — a **weighted** average grouped by distinct rating value, set via
  `UpdateDeliveryRateForLastThreeMonths(deliveryReviews)` (`DeliveryMen.cs:276-298`) — the caller
  presumably passes in a pre-filtered "last 3 months" review list (not filtered inside this method).
- `Rate()` (`DeliveryMen.cs:569-580`) — a plain arithmetic mean over **all** of
  `TA_DeliveryManReviews`, computed on demand, not stored.
- **Possible drift risk, not yet confirmed as a bug:** these can legitimately disagree (one is a
  recent window, the other is lifetime), but nothing in this class documents which one is
  authoritative for which UI/screen — flagged as an Open Question, not force-classified as the
  repo's known "same rule implemented twice" pattern since the two may be intentionally different
  metrics (recent vs. lifetime).

### Rule 7: Admin-triggered deactivation blocks the delivery man from self-reactivating
- **Plain language:** If an admin deactivates a delivery man, that delivery man cannot simply go
  active again themselves — they must be told to contact the admin, until an admin (or something
  else) clears the flag.
- **Source:** `DeliveryMen.cs:514-528` (`ChangeActivationByDeliveryman`) —
  `if (isActive && UpdateFromAdmin && !Active) return Result.Failure("من فضلك قم بالرجوع الي الادمن")`
  ("Please go back to the admin"). The same guard appears in `StartBreak` (`:684-687`) and
  `ActivateAfterBreak` (`:729-732`) verbatim.
- `UpdateFromAdmin` is set by `Update(...)` (`DeliveryMen.cs:368-369`) only when an admin's update
  transitions the delivery man from active to inactive (`if (!Active && this.Active)`).

### Rule 8: Every online/offline transition writes (or closes) a shift log row
- **Plain language:** Going online while assigned to a shift opens a new attendance log entry; going
  offline closes the most recent still-open entry for that shift.
- **Source:** `DeliveryMen.cs:538-557` (`AddDeliveryManShiftLog`) — opens
  (`DeliverymanShiftLog.Instance(...)`) only if `active && ShiftId.HasValue && !this.Active`
  (transitioning off→on); closes the newest log with `OnlineTo == null` for that shift only if
  `!active && ShiftId.HasValue && this.Active` (transitioning on→off). Called from `Update` (admin
  edit), `ChangeActivationByDeliveryman` (self-service), and `DeActivateBySystem` (system-forced,
  presumably the nightly Hangfire force-close job — not yet confirmed, part of the not-yet-documented
  `DeliverymanShiftLog`/`DeliveryMenShifts` entities).

### Rule 9: Shift-window tolerance check has no geofencing in this class
- **Plain language:** Trying to go active outside the assigned shift's time window (with a tolerance
  buffer on both ends, correctly handling shifts that cross midnight) is rejected with an Arabic error
  message naming the shift's actual start/end time.
- **Source:** `DeliveryMen.cs:582-614` (`CanActivate(now, toleranceMinutes, active)`) — no `Shift`
  assigned → immediate failure; otherwise compares `now` against `[StartTime - tolerance, EndTime +
  tolerance]`, with explicit overnight-crossing handling (`crossesMidnight = earliest > latest`).
- **Open Question:** a prior (unverified, lost) research pass described this system as having
  **geofenced** clock-in. This class does accept a `Geometry location` parameter into
  `ChangeActivationByDeliveryman`/`AddDeliveryManShiftLog`, but no location/geofence validation
  appears in this file — either the geofence check lives in the Application-layer command handler
  (not yet read) or in `DeliverymanShiftLog` itself (next entity in this batch). Do not treat
  "geofenced" as confirmed until that note is written.

### Rule 10: Break-ending requires the same admin-override guard, and disables shift-log writes
- **Plain language:** Ending a break reactivates the delivery man through a separate path that
  deliberately does **not** touch shift logs (that's the online/offline path's job) — but is still
  blocked if an admin deactivated them.
- **Source:** `DeliveryMen.cs:727-737` (`ActivateAfterBreak`) — doc comment explicitly: "should only
  be used for break operations", sets `Active=true` without calling `AddDeliveryManShiftLog`.
- `StartBreak` (`DeliveryMen.cs:682-721`) sets `Active=false`, fires `BreakStartedEvent`, and —
  **only if currently assigned to a shift** — creates a `DeliverymanBreakLog` row; if not on a shift,
  it still succeeds but returns a `null` break log (`Result.Success<DeliverymanBreakLog>(null)`).

### Rule 11: Dismiss/ReHire reset financial balances; SoftDelete alone does not
- **Plain language:** Simply soft-deleting a delivery man leaves their insurance/asset balances
  untouched. Dismissing them explicitly zeroes those balances and records a final settlement figure;
  rehiring resets the same balances and restores a fresh insurance limit.
- **Source:** `DeliveryMen.cs:479-501` — `SoftDelete()` only sets `IsDeleted=true`; `Dismiss(netSettlement)`
  additionally zeroes `PaidFromInsuranceLimit`/`PaidFromAssets` and stores `NetSettlementAmount`;
  `ReHire(newInsuranceLimit)` un-deletes, zeroes `PaidFromInsuranceLimit`, sets a new
  `InsuranceLimit`, and zeroes `NetSettlementAmount`.

### Rule 12: Two overlapping supplier-unassignment methods
- **Plain language:** There are two different methods for detaching a delivery man from their
  delivery supplier, one of which also clears the loaded navigation object.
- **Source:** `DeliveryMen.cs:665-674` — `RemoveSupplier()` (`internal`) clears both
  `DeliverySupplier` (nav property) and `DeliverySupplierId`; `UnAssignFromSupplier()` (`public`)
  clears only `DeliverySupplierId`. Not confirmed whether both are actually needed by different
  callers or whether this is incidental duplication.

## Key Fields
| Field | Meaning | Constraints |
|-------|---------|-------------|
| `Id` (→ `DeliveryManId`) | Primary key | `TA_DeliveryMen` table |
| `PhoneNumber`/`UserName` | Identity — kept in sync (Rule 2) | max 50 chars; indexed, **not unique** (Rule 2 conflict) |
| `FawryProfileId` | Payment-provider profile id | max 50 chars, **DB-unique**, randomly generated at construction |
| `CashLimit` / `ExternalDeliveryCashLimit` | Max cash held before settlement required | see Rules 3-4 |
| `IsInternalDelivery` / `IsExternalDelivery` | Which delivery modes this person handles | nullable bools; combination drives Rule 4 |
| `MandatoryDailyDepositPercentage` | % of over-limit cash due as deposit | decimal |
| `InsuranceLimit` / `PaidFromInsuranceLimit` / `PaidFromAssets` | Deposit/equipment financial tracking | see Rules 5, 11 |
| `Active` / `IsAttend` / `IsDeleted` | Online status / attendance flag / soft-delete | see Rules 7-11 |
| `UpdateFromAdmin` | Marks that the last deactivation was admin-driven | drives the self-reactivation block (Rule 7) |
| `ShiftId` → `Shift` | Assigned shift | see Rules 8-9; `DeliveryMenShifts` not yet documented |
| `StatusId` → `TA_DeliveryManStatus` | Status lookup | FK, `OnDelete(Restrict)` |
| `DeliveryManRate` vs. `Rate()` | Two independent rating figures | see Rule 6 |

## Status / State
No single enum — `Active`/`IsAttend`/`IsDeleted`/`UpdateFromAdmin` combine into an implicit lifecycle:
```
Created (Active=true, IsAttend=true, IsDeleted=false)
  │
  ├── self toggles Active on/off (Rule 8-10, shift log open/close) ── blocked if UpdateFromAdmin (Rule 7)
  ├── Admin Update() sets Active=false ──► UpdateFromAdmin=true (self-reactivation now blocked)
  ├── DeActivateBySystem() ──► Active=false (system-forced, e.g. nightly close — not yet confirmed caller)
  ├── SoftDelete() ──► IsDeleted=true (balances untouched)
  ├── Dismiss(netSettlement) ──► IsDeleted=true, balances zeroed, NetSettlementAmount recorded
  └── ReHire(newLimit) ──► IsDeleted=false, balances reset, fresh InsuranceLimit
```

## Dependencies & Integrations
| Depends on / integrates | Side/Context | Via | Notes |
|--------------------------|---------------|-----|-------|
| `DeliverymanShiftLog` | Backend-Domain | 1:many (`DeliverymanShiftLogs`) | Not yet documented — next in batch; Rule 8-9 |
| `DeliveryMenShifts` (`Shift`) | Backend-Domain | FK (`ShiftId`) | Not yet documented — Rule 9 |
| `DeliverymanBreakLog` | Backend-Domain | 1:many | Not yet documented — Rule 10 |
| `DeliverymanTransaction` | Backend-Domain | 1:many | Not yet documented — cash accounting |
| `DeliverymanZone` / `DeliveryZone` | Backend-Domain | 1:many, via `Instance` factory | `DeliveryZone` not yet documented |
| `DeliverySupplier` | Backend-Domain (master) | FK | Rule 12 |
| `DeliveryManReview` | Backend-Domain | 1:many | Feeds both rating calcs (Rule 6) |
| `City` (`TA_City`) | Backend-Domain (master) | FK | Shared with `Customer.CurrentCity` |

## Change Surface
| Signal | Value | Notes |
|--------|-------|-------|
| Direct dependents (Ring 1) | 7+ | ShiftLog, Shifts, BreakLog, Transaction, Zone, Supplier, Review |
| Sides touched | 3/5 confirmed | Backend-Domain, Backend-Application (Update/financial commands), API host (`TalabatkDelivery` self-service, `AdminUi` admin edit) — Frontend not yet confirmed |
| Cross-context integrations | 2 likely | Delivery (self-service shift/break), Admin (provisioning/financial settings) — not yet confirmed pending those contexts' own passes |
| Domain events involved | 4 | `DeliveryManFinancialSettingsChangedEvent`, `ChangeActivationEvent`, `AddToShiftEvent`/`RemoveFromShiftEvent`, `BreakStartedEvent` |
| Hub? | yes | Referenced by shift, break, transaction, zone, and review entities |

## Related
- Business view: [[DeliveryMen.business|DeliveryMen]]

## Open Questions
- [ ] Whether `GetNewFinancialValues`'s "neither internal nor external" case (Rule 4) is a real,
  reachable state, and if so whether defaulting to `ExternalDeliveryCashLimit` there is intentional.
- [ ] Which callers/screens rely on `DeliveryManRate` (recent, weighted) vs. `Rate()` (lifetime,
  simple mean) — not confirmed whether this is a genuine drift risk or two intentionally distinct
  metrics (Rule 6).
- [x] ~~Whether the "geofenced clock-in" claim is accurate~~ — **Resolved 2026-08-03: yes, confirmed**,
  in `ChangeDeliveryManActivationCommand.cs` (Application layer), only on a shift's first activation —
  see [[DeliveryMan-Attendance|DeliveryMan Attendance & Shifts]]'s "Clock-in geofencing" section.
- [ ] Whether `RemoveSupplier` (internal) and `UnAssignFromSupplier` (public) are both genuinely
  needed or incidental duplication (Rule 12).
- [ ] Whether `AdminUi`/`TalabatkDelivery` frontend touches any of these fields directly (pending
  those contexts' research passes).
