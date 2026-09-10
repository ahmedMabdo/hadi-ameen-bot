---
id: 8orders/restaurant-portal/ops-and-infra/scenarios
title: Ops & Infra (Restaurant Portal) — Scenario Catalog
note_type: scenarios
context: Restaurant Portal
feature: Ops & Infra
audience: Business · QA · Developer
last_updated: 2026-08-23
tags: [restaurant-portal, ops-and-infra, scenarios]
---
# Ops & Infra (Restaurant Portal) — Scenario Catalog

## Happy path

| # | Precondition | Action | Expected outcome | Rule / source |
|---|---|---|---|---|
| H1 | Host process running | `GET health` | `200 "Healthy"` | `HealthController.cs:8-13` |
| H2 | Flag `X` enabled | `GET features?featureName=X` | `200 true` via MediatR `GetFeatureFlagQuery` | `FeatureMangamentController.cs:19-31` |
| H3 | Flag `X` disabled | same | `200 false` | same |
| H4 | Signed-in merchant | `GET api/TawkTo/GetChatWidgetLinks` | Widget links returned | `TawkToController.cs:24-29` |
| H5 | Signed-in merchant | `GET api/TawkTo/GetBusinessChatWidgetLinks` | Business widget links returned | `TawkToController.cs:37-42` |

## Negative / guard

| # | Precondition | Action | Expected outcome (rejection) | Rule / source |
|---|---|---|---|---|
| N1 | — | `GET features` with no `featureName` | `400 "Feature name is required"` | `FeatureMangamentController.cs:22-25` |
| N2 | Unknown flag name | `GET features?featureName=nonsense` | Whatever `GetFeatureFlagQuery` returns for an unknown flag — **not traced**; treat as unverified | `FeatureMangamentController.cs:27-29` |
| N3 | No token | `GET api/TawkTo/*` | 401 — class-level `[Authorize]` | `TawkToController.cs:13` |
| N4 | Database unavailable | `GET health` | Still `200 "Healthy"` — the probe touches nothing downstream | `HealthController.cs:8-13` |

## Integration (cross-side / cross-context)

| # | Precondition | Action | Expected outcome | Rule / source |
|---|---|---|---|---|
| I1 | Flag changed in Admin | portal reloaded | New value observed; no deployment needed | flag store owned by [[Admin/Admin Back-Office/_knowledge-graph\|Admin Back-Office]] |
| I2 | Orchestrator probe loop | `GET health` | Host kept in rotation while it answers | `HealthController.cs` |
| I3 | Merchant opens support | Tawk.to widget loads | Third-party JS from the returned links | `TawkToController.cs` |
| I4 | Same flag asked via the other endpoint | `GET api/FeatureMangement/GetFeatureStatus?featureName=X` | Answered by a **different mechanism** (`IFeatureManager`) — two code paths, one question | `_conflicts.md` #35 |

## Cross-tenant / exposure scenarios — current behaviour

| # | Precondition | Action | Actual outcome today | Finding |
|---|---|---|---|---|
| X1 | **No token** | `GET features?featureName=<guess>` | Flag state for any name a caller tries | #35 |
| X2 | No token | `GET api/FeatureMangement/GetFeatureStatus?featureName=<guess>` | Same, via the other mechanism | #35 |
| X3 | No token | `GET health` | Confirms the host exists and is reachable | — (accepted for a liveness probe) |

## Open Questions

- [ ] N2: what does `GetFeatureFlagQuery` return for an unknown flag — `false`, or an error? A default
      of `true` would be a real problem; not traced in this pass.
- [ ] Should `/health` become a dependency probe (database, `ChatContext`, Hangfire, IDS)?
- [ ] Are the Tawk.to links per-merchant or global? The actions take no parameters.
- [ ] Which of the two flag endpoints does the Angular client call? The other is dead code that still
      answers unauthenticated queries.
