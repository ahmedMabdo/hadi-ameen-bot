---
id: 8orders/identity-and-access/restaurant-and-admin-user-identity/permission-technical
note_type: technical
rule_count: 10
context: Identity & Access
feature: Restaurant & Admin User Identity
entity: Permission
entity_type: lookup
sources:
  - path: AdminUi/ClientApp/src/app/Shared/components/main-navbar/navbar.component.ts
    sha1: 7b923044a6d0
  - path: AdminUi/ClientApp/src/app/app-routing.module.ts
    sha1: 9d871c81acb6
  - path: AdminUi/ClientApp/src/app/auth-guard.guard.ts
    sha1: 692386091bea
  - path: AdminUi/ClientApp/src/app/non-delivery-reasons/components/banned-clients-report/banned-clients-report.component.ts
    sha1: d8004e7aa2bb
  - path: AdminUi/ClientApp/src/app/order/all-orders/all-orders.component.ts
    sha1: 75c228ef0656
  - path: AdminUi/ClientApp/src/app/order/order-details/order-details.component.ts
    sha1: e301f0bd3b4d
  - path: AdminUi/ClientApp/src/app/permission/add-role/add-role.component.ts
    sha1: aa949fe72c93
  - path: AdminUi/ClientApp/src/app/permission/permission-list/permission-list.component.html
    sha1: d3c32afb0b9f
  - path: AdminUi/ClientApp/src/app/restaurants/offers/offers.component.html
    sha1: 6661398a49b5
  - path: AdminUi/ClientApp/src/app/restaurants/offers/offers.component.ts
    sha1: 8d64a550bae6
  - path: AdminUi/ClientApp/src/app/restaurants/restaurants.component.ts
    sha1: 6fb3e235dbbd
  - path: AdminUi/ClientApp/src/app/wallet-transaction/wallet-transaction/wallet-transaction.component.ts
    sha1: ca82042a771e
  - path: AdminUi/Controllers/Permission/PermissionController.cs
    sha1: b66fad8da160
  - path: AdminUi/Helper/AuthorizationHelpers/AttributeAuthorizationHandler.cs
    sha1: 37403187a3ea
  - path: AdminUi/Helper/AuthorizationHelpers/PermissionAttribute.cs
    sha1: f0e5e60a8982
  - path: AdminUi/Helper/AuthorizationHelpers/PermissionAuthorizationHandler.cs
    sha1: 5f005f84a432
  - path: AdminUi/Helper/Permissions.cs
    sha1: 45e36d79f3f0
  - path: AdminUi/Startup.cs
    sha1: 9b3cc183bae1
  - path: Shared/TalabatkApplication/Commands/UpdateCompensationStateCommand/UpdateCompensationStateCommand.cs
    sha1: 7dc1b3655d34
  - path: Shared/TalabatkApplication/Queries/GetMerchantCapacityHours/GetMerchantCapacityHoursQuery.cs
    sha1: 77199880b218
  - path: Shared/TalabatkApplication/Queries/GetUserActiveHoursReportQuery/UserActiveHoursReportQuery.cs
    sha1: 490b2a4924f3
  - path: Shared/TalabatkApplication/Queries/GetUserPermissionsQuery/GetUserPermissionsQuery.cs
    sha1: 5e07172d7576
  - path: Shared/TalabatkData/Mapping/PermissionMap.cs
    sha1: 5570aed5b1bc
  - path: Shared/TalabatkData/Migrations/20230724073240_permissions.cs
    sha1: 2527852d62e0
  - path: Shared/TalabatkData/Migrations/20230724094622_initPermissions.cs
    sha1: d75941757548
  - path: Shared/TalabatkData/Migrations/20230726102446_ReportsPermissions.cs
    sha1: 6a3bba07f82d
  - path: Shared/TalabatkData/Migrations/20230801063232_AdjustPermissons.cs
    sha1: ca1b1706ab94
  - path: Shared/TalabatkData/Migrations/20231123122330_AlterPermissionName.cs
    sha1: 692bec4207e8
  - path: Shared/TalabatkData/Migrations/20240313091245_deliveryWebsitePermissions.cs
    sha1: e609c5ba486c
  - path: Shared/TalabatkData/Migrations/20260804131955_AddItemReplacementReportPermission.cs
    sha1: e0b1659cda5d
  - path: Shared/TalabatkLogic/Constants/PermissionNames.cs
    sha1: a1decfb9d3a4
  - path: Shared/TalabatkLogic/Enum/DeliveryWebSitePermissions.cs
    sha1: 4a3d3bfd264b
  - path: Shared/TalabatkLogic/TalabatkModels/AspNetUser.cs
    sha1: 237984dd9178
  - path: Shared/TalabatkLogic/TalabatkModels/Permission.cs
    sha1: 53b96a2b1c95
  - path: TalabatkDelivery/Helpers/AuthHelper/CustomPermissionFilter.cs
    sha1: 73b5dff5fff9
