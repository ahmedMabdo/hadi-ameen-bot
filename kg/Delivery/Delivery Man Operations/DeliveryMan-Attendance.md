---
id: 8orders/delivery/delivery-man-operations/deliveryman-attendance
note_type: single
context: Delivery
feature: Delivery Man Operations
sources:
  - path: Shared/TalabatkApplication/Commands/ChangeDeliveryManActivationCommand.cs
    sha1: 50997f8b8f8c
  - path: Shared/TalabatkLogic/TalabatkModels/DeliveryManShiftLog.cs
    sha1: caadaa7235ba
  - path: Shared/TalabatkLogic/TalabatkModels/DeliveryMenLocations.cs
    sha1: b2d325c74ccb
  - path: Shared/TalabatkLogic/TalabatkModels/DeliveryMenShifts.cs
    sha1: 981457b098db
  - path: Shared/TalabatkLogic/TalabatkModels/DeliverymanBreakLog.cs
    sha1: 58850d90ae8d
last_updated: 2026-08-23
tags: [delivery, delivery-man, child, technical, backend-domain]
---
# DeliveryMan Attendance & Shifts (DeliverymanShiftLog + DeliveryMenShifts + DeliverymanBreakLog)

Three small, thin child records — almost all the actual business rules governing them live on
[[DeliveryMen.technical|DeliveryMen]] (Rules 8-10 there), not in
these classes themselves. This note covers what each record *is*; see `DeliveryMen.technical.md` for
*when/why* they're created.

## DeliveryMenShifts
A shift **definition** (not a per-day instance) — a named time window a delivery man can be assigned
to. `Shared/TalabatkLogic/TalabatkModels/DeliveryMenShifts.cs`.

- **Fields:** `ShiftName`, `StartTime`/`EndTime` (`DateTime`, only the time-of-day portion is
  meaningful — `DeliveryMen.CanActivate`/`IsWithinShift` read `.TimeOfDay`), `IsActive`, optional
  `CityId`, `ArrangedCount` (planned headcount?), a roster (`DeliveryMen` — the assigned delivery men)
  and `StartPointsLocations` (a list of `ShiftLocation` geo-points — not read in this pass, likely the
  designated start/muster points for the shift).
- **Behavior methods** are simple property setters/collection mutators (`Update`, `ReversActivation`,
  `Activate`/`Deactivate`, `AddDeliveryMan`/`ClearDeliveryMen`, `AddLocation`/`ClearLocations`) — no
  embedded validation beyond what's shown; `Instance(...)` returns `Result<DeliveryMenShifts>` but
  has no failure path in this file (always succeeds).
- **Overnight shifts:** `StartTime > EndTime` is a valid, explicitly-handled configuration —
  `DeliveryMen.IsWithinShift`/`CanActivate` both branch on `crossesMidnight`.

## DeliverymanShiftLog
One row per online/offline session for a delivery man within a specific shift — the actual attendance
record. `Shared/TalabatkLogic/TalabatkModels/DeliveryManShiftLog.cs`.

- **Fields:** `DeliveryManId`, `DeliveryManShiftId`, `OnlineFrom` (set at creation despite the
  constructor parameter being misleadingly named `onlineTo` — `Instance(deliveryManId,
  deliveryManShiftId, onlineTo, location)` assigns `OnlineFrom = onlineTo`, `DeliveryManShiftLog.cs:26-35`;
  worth flagging as a confusing parameter name, not a functional bug since the caller,
  `DeliveryMen.AddDeliveryManShiftLog`, passes the actual "went online at" timestamp there), `OnlineTo`
  (nullable — null means still online), `StartShiftLocation` (a `Geometry` point captured at
  clock-in).
- **Open/close semantics** (who creates/closes these rows) are on `DeliveryMen`, not here — see
  DeliveryMen.technical.md Rule 8-9. This class is a pure record with a private constructor and only
  one mutator, `SetOnlineTo(...)`.
