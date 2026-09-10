---
id: 8orders/identity-and-access/ops-and-infra/scenarios
title: Ops & Infra (Identity & Access) — Scenario Catalog
note_type: scenarios
context: Identity & Access
feature: Ops & Infra
audience: Business · QA · Developer
last_updated: 2026-08-23
sources:
  - path: Talabatk.IDS/Controllers/FeaturesController.cs
    sha1: 987c2188e807
  - path: Talabatk.IDS/Controllers/BackgroundJobsController.cs
    sha1: 6771d86519f8
  - path: Talabatk.IDS/Controllers/MaintenanceController.cs
    sha1: 5bfa2acdbc7b
  - path: Talabatk.IDS/Controllers/PaymentController/PaymentController.cs
    sha1: 56e8e3dbf12c
tags: [identity-and-access, ops-and-infra, scenarios]
---
# Ops & Infra (Identity & Access) — Scenario Catalog

> The gate to remember while reading: this host issues tokens for **every** user type, so `[Authorize]`
> with no role admits customers and drivers, not just operators.

## Happy path

| # | Precondition | Action | Expected outcome | Rule / source |
|---|---|---|---|---|
| H1 | Process running | `GET health` | `200 "Healthy"` | `Talabatk.IDS/Controllers/HealthController/HealthController.cs:8-13` |
| H2 | Flag exists in Esquio | `GET features?featureName=X` | Current value, via MediatR | `Talabatk.IDS/Controllers/FeatureMangamentController/FeatureMangamentController.cs` |
| H3 | Operator holds a bearer token, Esquio reachable | `PUT api/Features/ChangeState` with `IsEnabled: true` | Rollout called on Esquio; `200` | `FeaturesController.cs:28-52` |
| H4 | Same, `IsEnabled: false` | `PUT api/Features/ChangeState` | Rollback called on Esquio; `200` | `FeaturesController.cs:37-38` |
| H5 | Authenticated caller | `POST api/BackgroundJobs/TriggerAutoAssignJob` | Auto-assign runs immediately; `200` | `BackgroundJobsController.cs:36-49` |
| H6 | Authenticated caller, no migration in flight | `POST api/BackgroundJobs/TriggerMigrateChatToCassandra` | Migration runs under the process-wide semaphore | `BackgroundJobsController.cs:51-60` |
| H7 | Staff member signed in | `GET /Maintenance/LowQualityImages` | Image-job console rendered | `MaintenanceController.cs:107-112` |
| H8 | Same, `dryRun: true` | `POST /Maintenance/RemoveLowQualityImages` | Job enqueued in dry-run mode; nothing deleted | `MaintenanceController.cs:121-126` |
| H9 | Customer returns from the payment provider | `/Payment/CallBack?merchant_order_id=…&success=true` | Landing page in the customer's own language | `PaymentController.cs:19-29` |

## Partial / incremental

| # | Precondition | Action | Expected outcome | Rule / source |
|---|---|---|---|---|
| P1 | A chat migration is already running in this process | second `TriggerMigrateChatToCassandra` | Waits on `MigrateChatLock` rather than running concurrently | `MaintenanceController.cs:15`; `BackgroundJobsController.cs:53-60` |
| P2 | **Two instances** of the host are running | one migration triggered on each | Both proceed — the semaphore is per-process, not distributed | `MaintenanceController.cs:15` |
| P3 | Image cleanup wanted for one folder | `POST RemoveLowQualityImages` with `subPath` | Only that path is enqueued; the scope is whatever the caller passed | `MaintenanceController.cs:121-126` |
| P4 | Esquio returns a non-success status | `PUT api/Features/ChangeState` | Response body surfaced as `BadRequest` — this path *does* report failure | `FeaturesController.cs:40-44` |

## Negative / guard

| # | Precondition | Action | Expected outcome (rejection) | Rule / source |
|---|---|---|---|---|
| N1 | No token | `PUT api/Features/ChangeState` | 401 | `FeaturesController.cs:27` |
| N2 | No token | `POST api/BackgroundJobs/*` | 401 | `BackgroundJobsController.cs:35`, `:53` |
| N3 | No token | `/Maintenance/*` | 401 — class-level `[Authorize]` | `MaintenanceController.cs:12` |
| N4 | Authenticated, missing anti-forgery token | `POST /Maintenance/RemoveLowQualityImages` | Rejected by the anti-forgery filter | `MaintenanceController.cs:122` |
| N5 | Auto-assign job throws | `POST TriggerAutoAssignJob` | Exception logged and surfaced as `BadRequest` — correct handling | `BackgroundJobsController.cs:41-46` |
| N6 | Database down | `GET health` | Still `200 "Healthy"` | `Talabatk.IDS/Controllers/HealthController/HealthController.cs:8-13` |