last_updated: 2026-08-23
tags: [identity-access, authorization, cross-cutting, technical, backend-domain, frontend]
---
# Permission — Technical

> **Layer:** Cross-cutting — spans Backend-Domain (`TA_Permission`/`TA_RolePermission` tables and
> their EF models), Backend-Application/API host (`AdminUi`'s custom `[Permission]` attribute +
> `PermissionAuthorizationHandler` policy handler), and Frontend (Angular `AuthGuardGuard` route guard
> + a per-component `HasPermission()` template gate, reimplemented independently many times).
> **Context:** Identity & Access — no single bounded context owns it; the DB tables and model classes
> are shared (`Shared/TalabatkLogic`, `Shared/TalabatkData`), but the entire enforcement mechanism
> (attribute, policy, controller, Angular guard) lives in `AdminUi`, which is why it's homed here per
> this repo's shared-entity convention rather than under Admin.
> **Source Path:** `Shared/TalabatkLogic/TalabatkModels/Permission.cs`   **Last Updated:** 2026-08-21

## Business Rules

### Rule 1: Server-side enforcement requires a method-level `[Permission("Name")]` attribute — but its absence isn't fail-closed
- **Plain language:** An admin API action is only permission-checked if a developer explicitly
  decorated it with `[Permission("SomeName")]`. If an action has that attribute, the framework forces
  it through the check; if it has no `[Authorize]`-derived attribute at all, nothing stops the request.
- **Source:** `AdminUi/Helper/AuthorizationHelpers/PermissionAttribute.cs:11-19` — `PermissionAttribute
  : AuthorizeAttribute`, constructor forces `base("Permission")` so every use always targets the same
  policy regardless of the name passed in. `AdminUi/Startup.cs:173` registers
  `PermissionAuthorizationHandler` as the handler for that policy; `AdminUi/Startup.cs:179-183`
  (`AddPolicy("Permission", ...)`) wires it to the shared `PermissionAuthorizationRequirements`.
