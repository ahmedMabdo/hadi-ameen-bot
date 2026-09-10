---
id: 8orders/admin/delivery-administration/scenarios
title: Delivery Administration — Scenario Catalog
note_type: scenarios
context: Admin
feature: Delivery Administration
audience: Business · QA · Developer
last_updated: 2026-08-23
sources:
  - path: AdminUi/Controllers/DeliverymanWallet/DeliverymanWalletController.cs
    sha1: 9714e0642f79
  - path: AdminUi/Controllers/DeliveryAnnouncementController/DeliveryAnnouncementController.cs
    sha1: 3a74b206d28d
  - path: AdminUi/Controllers/DeliveryMenController.cs
    sha1: 0c16e85a7b86
  - path: AdminUi/Controllers/Compensation/CompensationController.cs
    sha1: 800d6a471b5b
  - path: Shared/TalabatkLogic/DeliveryAnnouncementAggregate/DeliveryAnnouncement.cs
    sha1: a76bd37f02b4
  - path: Shared/TalabatkLogic/DeliveryManNotificationAggregate/DeliveryManNotification.cs
    sha1: 869546a4890e
tags: [admin, delivery-administration, scenarios]
---
# Delivery Administration — Scenario Catalog

> Rule detail for the two aggregates lives in [[DeliveryAnnouncement.technical|DeliveryAnnouncement]]
> and [[DeliveryManNotification.technical|DeliveryManNotification]]; the rows below exercise them from
> the Admin side.

## Happy path

| # | Precondition | Action | Expected outcome | Rule / source |
|---|---|---|---|---|
| H1 | Admin with the announcements permission | `POST api/DeliveryAnnouncement/AddDeliveryAnnouncement` | Created after the aggregate validates city, dates and language fields | `AdminUi/Controllers/DeliveryAnnouncementController/DeliveryAnnouncementController.cs:71-72`; guards at `Shared/TalabatkLogic/DeliveryAnnouncementAggregate/DeliveryAnnouncement.cs:145-174` |
| H2 | Same | `GET api/DeliveryAnnouncement/GetDeliveryAnnouncements` | Paged list | `AdminUi/Controllers/DeliveryAnnouncementController/DeliveryAnnouncementController.cs:38-39` |
| H3 | Admin authors a driver push | `POST api/DeliveryManNotification/AddDeliveryManNotification` | Created `Pending`; bilingual fields required | `Shared/TalabatkLogic/DeliveryManNotificationAggregate/DeliveryManNotification.cs:184-194` |
| H4 | Scheduled time arrives | Hangfire fires the job | `MarkAsSent`: only drivers on shift are recorded as reached; status → `Sent` | `Shared/TalabatkLogic/DeliveryManNotificationAggregate/DeliveryManNotification.cs:159-167` |
| H5 | Finance adjusts a driver balance | `POST api/DeliverymanWallet/Add` | Wallet transaction written | `AdminUi/Controllers/DeliverymanWallet/DeliverymanWalletController.cs:55-58` |
| H6 | Finance reviews driver money | `GET api/DeliverymanWallet/GetTransactions` | Transactions for the queried driver | `AdminUi/Controllers/DeliverymanWallet/DeliverymanWalletController.cs:32-35` |
| H7 | Operations raise a compensation | `POST api/Compensation/AddNewCompensation` | Compensation created | `AdminUi/Controllers/Compensation/CompensationController.cs` |
| H8 | Compensation approved | `POST api/Compensation/UpdateCompensationState` | State advanced; the enum is served to the UI by `GetCompensationStatusEnum` | `AdminUi/Controllers/Compensation/CompensationController.cs` |
| H9 | Operations configure a bonus | `POST api/DeliveryBouns/Add` | Bonus scheme created for a city and shift | `AdminUi/Controllers/DeliveryBouns/DeliveryBounsController.cs` |
| H10 | Operations look up drivers for an order | `GET api/DeliveryMen/GetAllDeliveryMenByOrderId` | Candidate drivers | `AdminUi/Controllers/DeliveryMenController.cs` |

## Partial / incremental

| # | Precondition | Action | Expected outcome | Rule / source |
|---|---|---|---|---|
| P1 | Announcement is an image banner | create with the banner flag, then set the image | Titles and descriptions are **silently blanked**; the image is required only on the separate `SetImageUrl` call | `Shared/TalabatkLogic/DeliveryAnnouncementAggregate/DeliveryAnnouncement.cs:63-66`, `:125-126` |
| P2 | Notification not yet sent | `POST …/EditDeliveryManNotification` | Allowed while `Pending` | `Shared/TalabatkLogic/DeliveryManNotificationAggregate/DeliveryManNotification.cs:104-105` |
| P3 | Some targeted drivers were off shift | send fires | Their per-recipient rows stay unsent; no retry mechanism exists | `Shared/TalabatkLogic/DeliveryManNotificationAggregate/DeliveryManNotification.cs:159-164` |
| P4 | Compensation needs several steps | repeated `UpdateCompensationState` | Advanced one state at a time from the UI | `AdminUi/Controllers/Compensation/CompensationController.cs` |

## Negative / guard

