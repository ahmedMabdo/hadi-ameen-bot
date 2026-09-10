---
id: 8orders/identity-and-access/authentication-and-tokens/login-and-activation
note_type: single
context: Identity & Access
feature: Authentication & Tokens
sources:
  - path: Talabatk.IDS/Controllers/Account/AccountController.cs
    sha1: 9c1caf8ae094
  - path: Talabatk.IDS/Controllers/DeliveryMenController.cs
    sha1: d1bc8eebe1c5
  - path: Talabatk.IDS/Controllers/DeliveryMenController/DeliveryManController.cs
    sha1: 3bb0cd400cde
  - path: Talabatk.IDS/CustomerIdentityProfileService.cs
    sha1: 50f1db0f2635
  - path: Talabatk.IDS/CustomerResourceOwnerValidator.cs
    sha1: 949797e366d7
  - path: Talabatk.IDS/OtpGrantValidator/OtpCustomerGrantValidator.cs
    sha1: 6419cf4db2c4
last_updated: 2026-08-23
tags: [identity-access, transactional, technical, backend-domain, security]
---
# Login & Activation Checks Across Actor Types

Confirms and precisely locates two previously-flagged-but-unverified findings from an earlier, lost
research pass — both now cited exactly, with one turning out more severe than originally described.
Covers `Talabatk.IDS/CustomerResourceOwnerValidator.cs` (password-grant login) and
`Talabatk.IDS/CustomerIdentityProfileService.cs` (per-request active-check + claims issuance).

## Login-path comparison across actor types (`CustomerResourceOwnerValidator.ValidateAsync`)
| Client (actor) | User lookup | Password check | Status checks beyond password |
|---|---|---|---|
| `mobile`/`TalabatkAdminApis`/`TalabatkExternalTool` (Customer) | by `PhoneNumber` | ✅ | `Deleted`, `PhoneNumberConfirmed && Active`, `IsBlocked` — **3 checks** (`:96-127`) |
| `OldCustomerMobile` | by id | none checked in this method | `Deleted`, `PhoneNumberConfirmed && Active`, `IsBlocked` (`:357-377`) |
| `deliverymobile` (Delivery Man) | by `UserName` | ✅ | `IsDeleted` (`:421-427`) |
| `RestaurantMobile` | by `PhoneNumber` | ✅ | **none** (`:212-254`) |
| `AngulatTest`/`deliveryAdmin`, `StoresTest` (test/admin clients) | by email | ✅ | none (test/back-office clients, lower stakes) |

### ⚠️ Confirmed — `RestaurantMobile` has zero status checks, at login or afterward
- **Plain language:** Every other real actor type (Customer, Delivery Man) is checked for
  deleted/blocked/inactive status both at login and on every subsequent request. `RestaurantMobile`
  is checked for **neither** — a restaurant user whose account is deactivated or blocked can still
  authenticate with a correct password and use a live token indefinitely.
- **Login gap:** `CustomerResourceOwnerValidator.cs:212-254` — the `RestaurantMobile` branch checks
  only that the user exists and the password matches; no `Active`/`IsBlocked`/`Deleted`-equivalent
  field is referenced at all.
- **Ongoing gap, not just login:** `CustomerIdentityProfileService.IsActiveAsync` (`:200-272`), which
  re-validates on every subsequent request/token-refresh, has explicit branches for `mobile`,
  `deliverymobile`, `TalabatkAdminDelivery`, `AngularClient`, `AdminAngularClient`, `StoresTest` — but
  **no branch at all for `RestaurantMobile`**. Falling through all the `if`/`else if` chains with no
  match leaves `context.IsActive` at its default, uninspected value — worth confirming what
  IdentityServer4 does with an unset `IsActive` (likely defaults to `true`, meaning the token is
  treated as still valid) rather than assuming this is a neutral no-op.

## `IsActiveAsync`'s `deliverymobile` branch — two bugs stacked in five lines
- **Source:** `CustomerIdentityProfileService.cs:221-236`:
  ```
  var user = await deliveryUserManager.FindByIdAsync(sub);
  if (user is null)
  {
      context.IsActive = false;
  }                                    // <-- no return/continue here

  var isDeliveryManDeleted = user.IsDeleted;   // <-- NullReferenceException if user was null
  if (isDeliveryManDeleted)
  {
      context.IsActive = false;
  }

  context.IsActive = true;            // <-- unconditionally overwrites both checks above
  ```
