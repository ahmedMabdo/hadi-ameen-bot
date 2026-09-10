---
id: 8orders/identity-and-access/authentication-and-tokens/knowledge-graph
title: Authentication & Tokens — Knowledge Graph
note_type: knowledge-graph
context: Identity & Access
feature: Authentication & Tokens
last_updated: 2026-08-23
sources:
  - path: Talabatk.IDS/Controllers/Account/AccountController.cs
    sha1: 9c1caf8ae094
  - path: Talabatk.IDS/Configurations/Identity.cs
    sha1: 9ac57860f5a7
  - path: Talabatk.IDS/Controllers/Account/ExternalController.cs
    sha1: 7fd2e6579cee
  - path: Talabatk.IDS/Controllers/Account/HomeController.cs
    sha1: 67f57911cc26
tags: [identity-and-access, authentication-and-tokens, technical, api-host]
---
# Authentication & Tokens — Knowledge Graph

> **Context:** Identity & Access
> **Source Project:** `Talabatk.IDS` — IdentityServer4 host: `Controllers/Account/` (3 controllers) +
> `Configurations/Identity.cs`
> **Entities:** [[Identity.technical|Identity]], [[Login-and-Activation|Login & Activation]],
> `AspNetUser` / `AspNetRole`
> **Register findings open here:** #612, #613, plus the four-copy token-validation drift (row 3 of the
> integration register)

This is the front door for **every** human user of 8Orders — customers, delivery men, merchant staff
and back-office admins all authenticate here, and every other service in the system trusts what this
one issues. There is exactly one interactive sign-in surface, which makes its two defects unusually
consequential: they are not "a" login's problems, they are the system's.

## The sign-in path, step by step

`AccountController` is `[AllowAnonymous]` at class level (`Talabatk.IDS/Controllers/Account/AccountController.cs:27`) — correct for a
login page — and the POST is CSRF-protected with `[ValidateAntiForgeryToken]` (`:82`).

```
GET  /Account/Login?returnUrl=…            -> render the form (:61-63)
POST /Account/Login                        -> (:81-83)
      ├── button != "login"  -> DenyAuthorizationAsync -> back to the client as access_denied (:92-115)
      ├── user not found     -> generic "Invalid User name Or Password" (:120-126)
      ├── client/role gates  -> see the table below                     (:128-148)
      ├── PasswordSignInAsync(..., lockoutOnFailure: FALSE)             (:150)   <-- #612
      │     ├── success -> UserLoginSuccessEvent + AddOperationAttendanceCommand (:155-156)
      │     │      ├── native client   -> LoadingPage("Redirect", returnUrl)     (:159-164)
      │     │      ├── local returnUrl -> Redirect                               (:170-173)
      │     │      ├── empty returnUrl -> Redirect("~/")                          (:174-177)
      │     │      └── otherwise -> UserLoginFAILUREEvent + "Url Is not accepted" (:181-183) <-- #613
      │     └── failure -> UserLoginFailureEvent + InvalidCredentialsErrorMessage (:189-190)
      └── ModelState invalid -> redisplay the form                                (:194-195)
```

### Client-and-role gates at sign-in

Authorisation happens partly *at login*, keyed on the OIDC client id, which is unusual enough to
record:

| Client id | Roles | Outcome | Source |
|---|---|---|---|
| `mvc.owin.hybrid` | `Merchant`, `MerchantAdmin` or `OrdinaryMerchant` | Refused with "the Restaurant Website had been Changed to {url}" — a **migration notice delivered as a login error** | `Talabatk.IDS/Controllers/Account/AccountController.cs:134-142` |
| `AdminAngularClient` | `Merchant` or `MerchantAdmin` | Refused with `"UnAuthorized"` — merchants may not use the admin SPA | `:142-148` |
| any other | any | Proceeds to `PasswordSignInAsync` | `:150` |

A merchant hitting the old portal is therefore told the site moved, at the login form, by the identity
service. Functional, but it means a URL change requires a change here rather than in the portal.

## The two defects

> ⚠️ **CONFIRMED — the lockout policy is configured and then opted out of**
> `Configurations/Identity.cs:204-206` sets `MaxFailedAccessAttempts = 5`,
> `DefaultLockoutTimeSpan = 5 minutes`, `AllowedForNewUsers = true`. The single interactive login then
> calls `PasswordSignInAsync(model.Username, model.Password, model.RememberLogin, lockoutOnFailure: false)`
> (`Talabatk.IDS/Controllers/Account/AccountController.cs:150`), so **failed attempts are never counted and no account is ever locked.**
> Unlimited password guessing is possible against every user type. This is worse than having no policy,
> because the configuration block reads as protection to anyone reviewing it.
> `_conflicts.md` **#612**.
>
> The password policy in the same block compounds it: 6 characters minimum with `RequireDigit`,
> `RequireLowercase`, `RequireUppercase` and `RequireNonAlphanumeric` all `false` and
> `RequiredUniqueChars = 0` (`Identity.cs:196-201`) — `aaaaaa` is a legal password for an admin.

