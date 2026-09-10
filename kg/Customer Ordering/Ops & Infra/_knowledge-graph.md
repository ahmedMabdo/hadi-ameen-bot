---
id: 8orders/customer-ordering/ops-and-infra/knowledge-graph
title: Ops & Infra (Customer Ordering) — Knowledge Graph
note_type: knowledge-graph
context: Customer Ordering
feature: Ops & Infra
last_updated: 2026-08-23
sources:
  - path: TalabatkAPIs/Controllers/HomeController.cs
    sha1: 0788cff1303d
  - path: TalabatkAPIs/Controllers/CentrifugoController.cs
    sha1: 641e04a1329f
  - path: TalabatkAPIs/Controllers/HealthController/HealthController.cs
    sha1: c6007cb45427
  - path: TalabatkAPIs/Controllers/AreaController/AreaController.cs
    sha1: 21fd4550299a
  - path: TalabatkAPIs/Controllers/City/CityController.cs
    sha1: ebd23c16fef7
  - path: TalabatkAPIs/Controllers/FeatureMangamentController/FeatureMangamentController.cs
    sha1: 54455ef4f47d
tags: [customer-ordering, ops-and-infra, technical, api-host]
---
# Ops & Infra (Customer Ordering) — Knowledge Graph

> **Context:** Customer Ordering
> **Source Project:** `TalabatkAPIs` (6 controllers)
> **Entities:** none of its own — geography lookups read [[City.technical|City]] and
> [[Area-and-Country|Area]]
> **Register findings open here:** #616 (this host holds the **worse** of its two instances)

The platform plumbing of the customer app's host: liveness, feature flags, the geography lookups the app
needs before it can show anything, and the realtime transport endpoint. `TalabatkAPIs` is a **pure API**
— no bundled web UI — so unlike the other hosts there is no SPA bootstrap or Razor page here; its only
consumer is the customer mobile app, which is not in this repository.

## The Centrifugo proxy — the richest and least protected endpoint in the feature

`POST api/centrifugo/publish` carries **no authorisation attribute of any kind**
(`TalabatkAPIs/Controllers/CentrifugoController.cs:10-12`) and does considerably more than its delivery-host
twin:

```
POST api/centrifugo/publish
  ├── logs the ENTIRE inbound request, message body included            (:26)
  ├── data null / typing / empty  -> acknowledged, nothing persisted    (:28-33)
  ├── channel starts "DeliveryManAdmin_"  -> persists driver<->support  (:37-45)
  └── channel starts "CustomerAdmin_"     -> persists customer<->support(:47-54)
        └── may return a BroadcastOverride that REWRITES what Centrifugo
            broadcasts to connected clients: type, body, phone, username,
            timestamp, bot metadata, clickability, message id             (:56-80)
```

Three consequences, all following from the missing gate:

1. **Both** conversation kinds are injectable from this host, not just the driver one.
2. The `BroadcastOverride` means an unauthenticated caller can influence **what other clients are
   shown**, not merely what is stored — the bot-selection flow depends on it.
3. Every call writes the message body to the log.

`_conflicts.md` **#616** now records both instances, with this one noted as the worse of the two. The
contrast that makes it an omission rather than a decision is in the same repository: the Fawry webhooks
verify a SHA-256 signature before acting (see
[[Delivery/Driver Cash & Compensation/_knowledge-graph|Driver Cash & Compensation]]).

## Endpoint index

| Endpoint | Auth | What it does | Notes |
|---|---|---|---|
| `GET health` | **none** | Returns the literal `"Healthy"` | `TalabatkAPIs/Controllers/HealthController/HealthController.cs`; the fourth identical copy across the hosts — no dependency probe |
| `GET features?featureName=X` | **none** | Feature-flag read via MediatR | `TalabatkAPIs/Controllers/FeatureMangamentController/FeatureMangamentController.cs`; one of six near-identical copies — `_conflicts.md` #39/#48 |
| `GET api/Area/GetAreaByCoordinates` | JWT bearer | Resolves a latitude/longitude to a serviceable area | `TalabatkAPIs/Controllers/AreaController/AreaController.cs`; the app cannot offer stores without it |
| `api/City/*` | JWT bearer | City lookups | `TalabatkAPIs/Controllers/City/CityController.cs` |
| `POST api/centrifugo/publish` | **none** | Realtime proxy for both chat kinds, with broadcast override | 🔴 #616 — `TalabatkAPIs/Controllers/CentrifugoController.cs:10-12` |
| `GET /` (`HomeController`) | none | Host root | `TalabatkAPIs/Controllers/HomeController.cs`; the host has no SPA, so this is a stub |

## Why the geography lookups belong here rather than in Discovery

`GetAreaByCoordinates` is the app's **first** call after location permission: until a coordinate resolves
to an area, there is no city, no delivery zone, no store list and no delivery fee. It is infrastructure
in the same sense as a health check — everything downstream assumes it succeeded. The entities it reads
are owned by [[Admin/City & Geography Administration/_knowledge-graph|City & Geography Administration]];
this feature owns only the lookup surface.

## Status / State

Stateless. The only state involved is the external feature-flag store and the Centrifugo connection the
customer app holds open.

## Entity Index

| Entity | Layer | Type | Responsibility |
|---|---|---|---|
| — | — | — | This feature owns no entities. `City` and `Area` are read-only here; the chat entities it persists belong to [[Customer Ordering/Support & Chat/_knowledge-graph\|Support & Chat]] |

