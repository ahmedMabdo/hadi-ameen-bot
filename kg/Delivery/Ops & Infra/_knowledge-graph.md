---
id: 8orders/delivery/ops-and-infra/knowledge-graph
title: Ops & Infra (Delivery) — Knowledge Graph
note_type: knowledge-graph
context: Delivery
feature: Ops & Infra
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
tags: [delivery, ops-and-infra, technical, api-host]
---
# Ops & Infra (Delivery) — Knowledge Graph

> **Context:** Delivery
> **Source Project:** `TalabatkDelivery` (4 controllers, 5 actions)
> **Entities:** none of its own
> **Register findings open here:** #39/#48 (the duplicated flag controller), and #616 is documented in
> [[Delivery/Delivery Support & Chat/_knowledge-graph|Delivery Support & Chat]] because that is where its
> effect lands

The platform plumbing of the driver app's host: liveness, feature flags, the host's own web root, and
the realtime transport endpoint. `TalabatkDelivery` differs from the two Angular hosts in one way that
matters here — it serves **Razor MVC views**, not a SPA, so its `HomeController` is a real web page
rather than a bootstrap shell.

## Endpoint index

| Endpoint | Auth | What it does | Notes |
|---|---|---|---|
| `GET health` | **none** | Returns the literal `"Healthy"` | Identical to the Restaurant Portal and identity-host copies, down to the string — `TalabatkDelivery/Controllers/Apis/HealthController/HealthController.cs:9-13`. No dependency probe: the database, Centrifugo and the identity host are all untested by it |
| `GET features?featureName=X` | **none** | Feature-flag read via MediatR `GetFeatureFlagQuery` | `TalabatkDelivery/Controllers/Apis/FeatureMangamentController/FeatureMangamentController.cs:20-27` — the **fourth** near-identical copy of this controller; `_conflicts.md` #39/#48 |
| `GET /Home/Index` | none | Razor landing page | `TalabatkDelivery/Controllers/HomeController.cs:12-15` |
| `GET /Home/Login` | `[Authorize]` | Returns the **`Index`** view, not a login form — the attribute triggers the OIDC challenge and the view is incidental | `TalabatkDelivery/Controllers/HomeController.cs:17-21` |
| `GET /Home/Logout` | none | Signs out of **both** the cookie and OpenID Connect schemes | `TalabatkDelivery/Controllers/HomeController.cs:23-26` |
| `POST api/centrifugo/publish` | **none** | Realtime proxy — documented in [[Delivery/Delivery Support & Chat/_knowledge-graph\|Delivery Support & Chat]] | 🔴 `_conflicts.md` #616 · `TalabatkDelivery/Controllers/Apis/CentrifugoController.cs:19-40` |

## The login/logout asymmetry, and why it is worth knowing

```
GET /Home/Login   [Authorize]  -> OIDC challenge -> identity host -> back here -> renders "Index"
GET /Home/Logout  (no auth)    -> SignOut(Cookie, OpenIdConnect)
```

`Login` is not a form; it is an `[Authorize]`-decorated action whose only job is to provoke the
authentication challenge, after which it renders the same view as `Index`
(`TalabatkDelivery/Controllers/HomeController.cs:17-21`). `Logout` carries **no** `[Authorize]`, and
signs out of both the local cookie and the OIDC session
(`TalabatkDelivery/Controllers/HomeController.cs:23-26`) — so an unauthenticated request to it is
harmless but also always accepted.

This host is therefore a **cookie + OIDC** web application as well as a bearer-token API: the MVC
controllers use the cookie scheme (see the mixed
`JwtBearerDefaults.AuthenticationScheme + "," + CookieAuthenticationDefaults.AuthenticationScheme`
on the operations map in [[Delivery/Delivery Man Operations/_knowledge-graph|Delivery Man Operations]]),
while the driver app uses bearer tokens. Two authentication models in one host is the single most
useful fact in this note for anyone adding an endpoint here: **you have to decide which scheme your new
action belongs to**, and the existing controllers do not make that obvious.

## The flag-controller copy, counted

`GET features` in this host is byte-similar to the same controller in `Talabatk.IDS`, `AdminUi` and
`TalabatkRestaurants`. The full four-mechanism picture is stated once, in
[[Restaurant Portal/Ops & Infra/_knowledge-graph|Ops & Infra (Restaurant Portal)]]; here it is enough to
record that this is one of the copies (#39 counts four instances, #48 counts six across the wider set)
and that, as everywhere else, **it requires no authentication**.

## Status / State

Stateless. The only state involved is the external feature-flag store, and the authentication cookie
this host issues after an OIDC round trip.

## Entity Index

| Entity | Layer | Type | Responsibility |
|---|---|---|---|
| — | — | — | This feature owns no entities |

## Feature Flow (Business Narrative)

```
1. ORCHESTRATOR
   └── GET /health -> "Healthy" (process only; nothing downstream is checked)
2. DRIVER APP BOOTSTRAP
   └── GET /features?featureName=X -> enables or hides app behaviour
3. STAFF OPEN THE WEB CONSOLE
   ├── /Home/Index      -> landing page
   ├── /Home/Login      -> [Authorize] provokes the OIDC challenge, then renders Index
   └── /Home/Logout     -> signs out of cookie AND OIDC
4. REALTIME
   └── Centrifugo proxies chat publishes to api/centrifugo/publish  (see Delivery Support & Chat)
```

## Key Cross-Cutting Relationships

| From | To | Relationship | Notes |
|---|---|---|---|
| This feature | [[Identity & Access/Authentication & Tokens/_knowledge-graph\|Authentication & Tokens]] | OIDC sign-in and sign-out | This host is an OIDC **client**, unlike the pure APIs |
| This feature | Admin flag store | reads feature flags | Flags gate driver-app behaviour such as `MultipleDeliveries` |
| This feature | [[Delivery/Delivery Support & Chat/_knowledge-graph\|Delivery Support & Chat]] | owns the Centrifugo endpoint's effect | #616 |
| Every Delivery feature | this one | flag reads decide behaviour | `MultipleDeliveries` and `DeliverymenOrdersV1` both branch driver logic |
| Orchestrator | `/health` | liveness | Shallow by design |

## Change Surface

| Signal | Value | Notes |
|---|---|---|
| Direct dependents (Ring 1) | driver app bootstrap, orchestrator probe, staff web console | |
| Sides touched | 2/5 | API host · server-rendered views |
| Cross-context integrations | 3 | Identity (OIDC), Admin (flags), Centrifugo |
| Register findings open | 2 shared (#39/#48) + #616 owned elsewhere | |
| Hub? | no | |
| Risk flags | two authentication schemes in one host — a new endpoint can silently pick the wrong one |

## Open Questions

- [ ] Which flags does the driver app actually read at bootstrap? `MultipleDeliveries` and
      `DeliverymenOrdersV1` are known to branch server-side behaviour; the client-side set is unlisted.
- [ ] Should `/health` probe the database, the identity host and Centrifugo? As written it cannot detect
      any of them being down, and this host's failure mode is drivers unable to work.
- [ ] Is `/Home/Index` meant to be publicly reachable, and what does it show to an anonymous visitor?
- [ ] Should `/Home/Logout` require authentication? Harmless today, but it accepts anonymous calls.
- [ ] Are the Razor MVC screens in this host (operations map, shifts, reasons) still used, or superseded
      by `AdminUi`? Several overlap with Admin features.
