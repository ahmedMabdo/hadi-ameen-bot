---
id: 8orders/restaurant-portal/ops-and-infra/knowledge-graph
title: Ops & Infra (Restaurant Portal) — Knowledge Graph
note_type: knowledge-graph
context: Restaurant Portal
feature: Ops & Infra
last_updated: 2026-08-23
sources:
  - path: TalabatkRestaurants/Controllers/FeatureMangamentController/FeatureMangamentController.cs
    sha1: 6a44146f1454
  - path: TalabatkRestaurants/Controllers/HealthController/HealthController.cs
    sha1: ff4d951a6411
  - path: TalabatkRestaurants/Controllers/TawkTo/TawkToController.cs
    sha1: c8128730a22d
  - path: TalabatkRestaurants/Controllers/FeatureMangement/FeatureMangementController.cs
    sha1: 2fd21fe75e1d
tags: [restaurant-portal, ops-and-infra, technical, api-host]
---
# Ops & Infra (Restaurant Portal) — Knowledge Graph

> **Context:** Restaurant Portal
> **Source Project:** `TalabatkRestaurants` (3 controllers, 4 actions)
> **Entities Covered:** none — this feature owns no domain data
> **Why it exists as a feature:** every host has a handful of endpoints that serve the *platform*
> rather than the business — liveness, feature flags, the support-chat widget. Left unassigned they
> become the endpoints nobody documents and nobody audits, which is exactly where two duplication
> findings and an unauthenticated flag probe were hiding.

## Endpoint index

| Endpoint | Auth | What it does | Notes |
|---|---|---|---|
| `GET health` | **none** | Returns the literal string `"Healthy"` | No dependency probe: it does not touch the database, `ChatContext`, Hangfire, or the IDS. A green health check therefore proves only that the process is listening — `TalabatkRestaurants/Controllers/HealthController/HealthController.cs:8-13` |
| `GET features?featureName=X` | **none** | Feature-flag check via MediatR `GetFeatureFlagQuery` | `TalabatkRestaurants/Controllers/FeatureMangamentController/FeatureMangamentController.cs:19-31`. Validates that `featureName` is non-empty and returns 400 otherwise |
| `GET api/FeatureMangement/GetFeatureStatus?featureName=X` | **none** | The *other* feature-flag check, via `IFeatureManager.IsFeatureEnabledAsync` | Lives in [[Restaurant Portal/Merchant Account & Access/_knowledge-graph\|Merchant Account & Access]]'s controller set; recorded here because the pair is the finding — `_conflicts.md` #35 |
| `GET api/TawkTo/GetChatWidgetLinks` | `[Authorize]` | Returns the Tawk.to widget links for the signed-in merchant | `TalabatkRestaurants/Controllers/TawkTo/TawkToController.cs:24-29` |
| `GET api/TawkTo/GetBusinessChatWidgetLinks` | `[Authorize]` | Same for the business/enterprise widget | `TalabatkRestaurants/Controllers/TawkTo/TawkToController.cs:37-42` |

## The feature-flag duplication, stated once and completely

This is the clearest instance of a systemic pattern, so it is documented here rather than repeated in
every feature that trips over it:

| Mechanism | Where | Route | Register |
|---|---|---|---|
| MediatR `GetFeatureFlagQuery` | `TalabatkRestaurants/Controllers/FeatureMangamentController/` | `GET features` | `_conflicts.md` #35 |
| `IFeatureManager.IsFeatureEnabledAsync` | `TalabatkRestaurants/Controllers/FeatureMangement/` | `GET api/FeatureMangement/GetFeatureStatus` | #35 |
| Byte-similar copy of the MediatR controller | `Talabatk.IDS/Controllers/FeatureMangamentController/` | `GET features` | #39 (4 instances) |
| Byte-similar copy again | `AdminUi/Controllers/FeatureMangamentController/` | `GET features` | #48 (6 instances) |
| Esquio as an action filter | `OptionCategoryController.OptionsCategoryFeature` | attribute-gated action | #44 |
| Esquio over raw HTTP | `Talabatk.IDS/FeaturesController.cs` | external service call | #39 |

Two spellings — `FeatureMangament` and `FeatureMangement`, both misspellings of "Management", differing
in one letter — sit in the same `Controllers/` folder of the same project. A developer searching for
"the" feature-flag endpoint finds the wrong one roughly half the time, which is the real cost of #35.

**None of the flag endpoints requires authentication.** A flag name is a small thing to leak, but the
set of flags is a map of unreleased functionality, and the endpoint answers `true`/`false` for any name
a caller cares to try.

