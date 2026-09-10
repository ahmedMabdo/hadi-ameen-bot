---
id: 8orders/admin/admin-back-office/scenarios
title: Admin Back-Office — Scenario Catalog
note_type: scenarios
context: Admin
feature: Admin Back-Office
audience: Business · QA · Developer
last_updated: 2026-08-23
sources:
  - path: AdminUi/Helper/AuthorizationHelpers/AttributeAuthorizationHandler.cs
    sha1: 37403187a3ea
  - path: AdminUi/Helper/AuthorizationHelpers/PermissionAttribute.cs
    sha1: f0e5e60a8982
  - path: AdminUi/Controllers/Permission/PermissionController.cs
    sha1: b66fad8da160
  - path: AdminUi/Controllers/Configuration/ConfigurationController.cs
    sha1: 5649b853ff01
  - path: AdminUi/Helper/BaseController.cs
    sha1: 68458c9125a2
tags: [admin, admin-back-office, scenarios]
---
# Admin Back-Office — Scenario Catalog

> This is the feature that grants access to the others, so its authorisation rows are the most
> consequential in the graph. Every one was read at the cited line.

## The permission check, as implemented

```
request -> [Authorize] passes (any signed-in user)
        -> policy "Permission" -> AttributeAuthorizationHandler.HandleRequirementAsync
             1. reflect over EVERY assembly in the AppDomain, every request      (:31-35)
             2. find the controller type by class-NAME string match              (:43-44)
             3. take the FIRST method whose name equals the action name          (:46-47)
             4. read its [Permission] attribute
                 ├── present -> evaluate against the user's permissions
                 └── absent  -> throw ApplicationException  => HTTP 500          (:52-55)
             5. var attr = GetAttributes(type);  // computed, never used         (:57)
```

## Happy path

| # | Precondition | Action | Expected outcome | Rule / source |
|---|---|---|---|---|
| H1 | Admin signed in with the right role | open a `[Permission]`-marked screen | Allowed | `AdminUi/Helper/AuthorizationHelpers/AttributeAuthorizationHandler.cs:49-59` |
| H2 | Admin with role-management rights | `POST api/Permission/AddNewRole` | Role created | `AdminUi/Controllers/Permission/PermissionController.cs` |
| H3 | Admin | `GET api/Permission/SystemRoles` | The role list | `AdminUi/Controllers/Permission/PermissionController.cs:25` (class-level `[Authorize]`) |
| H4 | Signed-in user | `GET api/Permission/AllUserPermissions` | **Their own** permissions — the session id wins when present | `AdminUi/Controllers/Permission/PermissionController.cs:109` |
| H5 | Operations staff | `GET api/Configuration/GetDeliveryConfiguration` | Current delivery settings | `AdminUi/Controllers/Configuration/ConfigurationController.cs` |
| H6 | Same | `POST api/Configuration/UpdateDeliveryConfiguration` | Settings changed; the platform picks them up without a deploy | `AdminUi/Controllers/Configuration/ConfigurationController.cs` |
| H7 | Marketing | `POST api/Configuration/UpdateLoyaltyPointsConfiguration` | Loyalty rules changed **and** an audit-log row written | `AdminUi/Controllers/Configuration/ConfigurationController.cs` |
| H8 | Finance asks who changed loyalty | `GET api/Configuration/GetLoyaltyConfigAuditLog` | The change history | `AdminUi/Controllers/Configuration/ConfigurationController.cs` |
| H9 | Marketing | `POST api/Configuration/UpdateMerchantLoyaltyConfigBulk` | Many merchants' participation updated at once | `AdminUi/Controllers/Configuration/ConfigurationController.cs` |

## Partial / incremental

| # | Precondition | Action | Expected outcome | Rule / source |
|---|---|---|---|---|
| P1 | Several merchants to enrol | bulk update, then display-order update | Two steps: participation, then the order they appear in | `AdminUi/Controllers/Configuration/ConfigurationController.cs` |
| P2 | 36 actions on one configuration controller | any single update | Each settings group is updated independently; there is no all-or-nothing save | `AdminUi/Controllers/Configuration/ConfigurationController.cs` |
| P3 | Role edited while a user is signed in | `POST api/Permission/UpdateRole` | Effect on the live session is untraced — permissions are read per request, so it is likely immediate | `AdminUi/Helper/AuthorizationHelpers/AttributeAuthorizationHandler.cs:26-59` |

## Negative / guard

