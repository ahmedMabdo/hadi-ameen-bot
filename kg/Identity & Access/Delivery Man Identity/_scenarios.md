---
id: 8orders/identity-and-access/delivery-man-identity/scenarios
title: Delivery Man Identity — Scenario Catalog
note_type: scenarios
context: Identity & Access
feature: Delivery Man Identity
audience: Business · QA · Developer
last_updated: 2026-08-23
sources:
  - path: Talabatk.IDS/Controllers/DeliveryMenController.cs
    sha1: d1bc8eebe1c5
  - path: Talabatk.IDS/DeliveryManManager/DeliveryUserManager.cs
    sha1: 8e14823969da
  - path: Talabatk.IDS/Application/Commands/ResetPasswordCommand/ResetPasswordDto.cs
    sha1: 01750106bcd2
  - path: Talabatk.IDS/Controllers/DeliveryMenController/DeliveryManTestController.cs
    sha1: 64a9c16f2a1d
tags: [identity-and-access, delivery-man-identity, scenarios]
---
# Delivery Man Identity — Scenario Catalog

> Every row states **what the code does today**. The security rows are not hypotheses: each was read
> at the cited line. A regression suite written from a wished-for outcome would pass against a fix and
> hide the present behaviour, so the present behaviour is what is written down.

## Happy path

| # | Precondition | Action | Expected outcome | Rule / source |
|---|---|---|---|---|
| H1 | Phone number not yet registered | `POST api/DeliveryMen/Register` | Driver record created, activation code issued and sent | `Talabatk.IDS/Controllers/DeliveryMenController.cs:60-90` |
| H2 | Registered, code received | `POST api/DeliveryMen/ActivateUser` | `PhoneNumberConfirmed = true`; account usable | `:148-179` |
| H3 | Activated driver | sign in via IdentityServer | JWT issued; every host accepts it | `_integrations.md` row 3 |
| H4 | Code never arrived | `GET api/DeliveryMen/ResendActivationCode` | A new code is issued and sent | `:93-113` |
| H5 | Driver forgot the password | `GET api/DeliveryMen/ForgotPassword` | Reset code issued | `:182-210` |
| H6 | Reset code in hand | `POST api/DeliveryMen/CheckResetPasswordCode` | Code verified — this action does check it | `:213-234` |
| H7 | Admin corrects a phone number | `POST …/DeliveryManController/EditDeliveryMan` | Record updated | `DeliveryManController.cs` |
| H8 | Driver leaves | `POST …/DeliveryManController/Dismiss` | `DriverDismissalLog` row written; driver deactivated | `DeliveryManController.cs` |
| H9 | Driver returns | `POST …/DeliveryManController/ReHire` | Reactivated; dismissal history retained | `DeliveryManController.cs` |

## Partial / incremental

| # | Precondition | Action | Expected outcome | Rule / source |
|---|---|---|---|---|
| P1 | Registered but never activated | attempt to sign in | Rejected until `PhoneNumberConfirmed` is set | `:148-179` |
| P2 | Driver requests several codes | repeated `ResendActivationCode` | Each call issues a **new** code, invalidating the previous one | `:93-113`; `DeliveryUserManager.cs:61-66` |
| P3 | Dismissal being considered | `GET …/DismissalPreview` | Shows the consequences before committing — a two-step operation | `DeliveryManController.cs` |
| P4 | Driver dismissed and re-hired repeatedly | `GET …/DismissalLog` | Full history, since dismissal appends rather than overwrites | `DeliveryManController.cs` |

## Negative / guard

| # | Precondition | Action | Expected outcome (rejection) | Rule / source |
|---|---|---|---|---|
| N1 | `Phone` or `NewPassword` empty | `POST ResetPassword` | `400 BadParameter` | `:245-248` |
| N2 | Phone not registered | `POST ResetPassword` | `400 UserNotFound` — which also **confirms whether a number is registered** to an anonymous caller | `:250-254` |
| N3 | Wrong reset code | `POST CheckResetPasswordCode` | Rejected — this action does verify | `:213-234` |
| N4 | Password fails Identity policy | `POST ResetPassword` | **Not rejected**: the override hashes whatever it is given without running the validators | `DeliveryUserManager.cs:69-73` |
| N5 | No token | `POST EditDeliveryman` | 401 — JWT bearer scheme required | `:282-284` |
| N6 | Any authenticated bearer principal | `…/DeliveryManTestController/*` | **Accepted** — no role or permission check | `_conflicts.md` #444 |

## Returns / cancellation / reversal

| # | Precondition | Action | Expected outcome | Rule / source |
|---|---|---|---|---|
| R1 | Driver dismissed in error | `ReHire` | Reversible; the log keeps both events | `DeliveryManController.cs` |
| R2 | Driver has an outstanding cash balance at dismissal | `Dismiss` | Whether the balance blocks dismissal is **not traced** — see Open Questions | [[Driver-Cash-Cycle.technical\|Driver Cash Cycle]] |
| R3 | Password changed by mistake | — | No undo; a new reset is the only path | `:239-265` |