> ⚠️ **CONFIRMED — a successful login can be written to the audit log as a failure**
> Inside the `if (result.Succeeded)` branch, the final `else` (return URL neither local nor empty)
> raises `UserLoginFailureEvent(model.Username, "invalid credentials")` (`Talabatk.IDS/Controllers/Account/AccountController.cs:182-183`)
> — for a login whose credentials were correct. The same request has already raised
> `UserLoginSuccessEvent` at `:155`. Any incident investigation or alert rule counting failed logins is
> reading a signal that does not mean what it says. `_conflicts.md` **#613**.

Also present, and deliberately *not* raised as findings: a `try { … } catch (Exception exp) { throw; }`
wrapper around the whole action (`:85`, `:197-200`) that catches and rethrows without adding anything,
and `AccountOptions` / `ExternalProvider` living in `Controllers/Account/` although neither is an
endpoint (both are classified `non-controller` in `_feature-map.tsv` with that reason).

## Endpoint index

| Endpoint | Auth | What it does | Notes |
|---|---|---|---|
| `GET /Account/Login` | `[AllowAnonymous]` (class) | Renders the login form | `Talabatk.IDS/Controllers/Account/AccountController.cs:61-63` |
| `POST /Account/Login` | anonymous + `[ValidateAntiForgeryToken]` | Authenticates; issues the IdentityServer session | 🔴 #612, #613 — `:81-83` |
| `GET /Account/Logout` | `[AllowAnonymous]` | Shows the logout page | `:208-210` |
| `POST /Account/Logout` | `[AllowAnonymous]` | Performs sign-out | `:228-231` |
| `GET /Account/AccessDenied` | class-level anonymous | Access-denied page | `:260-261` |
| `GET /External/Challenge` | `[AllowAnonymous]` (class, `:24`) | Starts an external-provider sign-in | `ExternalController.cs:53-54` |
| `GET /External/Callback` | `[AllowAnonymous]` | Handles the provider's callback | `ExternalController.cs:83-84` |
| `GET /Home/Index` · `Error` · `Privacy` · `RedirectToadmin` | `[AllowAnonymous]` (class, `:13`) | IdentityServer quickstart pages | `Talabatk.IDS/Controllers/Account/HomeController.cs:32,44,61,65` |

## Status / State — what a session actually is

```
anonymous
   └── POST /Account/Login (correct credentials)
         └── IdentityServer session cookie established
               ├── OIDC authorization code -> client exchanges it for a JWT
               │      └── every API host validates that JWT with ITS OWN COPY of the checking code
               └── POST /Account/Logout -> session ended (client tokens already issued remain valid
                     until they expire — no server-side revocation is performed here)
```

Token *validation* is the important asymmetry: issuance is centralised here, and validation is
**duplicated four times** — `Shared/SharedWeb`, `TalabatkAPIs`, `TalabatkRestaurants` and
`TalabatkDelivery` each carry their own `IdentityProvider.cs`. A change to issuer, audience or lifetime
rules must be mirrored in all four; `references/repo-map.md` records this as a standing drift risk and
`_integrations.md` row 3 registers it as the integration it is.

## Entity Index

| Entity | Layer | Type | Responsibility |
|---|---|---|---|
| `AspNetUser` | Domain — Identity base | Master | The credential holder for every user type; see [[Identity.technical\|Identity]] |
| `AspNetRole` | Domain — Identity | Master | Roles the login gates on (`Merchant`, `MerchantAdmin`, `Customer`, admin roles) |
| `Application` | Domain — legacy POCO | Lookup | OAuth client registration: `Id`, `Secret`, `ApplicationType`, `RefreshTokenLifeTime`, `AllowedOrigin` |
| `RefreshToken` | Domain — legacy POCO | Lookup | Persisted refresh tokens for the legacy flow |
| IdentityServer4 `PersistedGrant` | Data | — | Grant/token store; its migration sits oddly under `Migrations/Data/Migrations/IdentityServer/PersistedGrantDb/` rather than under this project |

## Feature Flow (Business Narrative)

