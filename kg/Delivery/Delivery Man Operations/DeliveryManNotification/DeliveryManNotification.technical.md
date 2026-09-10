---
id: 8orders/delivery/delivery-man-operations/deliverymannotification-technical
title: DeliveryManNotification — Technical
note_type: technical
context: Delivery
feature: Delivery Man Operations
entity: DeliveryManNotification
entity_type: aggregate-root
side: backend-domain
rule_count: 11
last_updated: 2026-08-23
covers: [DeliveryManNotificationDetail]
sources:
  - path: Shared/TalabatkLogic/DeliveryManNotificationAggregate/DeliveryManNotification.cs
    sha1: 869546a4890e
  - path: Shared/TalabatkLogic/DeliveryManNotificationAggregate/DeliveryManNotificationDetail.cs
    sha1: 7377f391bd82
  - path: Shared/TalabatkLogic/DeliveryManNotificationAggregate/DeliveryManNotificationStatusEnum.cs
    sha1: 18244338d439
  - path: Shared/TalabatkApplication/Helper/HangFire/SendDeliveryManNotificationJob.cs
    sha1: cff29c19e542
tags: [delivery, delivery-man-operations, transactional, technical, backend-domain]
---
# DeliveryManNotification — Technical

> **Layer:** Domain — **Aggregate Root** with a child collection (one of only 4 real DDD aggregates)
> **Context:** Delivery (consumption) / Admin (management)   **Feature:** Delivery Man Operations
> **Source Path:** `Shared/TalabatkLogic/DeliveryManNotificationAggregate/DeliveryManNotification.cs`
> **Child:** `DeliveryManNotificationDetail` (one row per targeted driver)
> **Last Updated:** 2026-08-23

A push message sent to delivery men in a city — optionally narrowed to one delivery zone, optionally
scheduled for later, and tracked per recipient (sent / read / deleted). This is the **only** aggregate
in the codebase that owns a child collection exposed as `IReadOnlyList<T>`
(`DeliveryManNotification.cs:32`), so it is the reference example of the pattern the architecture rules
ask for.

Like [[DeliveryAnnouncement.technical|DeliveryAnnouncement]], it had **no documentation before this
note** despite being one of four genuine DDD aggregates.

## Status / State — a real two-state machine

`DeliveryManNotificationStatusEnum`
(`Shared/TalabatkLogic/DeliveryManNotificationAggregate/DeliveryManNotificationStatusEnum.cs:5-6`):

| Status | Value | Meaning |
|---|---|---|
| `Pending` | 1 | Created, not yet delivered |
| `Sent` | 2 | Delivered — **terminal** |

```
Pending(1) ──MarkAsSent(deliveryMenInShift, sentDate, updatedBy)──> Sent(2)   [terminal]
   │
   ├── Update(...)         allowed only while Pending
   └── (scheduled) a Hangfire job fires at ScheduledDate and calls MarkAsSent
```

`Sent` is terminal in both directions that matter: it blocks editing (Rule 6) and blocks re-sending
(Rule 7). The per-recipient child rows carry their own independent flags — see the child section.

## Business Rules

### Rule 1: A city is mandatory
- **Trigger:** `Create`.
- **Violation result:** `Result.Failure<DeliveryManNotification>("City is required")`
- **Source:** `DeliveryManNotification.cs:52-53`

### Rule 2: Both titles and both bodies are required
- **Plain language:** A notification must be complete in Arabic and English — no partial bilingual push.
- **Trigger:** `Create` and `Update`, via `Validate`.
- **Violation result:** `"Arabic title is required"` / `"English title is required"` /
  `"Arabic body is required"` / `"English body is required"`
- **Source:** `DeliveryManNotification.cs:184-194`

### Rule 3: A scheduled notification must say when
- **Trigger:** `Create`/`Update` with `isScheduled` true.
- **Violation result:** `Result.Failure("Scheduled date is required when notification is scheduled")`
- **Source:** `DeliveryManNotification.cs:196-197`

### Rule 4: A scheduled date must be in the future
- **Plain language:** You cannot schedule a push for a moment that has already passed.
- **Trigger:** `Create`/`Update` with `isScheduled` true and a value.
- **Violation result:** `Result.Failure("Scheduled date must be in the future")`
- **Source:** `DeliveryManNotification.cs:199-200`
- **Note:** compared against an injected `dateTimeNow`, not `DateTime.Now` — the caller defines "now".

