---
id: 8orders/identity-and-access/restaurant-and-admin-user-identity/scenarios
title: Restaurant & Admin User Identity — Scenario Catalog
note_type: scenarios
context: Identity & Access
feature: Restaurant & Admin User Identity
audience: Business · QA · Developer
last_updated: 2026-08-23
sources:
  - path: Talabatk.IDS/Controllers/RestaurantUserController/RestaurantUserController.cs
    sha1: a4c44c8baa83
  - path: Talabatk.IDS/Controllers/UsersController/UsersController.cs
    sha1: 2c7b220012a2
  - path: Talabatk.IDS/Application/Commands/ResetPasswordForRestaurantUserCommand/ResetPasswordForRestaurantUserCommand.cs
    sha1: 895b1dce0204
  - path: Talabatk.IDS/Application/Commands/DeleteUserCommand/DeleteUserCommand.cs
    sha1: 14bbc5b5e13d
tags: [identity-and-access, restaurant-and-admin-user-identity, scenarios]
---
# Restaurant & Admin User Identity — Scenario Catalog

> Two surfaces in one feature: a role-gated JSON API the Restaurant Portal calls, and a Razor
> back-office UI gated only by "is authenticated". Rows say which.

## Happy path

| # | Precondition | Action | Expected outcome | Rule / source |
|---|---|---|---|---|
| H1 | Signed-in `RestaurantAdmin` | `POST api/RestaurantUser/AddNewUser` | Sub-user created under that restaurant | `RestaurantUserController.cs:68-71` |
| H2 | Signed-in `MerchantAdmin` | `POST api/RestaurantUser/AddNewStoreUser` | Store user created | `:179-182` |
| H3 | New staff member has the code | `POST api/RestaurantUser/ActivateUser` | Phone confirmed; the account can sign in | `:138-143` |
| H4 | Activated staff | sign in at the single login form | Pass issued carrying role **and** branch list | [[Identity & Access/Authentication & Tokens/_knowledge-graph\|Authentication & Tokens]] |
| H5 | Signed-in `restaurant` / `RestaurantAdmin` | `POST api/RestaurantUser/ChangePassword` | Own password changed | `:52-55` |
| H6 | Forgotten password | `GET api/RestaurantUser/ForgotPassword` | Reset code sent | `:98-101` |
| H7 | Correct reset code | `POST api/RestaurantUser/ResetPassword` | Code **verified**, then the password is changed | `ResetPasswordForRestaurantUserCommand.cs:51-55` |
| H8 | Signed-in `MerchantAdmin`, several users to fix | `POST api/RestaurantUser/EditMultipleStoreUser` | Bulk edit applied | `:278-280` |
| H9 | 8Orders staff, authenticated | back-office `AllUsers` page | Every user listed and searchable | `UsersController.cs:31` |
| H10 | Same | back-office `AddUser` | Internal user created | `UsersController.cs:124` |

## Partial / incremental

| # | Precondition | Action | Expected outcome | Rule / source |
|---|---|---|---|---|
| P1 | Account created by an admin, never activated | attempt to sign in | Blocked until the phone is confirmed — activation is a separate, anonymous step | `:138-143` |
| P2 | Code never arrived | `GET api/RestaurantUser/ResendActivationCode` | New code issued, replacing the previous one | `:157-160` |
| P3 | Staff member gains a second branch | branch list updated | Takes effect at next sign-in, because the list is carried in the pass | `AspNetUserRestaurants` → `userRestaurants` claim |
| P4 | Back-office user edited | `EditUser` GET then POST | Two-step load-then-save | `UsersController.cs:62`, `:72` |

## Negative / guard

| # | Precondition | Action | Expected outcome (rejection) | Rule / source |
|---|---|---|---|---|
| N1 | `restaurant` role (not admin) | `POST AddNewUser` | 403 — requires `RestaurantAdmin` | `:70` |
| N2 | `RestaurantAdmin` (not merchant admin) | `POST AddNewStoreUser` | 403 — requires `MerchantAdmin` | `:181` |
| N3 | Wrong reset code | `POST ResetPassword` | Rejected with `WrongActivationCode` | `ResetPasswordForRestaurantUserCommand.cs:51-55` |
| N4 | No token | any role-gated API action | 401 | `:54`, `:70`, `:181`, `:280`, `:315` |
| N5 | Authenticated with **any** role | back-office `DeleteUser` | **Accepted** — the class carries `[Authorize]` with no roles and no permission attributes | 🔴 `UsersController.cs:19`, `:167` |

