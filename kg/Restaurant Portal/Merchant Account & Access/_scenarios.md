---
id: 8orders/restaurant-portal/merchant-account-and-access/scenarios
title: Merchant Account & Access — Scenario Catalog
note_type: scenarios
context: Restaurant Portal
feature: Merchant Account & Access
audience: Business · QA · Developer
last_updated: 2026-08-23
sources:
  - path: TalabatkRestaurants/Controllers/StoreUsers/StoreUsersController.cs
    sha1: 5cb9ac714756
  - path: TalabatkRestaurants/Controllers/Restaurants/RestaurantsController.cs
    sha1: c85216d0ea52
  - path: TalabatkRestaurants/Controllers/UserPermissions/UserPermissionsController.cs
    sha1: 39835c53c3e7
  - path: TalabatkRestaurants/Helpers/Middlewares/SessionHandlerMiddleware.cs
    sha1: 16a9e0124cb2
tags: [restaurant-portal, merchant-account-and-access, scenarios]
---
# Merchant Account & Access — Scenario Catalog

> Every meaningful behaviour as precondition → action → expected outcome, with the rule it exercises.
> **"Expected outcome" here means what the code actually does today**, not what it ought to do; where
> those differ the row says so and names the finding. A test written from a wished-for outcome would
> pass against a fix and hide the current behaviour.

## Happy path

| # | Precondition | Action | Expected outcome | Rule / source |
|---|---|---|---|---|
| H1 | Merchant admin signed in, `userRestaurants` = `"12,13,14"` | `GET api/StoreUsers/GetStoreUsers` | Users of stores 12, 13 and 14 only | `StoreUsersController.cs:55` |
| H2 | Restaurant admin signed in, `userRestaurants` empty, `RestaurantId` = 12 | `GET api/StoreUsers/GetStoreUsers` | Falls back to the single store 12 | `StoreUsersController.cs:55` |
| H3 | Merchant admin of store 12 | `POST api/StoreUsers/AddNewStoreUser` with `RestaurantId: 99` in the body | User is created against **store 12** — the session overwrites the body | `StoreUsersController.cs:114` |
| H4 | Same, bulk form | `POST api/StoreUsers/AddMultipleStoreUser` | All users attached to the session's store | `StoreUsersController.cs:126` |
| H5 | Staff signed in | `GET api/Restaurant/UserRestaurants` | The branch list for this user id | `TalabatkRestaurants/Controllers/Restaurants/RestaurantsController.cs:191` |
| H6 | Staff of store 12, kitchen overwhelmed | `POST api/Restaurant/SaveBusyTime` | Busy window recorded for store 12, `CreatedBy` = session user name | `TalabatkRestaurants/Controllers/Restaurants/RestaurantsController.cs:326-327` |
| H7 | Staff of store 12 | `GET api/Restaurant/GetRestaurantBusy` | Only store 12's busy history | `TalabatkRestaurants/Controllers/Restaurants/RestaurantsController.cs:259` |
| H8 | Kitchen tablet signs in | `POST api/Restaurant/AddDeviceIds` | Device registered against the session user, so new-order pushes reach it | `TalabatkRestaurants/Controllers/Restaurants/RestaurantsController.cs:436` |
| H9 | Staff of stores 12,13 | `POST api/Restaurant/pingV2` | Liveness recorded for both stores | `TalabatkRestaurants/Controllers/Restaurants/RestaurantsController.cs:517` |
| H10 | Merchant admin of store 12 | `GET api/Restaurant/GetRestaurantReviews` | Only store 12's reviews | `TalabatkRestaurants/Controllers/Restaurants/RestaurantsController.cs:57` |

## Partial / incremental

| # | Precondition | Action | Expected outcome | Rule / source |
|---|---|---|---|---|
| P1 | Merchant admin manages 3 branches, edits 2 | `POST api/StoreUsers/UpdateMultipleStoreUser` | Every row is stamped with `sessionInfo.RestaurantId` — a single store, even though the admin manages three | `StoreUsersController.cs:151` — worth confirming this is intended for multi-branch admins |
| P2 | Store marked busy until 20:00, cleared at 19:30 | `POST api/Restaurant/EndRestaurantBusy` | Window terminated early, `TerminatedBy` recorded | `TalabatkRestaurants/Controllers/Restaurants/RestaurantsController.cs:298-300` |
| P3 | Working-days schedule saved with `ApplyWorkingDays = false` | `POST api/Restaurant/MangeWorkingDays` | Schedule stored but not enforced; the store falls back to its legacy `OpenFrom`/`OpenTo` | `MangeRestaurantWorkingDaysCommand.cs:20-24`; see `_conflicts.md` #90 for the parse bug in the same command |

## Negative / guard