| # | Precondition | Action | Expected outcome (rejection) | Rule / source |
|---|---|---|---|---|
| N1 | No city supplied | create an announcement | Rejected — "City is required" | `Shared/TalabatkLogic/DeliveryAnnouncementAggregate/DeliveryAnnouncement.cs:145-146` |
| N2 | End date not after start | create/edit an announcement | Rejected | `Shared/TalabatkLogic/DeliveryAnnouncementAggregate/DeliveryAnnouncement.cs:170-171` |
| N3 | Another announcement covers those dates for that city | create/edit | Rejected — but the overlap is computed by the **caller**, not the aggregate | `Shared/TalabatkLogic/DeliveryAnnouncementAggregate/DeliveryAnnouncement.cs:173-174` |
| N4 | Notification already sent | edit it | Rejected — "Cannot edit notification that has already been sent" | `Shared/TalabatkLogic/DeliveryManNotificationAggregate/DeliveryManNotification.cs:104-105` |
| N5 | Notification already sent | send again | Rejected — the idempotence guard that makes a Hangfire retry safe | `Shared/TalabatkLogic/DeliveryManNotificationAggregate/DeliveryManNotification.cs:153-154` |
| N6 | Scheduled date in the past | create a scheduled notification | Rejected | `Shared/TalabatkLogic/DeliveryManNotificationAggregate/DeliveryManNotification.cs:199-200` |
| N7 | Admin without the announcements permission | any announcement action | Denied by the permission attribute | `AdminUi/Controllers/DeliveryAnnouncementController/DeliveryAnnouncementController.cs:38` |
| N8 | Signed-in user with **no particular role** | `POST api/DeliverymanWallet/Add` | **Accepted** — no permission attribute on this controller | 🔴 `AdminUi/Controllers/DeliverymanWallet/DeliverymanWalletController.cs:19`, `:55-58` · #569 |

## Returns / cancellation / reversal

| # | Precondition | Action | Expected outcome | Rule / source |
|---|---|---|---|---|
| R1 | Announcement published in error | `POST …/DeleteDeliveryAnnouncement` | Deleted — there is **no** pause, because liveness is derived from dates | `AdminUi/Controllers/DeliveryAnnouncementController/DeliveryAnnouncementController.cs` |
| R2 | Notification scheduled by mistake, not yet sent | delete or edit it | Allowed while `Pending`; the scheduled job id is derived from the notification id | `Shared/TalabatkLogic/DeliveryManNotificationAggregate/DeliveryManNotification.cs:205` |
| R3 | Notification already sent | — | No recall; a correcting notification must be sent | `Shared/TalabatkLogic/DeliveryManNotificationAggregate/DeliveryManNotification.cs:104-105` |
| R4 | Wallet adjustment wrong | post an opposite transaction | The ledger is append-only | [[DeliverymanTransaction.technical\|DeliverymanTransaction]] |
| R5 | Compensation approved in error | advance state / opposite entry | State machine driven from the UI | `AdminUi/Controllers/Compensation/CompensationController.cs` |

## Integration (cross-side / cross-context)

| # | Precondition | Action | Expected outcome | Rule / source |
|---|---|---|---|---|
| I1 | Notification sent | FCM push | Delivered via the driver notification provider | `_integrations.md` row 21 |
| I2 | Break started by a driver | delayed job | Break-ending reminder uses this feature's notification machinery | `_integrations.md` row 21 |
| I3 | Wallet or compensation posted | daily batch | Movements reach AccFlex ERP's general ledger | `_integrations.md` row 20 |
| I4 | Restaurant repeatedly ignores orders | RoboCall | Automated voice call, scheduled by a Hangfire job | `_integrations.md` row 17 |
| I5 | Announcement published | driver app | Read via the driver-facing announcements endpoint | [[Delivery/Delivery Man Operations/_knowledge-graph\|Delivery Man Operations]] |

## Security scenarios — current behaviour

| # | Precondition | Action | Actual outcome today | Finding |
|---|---|---|---|---|
| X1 | **No token at all** | `POST api/DeliveryMen/DailyRefundableDeposit` | The daily insurance-deduction batch runs across delivery men. No parameters, no date guard, no already-run check | 🔴 `_conflicts.md` **#375** · `AdminUi/Controllers/DeliveryMenController.cs:198` |
| X2 | Any signed-in user | `GET api/DeliverymanWallet/GetTransactions` with any driver id | That driver's transactions | 🔴 `_conflicts.md` **#568** · `AdminUi/Controllers/DeliverymanWallet/DeliverymanWalletController.cs:32-35` |
| X3 | Any signed-in user | `POST api/DeliverymanWallet/Add` | A **wallet transaction is written** — money moved with no role or permission check | 🔴 `_conflicts.md` **#569** · `AdminUi/Controllers/DeliverymanWallet/DeliverymanWalletController.cs:55-58` |
| X4 | Any signed-in user | most other actions in this feature | Allowed — only the two aggregate controllers carry `[Permission]` | ⚠️ #617/#618 context |
| X5 | Notification targeted at a city at 3am | scheduled send fires | Marked `Sent` with **nobody** recorded as reached, and nothing records the zero reach | ⚠️ `Shared/TalabatkLogic/DeliveryManNotificationAggregate/DeliveryManNotification.cs:156-167` |

## Open Questions

- [ ] Should the wallet actions carry a `[Permission]`? They are the only money-writing endpoints in the
      feature without one.
- [ ] Is `DailyRefundableDeposit` called by an internal scheduler? If so it could use a shared secret,
      as the Fawry webhooks do.
- [ ] Who computes the announcement overlap check (N3)? The invariant is only as good as that query.
- [ ] Can a scheduled notification be cancelled from the Admin UI, and does that cancel the Hangfire job?
- [ ] Does compensation state have guarded transitions, or can any state follow any other?
