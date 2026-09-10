---
id: 8orders/admin/admin-back-office/configuration-technical
note_type: technical
context: Admin
feature: Admin Back-Office
entity: Configuration
entity_type: legacy-poco-root
covers: [Audit, BitirixLeadStatus, EntityChangeHistory, ExcutionHistory, LanGuage, SalesDaily, TaskType, Tasks, Webhook, WebhookEvent, WebhookSubscription]
rule_count: 12
sources:
  - path: Shared/TalabatkLogic/TalabatkModels/Configuration.cs
    sha1: 8cf331bb6f9f
  - path: Shared/TalabatkLogic/TalabatkModels/Audit.cs
    sha1: 06e8235eb09c
  - path: Shared/TalabatkLogic/TalabatkModels/BitirixLeadStatus.cs
    sha1: 564d6e9032f0
  - path: Shared/TalabatkLogic/TalabatkModels/EntityChangeHistory.cs
    sha1: 10333c5f47d5
  - path: Shared/TalabatkLogic/TalabatkModels/ExcutionHistory.cs
    sha1: b07fd0c862e2
  - path: Shared/TalabatkLogic/TalabatkModels/LanGuage.cs
    sha1: 0f63d47b4373
  - path: Shared/TalabatkLogic/TalabatkModels/SalesDaily.cs
    sha1: 7a4ab1246b67
  - path: Shared/TalabatkLogic/TalabatkModels/TaskType.cs
    sha1: bfee78db9d01
  - path: Shared/TalabatkLogic/TalabatkModels/Tasks.cs
    sha1: 2ddce5b1433f
  - path: Shared/TalabatkLogic/TalabatkModels/Webhook.cs
    sha1: 2f7aca8312bb
  - path: Shared/TalabatkLogic/TalabatkModels/WebhookEvent.cs
    sha1: 3121edc2683e
  - path: Shared/TalabatkLogic/TalabatkModels/WebhookSubscription.cs
    sha1: 04364361acd0
  - path: AdminUi/Controllers/Webhook/WebhookController.cs
    sha1: a029042a6a7f
last_updated: 2026-08-23
tags: [admin, config, technical, backend-domain]
---
# Configuration — Technical

> **Layer:** Backend-Domain — a single-row, system-wide settings entity (~130 fields). Not enumerated
> field-by-field here (low individual complexity per field); the value in this note is the handful of
> real embedded rules and a confirmed cross-cutting inconsistency in how it's updated.
> **Context:** Admin (system-wide config, no single owning bounded context).
> **Source Path:** `Shared/TalabatkLogic/TalabatkModels/Configuration.cs`   **Last Updated:** 2026-08-03

## Business Rules

### Rule 1: Validation is inconsistent across the ~7 grouped update methods — one validates, the rest don't
- **Plain language:** Of the several methods that update this settings row in bulk, only one
  actually checks its inputs are sane; the rest will happily accept negative times, negative amounts,
  or out-of-range percentages for settings where that clearly doesn't make sense.
- **Validates its inputs:** `UpdateDeliveryConfiguration` (`:341-394`) — 7 explicit `< 0` guards
  (out-of-zone time, manual-assign threshold, auto-assign time, offline time, rider-shift tolerance,
  box units, shift-start-distance tolerance) plus a range check on
  `ExternalDeliveryProfitPrecentage` (0-100).
- **No validation at all:** `UpdateOperationConfiguration` (`:247-312`, sets order-distribution stage
  times, compensation limits/percentage, restaurant pickup-distance range, registration bonus, and
  more), `UpdateAccountingConfiguration` (`:192-245`, sets ~20 accounting ledger account-id mappings),
  `UpdateLoyaltyPointsConfiguration` (`:314-339`, sets the entire points-earning/redemption economics),
  `UpdateReviewsConfiguration` (`:396-431`, sets every review-ranking weight/threshold). A negative
  `OrderDistributionFirstStageTime` or a negative `MinimumRoundOrderAmount`, for instance, would be
  silently accepted.
- This is a system-wide instance of the same "some paths validate, some don't" shape already seen on
  individual entities elsewhere in this pass (`DeliveryZone`, `DeliverySupplier`) — but here it's
  across the single most centrally-read configuration object in the codebase, making the blast radius
  of an admin fat-fingering a negative value into one of the unvalidated groups noticeably larger.

### Rule 2: Two independent CSV-in-a-string parsers for "list of eligible ids", one safe, one not
- **Plain language:** Two different settings store a comma-separated list of ids as a plain string
  and parse it back out on demand — one does it safely, the other would crash on bad data.
- **`Configuration.IsQuickItemReplacementEnabledForStoreType`** (`:124-135`) — splits
  `QuickItemReplacementEligibleStoreTypeIds` on `,`, uses `int.TryParse` per entry, silently skips
  anything unparseable. Safe.