- **Bug 1 (more severe than the original informal finding described):** the `user is null` branch
  sets `IsActive = false` but doesn't `return`, so execution falls through to `user.IsDeleted` —
  an unhandled `NullReferenceException` for a delivery man id that doesn't resolve, rather than the
  intended "not active" result.
- **Bug 2 (the originally-flagged dead code, now confirmed with exact lines):** even if `user` is not
  null and genuinely deleted, `context.IsActive = true` on the very next line unconditionally
  overwrites that result — a deleted delivery man's token is still reported active. Confirms the
  earlier finding exactly.

## The OTP grant flow — resolved (2026-08-03)
Closes a question open since the very first session on this effort: the custom `"otp"` IdentityServer4
extension grant, `Talabatk.IDS/OtpGrantValidator/OtpCustomerGrantValidator.cs`.

### Rule 1: Unknown phone number — peek-validate without consuming, signal `registration_required`
- **Plain language:** The mobile app always calls the OTP endpoint first without knowing whether the
  number is registered. If the number has no `Customer` row, the OTP is checked for validity (but not
  used up) so the app can safely say "please register" only if the code was actually right — a wrong
  or expired code still gets a generic invalid-OTP error, not leaking anything about whether
  registration would be required.
- **Source:** `:64-98`. Gated by the `OtpLoginOrRegister` feature flag (`:69`) — if off, an unknown
  number is just told "invalid OTP" (legacy behavior). If on: `_otpService.ValidateOtpAsync(phone,
  otp, consume: false)` (`:79`) — a **peek**, not a consume. On success, returns a specific
  `registration_required` error code both as the grant error description and as a custom
  `error_code` field in the response dictionary (`:93-96`) — the OTP is **still unconsumed** at this
  point; the actual registration command (`RegisterCustomerV2Command`, already documented) is what
  consumes it once the account is created.

### Rule 2: Existing user — `Active` is checked before `IsBlocked`, both before the OTP is ever consumed
- **Source:** `:100-118` — an inactive user or a blocked user is rejected immediately (order: Active
  first, then Blocked), without ever calling `ValidateOtpAsync` at all for this attempt — meaning a
  blocked/inactive user's OTP attempt doesn't spend the code.

### Rule 3: Existing, active, unblocked user — this is the one path that actually consumes the OTP
- **Source:** `:121-144` — `ValidateOtpAsync(phone, otp)` (default `consume: true`). On success,
  triggers the same `TryMergeGuestCartAsync` guest-replaces merge already documented for the password
  grant (`Login-and-Activation.md` above) and `RegisterCustomerV2Command`'s `PromoteFromGuest` path —
  **this is the third confirmed site in the codebase running the identical guest-cart-merge/promotion
  pattern** (registration, password login, OTP login), reinforcing that it's a deliberately shared,
  not accidentally duplicated, cross-cutting concern.

## MVC Account controller — a third, browser-based login surface (2026-08-03, completes Phase 1)
`Talabatk.IDS/Controllers/Account/AccountController.cs` — the server-rendered login form, used by
non-API clients (`mvc.owin.hybrid`, `AdminAngularClient`), on top of the two grant validators already
documented (password/OTP).

### Rule: Role-based client restriction — Merchant/MerchantAdmin blocked from two specific clients
- **Plain language:** A merchant account can authenticate its credentials correctly but is still
  refused login on two specific front-doors, with a message steering them elsewhere.