| # | Precondition | Action | Expected outcome (rejection) | Rule / source |
|---|---|---|---|---|
| N1 | Not signed in | any `[Authorize]` Admin screen | 401 | class-level attributes throughout `AdminUi/Controllers/` |
| N2 | Signed in, role lacks the permission | a `[Permission]`-marked action | Denied by the handler | `AdminUi/Helper/AuthorizationHelpers/AttributeAuthorizationHandler.cs:59` |
| N3 | Action under the Permission policy **without** a `[Permission]` attribute | any call | **HTTP 500** — `ApplicationException("ModuleId not provided for this action …")`, not a 403 | 🔴 `AdminUi/Helper/AuthorizationHelpers/AttributeAuthorizationHandler.cs:52-55` · #617 |
| N4 | Route whose controller name matches no type | any call | The type lookup is **unguarded** (`FirstOrDefault` then immediate member access), so a non-matching controller name faults rather than denying | 🔴 `AdminUi/Helper/AuthorizationHelpers/AttributeAuthorizationHandler.cs:43-46` · #618 |
| N5 | Action name overloaded (GET form + POST save) | the POST | Permission may be read from the **first** overload found by reflection | 🔴 `AdminUi/Helper/AuthorizationHelpers/AttributeAuthorizationHandler.cs:46-47` · #618 |

## Returns / cancellation / reversal

| # | Precondition | Action | Expected outcome | Rule / source |
|---|---|---|---|---|
| R1 | Role created in error | `POST api/Permission/DeleteRole` | Deleted — and reachable by any signed-in user | 🔴 `_conflicts.md` #447 |
| R2 | Configuration changed in error | change it back | Symmetric; only loyalty keeps an audit trail of who changed what | `AdminUi/Controllers/Configuration/ConfigurationController.cs` |
| R3 | Loyalty setting change disputed | read the audit log | Answer available for loyalty only, not for delivery, accounting, tips or operations | `AdminUi/Controllers/Configuration/ConfigurationController.cs` |

## Integration (cross-side / cross-context)

| # | Precondition | Action | Expected outcome | Rule / source |
|---|---|---|---|---|
| I1 | Any Admin screen loads | permission check | Reflects over the whole AppDomain **per request**; no caching | `AdminUi/Helper/AuthorizationHelpers/AttributeAuthorizationHandler.cs:31-35` |
| I2 | Configuration changed | every context reads it | Delivery fees, accounting rules and loyalty rates are consumed by Customer Ordering, Delivery and Restaurant Portal | `AdminUi/Controllers/Configuration/ConfigurationController.cs` |
| I3 | Report opened anywhere | shared report engine | Registered with **no authorization callback** | 🔴 `_conflicts.md` #571, #580 |
| I4 | Admin SPA route guard | front end | Broken three independent ways | 🔴 `_conflicts.md` #456 |
| I5 | Sign-in | identity host | Merchant roles are refused on the Admin SPA at login | [[Identity & Access/Authentication & Tokens/_knowledge-graph\|Authentication & Tokens]] |

## Security scenarios — current behaviour

| # | Precondition | Action | Actual outcome today | Finding |
|---|---|---|---|---|
| X1 | **Any** signed-in portal user | `POST api/Permission/AddNewRole` / `UpdateRole` / `DeleteRole` | Roles created, rewritten or deleted — a path from any account to full admin | 🔴 `_conflicts.md` **#447** |
| X2 | **Not signed in at all** | `GET api/Permission/AllUserPermissions?userId=<n>` | That user's full permission list. The action is `[AllowAnonymous]` and falls back to the **caller-supplied** id precisely when there is no session (`info.UserId == 0 ? userId : info.UserId`) | 🔴 `_conflicts.md` **#405** · `AdminUi/Controllers/Permission/PermissionController.cs:101-109` |
| X3 | Signed-in user, screen has no `[Permission]` | open it | Allowed — roughly two-thirds of `AdminUi/Controllers/` files carry no permission marker at all | ⚠️ #446, #560, #567 |
| X4 | Screen under the Permission policy, marker missing | open it | **500**, not 403 — invisible to access-denied monitoring | 🔴 #617 |
| X5 | Two controllers with near-identical names | either route | Resolved by string match; a mismatch throws rather than denying | 🔴 #618 |
| X6 | No token | the report engine's designer/viewer endpoints | Respond | 🔴 #571, #580 |
| X7 | Load spike on Admin | every request | Full AppDomain reflection per authorization check | 🔴 #618 |

## Open Questions

- [ ] `BaseController`'s constructor accepts `IMediator` and `SessionInfo` and **uses neither**
      (`AdminUi/Helper/BaseController.cs:15-18`). Which controllers rely on it for those, and do they
      inject their own? Worth confirming before anyone "tidies" the base class.
- [ ] Should the ~two-thirds of Admin controllers without `[Permission]` have one? That is a policy
      decision, not a bug, but it needs stating either way.
- [ ] Does a role change take effect immediately for a signed-in user (P3)?
- [ ] Why does only loyalty configuration have an audit log? Delivery and accounting settings move money
      too.
- [ ] Is the report engine reachable from outside? #571/#580 depend on it.