- **Open Question carried over from `DeliveryMen.technical.md`:** whether clock-in is actually
  geofenced against `StartShiftLocation` (a prior, unverified pass claimed this) — this class stores a
  location but performs no validation against it itself; the check, if it exists, would be in the
  Application-layer command handler that calls `DeliveryMen.ChangeActivationByDeliveryman` (not yet
  read).

## DeliverymanBreakLog
One row per break taken during a shift, with notification scheduling for when the break should end.
`Shared/TalabatkLogic/TalabatkModels/DeliverymanBreakLog.cs`.

- **Fields:** `BreakType` (enum), `BreakFrom`/`BreakTo`, `SelectedDurationMinutes` (what the delivery
  man picked) vs. `ActualDurationMinutes` (computed on `SetBreakTo`, rounded to the nearest minute —
  `DeliverymanBreakLog.cs:50-57`), `NotificationSent`, `ScheduledNotificationId`/`ScheduledJobId`
  (ties to a Hangfire job — not yet traced, part of the not-yet-documented `HangfireJobs` folder).
- **Domain event:** `SetBreakTo(...)` fires a `BreakEndedEvent` — but only if a scheduled job exists
  and hasn't already fired (`!string.IsNullOrWhiteSpace(ScheduledJobId) && !NotificationSent`,
  `DeliverymanBreakLog.cs:60-71`) — presumably to cancel a still-pending "break is ending soon"
  notification job when the delivery man ends the break early.

## DeliveryMenLocations (GPS ping log, related but not part of the shift/break trio above)
A single GPS ping for a delivery man at a point in time — `longitude`/`latitude`/`LocationDate`.
`Shared/TalabatkLogic/TalabatkModels/DeliveryMenLocations.cs`. No validation in `Instance`/`UpdateLocation`;
a computed `Point` property builds a `Geometry` on demand from the stored lat/long. Presumably written
on a polling interval from the delivery-man mobile app — the write frequency/caller wasn't traced.

## Related
- [[DeliveryMen.technical|DeliveryMen]] — owns all the actual
  activation/shift-window/break business rules (Rules 7-10).
- [[DeliveryMen.business|DeliveryMen (business)]]

## Clock-in geofencing — resolved (2026-08-03)
**Confirmed: yes, but only on the first activation within a shift's time window, and only in the
Application layer, not on the `DeliveryMen`/`DeliverymanShiftLog` entities themselves** — which is
why it wasn't found in the earlier entity-only pass.
- **Source:** `ChangeDeliveryManActivationCommand.cs:223-254` (`CanStartShift`) — the geofence check
  (`:272-289`, `ValidateShiftStartLocationAsync`) only runs when: activating (not deactivating), the
  shift has ≥1 configured `StartPointsLocations`, **and** there's no existing shift-log entry already
  within this shift's time window today (`:264-270`) — i.e. re-toggling active/inactive later in an
  already-started shift skips the geofence check entirely.
- The check itself (`:306-329`, `CheckIfWithinStartPoint`) requires a recent `DeliveryMenLocations`
  ping to exist (`:177-185`/`:291-297`) and tests it against **every** configured start point using
  `IDistanceCalculator.IsWithinRadius`, with a tolerance from `Configuration.DeliveryManShiftStartDistanceTolerance`
  (`:299-304`) — any one matching point passes.
- If the shift's time window has already ended, activation is rejected before the geofence check even
  runs (`:242-245`, `"موعد الشفت أنتهي"`).
- Reactivating **automatically ends any currently-open break** first (`:158-175`,
  `HandleBreakCleanupAsync` → `IBreakCleanupService.EndBreakAsync`) — a real, previously-undocumented
  cleanup rule.

## Open Questions
- [ ] What schedules/handles the `ScheduledJobId` Hangfire job behind break-ending notifications —
  part of the not-yet-documented `Shared/TalabatkLogic/HangfireJobs/` folder.
- [ ] What the nightly "force-close open shifts, write 0-hour rows for absentees" job (mentioned by an
  earlier, unverified research pass) actually is — not yet located/confirmed in this pass.
- [ ] `ShiftLocation` (the `StartPointsLocations` element type) was not opened.
