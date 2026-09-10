---
id: 8orders/identity-and-access/ops-and-infra/knowledge-graph
title: Ops & Infra (Identity & Access) — Knowledge Graph
note_type: knowledge-graph
context: Identity & Access
feature: Ops & Infra
last_updated: 2026-08-23
sources:
  - path: Talabatk.IDS/Controllers/FeaturesController.cs
    sha1: 987c2188e807
  - path: Talabatk.IDS/Controllers/BackgroundJobsController.cs
    sha1: 6771d86519f8
  - path: Talabatk.IDS/Controllers/MaintenanceController.cs
    sha1: 5bfa2acdbc7b
  - path: Talabatk.IDS/Controllers/HealthController/HealthController.cs
    sha1: 943077745a0c
  - path: Talabatk.IDS/Controllers/PaymentController/PaymentController.cs
    sha1: 56e8e3dbf12c
  - path: Talabatk.IDS/Controllers/FeatureMangamentController/FeatureMangamentController.cs
    sha1: a1851001420f
tags: [identity-and-access, ops-and-infra, technical, api-host]
---
# Ops & Infra (Identity & Access) — Knowledge Graph

> **Context:** Identity & Access
> **Source Project:** `Talabatk.IDS` (6 controllers)
> **Entities:** none of its own
> **Register findings open here:** #614, #615, #39 (the Esquio duplication)

The identity host's non-identity endpoints: liveness, feature flags, operator tooling and a payment
landing page. This is not the harmless corner it looks like. **The identity host issues tokens for
every user type in the system**, so an endpoint here gated only by "is authenticated" is reachable with
a *customer's* token — a wider audience than the same gate would give on any other host.

## Correction carried into this note

`_conflicts.md` **#375** — "an unauthenticated caller can trigger the delivery-men insurance-deduction
batch job" — was cited to line 198 of `Talabatk.IDS/Controllers/DeliveryMenController.cs` and is **not
in this host**. The endpoint is `AdminUi/Controllers/DeliveryMenController.cs:193-201`, where an
`[AllowAnonymous]` at `AdminUi/Controllers/DeliveryMenController.cs:198` overrides the class-level
`[Authorize]` at `AdminUi/Controllers/DeliveryMenController.cs:32`. Both projects contain a file with
that basename and both have a line 198, so the wrong-file citation resolved to a plausible line and
stood unchallenged. The finding is real; it belongs to
[[Admin/Delivery Administration/_knowledge-graph|Delivery Administration]]. The register row now says
so, and `verify-citations.js` gained a `CITE-BASENAME-AMBIGUOUS` class so bare filenames shared across
projects are surfaced rather than silently skipped.

## Endpoint index

| Endpoint | Auth | What it does | Verdict |
|---|---|---|---|
| `GET health` | **none** | Returns the literal `"Healthy"` | Shallow by design — touches no database, no Cassandra, no Esquio. A green probe proves only that the process is listening — `Talabatk.IDS/Controllers/HealthController/HealthController.cs:8-13` |
| `GET features?featureName=X` | **none** | Feature-flag **read** via MediatR `GetFeatureFlagQuery` | Byte-similar copy of the same controller in five other hosts — `_conflicts.md` #39/#48 — `Talabatk.IDS/Controllers/FeatureMangamentController/FeatureMangamentController.cs` |
| `PUT api/Features/ChangeState` | JWT bearer, **no role** | Feature-flag **write**: rolls a flag out or back via the external Esquio service, forwarding the caller's own `Authorization` header (`FeaturesController.cs:34`) | 🔴 `_conflicts.md` **#614** — an exception is logged and then `Ok()` is returned, so a failed toggle reports success (`:46-52`) |
| `POST api/BackgroundJobs/TriggerAutoAssignJob` | JWT bearer, **no role**, and **no audience check on this host** | Runs the delivery auto-assign job on demand | 🔴 `_conflicts.md` **#615** — `:35-49`; reachable with a customer or driver token, **#649** |
| `POST api/BackgroundJobs/TriggerMigrateChatToCassandra` | JWT bearer, **no role** | Runs the chat→Cassandra **data migration**, guarded by a static `SemaphoreSlim` so two runs cannot overlap in one process | 🔴 **#615** — `:51-60`; the lock is per-process, so two instances can still overlap |
| `GET`/`POST /Maintenance/MigrateChat` | `[Authorize]`, **no role** | Chat migration through a Razor page | 🔴 **#615** — `MaintenanceController.cs:12`, `:36-45` |
| `GET`/`POST /Maintenance/BackfillChatReports` | `[Authorize]`, no role | Backfills chat reports | 🔴 **#615** — `:85-93` |
| `GET /Maintenance/LowQualityImages` | `[Authorize]`, no role | Image-job console | `:107-111` |
| `POST /Maintenance/GenerateLowQualityImages` | `[Authorize]`, no role, `[ValidateAntiForgeryToken]` | Enqueues generation of low-quality images under a caller-supplied `subPath`, with a `dryRun` switch | 🔴 **#615** — `:114-119` |
| `POST /Maintenance/RemoveLowQualityImages` | `[Authorize]`, no role, `[ValidateAntiForgeryToken]` | Enqueues **deletion** of image files under a caller-supplied `subPath` | 🔴 **#615** — the most destructive action in the feature — `:121-126` |
| `/Payment/CallBack?merchant_order_id=…&success=…` | none (no attributes at all) | Renders the post-payment landing page | ⚠️ see the note below — **not** a money mutation |

