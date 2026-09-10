---
id: 8orders/admin/admin-back-office/admin-access-and-oversight-technical
note_type: technical
context: Admin
feature: Admin Back-Office
sources:
  - path: AdminUi/ClientApp/src/app/app-routing.module.ts
    sha1: 9d871c81acb6
  - path: AdminUi/ClientApp/src/app/auth-guard.guard.ts
    sha1: 692386091bea
  - path: AdminUi/ClientApp/src/app/permission/add-role/add-role.component.ts
    sha1: aa949fe72c93
  - path: AdminUi/Controllers/Configuration/ConfigurationController.cs
    sha1: 5649b853ff01
  - path: AdminUi/Controllers/DashboardController/DynamicDashboardController.cs
    sha1: 8666def124d3
  - path: AdminUi/Controllers/FeaturesManagementController.cs
    sha1: 5a07a4ab6678
  - path: AdminUi/Controllers/Permission/PermissionController.cs
    sha1: b66fad8da160
  - path: AdminUi/Controllers/ReportsController/ReportsController.cs
    sha1: e68231848fc9
  - path: AdminUi/Helper/AuthorizationHelpers/AttributeAuthorizationHandler.cs
    sha1: 37403187a3ea
  - path: AdminUi/Helper/AuthorizationHelpers/PermissionAttribute.cs
    sha1: f0e5e60a8982
  - path: AdminUi/Helper/AuthorizationHelpers/PermissionAuthorizationHandler.cs
    sha1: 5f005f84a432
  - path: Shared/TalabatkApplication/Commands/AddNewRoleCommand/AddNewRoleCommand.cs
    sha1: df451fd4691f
  - path: Shared/TalabatkApplication/Commands/UpdateRoleCommand/UpdateRoleCommand.cs
    sha1: 12fb81ffe22d
  - path: Shared/TalabatkData/Talabatk_Context/TalabatkContext.cs
    sha1: b68ecc55a647
  - path: Shared/TalabatkLogic/TalabatkModels/AspNetRole.cs
    sha1: d85b42448589
  - path: Shared/TalabatkLogic/TalabatkModels/Configuration.cs
    sha1: 8cf331bb6f9f
  - path: Talabatk.IDS/Application/Commands/AddNewUserCommand/AddnewUserCommand.cs
    sha1: eebe6161535c
  - path: Talabatk.IDS/Application/Commands/AddNewUserCommand/AddnewUserCommandValidator.cs
    sha1: cda42ee2ccf6
  - path: Talabatk.IDS/Configurations/Identity.cs
    sha1: 9ac57860f5a7
  - path: Talabatk.IDS/Controllers/UsersController/UsersController.cs
    sha1: 2c7b220012a2
  - path: Talabatk.IDS/Helper/AuthHelper/UserAndDeliveryAuthorizationFilter.cs
    sha1: 76f12f193e02
last_updated: 2026-08-23
tags: [flow, technical]
---
# Admin Back-Office — Access and Oversight — Technical

End-to-end trace of how an internal user gets a back-office identity, what decides their
capabilities, how that's (and isn't) enforced across the Angular UI / API attributes / report
surface, and whether the result is recorded. Bridges to
[[Permission.technical|Permission]] and
[[Identity.technical|Identity]] (both read in full) and to
[[_idor-instances|_idor-instances]] for the controller-layer IDOR list — not restated
here. Findings cited by number (`#NNN`) are established in `_system/_conflicts.md`, not
re-investigated.

## Trigger
Two entry points converge on the same tables:
- `Talabatk.IDS/Controllers/UsersController/UsersController.cs:114-163` (`AddNewUser`/`AddUser`,
  MVC, not JSON API) — creates a new staff `AspNetUser`, assigns a role by name.
- `AdminUi/Controllers/Permission/PermissionController.cs:121-177` (`UpdateRole`/`AddNewRole`/
  `DeleteRole`) — reshapes what a role (new or existing) is allowed to do.

## Step-by-step

### 1. Reaching the "create user" page
`UsersController` (`:18-20`) carries class `[Authorize]` plus
`[TypeFilter(typeof(UserAndDeliveryAuthorizationFilter))]`. MVC/Razor, not a JSON API.

