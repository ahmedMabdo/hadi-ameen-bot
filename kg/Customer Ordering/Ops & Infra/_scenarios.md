---
id: 8orders/customer-ordering/ops-and-infra/scenarios
title: Ops & Infra (Customer Ordering) — Scenario Catalog
note_type: scenarios
context: Customer Ordering
feature: Ops & Infra
audience: Business · QA · Developer
last_updated: 2026-08-23
sources:
  - path: TalabatkAPIs/Controllers/CentrifugoController.cs
    sha1: 641e04a1329f
  - path: TalabatkAPIs/Controllers/HealthController/HealthController.cs
    sha1: c6007cb45427
  - path: TalabatkAPIs/Controllers/AreaController/AreaController.cs
    sha1: 21fd4550299a
  - path: TalabatkAPIs/Controllers/FeatureMangamentController/FeatureMangamentController.cs
    sha1: 54455ef4f47d
tags: [customer-ordering, ops-and-infra, scenarios]
---
# Ops & Infra (Customer Ordering) — Scenario Catalog

> Small feature, large consequences: area resolution gates the whole customer journey, and the chat
> proxy here is the more capable of the two unauthenticated Centrifugo endpoints.

## Happy path

| # | Precondition | Action | Expected outcome | Rule / source |
|---|---|---|---|---|
| H1 | Process running | `GET health` | `200 "Healthy"` | `TalabatkAPIs/Controllers/HealthController/HealthController.cs` |
| H2 | App launching | `GET features?featureName=X` | Flag value; app adjusts | `TalabatkAPIs/Controllers/FeatureMangamentController/FeatureMangamentController.cs` |
| H3 | Customer grants location permission, inside coverage | `GET api/Area/GetAreaByCoordinates` | The serviceable area; browsing can begin | `TalabatkAPIs/Controllers/AreaController/AreaController.cs` |
| H4 | Area known | city lookup | The city, from which delivery zones and fees follow | `TalabatkAPIs/Controllers/City/CityController.cs` |
| H5 | Customer sends a support message | Centrifugo proxies it | Persisted against the customer↔support conversation | `TalabatkAPIs/Controllers/CentrifugoController.cs:47-54` |
| H6 | Bot offers selectable options | proxy responds | A broadcast override supplies what connected clients render | `TalabatkAPIs/Controllers/CentrifugoController.cs:56-80` |

## Partial / incremental

| # | Precondition | Action | Expected outcome | Rule / source |
|---|---|---|---|---|
| P1 | Someone is typing | proxy receives a typing message | Acknowledged, **not persisted** | `TalabatkAPIs/Controllers/CentrifugoController.cs:28-33` |
| P2 | Empty payload | proxy receives it | Acknowledged and skipped | `TalabatkAPIs/Controllers/CentrifugoController.cs:28-33` |
| P3 | Driver↔support message arrives on the customer host | proxy routes it | Handled here too — this endpoint serves **both** channel prefixes | `TalabatkAPIs/Controllers/CentrifugoController.cs:37`, `:47-48` |
| P4 | Customer outside coverage | area lookup | No serviceable area returned; the app's handling is outside this repository | `TalabatkAPIs/Controllers/AreaController/AreaController.cs` |

## Negative / guard

| # | Precondition | Action | Expected outcome (rejection) | Rule / source |
|---|---|---|---|---|
| N1 | No token | `GET api/Area/GetAreaByCoordinates` | 401 — JWT bearer required | `TalabatkAPIs/Controllers/AreaController/AreaController.cs` |
| N2 | No token | city lookups | 401 | `TalabatkAPIs/Controllers/City/CityController.cs` |
| N3 | No token | `GET features` | **Accepted** — no authorisation on the flag endpoint | ⚠️ `_conflicts.md` #39/#48 |
| N4 | No token | `POST api/centrifugo/publish` | **Accepted** — no authorisation attribute of any kind | 🔴 `TalabatkAPIs/Controllers/CentrifugoController.cs:10-12` · #616 |
| N5 | Channel prefix unknown | proxy receives it | Acknowledged with success and nothing persisted — probing is quiet | `TalabatkAPIs/Controllers/CentrifugoController.cs:37-54` |
| N6 | Database unavailable | `GET health` | Still `200 "Healthy"` | `TalabatkAPIs/Controllers/HealthController/HealthController.cs` |