## Status / State

Stateless. No entity, no status field, no persistence. The only state involved is the feature-flag
store these endpoints read (Esquio / the `Features` table), owned by
[[Admin/Admin Back-Office/_knowledge-graph|Admin Back-Office]].

## Entity Index

| Entity | Layer | Type | Responsibility |
|---|---|---|---|
| — | — | — | This feature owns no entities. Flag definitions live with Admin; chat-widget configuration is read from configuration, not from a domain table |

## Feature Flow (Business Narrative)

```
1. LOAD BALANCER / ORCHESTRATOR
   └── GET /health -> "Healthy" (process is up; nothing downstream is checked)
2. ANGULAR PORTAL BOOTSTRAP
   └── GET /features?featureName=X  (or the other one) -> enables/hides UI
3. MERCHANT CLICKS SUPPORT
   └── GET api/TawkTo/GetChatWidgetLinks -> widget links for the signed-in user
```

## Key Cross-Cutting Relationships

| From | To | Relationship | Notes |
|---|---|---|---|
| This feature | Admin Back-Office | reads feature flags | Flag values are administered in `AdminUi`; see `_conflicts.md` #48 for the duplicated controller |
| This feature | Tawk.to (external) | support chat widget | Third-party JS widget; links only, no data exchange traced here |
| Every other Restaurant Portal feature | this one | reads flags to hide/show UI | A flag change alters merchant-visible behaviour without a deployment |
| Orchestrator / probes | `/health` | liveness | Shallow by design — worth knowing during an incident |

## Change Surface

| Signal | Value | Notes |
|---|---|---|
| Direct dependents (Ring 1) | Angular portal bootstrap, orchestrator health probe | |
| Sides touched | 2/5 | API host · Frontend |
| Cross-context integrations | 2 | Admin (flag store), Tawk.to (external widget) |
| Register findings open | 3 | #35 (this host's duplicate pair), #39, #48 (the copies in other hosts) |
| Hub? | no | |

<!-- BEGIN generated: endpoint index (insert-endpoints.js) -->

## Endpoint index — generated from the controllers

> Generated by `_system/insert-endpoints.js` from `_feature-map.tsv`; do not edit between the
> sentinels. Every row is anchored to a line, so `verify-citations.js` checks all of it and a
> controller that moves is caught on the next run. "Action gate" lists only attributes on the action
> itself — the class gate above each table still applies unless an action opts out of it.

**3 controller(s), 4 action(s)**; 4 have no action-level gate and rely entirely on the class attribute.

#### `TalabatkRestaurants/Controllers/FeatureMangamentController/FeatureMangamentController.cs`

Class gate: **no auth attribute on the class** — `TalabatkRestaurants/Controllers/FeatureMangamentController/FeatureMangamentController.cs:10`

| Route | Verb | Action gate | Anchor |
|---|---|---|---|
| `CheckFeature` | GET | — | `TalabatkRestaurants/Controllers/FeatureMangamentController/FeatureMangamentController.cs:20` |

#### `TalabatkRestaurants/Controllers/HealthController/HealthController.cs`

Class gate: **no auth attribute on the class** — `TalabatkRestaurants/Controllers/HealthController/HealthController.cs:7`

| Route | Verb | Action gate | Anchor |
|---|---|---|---|
| `Get` | GET | — | `TalabatkRestaurants/Controllers/HealthController/HealthController.cs:10` |

#### `TalabatkRestaurants/Controllers/TawkTo/TawkToController.cs`

Class gate: roleless `[Authorize]` — `TalabatkRestaurants/Controllers/TawkTo/TawkToController.cs:13`

| Route | Verb | Action gate | Anchor |
|---|---|---|---|
| `GetChatWidgetLinks` | GET | — | `TalabatkRestaurants/Controllers/TawkTo/TawkToController.cs:29` |
| `GetBusinessChatWidgetLinks` | GET | — | `TalabatkRestaurants/Controllers/TawkTo/TawkToController.cs:42` |

<!-- END generated: endpoint index -->

## Open Questions

- [ ] Which flag endpoint does the Angular client actually call? If only one, the other is dead code
      that still answers unauthenticated queries.
- [ ] Should `/health` probe its dependencies (`TalabatkContext`, `ChatContext`, Hangfire, IDS)? As
      written it cannot detect a database outage, so an orchestrator will keep routing traffic to a
      host that cannot serve it.
- [ ] Are the Tawk.to widget links tenant-specific, or the same for every merchant? The action takes no
      parameter, which suggests configuration-level, but the handler was not opened.