- **Reflection lookup, throws rather than defaults:** `AdminUi/Helper/AuthorizationHelpers/
  AttributeAuthorizationHandler.cs:39-56` resolves the current controller/action via route data and
  reflection, reads the **method-level** `PermissionAttribute` only, and throws `ApplicationException`
  if the action carries none (`:53-56`) — so a wired-up `[Permission]` action is safe, but an action
  with no attribute at all never reaches this handler in the first place and is simply unauthenticated
  by omission. Confirmed system-wide as **13 of 81 `AdminUi` controllers with no `[Authorize]`
  anywhere in the file** (`_conflicts.md` #374, root-caused to no global `FallbackPolicy` in any of the
  5 hosts' `Startup.cs`).

### Rule 2: Class-level `[Permission]` attributes are silently ignored — dead code, currently latent
- **Plain language:** The attribute can technically be placed on a whole controller class as well as
  on a single action (its `[AttributeUsage]` allows both), but the code that reads it only ever looks
  at the action method — a class-level placement would be read into a local variable and then thrown
  away, never enforced.
- **Source:** `AdminUi/Helper/AuthorizationHelpers/PermissionAttribute.cs:10` (`[AttributeUsage
  (AttributeTargets.Class | AttributeTargets.Method, ...)]`) vs.
  `AttributeAuthorizationHandler.cs:49` (`action.GetCustomAttribute<PermissionAttribute>()` — method
  only) and `:58` (`var attr = GetAttributes(type);` — fetches the class-level attributes into `attr`,
  which is never read or passed to `HandleRequirementAsync`). Checked whether any controller currently
  relies on class-level placement (`grep` across `AdminUi/Controllers` for `[Permission(` directly
  above a `class` declaration) — none found, so this is latent dead code, not a currently-exploited gap.

### Rule 3: Two hardcoded bypasses skip the permission check entirely, for any permission
- **Plain language:** Two conditions short-circuit the whole check and grant access regardless of what
  permission is being asked for: a per-user "Full Control" flag, and membership in the role whose ID is
  literally `1`.
- **Source:** `AdminUi/Helper/AuthorizationHelpers/PermissionAuthorizationHandler.cs:47-50`
  (`if (sessionInfo.FullControl) return true;`) and `:20,68-71`
  (`public const int AdminRoleId = 1;` ... `if (userRoles.Contains(AdminRoleId)) return true;`).
  `sessionInfo.FullControl` is populated from a `fullControl` JWT claim by
  `AdminUi/Helper/Middlewares/SessionHandlerMiddleware.cs:27,31` (identical duplicate at
  `Shared/SharedWeb/Helpers/Middlewares/SessionHandlerMiddleware.cs:27,32`), itself sourced from the
  `AspNetUser.FullControl` boolean (`Shared/TalabatkLogic/TalabatkModels/AspNetUser.cs:36`, private
  setter — only settable through the user's constructor/update methods, not traced further in this
  pass). A handful of individual Application-layer queries/commands additionally OR in `user.FullControl`
  as their own inline bypass, parallel to (not routed through) the attribute/policy mechanism:
  `Shared/TalabatkApplication/Commands/UpdateCompensationStateCommand/UpdateCompensationStateCommand.cs:54`,
  `Shared/TalabatkApplication/Queries/GetMerchantCapacityHours/GetMerchantCapacityHoursQuery.cs:39`,
  `Shared/TalabatkApplication/Queries/GetUserActiveHoursReportQuery/UserActiveHoursReportQuery.cs:43`.

### Rule 4: The actual check is an exact-string match against `TA_Permission.Name`, fail-closed on exception
- **Plain language:** Past the two bypasses, the system looks up every permission name reachable
  through the user's role(s) and checks whether the required permission name is exactly one of them —
  not a partial or case-insensitive match. If anything throws during that lookup, access is denied.
- **Source:** `PermissionAuthorizationHandler.cs:53-63` — joins `AspNetUserRole` → `RolePermission` →
  `Permission` for `sessionInfo.UserId`, then `:74-79` (`currentUserPermissions.Contains(permission)`,
  exact match). `:85-89` — the whole `AuthorizeAsync` body is wrapped in `try/catch` returning `false`
  on any exception, i.e. this path fails closed (contrast the Angular-side checks in Rule 7, which do
  not).

### Rule 5: Permissions are DB-seeded via raw SQL in migrations, not defined by the C# constants — and two unsynced constants files exist
- **Plain language:** The actual list of permissions the system knows about lives in database rows,
  added by hand in a fresh migration nearly every time a new admin feature ships — not derived from
  any single source of truth in code. Two separate C# files each hold their own hardcoded copies of
  some permission-name strings, and neither is checked against the database rows or against each other.
- **Source:** Schema created by `Shared/TalabatkData/Migrations/20230724073240_permissions.cs:12-45`
  (`TA_Permission(PermissionId, Name)`; `TA_RolePermission(PermissionId, RoleId)` join table, cascade
  FKs to `AspNetRoles` and `TA_Permission`). First seeded by
  `20230724094622_initPermissions.cs:10-21` (72 rows) and `20230726102446_ReportsPermissions.cs:10-17`
  (+28 rows); **at least 52 separate migration files** insert `TA_Permission` rows directly via raw
  SQL (confirmed via `grep -rl "INSERT INTO TA_Permission\|INSERT into TA_Permission"
  Shared/TalabatkData/Migrations`), one per admin feature, continuing through
  `20260804131955_AddItemReplacementReportPermission.cs` — the most recent as of this pass. Two
  separate constants files exist: `AdminUi/Helper/Permissions.cs:1-171` (~140 nested static string
  constants, e.g. `Permissions.Order.Orders`, used as the argument to `[Permission(...)]`) and
  `Shared/TalabatkLogic/Constants/PermissionNames.cs:1-7` (a second, much smaller class holding only
  `HireOrDismissDrivers`, whose own doc-comment says these "must match migrations / role assignments"
  — an acknowledgement that nothing enforces the match). No verifier or build-time check ties either
  file to the seeded `TA_Permission.Name` rows; a typo in any of the three places silently produces a
  permission that can never be granted, or a check that can never succeed. Not traced further in this
  pass — no script for detecting this drift was found.
- **Name values aren't stable identifiers either:** `20231123122330_AlterPermissionName.cs:10-13`
  renames a seeded permission's `Name` in place (`CustomersWalletTransactionHistory` →
  `TotalWalletTransactionHistory`) after the fact — any hardcoded reference to the old string name
  would silently stop matching.