## Returns / cancellation / reversal

| # | Precondition | Action | Expected outcome | Rule / source |
|---|---|---|---|---|
| R1 | Message persisted via the proxy | — | No delete path on this endpoint | `TalabatkAPIs/Controllers/CentrifugoController.cs` |
| R2 | Flag flipped in Admin | app restarted | New behaviour; no release needed — but see #614, the flag write can report false success | 🔴 `_conflicts.md` #614 |
| R3 | Customer moves to another area | area lookup again | Resolution is per call, so it follows the customer | `TalabatkAPIs/Controllers/AreaController/AreaController.cs` |

## Integration (cross-side / cross-context)

| # | Precondition | Action | Expected outcome | Rule / source |
|---|---|---|---|---|
| I1 | Any chat message | Centrifugo → this host | Persisted, and possibly re-broadcast with overridden content | `TalabatkAPIs/Controllers/CentrifugoController.cs:56-80` |
| I2 | Area resolution | reads Admin geography | Cities, areas and zones administered in [[Admin/City & Geography Administration/_knowledge-graph\|City & Geography Administration]] | |
| I3 | Flag read | Admin flag store | One of six near-identical controllers | `_conflicts.md` #39, #48 |
| I4 | Customer support conversation | Admin dashboards | The same conversation appears in [[Admin/Chat Administration/_knowledge-graph\|Chat Administration]] | `_integrations.md` row 2 |
| I5 | Customer app | this host | The only consumer; not in this repository, so behaviour beyond the API contract is inferred | `references/repo-map.md` |

## Exposure scenarios — current behaviour

| # | Precondition | Action | Actual outcome today | Finding |
|---|---|---|---|---|
| X1 | **No credential** | `POST api/centrifugo/publish` with a `CustomerAdmin_` channel | A message is persisted into a customer↔support conversation and shown as genuine | 🔴 `_conflicts.md` **#616** · `TalabatkAPIs/Controllers/CentrifugoController.cs:47-54` |
| X2 | Same, with a `DeliveryManAdmin_` channel | same endpoint | Driver↔support conversation injected from the customer host | 🔴 #616 · `TalabatkAPIs/Controllers/CentrifugoController.cs:37-45` |
| X3 | Same, customer-admin channel | response returns a broadcast override | **What other connected clients are shown** is replaced — content, sender name, phone, timestamp | 🔴 #616 · `TalabatkAPIs/Controllers/CentrifugoController.cs:56-80` |
| X4 | Anyone with log access | read the service log | Every chat message body, logged on each publish | ⚠️ `TalabatkAPIs/Controllers/CentrifugoController.cs:26` |
| X5 | No token | `GET features?featureName=<guess>` | Flag values for any name tried | ⚠️ #39/#48 |
| X6 | Database down | orchestrator probes `/health` | Host stays in rotation for every customer | ⚠️ `TalabatkAPIs/Controllers/HealthController/HealthController.cs` |

## Open Questions

- [ ] Is the proxy endpoint network-restricted to the Centrifugo server? X1–X3 depend entirely on it.
- [ ] What is the `BroadcastOverride` for, and can it be constrained to bot-originated flows only?
- [ ] Should message bodies be logged on every publish (X4)?
- [ ] Should `/health` probe the database on the host that serves all customers?
- [ ] What is the defined out-of-coverage experience when area resolution finds nothing (P4)?
- [ ] Which flags does the customer app read at launch, and what happens if the flag endpoint is
      unavailable?