## Integration (cross-side / cross-context)

| # | Precondition | Action | Expected outcome | Rule / source |
|---|---|---|---|---|
| I1 | Driver signs in | IdentityServer issues a JWT | Accepted by `TalabatkAPIs`, `TalabatkRestaurants`, `TalabatkDelivery` and `SharedWeb` — each with **its own copy** of the validation code | `_integrations.md` row 3 |
| I2 | Driver's app registers its device | token stored in `AndroidDevices` (`;`-separated) | Enables FCM push to that driver | `:121` reads this column |
| I3 | Break started (Delivery context) | Hangfire delayed job | Break-ending reminder pushed to the driver | `_integrations.md` row 21 |
| I4 | Driver dismissed | Admin context | Bans, unban reasons and wallet handled in [[Admin/Delivery Administration/_knowledge-graph\|Delivery Administration]] | |
| I5 | Order delivered | domain event | `RequiredPayment` / `ExceededCashLimit` recomputed on the driver record | [[Money-Path.technical\|The Money Path]] step 8 |

## Security scenarios — current behaviour, each read at the cited line

| # | Precondition | Action | Actual outcome today | Finding |
|---|---|---|---|---|
| X1 | **Nothing.** Attacker knows a driver's phone number | `POST api/DeliveryMen/ResetPassword` with `{Phone, NewPassword}` | **Password changed; account taken over.** The `Code` field the DTO declares is never read; the server mints a token via `GenerateChangePhoneNumberTokenAsync` and the `ResetPasswordAsync` override ignores it | 🔴 `_conflicts.md` **#509** · `:239-265`, `DeliveryUserManager.cs:61-73` |
| X2 | Any reset attempt, successful or not | `POST ResetPassword` or `ForgotPassword` | The driver's `ActiveCode` is **regenerated and persisted**, invalidating a legitimate OTP in flight — so probing phone numbers silently breaks real drivers' codes | 🔴 #509 side effect · `DeliveryUserManager.cs:61-66` |
| X3 | Anyone with log access | read the application log | Plaintext driver passwords, labelled `phone:` | 🔴 `_conflicts.md` **#510** · `:244`, `ResetPasswordDto.cs:10-17` |
| X4 | Nothing | `GET SimulateSendNewConfirmedOrderNotification?deliveryManId=<n>` | Any driver's FCM device tokens are **returned in the response**, and a fake "you have a new order" push is sent to their phone | 🔴 `_conflicts.md` **#609** · `:115-143` |
| X5 | Nothing | `GET GetDeliverymenQueues` | The whole live rider-queue-per-zone map | 🔴 `_conflicts.md` **#610** · `:268-279` |
| X6 | Nothing | `POST ResetPassword` with an unregistered phone | `UserNotFound` — a phone-number enumeration oracle | 🟡 `:250-254` |
| X7 | Any authenticated bearer token (any role) | `POST …/DeliveryManTestController/EditDeliveryMan` | **Resets any driver's password by id** | 🔴 `_conflicts.md` **#573** |
| X8 | Any authenticated caller | `…/DeliveryManTestController/GetAllDeliveryMen` | Every driver's record — including, per #386, the **password hash** | 🔴 #444, #386 |
| X9 | Any authenticated caller | `GET …/DeliveryManController/EditDeliveryMan?DeliveryManid=<n>` | Any driver's record; supplier ownership never constrains the fetch | 🔴 `_idor-instances.md` **#23** |
| X10 | Any authenticated caller | `GET …/GetAssetsTransactions?DeliveryManId=<n>` | Any driver's asset transactions; the request DTO has no caller field | 🔴 `_idor-instances.md` **#24** |
| X11 | Nothing | trigger the insurance-deduction batch job | An unauthenticated caller can start a **financial** batch | 🔴 `_conflicts.md` **#375** (endpoint lives in [[Identity & Access/Ops & Infra/_knowledge-graph\|Ops & Infra]]) |
| X12 | Nothing | request driver GPS / working hours | Unauthenticated driver location and hours | 🔴 `_conflicts.md` **#412** |

## Open Questions

- [ ] Is `DeliveryManTestController` actually routed in production, or blocked at a gateway? The
      mitigation, if any, exists nowhere in code — and it decides whether X7/X8 are live.
- [ ] Any rate limiting on `Register`, `ResendActivationCode`, `ForgotPassword`? All three are
      anonymous and all three send SMS.
- [ ] R2: does an outstanding cash balance block dismissal, or can a driver be dismissed still owing
      money?
- [ ] Does `EditDeliveryman` (`:282-289`) check in its handler that the caller may edit that driver?
- [ ] Is there any password policy for drivers? N4 says the validators are bypassed.
- [ ] Does any audit trail record *who* reset a password? The action is anonymous, so presumably not.