- **A full wipe-and-renumber happened once:** `20230801063232_AdjustPermissons.cs:10-18` runs `DELETE
  FROM TA_RolePermission` then `DELETE FROM TA_Permission` before reseeding from `PermissionId 1` —
  every prior role→permission assignment was deleted and every permission ID renumbered in this single
  migration, early in the project's history.

### Rule 6: A third, ID-based enforcement path exists in `TalabatkDelivery`, hardcoded to specific `PermissionId` values
- **Plain language:** Outside `AdminUi`, the delivery web host has its own, completely separate
  permission check that doesn't compare names at all — it compares the numeric database ID of a
  permission against numbers baked into an enum. If those specific rows were ever renumbered (as Rule
  5 shows already happened once, project-wide), this check would silently start checking the wrong
  permission, or a nonexistent one.
- **Source:** `TalabatkDelivery/Helpers/AuthHelper/CustomPermissionFilter.cs:37-50` — loads
  `Roles.Include(x => x.RolePermissions)` and checks `permissions.Any(x => x.PermissionId ==
  (int)DeliveryWebSitePermissions.DeliveryMaps)` (and two siblings). The enum
  (`Shared/TalabatkLogic/Enum/DeliveryWebSitePermissions.cs:4-9`, namespace
  `TalabatkLogic.TalabatkModel.Enum`) hardcodes `DeliveryMaps = 110`,
  `DeliveryMenShif = 111`, `DeliveryManReasonsForNotDeliveringOrder = 112` — matching exactly the IDs
  `IDENTITY_INSERT`-ed for those three names in
  `Shared/TalabatkData/Migrations/20240313091245_deliveryWebsitePermissions.cs:10-12`. This reuses the
  same `TA_Permission`/`TA_RolePermission` tables as `AdminUi` but via a third, independent mechanism
  (by ID, not by name), unrelated to the `[Permission]` attribute/policy of Rules 1-4.

### Rule 7: Client-side route gating (`AuthGuardGuard`) mixes an exact-match branch with a confirmed substring-match branch
- **Plain language:** The route guard reads a comma-joined list of the user's permission names cached
  in the browser. For a normal single required permission it splits that list and checks for an exact
  match. For "report" routes it instead checks whether the raw permission string merely *contains* the
  required code anywhere — a permission code that happens to be a substring of another one the user
  holds would incorrectly pass.
- **Source:** `AdminUi/ClientApp/src/app/auth-guard.guard.ts:27-40` — `:32-36`
  (`permissionString?.includes(element)`, substring, for `route.data['ReportPermissions']`) vs.
  `:37-40` (`permissionString?.split(',')` then `.includes(requiredPermissions)`, exact, for
  `route.data['permission']`) — logged as `_conflicts.md` #316, unverified whether any current
  permission code is actually a substring of another.