## Returns / cancellation / reversal

| # | Precondition | Action | Expected outcome | Rule / source |
|---|---|---|---|---|
| R1 | Flag turned on by mistake | `PUT api/Features/ChangeState` with `IsEnabled: false` | Rollback — the switch is symmetric | `FeaturesController.cs:37-38` |
| R2 | Images deleted for the wrong path | — | No undo; `dryRun` beforehand is the only safeguard | `MaintenanceController.cs:121-126` |
| R3 | Chat migration half-finished | re-trigger | Idempotence beyond the in-process lock is unverified — see Open Questions | `BackgroundJobsController.cs:53-60` |

## Integration (cross-side / cross-context)

| # | Precondition | Action | Expected outcome | Rule / source |
|---|---|---|---|---|
| I1 | Operator changes a flag | Esquio called over HTTP | The **caller's own `Authorization` header** is forwarded to Esquio, so Esquio applies its own authorisation | `FeaturesController.cs:34` |
| I2 | Flag read by any client | MediatR query | One of six near-identical controllers across hosts | `_conflicts.md` #39, #48 |
| I3 | Chat migration runs | chat data moves to Cassandra | Target store documented in [[Admin/Chat Administration/_knowledge-graph\|Chat Administration]] | `BackgroundJobsController.cs:53-60` |
| I4 | Auto-assign triggered here | delivery assignment runs | Same job Hangfire runs on a schedule — see [[Delivery/Delivery Man Operations/_knowledge-graph\|Delivery Man Operations]] | `BackgroundJobsController.cs:36-40` |
| I5 | Customer finishes paying | provider redirects the browser here | Display only. The money-moving callback is HMAC-verified in `Shared/TalabatkApplication/Commands/PayMobCallBackCommand/PayMobCallBackCommand.cs:78` | `PaymentController.cs:19-29` |

## Security scenarios — current behaviour

| # | Precondition | Action | Actual outcome today | Finding |
|---|---|---|---|---|
| X1 | Esquio unreachable (DNS, timeout, bad config) | `PUT api/Features/ChangeState` | Exception logged, **`200 OK` returned** — the operator believes the flag changed and it did not | 🔴 `_conflicts.md` **#614** · `FeaturesController.cs:47-52` |
| X2 | **A customer's** token | `POST api/BackgroundJobs/TriggerMigrateChatToCassandra` | The chat data migration runs | 🔴 `_conflicts.md` **#615** · `BackgroundJobsController.cs:53` |
| X3 | A driver's token | `POST /Maintenance/RemoveLowQualityImages` with `dryRun: false` | Image deletion enqueued for the caller's chosen path | 🔴 **#615** · `MaintenanceController.cs:121-126` |
| X4 | Any authenticated token | `POST api/BackgroundJobs/TriggerAutoAssignJob` | Delivery auto-assignment runs on demand | 🔴 **#615** · `BackgroundJobsController.cs:35` |
| X5 | Anyone with a valid order code | `/Payment/CallBack?merchant_order_id=…` | That customer's language preference is revealed; **nothing is written** | ⚠️ minor · `PaymentController.cs:19-29` |
| X6 | Nothing | `GET health`, `GET features?featureName=…` | Confirms the host exists; flag values readable unauthenticated | ⚠️ #39/#48 |

## Open Questions

- [ ] Is `/Maintenance/*` reachable from outside the cluster? X3's severity depends entirely on it.
- [ ] What does `subPath` accept? If it is not constrained to a known root, the caller chooses the
      directory that gets cleaned — not traced into `LowQualityImageJob`.
- [ ] Does the chat migration have an idempotence guard beyond the in-process semaphore (P2, R3)?
- [ ] Since the caller's token is forwarded to Esquio (I1), is Esquio's own authorisation the real gate?
      If so, #615's flag half matters less than its maintenance half.
- [ ] Should `/health` probe the database, Cassandra and Esquio?
- [ ] Is there any audit record of who triggered a maintenance job? None observed in either controller.