| # | Precondition | Action | Expected outcome (rejection) | Rule / source |
|---|---|---|---|---|
| N1 | Plain staff role (not admin) | `GET api/StoreUsers/GetStoreUsers` | 403 — role gate `MerchantAdmin, RestaurantAdmin` | `StoreUsersController.cs:47` |
| N2 | No token at all | any `[Authorize]` action | 401 before the action runs | `TalabatkRestaurants/Startup.cs:222` middleware order |
| N3 | Token present, `userRestaurants` claim **empty** | `GET api/StoreUsers/GetStoreUserInfo` | **500, not an empty list** — `"".Split(",")` yields `[""]` and `int.Parse` throws | `StoreUsersController.cs:76` |
| N4 | Same, on the liveness ping | `POST api/Restaurant/ping` | Same 500 shape | `TalabatkRestaurants/Controllers/Restaurants/RestaurantsController.cs:502` |
| N5 | Token whose `RestaurantId` claim is missing | any session-scoped read | Session silently becomes store `0`; the query returns nothing rather than failing | `TalabatkRestaurants/Helpers/Middlewares/SessionHandlerMiddleware.cs:28,42` |

## Returns / cancellation / reversal

| # | Precondition | Action | Expected outcome | Rule / source |
|---|---|---|---|---|
| R1 | Store user exists in this restaurant | `POST api/StoreUsers/DeleteStoreUser` | Request is **proxied to Identity & Access** with the caller's token and the caller's body; deletion happens there | `StoreUsersController.cs:163-166`, `:170-190` |
| R2 | Busy window active | `EndRestaurantBusy` | Reversal is an update with a terminator, not a delete — history is preserved | `TalabatkRestaurants/Controllers/Restaurants/RestaurantsController.cs:288-300` |

## Integration (cross-side / cross-context)

| # | Precondition | Action | Expected outcome | Rule / source |
|---|---|---|---|---|
| I1 | Any request | middleware runs | JWT claims minted by `Talabatk.IDS` become `SessionInfo`; **this context trusts them without re-deriving them** | `TalabatkRestaurants/Helpers/Middlewares/SessionHandlerMiddleware.cs:25-47`; issuance side in [[Identity & Access/_context\|Identity & Access]] |
| I2 | `DeleteStoreUser` called | proxy to IDS | `POST {IDS}/api/RestaurantUser/DeleteStoreUser`, new `HttpClient` per call, caller's bearer token forwarded | `StoreUsersController.cs:165-178` |
| I3 | Angular portal loads | `GET api/FeatureMangement/GetFeatureStatus` | Feature flag returned to an **unauthenticated** caller; a duplicate endpoint with the same purpose exists in Ops & Infra | `FeatureMangementController.cs:24`; `_conflicts.md` #35 |
| I4 | Device registered (H8) | new order arrives | Push reaches the registered device via the notification path documented in [[Restaurant Portal/Menu & Order Management/_knowledge-graph\|Menu & Order Management]] | `TalabatkRestaurants/Controllers/Restaurants/RestaurantsController.cs:436` |

## Cross-tenant scenarios — what a signed-in merchant can reach today

These are the current behaviour of the code, each tied to a register finding. They belong in the
catalog precisely because they are behaviour; leaving them out would make the catalog describe an
application that does not exist.

| # | Precondition | Action | Actual outcome today | Finding |
|---|---|---|---|---|
| X1 | Signed in as store 12 | `GET api/Restaurant/WorkingDays?restaurantId=99` | Store 99's schedule is returned | `_conflicts.md` #606 · `TalabatkRestaurants/Controllers/Restaurants/RestaurantsController.cs:110` |
| X2 | Signed in as store 12 | `POST api/Restaurant/MangeWorkingDays` with `RestaruantId: 99` | **Store 99's opening hours are overwritten** | `_conflicts.md` #607 · `TalabatkRestaurants/Controllers/Restaurants/RestaurantsController.cs:132` |
| X3 | Signed in as store 12, merchant-admin role | `GET api/Restaurant/GetRestaurantReviewsByIds?restaurantIds=99` | Store 99's reviews **plus each reviewer's first name** | `_conflicts.md` #608 · `TalabatkRestaurants/Controllers/Restaurants/RestaurantsController.cs:173`, handler `GetRestaurantReviewsByIdsQuery.cs:24,33` |
| X4 | Signed in as store 12 | `GET api/Restaurant/GetRestaurantBusyByIds?restaurantIds=99` | Store 99's busy history with `Reason`, `CreatedBy`, `TerminatedBy` | `_idor-instances.md` #11 · `TalabatkRestaurants/Controllers/Restaurants/RestaurantsController.cs:279` |
| X5 | Signed in as store 12 | `POST api/StoreUsers/DeleteStoreUser` naming a user of store 99 | Proxied unscoped; deletion decided by IDS, which receives no restaurant context | `_conflicts.md` #604 · `StoreUsersController.cs:163` |
| X6 | Any authenticated portal user, any role | `GET api/UserPermissions/GetUserPermissions?userId=<other>` | Another user's permission list | `_conflicts.md` #605 · `UserPermissionsController.cs:34` |

## Open Questions

- [ ] Does the Angular client ever legitimately request ids outside the caller's branch list
      (X3/X4)? If never, these are latent rather than exercised.
- [ ] P1: is stamping one `RestaurantId` onto a multi-store bulk edit correct for a chain admin?
- [ ] N3/N4: is an empty `userRestaurants` claim actually reachable in production, or does IDS always
      populate it? The claim is optional in the middleware, which implies yes.
- [ ] R1: does `Talabatk.IDS`'s `DeleteStoreUser` apply its own tenant check? If it does, #604 is
      mitigated one hop away — not yet traced.
