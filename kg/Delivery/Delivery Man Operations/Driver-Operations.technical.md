---
id: 8orders/delivery/delivery-man-operations/driver-operations-technical
note_type: technical
context: Delivery
feature: Delivery Man Operations
group: Driver-Operations
covers: [DeliveryManAdminChat, DeliveryManAdminChatMessage, DeliveryManDaily, DeliveryManLowRateReasons, DeliveryManOfflineLog, DeliveryManPayments, DeliveryManPrice, DeliveryManReview, DeliveryManReviewMap, DeliverymanShiftLog, DeliveryManStates, DeliveryManWorkingHours, DeliveryMenAttendance, DeliveryMenLocations, DeliveryMenMoneyRequest, DeliveryMenShifts, DeliverymanBreakLog, DeliverymanZone, DriverDismissalLog, ShiftLocation, WorkUsDelivery, WorkUsDeliveryHistory, WorkUsDeliveryStatus, WorkUsRestaurant, WorkUsRestaurantComment, DeliveryManNotificationDetail]
sources:
  - path: Shared/TalabatkLogic/TalabatkModels/DeliveryManAdminChat.cs
    sha1: 42f75fffddb5
  - path: Shared/TalabatkLogic/TalabatkModels/DeliveryManAdminChatMessage.cs
    sha1: 5d0e848f0236
  - path: Shared/TalabatkLogic/TalabatkModels/DeliveryManDaily.cs
    sha1: a1ed83526c67
  - path: Shared/TalabatkLogic/TalabatkModels/DeliveryManLowRateReasons.cs
    sha1: d690b5a066d6
  - path: Shared/TalabatkLogic/TalabatkModels/DeliveryManPayments.cs
    sha1: ceaf3052e13d
  - path: Shared/TalabatkLogic/TalabatkModels/DeliveryManPrice.cs
    sha1: 4c7143355396
  - path: Shared/TalabatkLogic/TalabatkModels/DeliveryManStates.cs
    sha1: 09126f1b7d46
  - path: Shared/TalabatkLogic/TalabatkModels/DeliveryMenMoneyRequest.cs
    sha1: 6392e6d597f9
  - path: Shared/TalabatkLogic/TalabatkModels/DeliverymanZone.cs
    sha1: 9695a4f9a823
  - path: Shared/TalabatkLogic/TalabatkModels/DriverDismissalLog.cs
    sha1: c48eeae56ac3
  - path: Shared/TalabatkLogic/TalabatkModels/ShiftLocation.cs
    sha1: ae31599605a1
  - path: Shared/TalabatkLogic/TalabatkModels/WorkUsDelivery.cs
    sha1: c722840f48a6
  - path: Shared/TalabatkLogic/TalabatkModels/WorkUsDeliveryHistory.cs
    sha1: 4f20c7bdcd3b
  - path: Shared/TalabatkLogic/TalabatkModels/WorkUsDeliveryStatus.cs
    sha1: 07217093ba8a
  - path: Shared/TalabatkLogic/TalabatkModels/WorkUsRestaurant.cs
    sha1: 14a54b464afa
  - path: Shared/TalabatkLogic/TalabatkModels/WorkUsRestaurantComment.cs
    sha1: 955a311251ce
  - path: Shared/TalabatkLogic/DeliveryManNotificationAggregate/DeliveryManNotificationDetail.cs
    sha1: 7377f391bd82
  - path: Shared/TalabatkApplication/Commands/AddDeliveryManLocationCommand/AddDeliveryManLocationCommand.cs
    sha1: 992c91417d4e
  - path: Shared/TalabatkApplication/Commands/AddDeliveryManLocationCommand/AddDeliveryManLocationCommand_V1.cs
    sha1: 6b6fe74b43d1
  - path: Shared/TalabatkApplication/Commands/ChangeDeliveryManActivationCommand.cs
    sha1: 50997f8b8f8c
  - path: Shared/TalabatkApplication/Helper/DeliveryManRatingCalculator.cs
    sha1: e67c20c5b909
  - path: Shared/TalabatkApplication/Queries/GetBreakOptionsQuery/GetBreakOptionsQuery.cs
    sha1: c193be80cc33
  - path: Shared/TalabatkApplication/Services/BreakCleanupService.cs
    sha1: d2c389f559a6
  - path: Shared/TalabatkLogic/TalabatkModels/DeliveryMen.cs
    sha1: e592516c13f2
  - path: Talabatk.IDS/Application/Commands/AddDeliveryManAttendanceCommand/AddDeliveryManAttendanceCommand.cs
    sha1: a0673826fb16
  - path: Talabatk.IDS/Application/Commands/AddOperationAttendanceCommand/AddOperationAttendanceCommand.cs
    sha1: c7216804a249
  - path: Talabatk.IDS/Application/Commands/AssigneOrderToDeliveryManTasksDistributionCommand/AssigneOrderToDeliveryManTasksDistributionCommand.cs
    sha1: 37f8b92a0bf9
  - path: Talabatk.IDS/Application/Commands/CheckLateOrderCommand/CheckLateOrderCommand.cs
    sha1: a81253096ae2
  - path: Talabatk.IDS/Controllers/Account/AccountController.cs
    sha1: 9c1caf8ae094
  - path: Talabatk.IDS/CustomerResourceOwnerValidator.cs
    sha1: 949797e366d7
  - path: Talabatk.IDS/Helper/HangFire/CalculateDeliveryManCurrentRatingJob.cs
    sha1: 7e8148a3b98c
  - path: Talabatk.IDS/Helper/HangFire/CalculateDeliveryManWorkingHoursJob.cs
    sha1: 0f2502adb5af
  - path: Talabatk.IDS/Startup.cs
    sha1: 32fc90149757
  - path: TalabatkDelivery/Controllers/Apis/DeliveryManMaps/DeliveryManMapsController.cs
    sha1: 4a323bfac4f7
  - path: TalabatkDelivery/Startup.cs
    sha1: 9c87b1495b33