- **Source:** `Talabatk.IDS/Controllers/Account/AccountController.cs:130-148` — if the authenticated user has the `Merchant` or
  `MerchantAdmin` role: for `mvc.owin.hybrid`, rejected with a message naming the new Restaurant
  Portal URL (`config["Restaurants"]`); for `AdminAngularClient`, rejected with a bare "UnAuthorized"
  message. This is a **different mechanism** from `CustomerResourceOwnerValidator`'s per-client status
  checks (`_conflicts.md` #31) — it's a role-vs-client mismatch check, not an active/blocked check,
  and it lives only on this MVC path, not on any API grant.

### Rule: Successful MVC login also logs "operation attendance"
- **Source:** `Talabatk.IDS/Controllers/Account/AccountController.cs:150-156` — on successful `PasswordSignInAsync`, dispatches
  `AddOperationAttendanceCommand { UserId = user.Id }` — a previously-undocumented
  admin/operator attendance-tracking feature, distinct from `DeliveryMen`'s attendance system
  (`DeliverymanShiftLog`). Not traced further — the command's own logic wasn't opened.

### Rule: No lockout on repeated failed MVC login attempts
- **Source:** `Talabatk.IDS/Controllers/Account/AccountController.cs:150` — `PasswordSignInAsync(..., lockoutOnFailure: false)`
  explicitly disables ASP.NET Identity's built-in lockout for this login path.

## Duplicate/legacy delivery-man registration surface — confirmed (2026-08-03)
**A third delivery-man CRUD entry point exists**, on top of the two already known
(`Talabatk.IDS/Controllers/DeliveryMenController/DeliveryManController.cs`, the MVC admin UI seen from
Phase 1's original pass, and `DeliveryManTestController`, explicitly bearer-API-for-testing):
- `Talabatk.IDS/Controllers/DeliveryMenController.cs` (**top-level**, not in either subfolder) has its
  own `Register`/`ActivateUser`/`ForgotPassword`/`ResetPassword`/`EditDeliveryman` routes, calling
  `DeliveryMen.Instance` and ASP.NET Identity's `UserManager` directly.
- **`ActivateUser` here (`:148-180`) sets `user.PhoneNumberConfirmed = true` directly via
  `userManager.UpdateAsync`, bypassing `DeliveryMen`'s own entity methods entirely** — no call to any
  `DeliveryMen`-level activation method. Not confirmed whether this is dead/legacy code superseded by
  the other two controllers, or a live third path — worth flagging rather than assuming.
- Also reveals `GetDeliverymenQueues` (`:268-280`) — a distributed priority queue
  (`IDistributedPriorityQueue`, key `CacheKeys.DeliveryZoneRiders`) backing delivery-zone rider
  assignment — infrastructure not previously documented, ties to
  [[Delivery-Assignment-Strategies|Delivery Assignment Strategies]].

## Other Phase 1 files (all thin/boilerplate, no findings)
`ExternalController`/`HomeController` (standard IdentityServer4 quickstart external-login/error-page
boilerplate), `AccountOptions`/`ExternalProvider`/`Extensions`/`SecurityHeadersAttribute` (config
constants, DTOs, HTTP-header middleware — not business logic), `PaymentController` (payment-callback
landing page, thin), `BackgroundJobsController`/`MaintenanceController` (manual triggers for
`AutoAssignJob` and a Cassandra chat-data migration — ops tooling, confirms `AutoAssignJob` exists as
a distinct background job), `HealthController` (trivial). **`FeatureMangamentController`** — an
**exact duplicate** of the same thin `features`/`GetFeatureFlagQuery` pattern already found in
`TalabatkRestaurants` — a third confirmed copy of this pattern across hosts. `FeaturesController`
(different from `FeatureMangamentController`) reveals a **fourth, separate feature-flag mechanism**:
an HTTP call to an external "Esquio" feature-management service (`ChangeState` route) — on top of the
already-known `IFeatureManager.IsFeatureEnabledAsync` and the MediatR `GetFeatureFlagQuery` seen
elsewhere, this is genuinely a third/fourth distinct feature-flag system coexisting in this codebase.

## Related
- [[DeliveryMen.technical|DeliveryMen]]
- [[Customer.technical|Customer]] — the guest-merge-on-password-login
  trace (`CustomerResourceOwnerValidator.cs:131-182`) matches
  `MergeGuestCartIntoCustomerCommand`'s already-documented behavior exactly — confirms the password
  login path and the OTP login path (not traced in this pass) both trigger the same guest-merge
  command.

## Open Questions
- [ ] What IdentityServer4 actually does with `IsActiveContext.IsActive` when no branch in
  `IsActiveAsync` matches the client id (the `RestaurantMobile` gap) — needs confirming against the
  IdentityServer4 version in use, not assumed.
- [x] ~~The custom OTP grant~~ — **Resolved 2026-08-03**, see "The OTP grant flow" section above.
- [ ] Whether `RestaurantMobile`'s missing status checks have been exploited or noticed in practice —
  flagged as a code-reading finding, not a confirmed incident.
- [ ] `IOtpAuthService.ValidateOtpAsync`'s own internals (rate limiting, expiry window, attempt
  counting) not opened in this pass — only its two call modes (peek/consume) from the grant
  validator's perspective.
