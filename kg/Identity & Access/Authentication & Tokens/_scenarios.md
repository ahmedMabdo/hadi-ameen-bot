---
id: 8orders/identity-and-access/authentication-and-tokens/scenarios
title: Authentication & Tokens — Scenario Catalog
note_type: scenarios
context: Identity & Access
feature: Authentication & Tokens
audience: Business · QA · Developer
last_updated: 2026-08-23
sources:
  - path: Talabatk.IDS/Controllers/Account/AccountController.cs
    sha1: 9c1caf8ae094
  - path: Talabatk.IDS/Configurations/Identity.cs
    sha1: 9ac57860f5a7
  - path: Talabatk.IDS/Controllers/Account/ExternalController.cs
    sha1: 7fd2e6579cee
tags: [identity-and-access, authentication-and-tokens, scenarios]
---
# Authentication & Tokens — Scenario Catalog

> One sign-in surface serves every user type, so every row applies to customers, drivers, merchant staff
> and back-office admins alike unless it names a role.

## Happy path

| # | Precondition | Action | Expected outcome | Rule / source |
|---|---|---|---|---|
| H1 | Client redirects with a valid `returnUrl` | `GET /Account/Login` | Form rendered, authorization context resolved | `Talabatk.IDS/Controllers/Account/AccountController.cs:61-63` |
| H2 | Correct credentials, native client | `POST /Account/Login` | Success event raised, attendance written, loading-page redirect returned | `:150-164` |
| H3 | Correct credentials, local `returnUrl` | `POST /Account/Login` | Redirect to that URL | `:170-173` |
| H4 | Correct credentials, empty `returnUrl` | `POST /Account/Login` | Redirect to the host root | `:174-177` |
| H5 | Any successful sign-in | — | `AddOperationAttendanceCommand` records the user id | `:156` |
| H6 | Signed in | `POST /Account/Logout` | Session ended | `:228-231` |
| H7 | External provider configured | `GET /External/Challenge` | Redirected to the provider | `ExternalController.cs:53-54` |
| H8 | Provider returns | `GET /External/Callback` | Provider result turned into a local session | `ExternalController.cs:83-84` |

## Partial / incremental

| # | Precondition | Action | Expected outcome | Rule / source |
|---|---|---|---|---|
| P1 | User clicks Cancel with a valid authorization context | `POST /Account/Login`, button not "login" | `DenyAuthorizationAsync` — the client receives an OIDC access-denied, as if consent were refused | `:92-107` |
| P2 | Same, no valid context | `POST /Account/Login`, button not "login" | Redirect to the host root | `:110-114` |
| P3 | Signed in; a token was already issued | `POST /Account/Logout` | Session ends, issued token remains valid to expiry — no revocation here | `:228-231` |

## Negative / guard

| # | Precondition | Action | Expected outcome (rejection) | Rule / source |
|---|---|---|---|---|
| N1 | Unknown username | `POST /Account/Login` | Generic invalid-username-or-password message; no account-existence disclosure | `:120-126` |
| N2 | Wrong password | `POST /Account/Login` | Failure event raised, generic error shown, **and nothing counted** | `:150`, `:189-190` |
| N3 | Merchant role on the legacy portal client | `POST /Account/Login` | Refused, told the portal moved — even with correct credentials | `:132-140` |
| N4 | Merchant role on the admin SPA client | `POST /Account/Login` | Refused as unauthorized | `:142-148` |
| N5 | Missing or invalid anti-forgery token | `POST /Account/Login` | Rejected by the anti-forgery filter | `:82` |
| N6 | Password shorter than 6 characters | account creation | Rejected — the only password rule that bites | `Identity.cs:200` |
| N7 | Password of six identical letters | account creation | **Accepted** — no digit, case, symbol or uniqueness requirement | `Identity.cs:196-201` |
| N8 | 500 wrong passwords for one account | repeated `POST /Account/Login` | **All 500 attempted; the account is never locked** | 🔴 `:150` · `_conflicts.md` #612 |

## Returns / cancellation / reversal

| # | Precondition | Action | Expected outcome | Rule / source |
|---|---|---|---|---|
| R1 | Signed in | logout | Session ended; a new sign-in is needed for a new session | `:228-231` |
| R2 | Token issued, then user logged out | reuse the old token | Still accepted by API hosts until it expires | `:208-231` |
| R3 | Consent denied (P1) | client retries | Client receives access-denied and may start again | `:99` |

## Integration (cross-side / cross-context)

| # | Precondition | Action | Expected outcome | Rule / source |
|---|---|---|---|---|
| I1 | Sign-in succeeds | token issued to the client | Validated independently by `Shared/SharedWeb`, `TalabatkAPIs`, `TalabatkRestaurants` and `TalabatkDelivery` — **four separate copies** of the validation code | `_integrations.md` row 3 |
| I2 | Back-office user signs in | attendance command | Attendance row written in the Admin domain | `:156` |
| I3 | Merchant signs in on the legacy portal client | client and role gate | Told the portal moved — a URL change means editing this controller | `:132-140` |
| I4 | Driver resets a password | — | **Bypasses this feature entirely** through the anonymous driver reset path | `_conflicts.md` #509; [[Identity & Access/Delivery Man Identity/_knowledge-graph\|Delivery Man Identity]] |
| I5 | Customer resets a password | — | Goes through the verified customer path | [[Identity & Access/Customer Identity/_knowledge-graph\|Customer Identity]] |

## Security scenarios — current behaviour

| # | Precondition | Action | Actual outcome today | Finding |
|---|---|---|---|---|
| X1 | Attacker knows any username | guess passwords in a loop | **Unlimited attempts; no lockout ever applies** — the configured policy at `Identity.cs:204-206` is opted out of at the call site | 🔴 #612 · `:150` |
| X2 | Same, targeting an administrator | as above | Identical exposure — one login surface serves every user type | 🔴 #612 |
| X3 | Correct credentials, return URL neither local nor empty | `POST /Account/Login` | Sign-in **succeeds** and the audit log records an invalid-credentials failure for it | 🔴 #613 · `:181-183` |
| X4 | Investigator counts failed logins during an incident | read the audit log | The count includes successful sign-ins (X3), so it cannot be trusted in either direction | 🔴 #613 |
| X5 | Token validation rules change in one host | deploy | The other three keep the old rules; nothing detects the divergence | ⚠️ `_integrations.md` row 3 |

## Open Questions

- [ ] Was disabling lockout deliberate (avoiding support calls from locked-out merchants) or copied from
      the IdentityServer4 quickstart, which ships it enabled?
- [ ] Is there rate limiting in front of the login POST at a gateway? Nothing in code, and it is the only
      thing that would blunt X1.
- [ ] Does logout revoke refresh tokens, or only the session cookie (R2)?
- [ ] Which external providers are registered? The controller is generic over the scheme name; the
      registered schemes were not enumerated in this pass.
- [ ] Should a customer sign-in write an attendance row (I2), or is that intended for staff only?
- [ ] Do the four validator copies currently agree? Not diffed in this pass.