last_updated: 2026-08-23
tags: [flow, technical]
---
# Driver Operations — A Delivery Man's Working Day — Technical

Bridges: [[DeliveryMen.technical|DeliveryMen]] (entity rules 6-10 —
activation, break, shift-log semantics — cited, not restated), [[DeliveryMan-Attendance|DeliveryMan
Attendance & Shifts]] (field reference for `DeliveryMenShifts`/`DeliverymanShiftLog`/
`DeliverymanBreakLog`), [[Driver-Cash-Cycle.technical|Driver Cash and Settlement Cycle]] and
[[Delivery-Fee-and-Assignment.technical|Delivery Fee Calculation & Driver Assignment]] (cash and
assignment mechanics — not re-derived). This note is the connective tissue across one working day.

## Trigger

No single "start shift" event — each stage below has its own trigger, noted inline.

## Step-by-step

### 1. Login → attendance attempt (delivery man)
OAuth password-grant login for client `deliverymobile` unconditionally calls the attendance command
before returning tokens — `Talabatk.IDS/CustomerResourceOwnerValidator.cs:456` (password grant only;
a refreshed session does not re-trigger). `AddDeliveryManAttendanceCommandHandler.Handle`
(`Talabatk.IDS/Application/Commands/AddDeliveryManAttendanceCommand/
AddDeliveryManAttendanceCommand.cs:30-48`) loads the driver's `DeliveryMenShifts` row and, if
`shift.StartTime.Hour <= now.Hour && shift.EndTime.Hour > now.Hour` (`:41`) and no attendance row
exists today, inserts one; always returns `Success = true` regardless. **#430**: for any shift
crossing midnight the comparison is unsatisfiable — no `DeliveryMenAttendance` row is ever written
for a night-shift driver, and the caller still sees success.

### 2. Login → attendance attempt (operations staff, sibling path)
`Talabatk.IDS/Controllers/Account/AccountController.cs:156` calls `AddOperationAttendanceCommand`
(`Talabatk.IDS/Application/Commands/AddOperationAttendanceCommand/
AddOperationAttendanceCommand.cs:30-69`), same hour-only comparison at `:53` against
`AspNetUserShift.FromTime`/`ToTime` (plain `int` hours, no wraparound —
`Shared/TalabatkLogic/TalabatkModels/AspNetUserShift.cs:14-17,36-50`). **#432**: same unsatisfiable-
window defect against the *staff* shift model, systemic across six sites including **task
distribution** (`AssigneOrderToDeliveryManTasksDistributionCommand.cs:52-54`) and **late-order
escalation** (`CheckLateOrderCommand.cs:72-74`) — relevant to step 5 even though the entity checked
is staff, not the driver.