### Rule 5: Creation succeeds only after every validation
- **Trigger:** `Create`.
- **Violation result:** the `Validate` failure is propagated unchanged.
- **Source:** `DeliveryManNotification.cs:64-65`

### Rule 6: A sent notification cannot be edited
- **Plain language:** Once it has gone out, its text and targeting are frozen — there is no recall.
- **Trigger:** `Update`.
- **Violation result:** `Result.Failure("Cannot edit notification that has already been sent")`
- **Source:** `DeliveryManNotification.cs:104-105`

### Rule 7: A notification cannot be sent twice
- **Trigger:** `MarkAsSent`.
- **Violation result:** `Result.Failure("Notification has already been sent")`
- **Source:** `DeliveryManNotification.cs:153-154`
- **Note:** this is the idempotence guard that makes a retried Hangfire job safe.

### Rule 8: Sending requires the in-shift driver list
- **Plain language:** The caller must supply which drivers were on shift; the aggregate will not guess.
- **Trigger:** `MarkAsSent` with a null list.
- **Violation result:** `Result.Failure("Delivery men in shift list is required")`
- **Source:** `DeliveryManNotification.cs:156-157`
- **Note:** `null` is rejected; an **empty** list is accepted and marks nothing as sent while still
  moving the notification to `Sent`. So a push that reached nobody is indistinguishable, at the
  aggregate level, from one that reached everyone.

### Rule 9: Only drivers who were in shift are marked as delivered
- **Plain language:** Recipients who were off shift when it fired keep their row unsent.
- **Trigger:** `MarkAsSent`.
- **Outcome:** the child rows whose `DeliveryManId` appears in the supplied list get `MarkAsSent()`;
  the rest are untouched.
- **Source:** `DeliveryManNotification.cs:159-164`
- **Note:** this is the interesting business rule of the whole aggregate — targeting is decided at
  creation, but *delivery* is decided by who was working at the moment it fired.

### Rule 10: A deleted recipient row cannot be marked read
- **Trigger:** `DeliveryManNotificationDetail.MarkNotificationAsRead`.
- **Violation result:** `Result.Failure("Cannot mark deleted notification as read")`
- **Source:** `DeliveryManNotificationDetail.cs:28-31`

### Rule 11: A recipient row cannot be deleted twice
- **Trigger:** `DeliveryManNotificationDetail.SoftDelete`.
- **Violation result:** `Result.Failure("Notification detail is already deleted")`
- **Source:** `DeliveryManNotificationDetail.cs:37-40`
- **Note:** deletion is a **soft** flag (`IsDeleted`), so a driver dismissing a notification does not
  destroy the delivery record.

## Rule / Decision Matrix

| # | Trigger (when) | Condition / guard | Outcome | Source |
|---|---|---|---|---|
| 1 | Create | city absent | rejected — "City is required" | `DeliveryManNotification.cs:52` |
| 2 | Create / Update | any of 4 language fields blank | rejected, field-specific | `:184-194` |
| 3 | Create / Update | scheduled with no date | rejected | `:196` |
| 4 | Create / Update | scheduled date not in the future | rejected | `:199` |
| 5 | Update | status already `Sent` | rejected — no editing after send | `:104` |
| 6 | MarkAsSent | status already `Sent` | rejected — idempotent | `:153` |
| 7 | MarkAsSent | driver list null | rejected | `:156` |
| 8 | MarkAsSent | driver list supplied | only in-shift recipients marked sent; status → `Sent` | `:159-167` |
| 9 | Detail.MarkNotificationAsRead | row soft-deleted | rejected | `DeliveryManNotificationDetail.cs:28` |
| 10 | Detail.SoftDelete | already deleted | rejected | `DeliveryManNotificationDetail.cs:37` |
| 11 | any | — | `GetJobId()` yields `DeliveryManNotification_{id}` for Hangfire | `DeliveryManNotification.cs:205` |

## Key Fields