- **`CityBreakConfiguration.GetAvailableDurations`** (see [[CityBreakConfiguration|CityBreakConfiguration]])
  — splits its own CSV field the same way but uses `int.Parse` (throws `FormatException` on a
  malformed entry). Unsafe.
- Both represent the same underlying pattern (a "list of numbers" setting persisted as a delimited
  string rather than a proper child table) implemented independently with diverging error-handling —
  worth a team conversation about consolidating, similar to the repo's other confirmed "same rule,
  two implementations" findings.

### Rule 3: Pickup-tag cap must be positive
- **Source:** `Configuration.cs:137-146` (`UpdatePickupTagMaxValue`) — rejects `<= 0`. Defaults to
  `1000` (`:116`). Ties directly to `OrderRestaurantDetails.PickupTag`, already documented in Customer
  Ordering — the `SKILL.md` reference materials specifically flagged "`PickupTagMaxValue` wraparound"
  as a conflict-hunting area of interest; this confirms the field and its one guard, but the
  wraparound behavior itself (what happens when the daily counter reaches this cap) lives in
  `OrderRestaurantDetails`/its Application-layer handler, not here — not re-verified in this pass.

### Rule 4: Loyalty-point redemption formula
- **Source:** `Configuration.cs:435-440` (`CalculatePointRedemptionAmount`) —
  `RedeemingPointsMoney * MinimumPointsForRedemption / RedeemingPointsNumber`. No divide-by-zero guard
  on `RedeemingPointsNumber` — if that setting were ever `0`, this throws `DivideByZeroException`
  (for `decimal`, this does throw, unlike `double`'s `Infinity`/`NaN`).

## Key Field Groups (not enumerated individually — ~130 fields, low complexity each)
| Group | Examples | Validated on update? |
|-------|----------|------------------------|
| Order distribution timing | `OrderDistributionFirstStageTime`...`LastStageTime` | ❌ (Rule 1) |
| Delivery assignment tolerances | `AutoAssignTimeInSeconds`, `RiderShiftToleranceInMinutes` | ✅ (Rule 1) |
| Accounting account-id mappings | `TotalOperationIncomeAccountId`, `CashCustomerAccountId`, ~18 more | ❌ (Rule 1) |
| Loyalty points economics | `EarningPointsNumber`/`Money`, `RedeemingPointsNumber`/`Money` | ❌ (Rule 1), see Rule 4 |
| Review ranking weights | `RankOneWeightOfReviews`, `FreshReviewWeight`, etc. | ❌ (Rule 1) |
| Pickup tag | `PickupTagMaxValue` | ✅ (Rule 3) |
| CSV-string list settings | `QuickItemReplacementEligibleStoreTypeIds` | N/A (read-side parsing, Rule 2) |

## Folded entities — the 11 satellites documented here

`Configuration` is the settings row; folded in with it are the other back-office plumbing entities that
have no feature of their own. Three of them are **audit trails**, and comparing them is the useful part:
the platform has three separate change-history mechanisms with three different shapes.

### The three audit trails

| Entity | What it is | Rules |
|---|---|---|
| `Audit` | A generic row-level audit: action, table name, primary key, serialised value, user | No factory and no guards — the only method is `UpdatePrimaryKey`, which returns `Result` and validates nothing (`Shared/TalabatkLogic/TalabatkModels/Audit.cs:30`). That method exists because the audit row is written **before** the entity is saved, so the generated key is not known yet and has to be patched in afterwards. It also means an audit row's identity is mutable after the fact |
| `EntityChangeHistory` | A field-level change log: property name, old value, new value, in both languages, scoped to a restaurant | The only one of the three that guards anything — `Create` rejects a zero restaurant id (`Shared/TalabatkLogic/TalabatkModels/EntityChangeHistory.cs:50`) and returns `Result`. Sixteen columns including `EntityNameAr` and `CategoryRelatedInfoAr`, so this trail is designed to be shown to Arabic-speaking merchants rather than only read by engineers |
| `ExcutionHistory` | Whether a journal-subscription run succeeded, with the error and how many restaurants it covered | `Instance` returns `Result` and cannot fail (`Shared/TalabatkLogic/TalabatkModels/ExcutionHistory.cs:20`). Note the misspelling in both the class and the file name |

Three mechanisms, three scopes — whole-row, per-field, per-job — and no shared abstraction. Which one
records a given change depends on which code path made it, so "who changed this?" has three places to
look and no index across them.

### Back-office task queue

| Entity | What it is | Rules |
|---|---|---|
| `Tasks` | A work item for a back-office user, with a status and timestamps for each transition | Nine methods, **no guards**: two `Instance` overloads (`Shared/TalabatkLogic/TalabatkModels/Tasks.cs:25`, `:38`), `TransferTasksIgnored` (`:52`), `CreateNewTaskstoTaskIgnored` (`:58`), `Resolved` (`:83`), `Activate` (`:89`), `Viewed` (`:94`), `Reject` (`:99`) and `CreateLateOrderTasks` (`:106`). Separate `ResolvedDate`, `ViewedDate`, `RejectedDate` and `TransferredDate` columns rather than a status history, so the lifecycle is reconstructed from which dates are non-null — and nothing stops a task being both resolved and rejected |
| `TaskType` | What a task is about, optionally linked to an order or a customer | Two `Instance` overloads and no guards (`Shared/TalabatkLogic/TalabatkModels/TaskType.cs:15`, `:29`) — one overload per link kind, which is how a task type is tied either to an order or to a customer without a discriminator |

### Outbound webhooks

| Entity | What it is | Rules |
|---|---|---|
| `Webhook` | A registered outbound URL and the events it subscribes to | `Instance` and `Update` both require a non-empty URL and at least one event id, with identical messages (`Shared/TalabatkLogic/TalabatkModels/Webhook.cs:24`, `:28`, `:42`, `:46`) — a properly symmetric pair. **The URL is checked for emptiness, not for being a URL**: no scheme check, no host allow-list, and `Update` replaces the whole subscription set (`:49-51`). The consumer POSTs restaurant-review data including `CustomerId` and the review comment to whatever is stored (`Shared/TalabatkApplication/DomainEventsHandlers/RestauarntReviewHandlers/RestauarntReviewCommentEventHandler.cs:35-38`). All five admin actions carry `[Permission(Permissions.Webhook.WebHook)]` (`AdminUi/Controllers/Webhook/WebhookController.cs:43`, `:63`, `:84`, `:100`, `:119`), so this is a typo-and-misconfiguration exposure rather than an open one — a wrong URL silently ships customer review data to a stranger |
| `WebhookEvent` | The catalogue of subscribable event types | Private ctor, **no methods at all** (`Shared/TalabatkLogic/TalabatkModels/WebhookEvent.cs`) — a seeded lookup |
| `WebhookSubscription` | One webhook's subscription to one event | Private ctor, `Instance` only (`Shared/TalabatkLogic/TalabatkModels/WebhookSubscription.cs:22`) |

### Reference and integration rows

| Entity | What it is | Rules |
|---|---|---|
| `LanGuage` | The language lookup — two columns, `LanguageId` and `language` | Nine lines, **no methods** (`Shared/TalabatkLogic/TalabatkModels/LanGuage.cs`). Every `*Description` entity in the repository keys off this table. The odd capitalisation and the lower-case property name are the real ones |
| `SalesDaily` | A daily sales rollup tied to an AccFlex treasury day | `Instance` only, no guards (`Shared/TalabatkLogic/TalabatkModels/SalesDaily.cs:29`). The merchant-side counterpart to `DeliveryManDaily` |
| `BitirixLeadStatus` | The CRM lead status mirrored from Bitrix for a merchant recruitment lead | `Instance` returns `Result` and **cannot fail**; `UpdateStatus` is an unguarded `void` (`Shared/TalabatkLogic/TalabatkModels/BitirixLeadStatus.cs:27`, `:38`). Holds Bitrix's own `LeadId`, `DateCreate` and `DateModify`, so this row is a cache of an external system's state with no reconciliation logic in the domain. Misspelling preserved — it is the real name, and it appears in `WorkUsRestaurant.BitirixLeadStatusId` too |

### What the split means

None of these eleven is business logic; all of them are infrastructure that happens to live in the
domain layer. That is why the validation is thin — but two consequences are worth carrying. The three
audit mechanisms mean there is no single answer to "who changed this record", and `Tasks` encodes its
lifecycle as four nullable dates rather than a state machine, so contradictory states are
representable and nothing objects.

## Related
- Business view: [[Configuration.business|Configuration]]
- [[CityBreakConfiguration|CityBreakConfiguration]] — Rule 2's parallel CSV-parsing pattern
- [[OrderRestaurantDetails|OrderRestaurantDetails]] — `PickupTag` (Rule 3)

## Open Questions
- [ ] Whether the unvalidated update groups (Rule 1) have ever actually received an invalid value in
  practice — this is a code-reading finding about *possible* input, not a confirmed incident.
- [ ] Whether `RedeemingPointsNumber` can ever legitimately be configured to `0` (Rule 4's
  divide-by-zero risk).
- [ ] The ~20 accounting account-id fields weren't individually cross-checked against an actual chart
  of accounts — flagged as configuration data, not verified for correctness.
