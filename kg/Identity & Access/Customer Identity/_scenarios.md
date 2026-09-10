---
id: 8orders/identity-and-access/customer-identity/scenarios
title: Customer Identity — Scenario Catalog
note_type: scenarios
context: Identity & Access
feature: Customer Identity
audience: Business · QA · Developer
last_updated: 2026-08-23
sources:
  - path: Talabatk.IDS/Controllers/CustomerController.cs
    sha1: f2a016cb6aa3
  - path: Talabatk.IDS/Application/Commands/ResetPasswordCommand/ResetPasswordCommand.cs
    sha1: 50ba98100b39
  - path: Talabatk.IDS/Application/Commands/ChangePasswordCommand/ChangePasswordDto.cs
    sha1: f518d1ce1e85
tags: [identity-and-access, customer-identity, scenarios]
---
# Customer Identity — Scenario Catalog

> Precondition → action → what the code does today. Where this feature and
> [[Identity & Access/Delivery Man Identity/_scenarios|Delivery Man Identity]] implement the same
> operation differently, the row says so — that contrast is the regression baseline for fixing #509.

## Happy path

| # | Precondition | Action | Expected outcome | Rule / source |
|---|---|---|---|---|
| H1 | Client holds a bearer token, phone unregistered | `POST api/Customer/Register` | Customer created; activation code issued | `Talabatk.IDS/Controllers/CustomerController.cs:50-52` |
| H2 | Same, V2 client | `POST api/Customer/RegisterV2` | Same via `RegisterCustomerV2Command` — but **no token required** | `:80-83` · #443 |
| H3 | Registered, code received | `POST api/Customer/ActivateUser` | Phone confirmed; account usable | `:131-134` |
| H4 | Same, V2 | `POST api/Customer/ActivateUserV2` | Same via `ActivateCustomerV2Command` | `:147-150` |
| H5 | Activated | sign in via IdentityServer | JWT issued carrying a `customerId` claim | `_integrations.md` row 3 |
| H6 | Code never arrived | `GET api/Customer/ResendActivationCode` | New code issued, replacing the previous one | `:115-118` |
| H7 | Password forgotten | `GET api/Customer/ForgotPassword` | Reset code issued | `:188-191` |
| H8 | Correct reset code in hand | `POST api/Customer/ResetPassword` | Code **verified** (`ResetPasswordCommand.cs:41-46`), password validated (`:48`), then changed | `Talabatk.IDS/Controllers/CustomerController.cs:203-210` |
| H9 | Signed-in customer knows the old password | `POST api/Customer/ChangePassword` | Password changed for **the caller** — id from the token claim, not the body | `:213-221` |
| H10 | Guest built a cart, then registers | registration completes | Guest state merges into the new account | ADR `TalabatkAPIs/docs/adr/0001-guest-mode-provisional-customer.md` |

## Partial / incremental

| # | Precondition | Action | Expected outcome | Rule / source |
|---|---|---|---|---|
| P1 | Registration started but not finished | `POST api/Customer/CompleteRegistration` | Completes it — anonymously | `:96-101` |
| P2 | Customer requests several codes | repeated `ResendActivationCode` | Each issues a new code, invalidating the previous | `:115-118` |
| P3 | Registered but never activated | attempt to sign in | Rejected until the phone is confirmed | `:131-134` |
| P4 | Guest with a cart, never registers | — | Provisional record persists; no account exists | ADR 0001 |

## Negative / guard

