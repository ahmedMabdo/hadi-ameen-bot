---
id: 8orders/identity-and-access/context
note_type: context
context: Identity & Access
sources:
  - path: Talabatk.IDS/Controllers/UsersController/UsersController.cs
    sha1: 2c7b220012a2
  - path: Talabatk.IDS/Views/DeliveryMan/EditDeliveryMan.cshtml
    sha1: bf80f8426aa9
  - path: Talabatk.IDS/Views/Users/EditUser.cshtml
    sha1: 44a836c5e92a
last_updated: 2026-08-23
tags: [context, identity-access]
---
# Identity & Access — Overview

Authenticates the three actor types (Customer, Delivery Man, Restaurant User) via IdentityServer4,
issues access tokens, and owns registration (`Talabatk.IDS`).

> Business-term glossary: [[../../../Talabatk.IDS/CONTEXT|CONTEXT.md]] — read that first (Customer /
> Delivery Man / Restaurant User definitions, account state, OTP flow). This hub is a **stub** —
> created only because [[Customer Ordering/_context|Customer Ordering]] links here as an
> integration target. Not yet documented feature-by-feature by this skill.

## Features
- [[Login-and-Activation|Login & Activation Checks]] — login-path comparison across all actor types;
  2 confirmed bugs found (`RestaurantMobile` has no status checks at all; `deliverymobile`'s
  `IsActiveAsync` has a null-ref risk plus dead-code deleted-check). **OTP grant flow now fully
  traced and resolved** (peek-vs-consume, `registration_required`, confirmed 3rd guest-merge site).

## Remaining controllers (Phase 1 gap-fill, 2026-08-03)
`CustomerController` (registration/OTP/password — `Register`/`RegisterV2` versioned pair, otherwise
thin MediatR wrappers matching already-documented commands), `UsersController` (MVC admin user CRUD —
**`DeleteUser` doesn't check the command's success result before redirecting**, unlike every other
action in the same controller, `UsersController.cs:167-173` — a silent-failure UX gap, not a security
issue), `DeliveryManController` (MVC delivery-man admin CRUD — ties into `DeliveryMen.Dismiss`/`ReHire`
already documented via `DismissDriverCommand`/`ReHireDriverCommand`, gated by a
`DriverDismissalPermissionHelper` role/permission check), `RestaurantUserController` (API — password
change/reset, sub-user creation scoped to the caller's own `RestaurantId`/`cityId` claims). No further
confirmed bugs beyond the `DeleteUser` gap. `AccountController`/`ExternalController` are the Razor
login/OTP UI, documented in
[[Identity & Access/Authentication & Tokens/Login-and-Activation|Login & Activation]].
`BackgroundJobsController` and `MaintenanceController` **have since been opened** — both are gated by a
roleless `[Authorize]` over operational and destructive actions (finding **#615**), and because this
host alone sets `ValidateAudience = false`, that gate is satisfied by a customer or driver app token
(finding **#649**); see
[[Identity & Access/Ops & Infra/_knowledge-graph|Ops & Infra]] for the endpoint-by-endpoint map.
`PaymentController` is not opened in this pass.

## Shared Entities Owned Here
- [[Customer.business|Customer]] · [[Customer.technical|technical]] — identity
  record for registered + guest customers; also the guest-promotion (`PromoteFromGuest`) and
  registration (`RegisterCustomerV2Command`) logic lives in this context's own project
  (`Talabatk.IDS`), even though the entity class itself is in `Shared/TalabatkLogic`.
- [[DeliveryMen.business|DeliveryMen]] · [[DeliveryMen.technical|technical]] —
  delivery-man identity, cash-handling limits, activation/shift state, rating. Heavily touched by
  Delivery (`TalabatkDelivery`, self-service) and Admin (`AdminUi`, provisioning) — those contexts'
  own passes will extend, not re-document, this note.

## Phase 6 — Razor views (2026-08-03)
All 21 `.cshtml` files in `Talabatk.IDS/Views/` read (Account: AccessDenied/LoggedOut/Login/Logout/
Register; Home: Error/Index/Privacy; Payment/CallBack; Users: AddNewUser/EditUser/AllUsers;
DeliveryMan: AddNewDeliveryMan/AllDeliveryMen/EditDeliveryMan; Maintenance: MigrateChat/
BackfillChatReports; Shared: _ValidationScriptsPartial/_ValidationSummary/_loginLayout;
_ViewImports/_ViewStart). Matches the plan's "expect this to be light" prediction for all but one:

- **`EditDeliveryMan.cshtml` is unexpectedly substantial**, not a thin server-rendered form like its
  siblings — it embeds a full hire/dismiss settlement workflow in JavaScript: a dismissal-preview
  fetch showing deposit/equipment/cash-balance/net-settlement figures, a `canDismiss`/
  `dismissalBlockMessages` gate that disables the confirm button when outstanding ledger entries block
  dismissal, a re-hire flow with a new-insurance-limit prompt, post-dismissal navigation branching to
  either a treasury-payment or treasury-receipt screen depending on which side owes money, and a
  paginated dismissal-log/asset-transactions view fetched via separate endpoints
  (`DismissalPreview`/`Dismiss`/`ReHire`/`DismissalLog`/`GetAssetsTransactions`, all on
  `DeliveryManController`, not opened from this pass). No bug found — flagged as a scope correction:
  this view carries real business logic, unlike the rest of the Razor surface in this repo.
- All other views (`AddNewUser`/`EditUser`/`AddNewDeliveryMan`/`AllUsers`/`AllDeliveryMen`, the
  Account/Home/Payment/Maintenance views, `_loginLayout`) are thin — form markup, select2 dropdown
  wiring, minor conditional field-disabling (e.g. `EditUser.cshtml`'s role-based disabling of the
  "Full Control" checkbox for the "Delivery Supplier" role) — no embedded business rules, no
  confirmed bugs.

## Integrates With
- Every other context — issues the JWTs each API host validates. **Note:** validation is
  duplicated across four near-identical `IdentityProvider.cs` copies (`Shared/SharedWeb`,
  `TalabatkAPIs`, `TalabatkRestaurants`, `TalabatkDelivery`), not shared code — see
  `references/repo-map.md` in the skill and `_system/_conflicts.md`.
- <see [[_integrations|integration register]] for details>