> **`/Payment/CallBack` is a display page, not a payment webhook — stated explicitly so nobody
> "fixes" the wrong thing.** The action resolves the customer's preferred language via
> `GetCustomerLanguageIdForPaymentCallBackQuery`, puts it and the `success` flag in `ViewBag`, and
> returns a view (`PaymentController.cs:19-29`). It writes nothing and marks nothing paid. The real,
> money-moving PayMob callback is HMAC-verified elsewhere
> (`Shared/TalabatkApplication/Commands/PayMobCallBackCommand/PayMobCallBackCommand.cs:78`) and is
> documented in [[Customer Ordering/Payments/_knowledge-graph|Payments]]. The only exposure here is
> that anyone passing a valid order code learns that customer's language preference — worth noting,
> not worth escalating.

## Why "authenticated but roleless" is worse on this host

Every other host validates tokens; **this host mints them**, for customers, delivery men, merchant
staff and back-office users alike. An action whose only gate is `[Authorize]` therefore admits the
entire user population, not an administrative subset:

```
customer token ─┐
driver token   ─┼──> [Authorize] with no Roles ──> chat migration, report backfill,
merchant token ─┤                                  image deletion, auto-assign job
admin token    ─┘
```

The POST actions do carry `[ValidateAntiForgeryToken]`, which rules out drive-by CSRF from a browser —
so this is "any authenticated principal who calls it deliberately", not "any web page". That is still
the wrong audience for a data migration.

## The four feature-flag mechanisms, seen from this host

This host contains **two** of the four mechanisms recorded across the system, which is why the
duplication findings keep pointing here:

| Mechanism | Where | Direction | Register |
|---|---|---|---|
| Esquio over raw HTTP, caller's `Authorization` forwarded | `FeaturesController.cs:33-38` | **write** (rollout/rollback) | #39 |
| MediatR `GetFeatureFlagQuery` | `Talabatk.IDS/Controllers/FeatureMangamentController/FeatureMangamentController.cs` | read | #39, #48 |
| `IFeatureManager.IsFeatureEnabledAsync` | Restaurant Portal | read | #35 |
| Esquio `[FeatureFilter]` attribute | Restaurant Portal | gate an action | #44 |

Only the first can *change* a flag. It is also the one that reports success when it fails (#614).

## Status / State

Stateless except for two operational locks and one external store:

- `MigrateChatLock` — a `static SemaphoreSlim(1,1)` in `MaintenanceController`
  (`MaintenanceController.cs:15`) preventing overlapping chat migrations **within one process**. With
  more than one instance running, two migrations can still overlap.
- Feature-flag state lives in **Esquio**, outside this repo. Nothing here caches it, so a flag read is
  a live call.
- Health is a constant.

## Entity Index

| Entity | Layer | Type | Responsibility |
|---|---|---|---|
| — | — | — | This feature owns no domain entities. Chat data it migrates belongs to [[Admin/Chat Administration/_knowledge-graph\|Chat Administration]]; flag definitions live in Esquio |

## Feature Flow (Business Narrative)

```
1. ORCHESTRATOR
   └── GET /health -> "Healthy" (process only)
2. CLIENT BOOTSTRAP
   └── GET /features?featureName=X -> read a flag
3. OPERATOR TOGGLES A FLAG
   └── PUT api/Features/ChangeState -> Esquio rollout/rollback
        └── on exception: logged, and 200 returned anyway (#614)
4. OPERATOR RUNS MAINTENANCE
   ├── chat -> Cassandra migration (also exposed as an API trigger)
   ├── chat-report backfill
   └── low-quality image generate / REMOVE, under a caller-supplied path
5. CUSTOMER RETURNS FROM THE PAYMENT GATEWAY
   └── /Payment/CallBack -> language-localised landing page (display only)
```

## Key Cross-Cutting Relationships

| From | To | Relationship | Notes |
|---|---|---|---|
| This feature | Esquio (external) | flag read and write | The only write path in the system; caller's bearer token forwarded |
| This feature | [[Admin/Chat Administration/_knowledge-graph\|Chat Administration]] | migrates its data to Cassandra | The migration is triggerable from here by any authenticated principal |
| This feature | [[Delivery/Delivery Man Operations/_knowledge-graph\|Delivery Man Operations]] | auto-assign job trigger | Same job Hangfire runs on a schedule |
| This feature | [[Customer Ordering/Payments/_knowledge-graph\|Payments]] | post-payment landing page | Display only; the HMAC-verified callback is elsewhere |
| Every context | this host's `/features` copy | flag reads | One of six near-identical controllers — #39, #48 |

## Change Surface

| Signal | Value | Notes |
|---|---|---|
| Direct dependents (Ring 1) | orchestrator probes, every client's flag read, operator tooling | |
| Sides touched | 3/5 | API host · Backend-Application · Backend-Data (chat migration) |
| Cross-context integrations | 2 | Esquio (external), Cassandra chat store |
| Register findings open | 3 new/here (#614, #615) + #39 | #375 moved out to Admin |
| Hub? | no — but it sits on the host with the widest token audience | |

## Open Questions

- [ ] Is `/Maintenance/*` reachable from outside the cluster? #615's severity depends entirely on it.
- [ ] What does `subPath` accept in the image jobs? If it is not constrained to a known root, a caller
      chooses which directory gets cleaned — not traced into `LowQualityImageJob`.
- [ ] Does the chat→Cassandra migration have an idempotence guard beyond the in-process semaphore? Two
      instances could run it simultaneously.
- [ ] Should `PUT api/Features/ChangeState` require a role? It is the only endpoint in the system that
      can change behaviour for every user at once.
- [ ] Is Esquio's own authorisation doing the real work here, given the caller's header is forwarded? If
      so, this endpoint is a proxy and its own missing role check matters less — worth confirming.
- [ ] Should `/health` probe the database, Cassandra and Esquio? As written it cannot detect any of them
      being down.