| # | Precondition | Action | Expected outcome (rejection) | Rule / source |
|---|---|---|---|---|
| N1 | **Wrong** reset code | `POST ResetPassword` | **Rejected** — `WrongActivationCode`. This is the check the driver path lacks | `ResetPasswordCommand.cs:41-46` |
| N2 | New password fails policy | `POST ResetPassword` | Rejected by `ValidatePassword` | `ResetPasswordCommand.cs:48` |
| N3 | Phone not registered | `POST ResetPassword` | `UserNotFound` | `ResetPasswordCommand.cs:36-39` |
| N4 | Wrong old password | `POST ChangePassword` | Rejected — the old password is required | `:213-221` |
| N5 | No token | `POST Register`, `ActivateUser`, `ResetPassword`, `ChangePassword` | 401 — JWT bearer required | `:51`, `:131`, `:203`, `:215` |
| N6 | Token without the `Customer` role | `POST ChangePassword` | 403 — this is the only action in the feature with a role gate | `:215` |
| N7 | No token | `POST RegisterV2`, `POST SendOTP` | **Accepted** — `[Authorize]` is commented out on both | `:80-83`, `:166-170` · #443 |

## Returns / cancellation / reversal

| # | Precondition | Action | Expected outcome | Rule / source |
|---|---|---|---|---|
| R1 | Password changed in error | — | No undo; change or reset again | `:213-221` |
| R2 | Guest merged into an account | — | Not reversible; the provisional record is consumed | ADR 0001 |
| R3 | Account no longer wanted | — | No self-service deletion endpoint exists in this controller | `CustomerController.cs` (10 actions, none delete) |

## Integration (cross-side / cross-context)

| # | Precondition | Action | Expected outcome | Rule / source |
|---|---|---|---|---|
| I1 | Customer signs in | IdentityServer issues a JWT | Validated by every API host, each with **its own copy** of the validation code | `_integrations.md` row 3 |
| I2 | Registration completes | guest merge | Cart and address continuity preserved — see [[Cart-and-Checkout-Validation.technical\|Cart & Checkout Validation]] | ADR 0001 |
| I3 | Account exists | wallet / loyalty balances | Hang off `Customer`; movements documented in [[Money-Path.technical\|The Money Path]] | |
| I4 | Item back in stock | FCM push | Reaches the customer via `SendNotificationJob`, grouped by payload | `_integrations.md` row 22 |
| I5 | Any action in this controller | `logger.LogInformation(<dto>.ToString())` | The controller's convention — and the vector for #611 | `:208`, `:218` |

## Security scenarios — current behaviour

| # | Precondition | Action | Actual outcome today | Finding |
|---|---|---|---|---|
| X1 | Anyone with log access | read the log after a customer changes their password | **Both the old and the new password**, labelled `OldPassword : … NewPassword : …` | 🔴 `_conflicts.md` **#611** · `:218`, `ChangePasswordDto.cs:11` |
| X2 | Anyone with log access | read the log after a password reset | The new password, mislabelled `phone:` | 🔴 **#611** / #510 · `:208` |
| X3 | **No token** | `POST api/Customer/SendOTP` with any phone number | An SMS code is sent to that number — cost and harassment surface | 🔴 `_conflicts.md` **#443** · `:166-170` |
| X4 | No token | `POST api/Customer/RegisterV2` | Registration proceeds with no client credential | 🔴 **#443** · `:80-83` |
| X5 | No token | `POST api/Customer/CompleteRegistration` | Completes a pending registration; what binds the caller to it is untraced | ⚠️ open question · `:96-101` |
| X6 | Attacker knows a customer's phone | `POST ResetPassword` without the code | **Rejected** — unlike the driver equivalent | ✅ `ResetPasswordCommand.cs:41-46` |

## Open Questions

- [ ] Is a pre-auth client token obtainable by an unregistered customer? Decides whether X3/X4 are a
      downgrade or a necessity.
- [ ] Is `SendOTP` rate-limited anywhere outside the code (gateway, WAF)? Nothing in code limits it.
- [ ] X5: what binds `CompleteRegistration` to the registration it completes? If only a phone number,
      it is an account-hijack candidate.
- [ ] Are V1 registration/activation still called, or is V2 the only live path? Four actions, two
      operations.
- [ ] Does `ValidatePassword` also run on `ChangePassword`, or only on reset?
- [ ] Is there any account-deletion or data-erasure path? None in this controller — relevant to any
      privacy obligation.