### 2. The gate: page-level only, not capability-level
`UserAndDeliveryAuthorizationFilter.OnAuthorization`
(`Talabatk.IDS/Helper/AuthHelper/UserAndDeliveryAuthorizationFilter.cs:32-86`): a `role` claim of
`"admin"` bypasses everything (`:39-43`); otherwise it looks up the caller's role's
`RolePermissions` (`:45-48`) and requires `PermissionId == 102` ("Users" page, `:21`) to reach any
`"Users"` route (`:66,73-77`) — `103` gates `"DeliveryMan"` the same way. This is the filter
`_idor-instances.md` documents as page-level-only and `#427` documents as failing open on a missed
role lookup. **As read in the current working tree** (git status shows this file modified,
uncommitted), the null-role branch now assigns `context.Result = new ForbidResult();` (`:60-61`)
instead of the bare `return` `#427` describes — the fix `#427` recommends appears applied locally;
not confirmed committed/deployed (Open Question). The gate answers "can this caller reach the Users
page," never "should this caller be allowed to grant these specific capabilities" — the gap step 6
exploits.

### 3-4. Building and validating the command
`AddUser(GetAddNewUserViewModel vm)` (`UsersController.cs:124-163`) maps the form onto
`AddnewUserCommand`, including `FullControl = vm.FullControl` (`:140`) and `Role = vm.Role`
(`:145`) verbatim. `AddnewUserCommandValidator.Validate`
(`Talabatk.IDS/Application/Commands/AddNewUserCommand/AddnewUserCommandValidator.cs:9-24`) checks
only that `Password`/`Email` are non-empty — `Role` and `FullControl` are unconstrained here.

### 5. `AddNewUserCommandHandler.Handle`
`Talabatk.IDS/Application/Commands/AddNewUserCommand/AddnewUserCommand.cs:46-228`: phone dedupe
(`:49-56`); delivery-supplier/restaurant-role combination rules (`:57-194`, business rules only, no
caller-privilege check); `AspNetUser.Instance(..., command.FullControl, ...)` (`:196-206`) —
`FullControl` flows straight from the request into the new account's persisted flag;
`userManager.CreateAsync` (`:212`) then `AddToRoleAsync(user, command.Role)` (`:219-223`) —
`Role` is a free-text Identity role name, a **different** mechanism from the `TA_RolePermission`
model steps 7-9 operate on, though both touch `AspNetRoles`. The symmetric edit path,
`UpdateUserCommand` (from `EditUser`, `Talabatk.IDS/Controllers/UsersController/UsersController.cs:83-101`),
accepts the same unconstrained `FullControl`/`Roles` for an *existing* account.

**Traced 2026-08-24: it is not merely the same gap, it is a strictly worse one — see #650.** The create
path mints a new privileged credential; the edit path elevates an account that already exists,
including the caller's own, because `UserId` arrives from the form (`vm.UserId`) and nothing compares
it to the caller. And it rewrites Identity roles wholesale: the handler calls
`user.AspNetUserRoles.Clear()`
(`Talabatk.IDS/Application/Commands/UpdateUserCommand/UpdateUserCommand.cs:231`) and then re-adds
whatever the request listed (`:233-243`). Every validation in that handler concerns role
*combinations* — DeliverySupplier cannot be mixed or hold `FullControl` (`:119-171`), MerchantAdmin
needs a merchant (`:180-204`) — and **none excludes `admin`**, checks the caller's own privilege, or
prevents self-edit. Since a `role` claim of `"admin"` short-circuits the whole authorization filter
(`Talabatk.IDS/Helper/AuthHelper/UserAndDeliveryAuthorizationFilter.cs:39-43`) and the `admin` role is
seeded at startup (`Talabatk.IDS/Configurations/Identity.cs:247-249`), Users-page access is sufficient
to grant yourself unrestricted access — and the Hangfire dashboard with it
(`Talabatk.IDS/Helper/HangFire/DashBoardAuthenticator.cs:13`).