### 3. Going online / activation
Trigger: driver toggles availability → `ChangeDeliveryManActivationCommand.Handle`
(`Shared/TalabatkApplication/Commands/ChangeDeliveryManActivationCommand.cs:44-91`). No-ops if
requested state equals current (`:54-57`). **Activating only:** rejects if any non-`Rejected`/
non-`Delivered` order exists today (`:114-130`); if the shift has ≥1 `StartPointsLocations` and no
`DeliverymanShiftLog` already open this window (`:264-270`), runs a **geofence check** —
`ValidateShiftStartLocationAsync` (`:272-289`) requires a recent `DeliveryMenLocations` ping within
`Configuration.DeliveryManShiftStartDistanceTolerance` of any configured start point (`:299-329`);
rejects outright if the shift window already ended (`:242-245`). The window arithmetic here,
`DeliveryManShiftStartEnd` (`:330-344`), **correctly** rolls `shiftEnd` to the next day when
`shiftEnd <= shiftStart` — a correct midnight implementation, unlike steps 1-2 and 4.
`ValidateActivationAsync` (`:143-156`) calls `DeliveryMen.CanActivate(now, tolerance, isActive)`
(`Shared/TalabatkLogic/TalabatkModels/DeliveryMen.cs:582-614`), which also **correctly** branches on
`crossesMidnight` (`:591`). **Deactivating** first auto-closes any open break (`:158-175`).
`ChangeActivationAsync` (`:187-200`) → `ChangeActivationByDeliveryman` (`DeliveryMen.cs:514-528`) —
blocked if admin-deactivated (`UpdateFromAdmin && !Active`); else opens/closes a
`DeliverymanShiftLog` (`AddDeliveryManShiftLog`, `:538-557`) and raises `ChangeActivationEvent`
(`:648-652`), feeding assignment/zone-matching (bridge, not re-derived).

### 4. Location ping / GPS heartbeat
Trigger: recurring client POST to `AddDeliveryManLocation`/`_V1`
(`TalabatkDelivery/Controllers/Apis/DeliveryManMaps/DeliveryManMapsController.cs:26-45`; interval
client-controlled, not traced). **V0** (`AddDeliveryManLocationCommand.cs:30-69`) no-ops unless
`Active` (`:35-40`), else upserts one `DeliveryMenLocations` row. **V1**
(`AddDeliveryManLocationCommand_V1.cs:43-126`) additionally mirrors the location into a Redis hash
(`ForceAssignDeliverymenService.UpdateDeliverymanHashField`, `:74-75`) and returns any pending
`AutoAssignRequest` for the driver still within `Configuration.AutoAssignTimeInSeconds` (`:84-123`)
— **this ping doubles as a task-distribution poll**, see [[Delivery-Fee-and-Assignment.technical|
assignment note]] §D for what populates `AutoAssignRequests`. `HandleDeliveryOfflineLogs`
(`:128-210`) logs an "offline gap" to `DeliveryManOfflineLog` when the gap since the last ping
exceeds `Configuration.OfflineTimeInSeconds`, but only if the *previous* ping falls inside today's
shift window (`:166-184`). **#393**: that window stamps both bounds onto today's date with no
midnight rollover, so for an overnight shift the guard is a tautology and **no offline gap is ever
logged** for a night-shift driver — same root-cause family as #430/#432 (#416), different symptom
(silence vs. false success).