- **Broader bypass than "full control":** `auth-guard.guard.ts:53-61` — `activated =
  isAdminWithFullControl || role == 'admin' || hasPermission` — **any** authenticated user whose
  cached `role` claim equals `'admin'`, not only those with the full-control flag, bypasses the guard
  entirely (`:59`).

### Rule 8: Template-level `HasPermission()` is independently reimplemented per component — with diverging behavior
- **Plain language:** There's no single shared place in the Angular app that answers "can this admin
  do X" for hiding/showing buttons — nearly every screen that needs the check has its own copy of a
  `HasPermission` method, and this pass found the copies don't all behave the same way.
- **At least 9 independent implementations**, confirmed via `grep -rn "HasPermission"
  AdminUi/ClientApp/src --include=*.ts`: `app.component.ts:218`,
  `Components/maincontent.component/maincontent.component.ts:88`,
  `non-delivery-reasons/components/banned-clients-report/banned-clients-report.component.ts:145`,
  `order/all-orders/all-orders.component.ts:423`,
  `order/order-details/order-details.component.ts:898` (plus a second, differently-named
  `IsUserHasPermission` at `:911`), `restaurants/offers/offers.component.ts:99`,
  `restaurants/restaurants.component.ts:179`,
  `Shared/components/main-navbar/navbar.component.ts:437`,
  `wallet-transaction/wallet-transaction/wallet-transaction.component.ts:123`.