### 6. New finding: page access alone is sufficient to mint a Full-Control account
Steps 2+3+5 combined: the only server check on `AddUser` is "does the caller's role hold
`PermissionId 102`." Nothing checks whether the *creator* holds `FullControl`, is role `admin`
(`AdminRoleId = 1`), or holds any permission beyond page access. A back-office account with nothing
but Users-page access can create a new account with `FullControl = true`
(`AddnewUserCommand.cs:196-206`), which per
[[Permission.technical|Permission]] Rule 3
(`AdminUi/Helper/AuthorizationHelpers/PermissionAuthorizationHandler.cs:47-50`) bypasses every
future `[Permission]` check for that account. **Not yet logged in `_conflicts.md`** — traced fresh
here, adjacent to and independent of `#447`.

### 7. Defining/editing a role: ungated by design (`#447`)
`PermissionController` — class bare `[Authorize]`, no `Roles` (`:25`). None of `UpdateRole`
(`:121-137`), `AddNewRole` (`:141-157`), `DeleteRole` (`:161-177`) add a `[Permission]`. Cite
**`#447`** (critical): any authenticated account — including the one from step 6, or any of the 8
roles seeded at startup (`Talabatk.IDS/Configurations/Identity.cs:240-300`:
`admin/operation/restaurant/DataEntry/Accountants/RestaurantAdmin/Customer/Delivery`) — can grant a
role every permission, or delete a role in use.

### 8. `AddNewRoleCommandHandler.Handle` — resolves a `Permission.technical.md` open question
`Shared/TalabatkApplication/Commands/AddNewRoleCommand/AddNewRoleCommand.cs:29-41` →
`AspNetRole.Instance(name, permissionIds, weight, isInOrdersRound)`
(`Shared/TalabatkLogic/TalabatkModels/AspNetRole.cs:71-91`) wraps every submitted `permissionId`
into a `RolePermission` (`:83-87`) with **no check it exists in `TA_Permission`**, and **no
duplicate-role-name check** (`:75-77`). Confirms `Permission.technical.md`'s open question —
`AddNewRole`/`UpdateRole` do not validate submitted `permissionIds`.

### 9. `UpdateRoleCommandHandler.Handle` — same gap, plus cache invalidation
`Shared/TalabatkApplication/Commands/UpdateRoleCommand/UpdateRoleCommand.cs:31-50`: loads the role
tracked, `roleDetails.UpdateRole(permissionIds)` (`Shared/TalabatkLogic/TalabatkModels/AspNetRole.cs:42-63`, same no-existence-check),
`UpdateWeightAndIsInOrdersRound` (`:65-69`), then invalidates the `UserPermissions`-prefixed
distributed-cache set (`UpdateRoleCommand.cs:47`) — the family the client's permission list is
served from (`Permission.technical.md` Rule 10).

### 10. The escalation chain: `#405` into `#447`
`PermissionController.AllUserPermissions(int userId)` (`:101-118`) carries `[AllowAnonymous]`
(`:102`) overriding the class attribute, computing `UserId = info.UserId == 0 ? userId :
info.UserId` (`:109`) — an unauthenticated caller always has `info.UserId == 0`
(`SessionHandlerMiddleware.cs:22,29`), so the supplied `userId` is used verbatim. Cite **`#405`**:
any account's permissions enumerable with no token, by walking sequential ids. Chained with
**`#447`**: read the map anonymously, sign in with any account, grant every permission found — a
complete unauthenticated-recon-to-full-admin path.

### 11. Server-side action gate, once a role/permission exists
`[Permission("Name")]` (`AdminUi/Helper/AuthorizationHelpers/PermissionAttribute.cs:11-19`) forces
every use through one policy, registered `AdminUi/Startup.cs:173,179-183`. Reflection reads the
**method-level** attribute only and throws if absent (`AttributeAuthorizationHandler.cs:39-56`) — an
action with no attribute never reaches this handler: **13 of 81 `AdminUi` controllers** have no
`[Authorize]` at all (**`#374`**, root cause — no fallback policy in any of 5 `Startup.cs` files).
Six more controllers' `[Authorize]` resolves to SignalR's namespace and enforces nothing
(**`#446`**). Past that, `AuthorizeAsync` has two hardcoded bypasses — `FullControl` claim, and
`AdminRoleId = 1` (`:47-50`, `:20,68-71`) — then an exact-string permission match, fail-closed on
exception (`Permission.technical.md` Rule 4).

