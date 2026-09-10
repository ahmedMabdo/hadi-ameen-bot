---
id: 8orders/admin/city-and-geography-administration/cityrushtimeconfiguration-technical
note_type: technical
context: Admin
feature: City & Geography Administration
entity: CityRushTimeConfiguration
entity_type: legacy-poco-root
rule_count: 17
sources:
  - path: Shared/TalabatkLogic/TalabatkModels/CityRushTimeConfiguration.cs
    sha1: f757c5b8a06e
last_updated: 2026-08-23
tags: [admin, delivery, transactional, technical, backend-domain]
---
# CityRushTimeConfiguration — Technical

> **Layer:** Backend-Domain — proper aggregate-style entity (`Result`-returning factory/behavior
> methods, encapsulated child collections), confirming an earlier, previously-uncited claim that this
> class is a rush/busy-mode state machine — now verified directly with citations.
> **Context:** Admin (city-level configuration, no single natural context owner).
> **Source Path:** `Shared/TalabatkLogic/TalabatkModels/CityRushTimeConfiguration.cs`   **Last Updated:** 2026-08-03

## Business Rules

### Rule 1: Creation validates threshold ordering and requires ≥1 area priority
- **Source:** `CityRushTimeConfiguration.cs:65-81` (`Instance`) — `busyThreshold > 0`,
  `busyThreshold > reOpenThreshold` (reopen must be strictly lower — the "calm down" bar is below the
  "get busy" bar, preventing flapping at the same number), `thresholdCheckerInMunites > 0`, and at
  least one `RushTimeAreaPriority`.

### Rule 2: Core thresholds are frozen while rush mode is active
- **Plain language:** You can toggle whether the configuration is active/inactive at any time, but
  you can't change the busy/reopen/check-interval numbers themselves until rush mode ends.
- **Source:** `CityRushTimeConfiguration.cs:114-154` (`Update`) — every threshold guard and the
  threshold field assignments are wrapped in `if (!this.RushMode)`; `Active` is set unconditionally;
  deactivating (`!active`) while currently in `RushMode` forces `DisableRushMode` as a side effect.

### Rule 3: ⚠️ Likely bug — `ForceEndRushMode`'s guard condition and error message contradict each other
- **Plain language:** The method meant to let an admin force rush mode to end has a check whose
  logic and whose own error message describe opposite situations.
- **Source:** `CityRushTimeConfiguration.cs:99-112` —
  ```
  if (this.BusyThreshold > timeOutRequestCount)
      return Result.Failure("Can not end rush mode because current timeout requests greater than busy threshold");
  ```
  The condition `BusyThreshold > timeOutRequestCount` is true when the current request count is
  **below** the threshold (i.e., load is *low*) — yet the failure message claims the block is because
  requests are "greater than" the threshold (i.e., load is *high*). Whichever is the actual intended
  business rule (blocking a force-end while load is still high is the intuitive one for a "force end"
  override), at least one of the condition or the message is wrong; as written, the method **blocks**
  force-ending exactly when load is low and calm, and **allows** it exactly when load is still high —
  the opposite of what "force end rush mode" should intuitively gate on. Not verified against a
  running system or the original requirement — flagged as high-confidence from reading the code, not
  a confirmed production incident.

### Rule 4: Enabling/disabling rush mode is idempotent and writes a history trail
- **Source:** `EnableRushMode` (`:212-230`) — fails if `currentTimeOutRequets < BusyThreshold`;
  succeeds as a no-op if already in rush mode; otherwise flips `RushMode=true` and opens a new
  `CityRushTimeConfigHistory` row (no `EndAt` yet). `DisableRushMode` (`:284-302`) — succeeds as a
  no-op if not in rush mode; otherwise flips `RushMode=false`, closes the currently-open history row
  (`GetCurrentActiveHistory`, `:54-55` — the history with the latest `StratAt` [sic] and a null
  `EndAt`) with the ending order count, and resets **every** area priority to not-busy
  (`SetAsNotBusy`).