- **A second, independent substring-match bug, not the same one as Rule 7:**
  `restaurants/restaurants.component.ts:179-189` — `if (this.role == 'admin') return true;` (any
  admin role, no full-control check needed), then `var userPermissions =
  localStorage.getItem('Permissions') as string; if (userPermissions.includes(permission))` — a raw
  string `.includes()` over the whole comma-joined cache, the identical class of over-grant risk as
  `_conflicts.md` #316, but in a component template gate rather than the route guard. This is the
  `HasPermission('Offers')` gate `_conflicts.md` #372 cites as the "good" convention `restaurants.
  component.html:38-42`'s Offer button follows (in contrast to the ungated Delete button beside it) —
  the convention itself is a fail-open substring check, newly traced in this pass, not previously
  logged.
- **A regex-normalization inconsistency:** `app.component.ts:220-223` and
  `Shared/components/main-navbar/navbar.component.ts:441-444` both run
  `permission.replace(/\s([A-Z])/g, '$1')` before comparing — stripping a space that precedes a
  capital letter — apparently a workaround for permission names that historically shipped with
  embedded spaces (e.g. `'AssignOrderToDelivery Man'` in the original seed,
  `Shared/TalabatkData/Migrations/20230724094622_initPermissions.cs:12`, vs. the space-free
  `Permissions.Order.AssignOrderToDeliveryMan` constant, `AdminUi/Helper/Permissions.cs:24`). The
  array-based sibling in `Components/maincontent.component/maincontent.component.ts:88-97` performs no
  such normalization. Whether any currently-seeded permission name still contains a raw space that
  would make these two families of `HasPermission` disagree on the same input is not confirmed in this
  pass (Open Question).
- **A dead, always-false implementation:** `restaurants/offers/offers.component.ts:99-104` — `if
  (this.role == 'admin') return true;` then unconditionally `return false;`, **ignoring its
  `permission` argument entirely**. Confirmed via `grep` that this method is never called anywhere in
  `offers.component.ts` or `offers.component.html` — dead code with no current functional impact, not
  a live bug, but a trap for a future caller who assumes it actually checks the permission passed in.

### Rule 9: Client-side gates are not a security boundary, and are inconsistently applied even as UI convenience
- **Plain language:** Because the browser-side checks above (Rules 7-8) can be wrong in either
  direction — over-granting via substring match, or (in one dead case) always denying — and because
  several admin screens skip the check altogether, the only real security boundary is the server-side
  `[Permission]` check from Rules 1-4, and even that has confirmed gaps.
- **Source:** Confirmed systemic gaps logged as `_conflicts.md` #372 (destructive/privileged controls
  — delete-merchant, rebuild-search-index, approve-mart-product — with no permission gate at all,
  beside sibling controls in the same view that do check); #370 (4 of 72 `AdminUi` routes, including
  the permission-administration route itself, `app-routing.module.ts:96`, carry neither a
  `canActivate` guard nor a `data: { permission }` declaration); #373 (the permission-management
  grid's own Edit/Delete buttons are tooltipped `hint="Clone"`,
  `permission-list.component.html:29-36`); #230 (`add-role.component.ts:35` —
  `new FormControl(Validators.required)` passes the validator function as the control's initial value
  instead of as its validator, so the role-creation form's permission-selection control silently skips
  required validation).

### Rule 10: The endpoint that supplies the client's permission cache is itself anonymous-accessible and trusts a caller-supplied user id
- **Plain language:** Right after login, the admin app calls an endpoint to fetch "what am I allowed
  to do." That endpoint is explicitly marked to allow anonymous callers, and when there's no
  authenticated session it falls back to whatever user id was passed on the query string — so an
  unauthenticated caller can ask for and receive **any** user's permission list by guessing or
  enumerating ids. This is a newly-traced finding in this pass, not yet present in `_conflicts.md`.
- **Source:** `AdminUi/Controllers/Permission/PermissionController.cs:23-26` — class-level
  `[Authorize]` — but `:101-109`, the `AllUserPermissions(int userId)` action carries its own
  `[AllowAnonymous]` (`:102`), overriding the class attribute, and computes `UserId = info.UserId == 0
  ? userId : info.UserId` (`:109`). `info.UserId` (`SessionInfo.UserId`) defaults to `0` for any
  request with no `sub` claim — confirmed at
  `AdminUi/Helper/Middlewares/SessionHandlerMiddleware.cs:22,29` (`context.User.Claims
  .FirstOrDefault(x => x.Type.Equals("sub"))?.Value ?? "0"`) — i.e. exactly the unauthenticated case.
  The handler this calls, `Shared/TalabatkApplication/Queries/GetUserPermissionsQuery/
  GetUserPermissionsQuery.cs:26-41`, returns that user's full distinct permission-name list on success;
  for a `userId` matching no user it instead hits the already-logged null-reference crash at
  `GetUserPermissionsQuery.cs:28-29` (`_conflicts.md` #183) rather than a graceful empty result.

## Key Fields
| Field | Meaning | Constraints |
|-------|---------|-------------|
| `TA_Permission.PermissionId` | Primary key | Seeded via raw SQL per migration (Rule 5), not app-generated |
| `TA_Permission.Name` | The permission's string identifier, matched exactly server-side (Rule 4) | No DB uniqueness/required constraint confirmed in `Shared/TalabatkData/Mapping/PermissionMap.cs:16-17` beyond the PK; renamed in place at least once (Rule 5) |
| `TA_RolePermission.RoleId` / `PermissionId` | Composite PK, many-to-many join to `AspNetRoles` | Cascade delete both directions (`20230724073240_permissions.cs:33-42`) |
| `AspNetUser.FullControl` | Per-user bypass flag (Rule 3) | Private setter — not traced how an admin sets this on another user |
| `PermissionAuthorizationHandler.AdminRoleId` (`= 1`) | Hardcoded role-ID bypass (Rule 3) | Any user in `RoleId 1` bypasses every permission check |
| `AdminUi/Helper/Permissions.cs` constants | ~140 nested string constants, the argument to `[Permission(...)]` | Not validated against DB rows (Rule 5) |
| `Shared/TalabatkLogic/Constants/PermissionNames.cs.HireOrDismissDrivers` | A second, separate permission-name constant | Independent of `Permissions.cs`; own doc-comment admits no enforced sync (Rule 5) |
| `DeliveryWebSitePermissions` enum (`110`/`111`/`112`) | Hardcoded `PermissionId` values for `TalabatkDelivery`'s own check | Fragile to any future ID renumbering (Rule 6) |

## Dependencies & Integrations
| Depends on / integrates | Side/Context | Via | Notes |
|--------------------------|---------------|-----|-------|
| `AspNetRole` / `AspNetUserRole` | Backend-Domain, Identity & Access | FK joins in every permission lookup | Same tables used by all three enforcement mechanisms (Rules 1-4, 6) |
| `AdminUi` controllers (~81) | Backend-Application / API host | `[Permission("Name")]` attribute | Only present where a developer added it (Rule 1); 13 controllers have no gate at all (#374) |
| `TalabatkDelivery` | Backend-Application / API host | `CustomPermissionFilter`, by `PermissionId`, not name | Independent third mechanism, same underlying tables (Rule 6) |
| Angular `AuthGuardGuard` | Frontend | `localStorage.getItem('Permissions')`, route `data.permission`/`data.ReportPermissions` | Exact-match and substring-match branches coexist (Rule 7, #316) |
| Angular per-component `HasPermission()` | Frontend | ~9 independent reimplementations | Diverging behavior confirmed (Rule 8) |
| [[DeliveryMen.technical\|DeliveryMen]] | Backend-Domain, Identity & Access | `HireOrDismissDrivers` permission name (`PermissionNames.cs:6`) gates dismissal/re-hire actions | Named-permission mechanism, not the ID-based one |

## Change Surface
| Signal | Value | Notes |
|--------|-------|-------|
| Direct dependents (Ring 1) | 81 `AdminUi` controllers + `TalabatkDelivery` | Every gated admin action references a permission name or ID |
| Sides touched | 3/5 confirmed | Backend-Domain (tables/models), Backend-Application/API host (`AdminUi`, `TalabatkDelivery`), Frontend (Angular guard + components) |
| Cross-context integrations | 1 confirmed (`TalabatkDelivery`'s ID-based reuse, Rule 6) | Otherwise `AdminUi`-scoped |
| Migrations touching `TA_Permission` | 52+ (raw-SQL seed inserts) | One project-wide wipe-and-renumber (`AdjustPermissons`, Rule 5) |
| Confirmed defects this entity is implicated in | 9 (`#183`, `#230`, `#316`, `#370`, `#372`, `#373`, `#374`, plus 2 newly traced in this pass: Rule 8's `restaurants.component.ts` substring match, Rule 10's anonymous `AllUserPermissions`) | High concentration of findings for one entity |
| Hub? | yes | Read by nearly every `AdminUi` screen/controller; the meta-finding `#383` flagged this note as missing prior to this pass |