### 12. Angular UI gate — mirrors the server, with a confirmed divergence on reports
`AuthGuardGuard.canActivate` (`AdminUi/ClientApp/src/app/auth-guard.guard.ts:27-61`): exact-match
for a single `data.permission` (`:37-40`); **substring** match for `data.ReportPermissions`
(`:32-36`, **`#316`**). Confirmed here that this flow's own report surface uses the buggy branch:
`app-routing.module.ts:270` registers Reports with `data: { ReportPermissions: [...8 report
codes...] }`, and `:263` routes Webhook/ApiKey management through the same family despite not being
reports. `role == 'admin'` also bypasses the guard outright (`:59`). Component-level
`HasPermission()` is reimplemented ~9 times with diverging behavior (Rule 8); the role-creation
form's permission-picker skips required validation (`add-role.component.ts:35`, **`#230`**).

### 13. Server-side gate on the report surface — correctly scoped, unlike step 12
`AdminUi/Controllers/ReportsController/ReportsController.cs` (1,335 lines): class `[Authorize]`
(`:59-60`); each action carries its own distinct `[Permission(Permissions.Reports.X)]` (e.g.
`MerchantsTotal` `:144,455`; `MerchantsDaily` `:219,537`; `ComplaintsReport` `:933`). Per-action
gating here is correct — the step-12 flaw lives in the client guard, not this controller.

