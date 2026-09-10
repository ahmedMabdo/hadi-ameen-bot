---
id: 8orders/delivery/driver-cash-and-compensation/deliverybouns-technical
note_type: technical
context: Delivery
feature: Driver Cash & Compensation
entity: DeliveryBouns
entity_type: legacy-poco-root
rule_count: 10
sources:
  - path: Shared/TalabatkLogic/TalabatkModels/DeliveryBouns.cs
    sha1: 479b5f38d721
last_updated: 2026-08-23
tags: [delivery, delivery-man, financial, technical, backend-domain]
---
# DeliveryBouns — Technical

> **Layer:** Backend-Domain — proper aggregate-style entity (private constructor, `Result`-returning
> `Create`/`Update`, encapsulated tier collection).
> **Context:** Delivery.
> **Source Path:** `Shared/TalabatkLogic/TalabatkModels/DeliveryBouns.cs`   **Last Updated:** 2026-08-03

## Business Rules

### Rule 1: Creation requires a name, valid date range, and ≥1 tier
- **Source:** `DeliveryBouns.cs:79-86` (`Create`) — `name` non-blank, `startDate <= endDate`,
  `deliveryBounsTierSpecs.Count > 0` (each tier itself validated via `DeliveryBounsTier.Create`,
  not opened in this pass).

### Rule 2: Cannot update or delete a currently-active campaign
- **Source:** `DeliveryBouns.cs:115-124` (`SoftDelete`) and `:127-176` (`Update`) both call
  `IsActiveNow(nowDate)` and fail (`"You cannot Delete/update an active delivery bonus."`) if true.
  `Update` re-validates the same three creation guards (Rule 1) before checking activity — a case
  where Update and Create **do** stay in sync, unlike several other entities in this pass.

### Rule 3: ⚠️ Likely bug — overnight-window detection uses a 6-second window, not 6 hours
- **Plain language:** The logic meant to detect "is `now` in the early-morning grace period right
  after midnight, for an overnight-crossing campaign" almost certainly intended a multi-hour window
  but as written only covers 6 **seconds** past midnight.
- **Source:** `DeliveryBouns.cs:200-201` —
  ```
  TimeSpan StratOverNight = new TimeSpan(0, 0, 0);
  TimeSpan EndOverNight = new TimeSpan(0, 0, 6);
  ```
  `TimeSpan`'s 3-argument constructor is `(hours, minutes, seconds)` — so `EndOverNight` is
  `00:00:06`, six seconds after midnight, not six *hours* (`new TimeSpan(6, 0, 0)`) as the variable
  name and evident intent suggest.
- **Impact:** `IsActiveNow` (`:192-218`) uses this window only when `StartTime >= EndTime` (an
  overnight-crossing campaign, e.g. 22:00-02:00) to decide whether `now` (if between midnight and the
  window) should be treated as "still within yesterday's start" or "before today's start". With the
  window effectively always false (except in the 6-second sliver), the overnight branch will almost
  always fall to the "not in the grace window" case — meaning an overnight campaign's activity check
  is very likely wrong for most of the early-morning hours it's supposed to cover. This directly gates
  Rule 2 (can't edit/delete while active), so a campaign that should be locked (active, mid-overnight-window)
  may incorrectly appear editable, or vice versa.
- Not confirmed against a running system — flagged as a high-confidence code-reading bug, not a
  verified production incident.

### Rule 4: Bonus lookup is a simple tier-range match
- **Source:** `DeliveryBouns.cs:63-67` (`GetTierBounsValueByOrderCount`) — first tier where
  `MinimumNumberOfOrders <= orderCount <= MaximumNumberOfOrders`, `default` (0) if none match. No
  guard against overlapping tier ranges — if two tiers overlap, whichever is enumerated first wins,
  silently.

## Key Fields
| Field | Meaning |
|-------|---------|
| `CityId` / `DeliveryShiftId` | Scope — which city and which shift definition this campaign applies to |
| `StartDate`/`EndDate`, `StartTime`/`EndTime` | Date range + time-of-day window (supports overnight, see Rule 3's bug) |
| `DeliveryBounsTiers` | Order-count → bonus-value tiers |

## Related
- Business view: [[DeliveryBouns.business|DeliveryBouns]]
- [[DeliverymanTransaction.technical|DeliverymanTransaction]] — `Shift_Bouns` type
- DeliveryMenShifts (see [[DeliveryMan-Attendance|DeliveryMan Attendance & Shifts]]) — `DeliveryShiftId` FK

## Open Questions
- [ ] Whether the 6-second-vs-6-hour `TimeSpan` bug (Rule 3) has caused any real-world incorrect
  active/inactive determination — not verified against production behavior.
- [ ] Whether overlapping bonus tiers are prevented anywhere upstream (Application layer, not traced).
- [ ] `DeliveryBounsTier.Create`'s own guards weren't opened in this pass.
