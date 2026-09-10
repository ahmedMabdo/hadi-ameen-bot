---
id: 8orders/delivery/ops-and-infra/scenarios
title: Ops & Infra (Delivery) — Scenario Catalog
note_type: scenarios
context: Delivery
feature: Ops & Infra
audience: Business · QA · Developer
last_updated: 2026-08-23
sources:
  - path: TalabatkDelivery/Controllers/Apis/HealthController/HealthController.cs
    sha1: b5c43571ef02
  - path: TalabatkDelivery/Controllers/Apis/FeatureMangamentController/FeatureMangamentController.cs
    sha1: 7243f2c22e0d
  - path: TalabatkDelivery/Controllers/HomeController.cs
    sha1: 6d80568f153e
  - path: TalabatkDelivery/Controllers/Apis/CentrifugoController.cs
    sha1: 31932d0044dd
tags: [delivery, ops-and-infra, scenarios]
---
# Ops & Infra (Delivery) — Scenario Catalog

> Small feature, two authentication schemes. Every row states which one applies, because that is the
> thing most easily got wrong when adding an endpoint to this host.

## Happy path

| # | Precondition | Action | Expected outcome | Rule / source |
|---|---|---|---|---|
| H1 | Process running | `GET health` | `200 "Healthy"` | `TalabatkDelivery/Controllers/Apis/HealthController/HealthController.cs:9-13` |
| H2 | Flag exists | `GET features?featureName=MultipleDeliveries` | Current value via MediatR | `TalabatkDelivery/Controllers/Apis/FeatureMangamentController/FeatureMangamentController.cs:20-27` |
| H3 | Staff member, no session | `GET /Home/Login` | `[Authorize]` provokes the OIDC challenge; after sign-in the `Index` view renders | `TalabatkDelivery/Controllers/HomeController.cs:17-21` |
| H4 | Staff member with a session | `GET /Home/Index` | Landing page | `TalabatkDelivery/Controllers/HomeController.cs:12-15` |
| H5 | Staff member done for the day | `GET /Home/Logout` | Signed out of **both** the cookie and the OIDC session | `TalabatkDelivery/Controllers/HomeController.cs:23-26` |
| H6 | Driver app starts | reads its flags | Behaviour adjusts — e.g. whether multiple simultaneous deliveries are offered | `TalabatkDelivery/Controllers/Apis/FeatureMangamentController/FeatureMangamentController.cs:20-27` |

## Partial / incremental

| # | Precondition | Action | Expected outcome | Rule / source |
|---|---|---|---|---|
| P1 | Flag flipped in Admin | driver app restarted | New behaviour, no deployment needed | flag store owned by [[Admin/Admin Back-Office/_knowledge-graph\|Admin Back-Office]] |
| P2 | Staff already signed in | `GET /Home/Login` again | No challenge; the `Index` view renders directly | `TalabatkDelivery/Controllers/HomeController.cs:17-21` |
| P3 | Driver app on a bearer token, staff on a cookie | both hit this host | Both are accepted — the host runs two schemes side by side | see the operations-map controller's mixed scheme in [[Delivery/Delivery Man Operations/_knowledge-graph\|Delivery Man Operations]] |

## Negative / guard

| # | Precondition | Action | Expected outcome (rejection) | Rule / source |
|---|---|---|---|---|
| N1 | No `featureName` | `GET features` | `400` — the parameter is validated | `TalabatkDelivery/Controllers/Apis/FeatureMangamentController/FeatureMangamentController.cs:20-27` |
| N2 | No session | `GET /Home/Login` | Redirected to the identity host rather than refused | `TalabatkDelivery/Controllers/HomeController.cs:17` |
| N3 | Database unavailable | `GET health` | Still `200 "Healthy"` — nothing downstream is probed | `TalabatkDelivery/Controllers/Apis/HealthController/HealthController.cs:9-13` |
| N4 | No session | `GET /Home/Logout` | **Accepted** — no `[Authorize]`; the sign-out is simply a no-op | `TalabatkDelivery/Controllers/HomeController.cs:23-26` |
| N5 | No token | `POST api/centrifugo/publish` | **Accepted** — see [[Delivery/Delivery Support & Chat/_scenarios\|Delivery Support & Chat]] X1 | 🔴 `TalabatkDelivery/Controllers/Apis/CentrifugoController.cs:19-40` |

## Returns / cancellation / reversal

| # | Precondition | Action | Expected outcome | Rule / source |
|---|---|---|---|---|
| R1 | Signed in by mistake | `GET /Home/Logout` | Both sessions ended | `TalabatkDelivery/Controllers/HomeController.cs:23-26` |
| R2 | Flag turned on in error | flip it back in Admin | Symmetric — but see #614: the flag-write endpoint can report success while failing | 🔴 `_conflicts.md` #614 |

## Integration (cross-side / cross-context)

| # | Precondition | Action | Expected outcome | Rule / source |
|---|---|---|---|---|
| I1 | Staff sign-in | OIDC round trip | This host is an OIDC **client** of [[Identity & Access/Authentication & Tokens/_knowledge-graph\|Authentication & Tokens]] | `TalabatkDelivery/Controllers/HomeController.cs:17-26` |
| I2 | Flag read | Admin flag store | Same store the other three copies of this controller read | `_conflicts.md` #39, #48 |
| I3 | Chat message | Centrifugo | Proxied to this host — effect documented under Delivery Support & Chat | 🔴 `_conflicts.md` #616 |
| I4 | Orchestrator probe | `GET health` | Host kept in rotation while it answers | `TalabatkDelivery/Controllers/Apis/HealthController/HealthController.cs:9-13` |

## Exposure scenarios — current behaviour

| # | Precondition | Action | Actual outcome today | Finding |
|---|---|---|---|---|
| X1 | **No token** | `GET features?featureName=<guess>` | Flag state for any name tried | ⚠️ `_conflicts.md` #39/#48 |
| X2 | No token | `GET health` | Confirms the host exists and is reachable | accepted for a liveness probe |
| X3 | No token | `POST api/centrifugo/publish` | Message injection — full detail in [[Delivery/Delivery Support & Chat/_scenarios\|Delivery Support & Chat]] | 🔴 #616 |
| X4 | Flag changed via the identity host's write endpoint, Esquio unreachable | `PUT api/Features/ChangeState` | Reports success; this host keeps reading the old value | 🔴 #614 |

## Open Questions

- [ ] Which flags does the driver app read at bootstrap? Only the server-side branches
      (`MultipleDeliveries`, `DeliverymenOrdersV1`) are known.
- [ ] Should `/health` probe the database, the identity host and Centrifugo? This host's failure stops
      drivers working, so a shallow probe is a real gap.
- [ ] What does `/Home/Index` show an anonymous visitor?
- [ ] Are this host's Razor screens (operations map, shifts, reasons) still in use, or superseded by
      `AdminUi`? Several overlap.
- [ ] Should `/Home/Logout` require authentication (N4)?