### 14. Dashboard surface
`AdminUi/Controllers/DashboardController/DynamicDashboardController.cs:8` — a DevExpress
`DashboardController` subclass, confirmed to carry no `[Authorize]`/`[Permission]` at all. Cite
**`#441`**: unauthenticated at the ASP.NET layer; internal DevExpress enforcement (if any) not
established. (`MerchantDashboardController`, also IDOR-listed, lives in `TalabatkRestaurants` —
out of this flow's scope.)

### 15. The paper trail: structurally dead
Every write above that calls `SaveChangesAsyncWithResult()` routes through
`TalabatkContext.Auditing()`. Cite **`#207`**: `Talabatk_Context/TalabatkContext.cs:574-577` filters
with `x.Entity.GetType().IsAssignableFrom(typeof(IAuditable))` — backwards (should be
`typeof(IAuditable).IsAssignableFrom(entityType)`) — never true for a real entity, so the audit
table has recorded nothing, for any save, system-wide. Every account creation, role edit and
permission grant above leaves no row here. No dedicated "who did what" screen exists in
`AdminUi/ClientApp`; the only "audit"-named UI is a narrow `loyalty-points-settings` log against
`LoyaltyConfigAuditLog`, a separate table (not traced further).

### 16. Configuration management — feature flags
`AdminUi/Controllers/FeaturesManagementController.cs:12-38` (whole file read): only
`[Route]`/`[ApiController]`, no auth attribute. Cite **`#439`**: anonymous read of feature-flag
state via `IFeatureManager.IsFeatureEnabledAsync` (`:32-36`). One of ≥3 distinct feature-flag
mechanisms confirmed codebase-wide (`IFeatureManager`; MediatR `GetFeatureFlagQuery` copy-pasted
across 4 hosts, **`#39`**; IDS's separate Esquio integration) — and the resolved namespace is wrong
in production (`FeatureManagement:DeploymentName` = `"Tests"`/`"Testing"`, never `"Production"`,
**`#356`**).

### 17. Configuration management — accounting config and a credential leak
`AdminUi/Controllers/Configuration/ConfigurationController.cs`: class bare `[Authorize]` (`:46`);
most actions carry `[Permission(...)]` (e.g. `:187` `GetAccountingConfiguration`, `:315`
`UpdateAccountingConfiguration`). **Exception, confirmed directly:** `GetVersioningApiKeyUrl()`
(`:602-617`) carries no `[Permission]`, so any authenticated role reads a live
`VersioningAPIKey` + base URL (`:609-614`, **`#440`**). Behind the correctly-gated
`UpdateAccountingConfiguration` action, `Configuration.UpdateAccountingConfiguration`
(`Configuration.cs:192-245`) validates none of its ~20 ledger account-id mappings
([[Configuration.technical|Configuration]] Rule 1, **`#17`**) — unlike the
sibling delivery-config path, which does validate.

### 18. Configuration management — city settings
Bridge to [[City.technical|City]] — administered through the same `[Permission]` pattern
(`CityController`), per the Admin Back-Office `_knowledge-graph.md` note. Not re-traced; `#441`
separately notes `CityController`/`AreaController`/`CountryController`/`DeliveryZoneController`
each gate mutations but leave reads ungated.

## Data written
1. `AspNetUsers` — new account, including `FullControl` (step 5).
2. `AspNetUserRoles` — join row for the assigned role name (step 5).
3. `AspNetRoles` — new role, or `Weight`/`IsInOrdersRound` on an existing one (steps 7-9).
4. `TA_RolePermission` — join rows reshaping a role's permissions (steps 8-9).
5. Distributed cache — `UserPermissions`-prefixed keys invalidated on role update (step 9).
6. `Configuration` — single system-wide settings row, some groups written with no validation (17).
7. `Audit`/`EntityChangeHistory` — intended for every row above; never actually written (`#207`).

## External calls
- Esquio — external feature-management HTTP service, `Talabatk.IDS` host only (`#39`).
- DevExpress dashboard/report-designer runtime — internal enforcement not established (`#441`).
- Versioning API — only the credential's exposure is in scope here; the call itself not traced
  (`#440`).

## Failure modes
- **`#447`** (critical) — role management ungated; self-service escalation (step 7).
- **`#405`** — anonymous permission-map enumeration, chains into `#447` (steps 6, 10).
- **New, not yet in `_conflicts.md`** — Users-page access alone is sufficient to mint a
  `FullControl` account (step 6); `AddNewRole`/`UpdateRole` never validate `permissionIds` exist,
  resolving a `Permission.technical.md` open question (step 8).
- **`#446`** — six controllers' `[Authorize]` resolves to the wrong namespace (step 11).
- **`#374`** — no fallback authorization policy; root cause of 13 wide-open controllers (step 11).
- **`#316`** — Reports route guard's substring-match branch, confirmed live on this route (step 12).
- **`#441`** — writes gated, reads not; dashboard/report-designer unauthenticated by design
  (steps 14, 18).
- **`#440`** — live third-party API key returned to any authenticated role (step 17).
- **`#439`** — feature-flag management controller fully anonymous (step 16).
- **`#356`** — feature-flag namespace wrong in production, inconsistent across hosts (step 16).
- **`#17`** — accounting/operation/loyalty/review config groups accept unvalidated input (step 17).
- **`#230`** — role-creation permission-picker skips required validation, client-side (step 12).
- **`#207`** — audit trail structurally dead for every write in this flow (step 15).

## Open Questions
- Whether the `UserAndDeliveryAuthorizationFilter` fix seen in the working tree (step 2) is
  committed/deployed or a local in-progress edit — git shows it modified, uncommitted.
- Whether `AddnewUserCommand`'s free-text `Role` and the `AspNetRole`/`TA_RolePermission` model
  (steps 7-9) can drift apart — not traced.
- Whether `UpdateUserCommand` (edit-existing-user) has the same unconstrained `FullControl`/`Roles`
  gap as `AddnewUserCommand` — not opened in this pass.
- Whether the 8 startup-seeded roles are meant to coexist with fully free-form role creation via
  `#447` — a product question, not a code question.
- DevExpress's internal enforcement (if any) for `DynamicDashboardController`/
  `CustomReportDesignerController` — carried over from `#441`, not independently established.
- `AspNetUser.FullControl`'s other call sites beyond `AddnewUserCommand` — carried over from
  `Permission.technical.md`'s own open question.
- Whether a duplicate `AspNetRoles.Name` (permitted per step 8) is reachable, and which row
  `UserAndDeliveryAuthorizationFilter`'s `.FirstOrDefault()` (step 2) would then resolve to.

## Related
- [[Permission.technical|Permission]] · [[Identity.technical|Identity]] — mechanism and rules not restated here.
- [[_idor-instances|_idor-instances]] — controller-layer IDOR list, incl.
  `UserPermissionsController` (`#405`'s authenticated twin) and the six no-token controllers.
- [[Configuration.technical|Configuration]] — the ~130-field settings entity.
- [[City.technical|City]] — city settings, bridged in step 18.
- [[_knowledge-graph|Admin Back-Office]] — the controller inventory this flow's entry points draw from.