### 5. Task / order distribution eligibility
Not re-derived — see [[Delivery-Fee-and-Assignment.technical|Delivery Fee Calculation & Driver
Assignment]] for zone auto-assign, manual broadcast, self-assign, admin assign. This flow only
establishes the gate: `Active` (step 3) plus a location ping (step 4, for V1's polling path). The
staff-facing distribution path sharing step 2's broken shift check
(`AssigneOrderToDeliveryManTasksDistributionCommand.cs:52-54`, **#432**) skips out-of-window
dispatchers regardless of the driver's own state.

### 6. Break request
Trigger: `StartBreakCommand.Handle` (`Shared/TalabatkApplication/Commands/StartBreakCommand/
StartBreakCommand.cs:54-94`) with a `BreakType` and duration. Requires `Active == true` (`:107-110`);
no active orders (Redis `HasOrders`, skipped for `Accident`, `:133-147`); no already-open break
(`:149-157`); `Shift != null && Shift.IsActive` (`:159-166` — admin on/off flag, not a time-window
check). Duration validated against `CityBreakConfiguration.GetAvailableDurations()` (default
`{15,30,45,60}`, `:179-212`). Non-Accident breaks are further capped by
`CityBreakConfiguration.RestBreakMaxPercentage` — max share of the shift simultaneously
offline-or-on-break (`:214-244`). `DeliveryMen.StartBreak(...)` (`DeliveryMen.cs:682-721`): blocked
by the same `UpdateFromAdmin` guard; sets `Active = false` and raises `ChangeActivationEvent`
(`:689-691` — drops off the assignment pool exactly like going offline); raises `BreakStartedEvent`
for notification scheduling (handler not traced); creates a `DeliverymanBreakLog` row only if
`ShiftId.HasValue` (`:705-720` — otherwise "succeeds" with a `null` log, though `StartBreakCommand`
already requires a shift, so likely unreachable).

### 7. Break auto-timeout
Trigger: Hangfire `AutoEndBreakJob.CheckAndAutoEndBreaks`, `Cron.Minutely`
(`TalabatkDelivery/Startup.cs:152-156`). `Shared/TalabatkApplication/Helper/HangFire/
AutoEndBreakJob.cs:36-105` loads every `DeliverymanBreakLog` with `BreakTo == null &&
SelectedDurationMinutes > 0`, and for each where elapsed time ≥ selected duration, calls
`IBreakCleanupService.EndBreakAsync`.

### 8. Break return (manual or auto)
Manual: `EndBreakCommand.Handle` (`Shared/TalabatkApplication/Commands/EndBreakCommand/
EndBreakCommand.cs:41-53`) → `BreakCleanupService.EndBreakAsync`
(`Shared/TalabatkApplication/Services/BreakCleanupService.cs:28-94`): closes the open
`DeliverymanBreakLog` (`SetBreakTo`, computing `ActualDurationMinutes`), then — only if not already
`Active` — calls `DeliveryMen.ActivateAfterBreak()` (`DeliveryMen.cs:727-737`), which sets
`Active = true` and raises `ChangeActivationEvent` **without** touching `DeliverymanShiftLogs`
(deliberately separate from the online/offline path). `GetBreakOptionsQuery.Handle`
(`Shared/TalabatkApplication/Queries/GetBreakOptionsQuery/GetBreakOptionsQuery.cs:44-101`) is what
the app calls to list break/end-shift options, and only offers "End Shift" if
`DeliveryMen.IsWithinShift(now)` (`:93-98`) — `IsWithinShift` (`DeliveryMen.cs:616-630`)
**correctly** branches on `crossesMidnight`, a second correct overnight implementation. But
`BuildEndShiftOption` → `CalculateShiftEndTime` (`:157-193`) **unconditionally** adds a day whenever
`EndTime <= StartTime`, without checking whether `now` is already past midnight — **#416(b)**: a
driver checking at 02:00 on a 22:00→06:00 shift is told ~1690 minutes remain instead of ~240.

### 9. Shift end — driver self-service
Same command as step 3 with `IsActive = false`: blocks on an in-progress order, auto-closes any open
break, then `ChangeActivationByDeliveryman(false, ...)` closes the open `DeliverymanShiftLog`
(`AddDeliveryManShiftLog`, `DeliveryMen.cs:544-557`) and raises `ChangeActivationEvent`.

### 10. Shift end — system-forced, once daily, no per-shift exception
Trigger: Hangfire `OfflineAllDeliveryMenJob.OfflineDeliveryMen`, registered at the same cron as
step 11 (`Talabatk.IDS/Startup.cs:443-447`, `CronExpressionAt4AM` = config key
`DeliveryManHours:CronExpression`). `Talabatk.IDS/Helper/HangFire/
OfflineAllDeliveryMenJob.cs:28-57` loads **every** `Active && !IsDeleted` `DeliveryMen` row (no
shift filter) and calls `DeActivateBySystem(now)` on each in parallel — sets `Active = false`,
closes the open shift log, raises `ChangeActivationEvent` (`DeliveryMen.cs:530-535`). **Observation
(not a numbered register finding, but directly on this flow's night-shift theme):** this job has no
per-driver shift-window check at all — any driver whose shift is scheduled past the cutoff hour is
logged off by the system mid-shift, independent of and in addition to #430. A parallel job,
`OfflineUserAvilableJob.OfflineUserAtThreeAMJob` (`Talabatk.IDS/Helper/HangFire/
OfflineUserAvilableJob.cs:25-52`, `Talabatk.IDS/Startup.cs:364-367`, `CronExpressionAt3AM`), does the
same blanket force-offline for a separate operations-staff availability model (`AspNetUser.
IsAvailable`, `UserShifts`/`ShiftDetails.OfflineTo`) — glimpsed, not traced further.

### 11. Daily shift-log closure and working-hours tally
Trigger: Hangfire `CalculateDeliveryManWorkingHoursJob.CalculateDeliveryManWorkingHours`, same
`CronExpressionAt4AM` (`Talabatk.IDS/Startup.cs:371-375`). `CloseDeliverymanShiftLogs`
(`Talabatk.IDS/Helper/HangFire/CalculateDeliveryManWorkingHoursJob.cs:113-186`) runs first,
force-closing any still-open `DeliverymanShiftLog` by reconstructing an end time from the shift's
configured `EndTime`, branching on whether `EndTime.Hour >= 12` (`:140-179`) — this resolves
[[DeliveryMan-Attendance|DeliveryMan-Attendance.md]]'s open question about the nightly force-close
job; the `>= 12` branch split's correctness was not independently verified for every configuration.
`CalculateDeliveryManWorkingHours` (`:31-110`) then sums each driver's closed shift-log spans
(clipped to the configured working-day window) into one `DeliveryManWorkingHours` row per driver
(`:88-105`), plus a `0`-hour row for any driver with no logs that day (`:93-103`) — resolving that
doc's "0-hour rows for absentees" half too.

### 12. Weekly rating recalculation
Trigger: Hangfire `CalculateDeliveryManCurrentRatingJob.CalculateAndUpdateCurrentRating`, cron
`DeliveryManCurrentRating:CronExpression` (`Talabatk.IDS/Startup.cs:463-469`, comment: Friday 6AM).
`Talabatk.IDS/Helper/HangFire/CalculateDeliveryManCurrentRatingJob.cs:45-259` batch-loads, for the
previous Friday-to-Thursday week: `DeliveryManWorkingHours` (step 11), completed `OrderDeliveries`
(delivered count), `DeliveryManReview` (customer rating), `OrderRestaurantDetails` (arrival times),
and a per-driver acceptance rate from `DeliveryManAcceptanceRateCalculator.CalculateAcceptanceRate`
(`Shared/TalabatkApplication/Helper/DeliveryManAcceptanceRateCalculator/
DeliveryManAcceptanceRateCalculator.cs:25-69` — `AcceptedOrders / AssignedOrders` over
`AutoAssignRequests`). `DeliveryManRatingCalculator.CalculateRatingForPeriod`
(`Shared/TalabatkApplication/Helper/DeliveryManRatingCalculator.cs:29-155`) combines six weighted
components — customer rating, working-hours ratio, delivered-orders ratio, acceptance rate,
restaurant/customer on-time-arrival ratios — each `(component + ConstantOfNonZeroRate) * cityWeight`,
summed, scaled by `rateMultiplier`, capped at `rateMultiplier` (`:123-132`); written via
`UpdateCurrentRating(rating)` (`CalculateDeliveryManCurrentRatingJob.cs:224`). This is a **third**
rating figure alongside the two in [[DeliveryMen.technical|
DeliveryMen]] Rule 6 (`Rate()` lifetime mean, 3-month weighted figure) — which surfaces where in the
app was not re-verified here.

## Data written

In driver-day order: `DeliveryMenAttendance` (1, night-shift gap per #430) → `DeliverymanShiftLog`
open (3) → `DeliveryMenLocations` + Redis location hash fields (4) → `DeliveryManOfflineLog` (4,
silently skipped for night shifts per #393) → `AutoAssignRequest.ExpirationDate` (4/5) →
`DeliverymanBreakLog` open (6) → `DeliverymanBreakLog.BreakTo`/`ActualDurationMinutes` closed (7-8) →
`DeliverymanShiftLog` closed, by the driver (9) or forcibly (10-11) → `DeliveryManWorkingHours` (11)
→ `DeliveryMen.CurrentRating` (12). `DeliveryMen.Active` flips repeatedly throughout (3, 6, 8, 9, 10).

## External calls

- **Redis** via `ForceAssignDeliverymenService`/`IDeliverymenCache`: hash fields `LastLocationDate`,
  `LastLocation`, `LastAssigningDate`, `LastAssigningRequest`, `HasOrders` — steps 4 and 6.
- **Hangfire** (SQL-backed recurring scheduler, out-of-request-cycle): steps 7, 10, 11, 12.
- No third-party HTTP/push call traced; `BreakStartedEvent`/`BreakEndedEvent` notification delivery
  is outside this note's read set (see Open Questions).

## Failure modes

- **#430** — Night-shift delivery-man login never records attendance; reports success regardless.
  Step 1, `AddDeliveryManAttendanceCommand.cs:41`.
- **#432** — Same defect against the operations-staff shift model; breaks staff attendance plus five
  downstream consumers including delivery-man task distribution and late-order escalation. Steps 2
  and 5, `AddOperationAttendanceCommand.cs:53` and siblings.
- **#393** — Night-shift location pings never trigger an offline-gap log (tautological guard). Step
  4, `AddDeliveryManLocationCommand_V1.cs:166-184`.
- **#416(b)** — Break-options screen overstates remaining shift time by up to ~24 hours after
  midnight on a night shift. Step 8, `GetBreakOptionsQuery.cs:177-193`.
- **#412** — Driver GPS location and shift hours readable with no authentication, by sequential id
  (`GetDeliveryMenLogsQuery.cs:14,24,26`, `DeliveryManController.cs:1149-1157`,
  `[AllowAnonymous]`) — a standing exposure of the same data written in step 4.
- **Unlogged observation** — the daily blanket force-offline (step 10) has no per-driver shift-window
  check, so a shift still running at the cutoff hour is cut short by the system itself, independent
  of #430.
- **Contrast, not itself a defect**: three call sites in this flow (`CanActivate`, `IsWithinShift`,
  `DeliveryManShiftStartEnd`) implement midnight-crossing math **correctly**, alongside the four+
  that don't (#430, #432, #393, #416b) — evidence the gap is a missing shared helper, not
  unfamiliarity with the problem (per #416's framing).

## Folded entities — the 17 satellites documented here

Everything the driver day touches that is not `DeliveryMen` itself. Grouped by what they are for.

### Driver support chat

| Entity | What it is | Rules |
|---|---|---|
| `DeliveryManAdminChat` | A driver↔support conversation, with tokens, online flags, timings and a rating | Fourteen mutators and **not one guard**: `Instance` (`Shared/TalabatkLogic/TalabatkModels/DeliveryManAdminChat.cs:56`), `AddNewMessage` (`:70`), the two online-flag setters (`:103`, `:108`), the two token setters (`:113`, `:118`), `EndChat` (`:123`), `SetExpirationDate` (`:131`), the two view-timestamp setters (`:136`, `:141`), `AssignAdmin` (`:146`), `SetFirstResponseAfter` (`:151`), `SetTotalChatTime` (`:156`) and `SetRate` (`:161`). So a chat can be ended twice, rated before it starts, or reassigned after closing. The KPI fields — `FirstResponseAfter`, `TotalChatTime` — are set by callers, not computed here |
| `DeliveryManAdminChatMessage` | One message in that conversation | The **child validates and the parent does not**: `Instance` requires message text (`Shared/TalabatkLogic/TalabatkModels/DeliveryManAdminChatMessage.cs:44`) and a session id (`:49`). Carries `SenderName` and `SenderPhoneNumber` denormalised onto the row — the fields the unauthenticated Centrifugo proxy can overwrite (🔴 `_conflicts.md` #616). `MarkAsRead` (`:71`) is unguarded |

### Money the driver handles

| Entity | What it is | Rules |
|---|---|---|
| `DeliveryManDaily` | A day's cash received from a driver, tied to an AccFlex treasury day | `Instance` only, **no validation** on an amount field (`Shared/TalabatkLogic/TalabatkModels/DeliveryManDaily.cs:20`). `AccFlexTreasuryDailyId` and `TreasuryDailyGuid` are the ERP handles — see `_integrations.md` |
| `DeliveryMenMoneyRequest` | One driver handing cash to another for an order | `Instance` (`Shared/TalabatkLogic/TalabatkModels/DeliveryMenMoneyRequest.cs:21`) plus two unguarded flag setters, `UpdateIsMoneySent` (`:42`) and `UpdateIsMoneyReceivedConfirmed` (`:46`). Nothing enforces that the sender and receiver differ, that the amount is positive, or that "received" cannot precede "sent" |
| `DeliveryManPayments` | A payment run against a driver | Private ctor, `Instance` only, and just three fields — two dates and an id (`Shared/TalabatkLogic/TalabatkModels/DeliveryManPayments.cs:16`). The amounts live elsewhere |
| `DeliveryManPrice` | The commission band for a city: a rate range and its percentage | `Instance` (`Shared/TalabatkLogic/TalabatkModels/DeliveryManPrice.cs:21`) and a `void Update` (`:65`), **neither validating**. So `FromRate` may exceed `ToRate`, `Percentage` may be negative or above 100, and bands for one city may overlap or leave gaps — nothing checks. This is the table that decides what a driver earns |

### Zones, shifts and lifecycle

| Entity | What it is | Rules |
|---|---|---|
| `DeliverymanZone` | Which delivery zones a driver works | Three fields, `Instance` only, no rules (`Shared/TalabatkLogic/TalabatkModels/DeliverymanZone.cs:12`) |
| `ShiftLocation` | A geographic point attached to a shift | Four fields, `Instance` only (`Shared/TalabatkLogic/TalabatkModels/ShiftLocation.cs:12`) |
| `DriverDismissalLog` | The settlement record when a driver is dismissed or re-hired | Private ctor with two named factories — `CreateDismissalLog` (`Shared/TalabatkLogic/TalabatkModels/DriverDismissalLog.cs:38`) and `CreateReHireLog` (`:66`) — and no guards. Captures the deposit collected, equipment still out, statement balance and net settlement at the moment of dismissal, plus a `Status` and `FailureReason`, so a failed settlement is recorded rather than lost |
| `DeliveryManStates` | The driver-status lookup table | Two properties, no methods (`Shared/TalabatkLogic/TalabatkModels/DeliveryManStates.cs`). Behaviour comes from the `DeliveryManStatus` enum, not this table |
| `DeliveryManLowRateReasons` | Why a driver received a low rating | `Instance` only, no rules (`Shared/TalabatkLogic/TalabatkModels/DeliveryManLowRateReasons.cs:17`). Denormalises `ReasonName` alongside `ReasonId`, so a renamed reason does not rewrite history |
| `DeliveryManNotificationDetail` | One driver's copy of a broadcast notification | The **only entity in this group that guards state transitions**: `MarkNotificationAsRead` refuses a deleted notification (`Shared/TalabatkLogic/DeliveryManNotificationAggregate/DeliveryManNotificationDetail.cs:31`) and `SoftDelete` refuses a second delete (`:40`). Both return `Result`. `MarkAsSent` (`:46`) is unguarded. It belongs to the `DeliveryManNotification` aggregate, which is one of the four real DDD aggregates in the codebase — and it shows |

### Recruitment — "work with us"

| Entity | What it is | Rules |
|---|---|---|
| `WorkUsDelivery` | A driver recruitment lead | `Instance` (`Shared/TalabatkLogic/TalabatkModels/WorkUsDelivery.cs:27`), `ChangeStatus` (`:39`) and `AddComment` (`:54`) — no guards, including none on the mobile number a recruiter will call |
| `WorkUsDeliveryHistory` | One status change on that lead, with a comment and a change type | `Instance` only (`Shared/TalabatkLogic/TalabatkModels/WorkUsDeliveryHistory.cs:30`). This is the audit trail for recruitment |
| `WorkUsDeliveryStatus` | The configurable status list for driver leads, with a colour and display order | `Instance` (`Shared/TalabatkLogic/TalabatkModels/WorkUsDeliveryStatus.cs:23`), `Update` (`:37`), `Deactivate`/`Activate` (`:45`, `:50`) — all `void`, none validating. Unlike `DeliveryManStates` this is a genuinely admin-editable status list, not an enum mirror |
| `WorkUsRestaurant` | A merchant recruitment lead, with its Bitrix CRM lead status | `Instance` (`Shared/TalabatkLogic/TalabatkModels/WorkUsRestaurant.cs:24`), `SetBitirixLeadStatus` (`:36`) and `AddComment` (`:41`), none validating. `BitirixLeadStatusId` is the CRM handle — note the spelling, which is the real one |
| `WorkUsRestaurantComment` | A comment on a merchant lead | **The one entity in this whole group that enforces authorisation, and it does it in the domain.** `CanModify` compares `CreatedBy` to the caller (`Shared/TalabatkLogic/TalabatkModels/WorkUsRestaurantComment.cs:39-42`); `Update` throws `InvalidOperationException` for someone else's comment (`:48`), rejects an empty comment (`:51`) and enforces a 250-character limit (`:54`); `EnsureCanDelete` throws the same way (`:60-63`). It is also the only one that **throws** rather than returning `Result` — so callers must catch, and a missed catch surfaces as a 500 rather than a validation message |

### What the split means

Fifteen of these seventeen have no validation at all, including every entity that carries money —
`DeliveryManDaily`, `DeliveryMenMoneyRequest` and `DeliveryManPrice`, the last of which decides driver
commission and cannot even reject an inverted rate band. The two exceptions are instructive and point in
opposite directions: `DeliveryManNotificationDetail` guards its transitions and returns `Result`, because
it belongs to a real aggregate; `WorkUsRestaurantComment` guards authorship and **throws**. The
codebase therefore contains a domain-layer ownership check — the very thing whose absence produces the
IDOR family (#227, #350, #364, #400) — on a recruitment comment, and nowhere near the driver's money.

## Open Questions

- [ ] `DeliveryManPrice` cannot reject `FromRate > ToRate`, a negative percentage, or overlapping bands
      for one city. Are those enforced anywhere upstream, or only by the admin screen?
- [ ] `DeliveryMenMoneyRequest` lets "received" be confirmed without "sent". Is the ordering enforced in
      the handler?
- [ ] `DeliveryManAdminChat` computes nothing: `FirstResponseAfter` and `TotalChatTime` are set by
      callers. Which caller, and does it run on every path that ends a chat?
- [ ] `WorkUsRestaurantComment` throws while the rest of the domain returns `Result`. Do its callers
      catch, or does an edit attempt on someone else's comment return a 500?
- Location-ping interval is client-side; not traced.
- `BreakStartedEvent`/`BreakEndedEvent` notification delivery (push service, the `ScheduledJobId`
  Hangfire job behind break-ending reminders) — not traced, carried over from
  [[DeliveryMan-Attendance|DeliveryMan-Attendance.md]].
- `CloseDeliverymanShiftLogs`' `EndTime.Hour >= 12` date-placement branch (step 11) was not
  independently verified for every shift configuration — flagged as untraced, not asserted broken.
- Whether the location-ping poll (step 4, V1) is the sole channel for learning of a new auto-assigned
  order, or a push channel also exists — unresolved; the assignment note doesn't say either.
- Which of the three rating figures (`Rate()`, 3-month weighted, weekly `CurrentRating`) is
  authoritative per UI surface — inherited open question from DeliveryMen.technical.md Rule 6, not
  re-investigated.
- `OfflineUserAvilableJob`/`UserShifts`/`ShiftDetails` (step 10's sibling job) is a separate system
  from `AspNetUserShift` (steps 2/#432) and `DeliveryMenShifts` (this flow's driver model) — only
  glimpsed, not traced.