| Field | Meaning | Constraints |
|---|---|---|
| `DeliveryManNotificationId` | Identity | private setter |
| `NotificationTitleByArabic` / `ByEnglish` | Title per language | both required |
| `NotificationBodyByArabic` / `ByEnglish` | Body per language | both required |
| `CityId` | Target city | required |
| `DeliveryZoneId` | Optional narrower target | nullable — null means the whole city |
| `Status` | `Pending` / `Sent` | `Sent` is terminal |
| `IsScheduled` | Whether it fires later | drives Rules 3 and 4 |
| `ScheduledDate` | When it fires | required and future when scheduled |
| `CreationDate` / `CreatedBy` · `UpdatedDate` / `UpdatedBy` | Audit | injected clock |
| `DeliveryManNotificationDetails` | Recipients | exposed as `IReadOnlyList<T>` (`:32`) — the only aggregate here that does this |

### Child — `DeliveryManNotificationDetail`

| Field | Meaning |
|---|---|
| `DeliveryManNotificationDetailId` | Identity |
| `DeliveryManNotificationId` | Parent |
| `DeliveryManId` | The targeted driver |
| `MarkAsRead` | The driver opened it |
| `IsDeleted` | The driver dismissed it (soft) |
| `IsSent` | It actually reached this driver (set only if they were in shift — Rule 9) |

`IsSent` on the child and `Status = Sent` on the parent answer **different** questions: the parent means
"the send ran", the child means "this driver got it". Reporting that conflates them will overstate reach.

## Dependencies & Integrations

| Depends on / integrates | Side/Context | Via | Notes |
|---|---|---|---|
| [[DeliveryMen.technical\|DeliveryMen]] | Backend-Domain | `List<DeliveryMen>` passed to `MarkAsSent` | The in-shift list — Rule 9 |
| [[City.technical\|City]], [[DeliveryZone\|DeliveryZone]] | Backend-Domain | targeting fields | Zone is optional |
| Hangfire | Backend-Application | `SendDeliveryManNotificationJob` | Delayed send; job id from `GetJobId()` (`:205`), stored so it can be cancelled — `_integrations.md` row 21 |
| Firebase Cloud Messaging | external | `IDeliverymanNotificationProvider` | The actual push — `Shared/TalabatkApplication/Helper/HangFire/SendDeliveryManNotificationJob.cs:36` |
| Admin authoring | Admin | `AdminUi/Controllers/DeliveryManNotificationController/` | See [[Admin/Delivery Administration/_knowledge-graph\|Delivery Administration]] |

The break-reminder flow in `_integrations.md` row 21 is the same machinery used from a different
trigger: `BreakStartedEventHandler` creates a notification and schedules `SendDeliveryManNotificationJob`
with a delay, storing the returned job id on the break log so an early break-end can cancel it.

## Change Surface

| Signal | Value | Notes |
|---|---|---|
| Direct dependents (Ring 1) | Admin authoring controller, `SendDeliveryManNotificationJob`, break-started handler, driver app | |
| Sides touched | 4/5 | Domain · Application · Data · API host |
| Cross-context integrations | 2 | Hangfire delayed send; FCM push to the driver app |
| Domain events involved | 0 raised; consumed by a handler that creates these | |
| Hub? | no | |
| Risk flags | scheduled sends carry a stored Hangfire job id — changing `GetJobId()`'s format orphans in-flight jobs |

## Related

- Business view: [[DeliveryManNotification.business|DeliveryManNotification]]
- [[DeliveryAnnouncement.technical|DeliveryAnnouncement]] — the passive, city-wide sibling
- [[DeliveryMen.technical|DeliveryMen]] — recipients, and the shift state Rule 9 depends on
- Also part of: [[Admin/Delivery Administration/_knowledge-graph|Delivery Administration]]

## Open Questions

- [ ] Rule 8: is an **empty** in-shift list a real scenario? It moves the notification to `Sent` while
      reaching nobody, and nothing records that outcome.
- [ ] Are unsent child rows ever retried for drivers who come on shift later? Nothing in the aggregate
      supports it — `Sent` is terminal.
- [ ] Who cancels a scheduled notification, and does that use `GetJobId()`? The break-reminder flow
      stores its job id explicitly; this aggregate only computes the id.
- [ ] Is `DeliveryZoneId` respected when the recipient list is built, or only `CityId`? Targeting is
      built by the caller, so the aggregate cannot enforce it.
- [ ] Can a driver's dismissal (`SoftDelete`) be undone? No method restores it.