## Related
- Business view: [[Permission.business|Permission]]
- [[DeliveryMen.technical|DeliveryMen]] — dismissal/re-hire gated by the named
  `HireOrDismissDrivers` permission
- [[City.technical|City]] — one of many master-data screens whose admin mutations are
  (unevenly) gated by this mechanism

## Open Questions
- [ ] Whether any currently-seeded `TA_Permission.Name` still contains a raw embedded space, which
  would make the regex-normalizing `HasPermission` copies (`app.component.ts`, `navbar.component.ts`)
  disagree with the non-normalizing ones (`maincontent.component.ts`) on the same permission (Rule 8).
- [ ] How/where `AspNetUser.FullControl` is actually set for a given admin (private setter, call site
  not traced in this pass) (Rule 3).
- [ ] Whether the `DeliveryWebSitePermissions` enum's hardcoded IDs (`110`/`111`/`112`) have ever
  drifted from the actual seeded rows since `AdjustPermissons` already renumbered everything once
  project-wide, just before those three were seeded (Rule 6) — the timeline suggests they postdate the
  renumbering, but this wasn't independently confirmed.
- [ ] Whether `PermissionController.UpdateRole`/`AddNewRole` (`PermissionController.cs:121-157`)
  validate that submitted `permissionIds` actually exist — not traced in this pass.
- [ ] The exact severity/exploitability of Rule 10's anonymous `AllUserPermissions` finding (e.g.
  whether `userId`s are easily guessable/sequential) wasn't assessed beyond confirming the code path;
  recommend logging this as a new `_conflicts.md` entry in the next pass.