## Feature Flow (Business Narrative)

```
1. ORCHESTRATOR
   └── GET /health -> "Healthy" (process only; database untested)
2. APP LAUNCH
   ├── GET /features?featureName=X   -> which behaviour is enabled
   └── GET api/Area/GetAreaByCoordinates -> where the customer is, and whether it is served
3. CHAT
   └── Centrifugo proxies each publish to api/centrifugo/publish, which persists it
       and may override what other clients see
```

## Key Cross-Cutting Relationships

| From | To | Relationship | Notes |
|---|---|---|---|
| This feature | [[Admin/City & Geography Administration/_knowledge-graph\|City & Geography Administration]] | reads the geography it administers | Area resolution gates the whole customer journey |
| This feature | [[Customer Ordering/Support & Chat/_knowledge-graph\|Support & Chat]] | persists customer↔support messages | #616 lands there |
| This feature | [[Delivery/Delivery Support & Chat/_knowledge-graph\|Delivery Support & Chat]] | persists driver↔support messages | The same endpoint handles both |
| This feature | Admin flag store | flag reads | Gates customer-app behaviour |
| Customer mobile app | this feature | the only consumer | Not in this repository — behaviour beyond the API contract is inferred |

## Change Surface

| Signal | Value | Notes |
|---|---|---|
| Direct dependents (Ring 1) | the customer mobile app, orchestrator probes, both chat kinds | |
| Sides touched | 2/5 | API host · Application |
| Cross-context integrations | 3 | Centrifugo, Admin flag store, Admin geography |
| Register findings open | 1 (#616, the worse instance) + the shared #39/#48 | |
| Hub? | no — but area resolution is a single point of failure for the customer journey | |
| Risk flags | an unauthenticated endpoint that both persists messages and rewrites broadcasts; a health check that cannot detect a database outage on the host serving all customers |

<!-- BEGIN generated: endpoint index (insert-endpoints.js) -->

## Endpoint index — generated from the controllers

> Generated by `_system/insert-endpoints.js` from `_feature-map.tsv`; do not edit between the
> sentinels. Every row is anchored to a line, so `verify-citations.js` checks all of it and a
> controller that moves is caught on the next run. "Action gate" lists only attributes on the action
> itself — the class gate above each table still applies unless an action opts out of it.

**6 controller(s), 5 action(s)**; 5 have no action-level gate and rely entirely on the class attribute.

#### `TalabatkAPIs/Controllers/AreaController/AreaController.cs`

Class gate: JWT bearer — `TalabatkAPIs/Controllers/AreaController/AreaController.cs:17`

| Route | Verb | Action gate | Anchor |
|---|---|---|---|
| `api/Area/GetAreaByCoordinates` | GET | — | `TalabatkAPIs/Controllers/AreaController/AreaController.cs:33` |

#### `TalabatkAPIs/Controllers/CentrifugoController.cs`

Class gate: **no auth attribute on the class** — `TalabatkAPIs/Controllers/CentrifugoController.cs:12`

| Route | Verb | Action gate | Anchor |
|---|---|---|---|
| `publish` | POST | — | `TalabatkAPIs/Controllers/CentrifugoController.cs:24` |

#### `TalabatkAPIs/Controllers/City/CityController.cs`

Class gate: JWT bearer — `TalabatkAPIs/Controllers/City/CityController.cs:19`

| Route | Verb | Action gate | Anchor |
|---|---|---|---|

#### `TalabatkAPIs/Controllers/FeatureMangamentController/FeatureMangamentController.cs`

Class gate: **no auth attribute on the class** — `TalabatkAPIs/Controllers/FeatureMangamentController/FeatureMangamentController.cs:10`

| Route | Verb | Action gate | Anchor |
|---|---|---|---|
| `CheckFeature` | GET | — | `TalabatkAPIs/Controllers/FeatureMangamentController/FeatureMangamentController.cs:20` |

#### `TalabatkAPIs/Controllers/HealthController/HealthController.cs`

Class gate: **no auth attribute on the class** — `TalabatkAPIs/Controllers/HealthController/HealthController.cs:7`

| Route | Verb | Action gate | Anchor |
|---|---|---|---|
| `Get` | GET | — | `TalabatkAPIs/Controllers/HealthController/HealthController.cs:10` |

#### `TalabatkAPIs/Controllers/HomeController.cs`

Class gate: **no auth attribute on the class** — `TalabatkAPIs/Controllers/HomeController.cs:5`

| Route | Verb | Action gate | Anchor |
|---|---|---|---|
| `Index` | — | — | `TalabatkAPIs/Controllers/HomeController.cs:7` |

<!-- END generated: endpoint index -->

## Open Questions

- [ ] Is `api/centrifugo/publish` restricted to the Centrifugo server's network? That is the only control
      standing between #616 and forged customer-support messages.
- [ ] What does the `BroadcastOverride` path exist for? It appears to serve the chat bot's selection
      flow, but the bot's contract was not traced here.
- [ ] Should the full request body be logged on every publish (`TalabatkAPIs/Controllers/CentrifugoController.cs:26`)? It puts message content in the log.
- [ ] Should `/health` probe the database? This host serves every customer.
- [ ] What does the app do when `GetAreaByCoordinates` returns no serviceable area — is there a defined
      out-of-coverage experience?
- [ ] Which flags does the customer app read at launch?