## Returns / cancellation / reversal

| # | Precondition | Action | Expected outcome | Rule / source |
|---|---|---|---|---|
| R1 | Store user no longer employed | `POST api/RestaurantUser/DeleteStoreUser` | Deleted by user id | `:313-315`; handler `DeleteUserCommand.cs:33-35` |
| R2 | Back-office user leaves | back-office `DeleteUser` | Deleted | `UsersController.cs:167` |
| R3 | Deletion was a mistake | — | No undo path in either surface; the account must be recreated | both delete actions |

## Integration (cross-side / cross-context)

| # | Precondition | Action | Expected outcome | Rule / source |
|---|---|---|---|---|
| I1 | Merchant admin removes a team member in the portal | portal proxies to this host | `POST {IDS}/api/RestaurantUser/DeleteStoreUser` with the caller's token and body | `TalabatkRestaurants/Controllers/StoreUsers/StoreUsersController.cs:163`; received at `:313-315` |
| I2 | Any staff sign-in | pass issued | Branch list becomes the `userRestaurants` claim the whole portal scopes on | [[Restaurant Portal/Merchant Account & Access/_knowledge-graph\|Merchant Account & Access]] |
| I3 | Branch list changed here | portal behaviour changes | Every merchant screen's scope shifts — this feature is upstream of all portal tenancy | same |
| I4 | Merchant password reset | code verified | Same mechanism the customer path uses, and the driver path skips | `_conflicts.md` #509 |

## Security scenarios — current behaviour

| # | Precondition | Action | Actual outcome today | Finding |
|---|---|---|---|---|
| X1 | `MerchantAdmin` of restaurant 12 | `POST DeleteStoreUser` naming a user of restaurant 99 | **The user is deleted.** The portal forwards without scoping and this side resolves the target by user id alone — `DeleteUserCommand` matches `x.Id == command.UserId` with no restaurant in the predicate, and the DTO carries only `UserId` | 🔴 `_conflicts.md` **#604** · `:313-315`, `DeleteUserCommand.cs:33-35` |
| X2 | Any authenticated principal reaching the identity host | back-office `AllUsers` | Every user in the system, listed and searchable | 🔴 `UsersController.cs:19`, `:31` |
| X3 | Same | back-office `DeleteUser` | Any user deleted, including 8Orders staff | 🔴 `UsersController.cs:167` |
| X4 | Anyone with log access | read the log after a merchant password reset | The new password in cleartext | 🔴 `_conflicts.md` **#611** · `:123` |
| X5 | Nothing | `GET api/RestaurantUser/ForgotPassword?phone=…` | An SMS code is sent to that number; also reveals whether the number is a merchant user | ⚠️ `:98-101` |
| X6 | Attacker knows a merchant's phone | `POST ResetPassword` without the code | **Rejected** — unlike the driver equivalent | ✅ `ResetPasswordForRestaurantUserCommand.cs:51-55` |

## Open Questions

- [ ] Is the identity host's Razor back-office reachable from outside the network? X2/X3 hinge on it.
- [ ] Should `UsersController` carry role or permission attributes? Every sibling admin surface in
      `AdminUi` at least attempts one.
- [ ] Does the merchant reset validate the new password against the policy? The customer path calls
      `ValidatePassword`; no equivalent was found in the merchant command.
- [ ] Who creates the first `MerchantAdmin`? `AddNewStoreUser` requires one to exist already.
- [ ] Is `AspNetUserRestaurants` written anywhere besides these endpoints? It decides portal tenancy.
- [ ] Are the anonymous merchant endpoints (`ForgotPassword`, `ResendActivationCode`, `ActivateUser`)
      rate-limited anywhere?