```
1. A user of ANY kind opens a client (customer app, driver app, merchant portal, admin SPA)
2. The client redirects to this host's login form
3. Credentials are checked — with no lockout counting (#612)
4. Client id + role decide whether this user may use THIS client at all
5. On success: an attendance record is written (AddOperationAttendanceCommand) and the session starts
6. The client receives a JWT
7. Every other service validates that JWT with its own private copy of the validation code
8. Logout ends the session here; already-issued tokens live until expiry
```

## Key Cross-Cutting Relationships

| From | To | Relationship | Notes |
|---|---|---|---|
| This feature | every context | issues the token each host validates | `_integrations.md` row 3; **four duplicated validators** |
| This feature | [[Identity & Access/Customer Identity/_knowledge-graph\|Customer Identity]] | account creation and recovery | Registration/activation live there; sign-in lives here |
| This feature | [[Identity & Access/Delivery Man Identity/_knowledge-graph\|Delivery Man Identity]] | same | And its #509 reset path bypasses this feature entirely |
| This feature | [[Identity & Access/Restaurant & Admin User Identity/_knowledge-graph\|Restaurant & Admin User Identity]] | merchant/admin accounts | The roles the client gates read |
| Login success | Admin attendance | `AddOperationAttendanceCommand` on every successful login (`:156`) | Sign-in doubles as an attendance clock-in for back-office staff |
| This feature | `mvc.owin.hybrid` (legacy portal client) | migration notice at login | `:132-140` |

## Change Surface

| Signal | Value | Notes |
|---|---|---|
| Direct dependents (Ring 1) | every client and every API host in the system | |
| Sides touched | 3/5 | API host · Backend-Application · Backend-Data (grant store) |
| Cross-context integrations | 1, but universal | Token issuance to all contexts |
| Register findings open | 2 new (#612, #613) + the validator drift, now measured — see #649 | |
| Hub? | **yes** — the authentication hub of the system | |
| Risk flags | any change here affects every user type at once; token validation is duplicated **five** times, so a validation change is five edits — and the fifth copy does not agree with the other four (#649) |

### Who accepts whose token

The bearer validator is copied per host. Four copies pin the audience to their own API; the fifth —
on the identity server itself — does not check audience at all, so it accepts **any** token this
IdentityServer ever issued, including a customer's or a driver's.

| Host | Audience accepted | Where |
|---|---|---|
| `AdminUi` (via `SharedWeb`) | `TalabatkAdmin`, `notifications` | `Shared/SharedWeb/Helpers/Extenstions/IdentityProvider.cs:57-58` |
| `TalabatkAPIs` | `TalabatkApis` | `TalabatkAPIs/Helper/Extension/IDentityProvider.cs:32-33` |
| `TalabatkDelivery` | `TalabatkApisDelivery` | `TalabatkDelivery/Helpers/Extensions/IdentityProvider.cs:105-106` |
| `TalabatkRestaurants` | `AngularApis` | `TalabatkRestaurants/Helpers/Extenstions/IdentityProvider.cs:67-68` |
| **`Talabatk.IDS`** | ⚠️ **any** — `ValidateAudience = false` | `Talabatk.IDS/Configurations/Identity.cs:168` |

This is what makes finding **#615** wider than its wording suggests. The roleless `[Authorize]` on
`Talabatk.IDS`'s `BackgroundJobsController` and `MaintenanceController` is not "any admin who happens
to lack a role" — it is any principal holding a valid token from any client of this IdentityServer.
A customer-app token is rejected by Delivery, Restaurants and AdminUi, and accepted here.

Two smaller facts from the same block: `RequireHttpsMetadata = false`
(`Talabatk.IDS/Configurations/Identity.cs:161`), and the SignalR convention of reading the token from
the query string — `context.Request.Query["access_token"]` for paths under `/hubs`
(`Talabatk.IDS/Configurations/Identity.cs:179`, `:183-185`), which puts bearer tokens in any access log
that records query strings.

## Open Questions

- [ ] Was `lockoutOnFailure: false` (#612) deliberate — e.g. to stop support calls from locked
      merchants — or copied from the IdentityServer4 quickstart? The quickstart ships `true`.
- [ ] Is there any rate limiting in front of `POST /Account/Login` (gateway, WAF)? Nothing in code, and
      it is the only thing standing between #612 and unlimited guessing.
- [ ] Does logout revoke issued refresh tokens, or only end the session cookie? Not traced.
- [ ] Which external providers are configured for `/External/Challenge`? The controller is generic over
      `scheme`; the registered schemes were not enumerated in this pass.
- [ ] Is `AddOperationAttendanceCommand` on every login intended for all user types, or only
      back-office staff? A customer signing in appears to write an attendance row.
- [ ] Do the four `IdentityProvider.cs` copies currently agree? `references/repo-map.md` flags the risk;
      a diff of the four was not performed here.