### Rule 5: Area-priority add/delete are blocked during rush mode; update is not
- **Source:** `AddNewRushTimeAreaPriority` (`:232-263`) and `DeleteRushTimeAreaPriority` (`:195-208`)
  both fail immediately if `this.RushMode` is true. `UpdateRushTimeAreaPriority` (`:156-193`) has no
  such guard — an existing priority's fields can be changed mid-rush. Not confirmed whether this is
  deliberate (restructuring the priority *set* is risky mid-rush, but adjusting one priority's
  existing settings is considered safe) or an oversight — flagged as an Open Question.

### Rule 6: No area may belong to two priority rankings at once
- **Source:** Both `AddNewRushTimeAreaPriority` (`:244-254`) and `UpdateRushTimeAreaPriority`
  (`:170-183`) compute the same conflict check — collect every other priority's assigned area ids,
  intersect with the incoming area ids, and fail listing the conflicting area names by name if any
  overlap. Duplicated logic, not shared via a helper — a change to one would need mirroring in the
  other (same shape as other duplicated-rule findings elsewhere in this pass).

### Rule 7: `EvaluateRushMode` only ever turns rush mode *on* — turning it off is a separate path
- **Plain language:** The main "check current load and react" entry point can start rush mode but
  never stops it — stopping requires a separate, explicit call.
- **Source:** `EvaluateRushMode` (`:268-281`) — computes `shouldOpenRushTime`, calls `EnableRushMode`
  if warranted, then always calls `MangeAreaPriorities` (updates each area's busy flag based on
  current load via `RushTimeAreaPriority.ChangeBusyAccordingToRequestCount`, not opened in this pass).
  It never calls `DisableRushMode`. The lower-threshold check for whether it's safe to end rush mode
  (`CanEndRushMode`, `:51-52` — `currentTimeoutRequests <= ReopenBelow`) is a separate public helper,
  implying the Application-layer caller runs `EvaluateRushMode` and `CanEndRushMode`/`DisableRushMode`
  as distinct steps rather than one unified evaluation — not confirmed against the actual caller
  (not traced in this pass).

## Key Fields
| Field | Meaning |
|-------|---------|
| `BusyThreshold` / `ReopenBelow` | Enter/exit thresholds — `ReopenBelow < BusyThreshold` enforced at creation (Rule 1) |
| `RushMode` | Current state |
| `Active` | Whether this configuration is in effect at all |
| `RushTimeAreaPriorities` | Ordered per-area busy-priority rules |
| `Histories` (`CityRushTimeConfigHistory`) | Append-only log of rush-mode periods (start/end/order count) |

## Dependencies & Integrations
| Depends on / integrates | Side/Context | Via | Notes |
|--------------------------|---------------|-----|-------|
| `City` | Backend-Domain (master) | FK (`CityId`) | |
| `RushTimeAreaPriority` | Backend-Domain | Owned child collection | Not opened in full in this pass |
| `CityRushTimeConfigHistory` | Backend-Domain | Owned child collection | Append-only audit trail (Rule 4) |
| `Area` | Backend-Domain (master) | Referenced by `RushTimeAreaPriority` | [[Area-and-Country\|Area]] |

## Change Surface
| Signal | Value | Notes |
|--------|-------|-------|
| Direct dependents (Ring 1) | 3 | RushTimeAreaPriority, CityRushTimeConfigHistory, City |
| Sides touched | 2/5 confirmed | Backend-Domain, Backend-Application (the polling caller of `EvaluateRushMode` not traced) |
| Cross-context integrations | 0 confirmed | Likely affects Delivery's assignment strategies indirectly (busy areas), not traced |
| Domain events involved | 0 | No events raised from this class itself |
| Hub? | no, but operationally significant | Gates delivery-assignment behavior during high load |

## Related
- Business view: [[CityRushTimeConfiguration.business|CityRushTimeConfiguration]]
- [[City.technical|City]]

## Open Questions
- [ ] `ForceEndRushMode`'s condition/message mismatch (Rule 3) — not verified against production;
  worth a direct question to the team about intended behavior.
- [ ] Whether `UpdateRushTimeAreaPriority` being allowed mid-rush (unlike add/delete) is deliberate
  (Rule 5).
- [ ] What calls `EvaluateRushMode` and how it's paired with the separate `CanEndRushMode`/
  `DisableRushMode` off-ramp (Rule 7) — not traced to the Application layer or a Hangfire job.
- [ ] `RushTimeAreaPriority.ChangeBusyAccordingToRequestCount`'s own logic wasn't opened.
