---
id: 8orders/admin/catalog-and-content-administration/scenarios
title: Catalog & Content Administration — Scenario Catalog
note_type: scenarios
context: Admin
feature: Catalog & Content Administration
audience: Business · QA · Developer
last_updated: 2026-08-23
sources:
  - path: AdminUi/Controllers/Ad/AdController.cs
    sha1: 07128ada807e
  - path: AdminUi/Controllers/AdCards/AdCardsController.cs
    sha1: f7c862205dca
  - path: AdminUi/Controllers/MartCategory/MartCategoryController.cs
    sha1: a5942025d000
  - path: AdminUi/Controllers/ScheduledNotificationController/ScheduledNotificationController.cs
    sha1: ddfb890c7cef
  - path: AdminUi/Controllers/AudianceController/AudianceController.cs
    sha1: 32cecf91a6be
  - path: AdminUi/Controllers/Brand/BrandController.cs
    sha1: fc4a7b94fdce
tags: [admin, catalog-and-content-administration, scenarios]
---
# Catalog & Content Administration — Scenario Catalog

> The classification rows are ordinary CRUD whose interest is what depends on them. The messaging rows
> are where this feature's recorded defects live.

## Happy path

| # | Precondition | Action | Expected outcome | Rule / source |
|---|---|---|---|---|
| H1 | New brand to add | create it | Available to classify items | `AdminUi/Controllers/Brand/BrandController.cs` |
| H2 | New grocery category | create it | Mart products can be filed under it | `AdminUi/Controllers/MartCategory/MartCategoryController.cs` |
| H3 | Marketing wants a home-screen banner | create a slider | Appears in the customer app carousel | `AdminUi/Controllers/Slider/Slider.cs` |
| H4 | Promotional placement needed | create an ad | Bilingual, city-scoped, with a date range **and** an hour window | `AdminUi/Controllers/Ad/AdController.cs` |
| H5 | Merchant-reservable slots needed | create ad cards | Merchants can reserve them from the portal | `AdminUi/Controllers/AdCards/AdCardsController.cs` |
| H6 | Campaign target needed | define an audience | Customers selected by behaviour | `AdminUi/Controllers/AudianceController/AudianceController.cs` |
| H7 | Message to send now | create a notification | Pushed to the selected customers | `AdminUi/Controllers/NotificationsController/NotificationsController.cs` |
| H8 | Message to repeat | create a scheduled campaign | Recurs on the configured interval | `AdminUi/Controllers/ScheduledNotificationController/ScheduledNotificationController.cs` |
| H9 | Policy text changes | edit the content page | Customer app shows the new text | `AdminUi/Controllers/PrivacyPolicyController/PrivacyPolicyController.cs` |

## Partial / incremental

| # | Precondition | Action | Expected outcome | Rule / source |
|---|---|---|---|---|
| P1 | Ad within its dates but outside its hour window | customer opens the app | **Not shown** — the hour window narrows the date range | `AdminUi/Controllers/Ad/AdController.cs` |
| P2 | Ad has only an Arabic image | customer on English | Per-language images are separate fields, so one may be missing | folded-entity table in [[Customer.technical\|Customer]] |
| P3 | Campaign defined "exactly 7 days" | audience evaluated | Selects **7 days or fewer** — wider than intended | 🔴 `_conflicts.md` #423 |
| P4 | Monthly campaign configured | schedule runs | Fires roughly every **second** month | 🔴 `_conflicts.md` #422 |
| P5 | Yearly campaign configured | schedule runs | Fires roughly every **third** year | 🔴 `_conflicts.md` #422 |

## Negative / guard

| # | Precondition | Action | Expected outcome (rejection) | Rule / source |
|---|---|---|---|---|
| N1 | Not signed in | ad-card screens | 401 — this controller is fully gated (8 permission attributes) | `AdminUi/Controllers/AdCards/AdCardsController.cs` |
| N2 | Signed in without a specific permission | brand, audience, notification screens | **Allowed** — those controllers carry no permission attributes | ⚠️ `AdminUi/Controllers/Brand/BrandController.cs`, `AdminUi/Controllers/AudianceController/AudianceController.cs` |
| N3 | **Not signed in** | Mart category screens | **Allowed** — the controller declares no attributes at all, and conventional routing reaches it | 🔴 `_conflicts.md` #567, #439 · `AdminUi/Controllers/MartCategory/MartCategoryController.cs` |
| N4 | **Not signed in** | scheduled-campaign screens | **Allowed** — anonymous CRUD over campaigns | 🔴 `_conflicts.md` #439 · `AdminUi/Controllers/ScheduledNotificationController/ScheduledNotificationController.cs:21-23` |
| N5 | Signed in, cooking-time screen | any action | Allowed — roleless `[Authorize]`, no permission attributes | 🔴 `_conflicts.md` #560 |

## Returns / cancellation / reversal

| # | Precondition | Action | Expected outcome | Rule / source |
|---|---|---|---|---|
| R1 | Ad published in error | deactivate or change its dates | Ads are date-bounded, so shortening the window ends them | `AdminUi/Controllers/Ad/AdController.cs` |
| R2 | Campaign created in error | delete it | Delete exists — and is reachable anonymously (N4) | `AdminUi/Controllers/ScheduledNotificationController/ScheduledNotificationController.cs` |
| R3 | Notification already sent | — | No recall; a correcting message is the only option | [[Customer.technical\|Customer]] notification section |
| R4 | Classification deleted | — | Items classified by it are affected; cascade behaviour not traced | `AdminUi/Controllers/Brand/BrandController.cs` |
| R5 | Content page wrong | edit it | Takes effect immediately for customers | `AdminUi/Controllers/PrivacyPolicyController/PrivacyPolicyController.cs` |

## Integration (cross-side / cross-context)

| # | Precondition | Action | Expected outcome | Rule / source |
|---|---|---|---|---|
| I1 | Notification created | FCM push | Delivered to the customer app, grouped by payload | `_integrations.md` row 22 |
| I2 | Classification changed | browsing and search | Customer-facing categories change | [[Customer Ordering/Restaurant & Menu Discovery/_knowledge-graph\|Restaurant & Menu Discovery]] |
| I3 | Mart taxonomy changed | stock sync | The same categories the ERP sync populates | `_integrations.md` row 19 |
| I4 | Ad cards published | merchant portal | Merchants reserve slots — and can reserve as another store (#603) | [[Restaurant Portal/Merchant Finance & Reporting/_knowledge-graph\|Merchant Finance & Reporting]] |
| I5 | Content page edited | customer app | Legal text is served from here | |

## Exposure and correctness scenarios — current behaviour

| # | Precondition | Action | Actual outcome today | Finding |
|---|---|---|---|---|
| X1 | **No token at all** | create or edit a scheduled campaign | Accepted — anonymous control over messages sent to the whole customer base | 🔴 `_conflicts.md` **#439** |
| X2 | **No token at all** | Mart category actions via conventional routing (`/MartCategory/{action}`) | Accepted — no attributes at all on the controller | 🔴 `_conflicts.md` **#567**, #439 |
| X3 | Marketing sets "exactly N days" | campaign runs | Reaches everyone within N days — a larger audience than intended | 🔴 #423 |
| X4 | Monthly or yearly campaign | schedule runs | Fires every second month / every third year | 🔴 #422 |
| X5 | Merchant opens available ad cards | portal loads | Response can contain literal `null` entries, breaking strict clients | 🔴 #437 |
| X6 | Any signed-in user | audience or notification screens | Allowed — no permission attributes on those controllers | ⚠️ #617/#618 context |

## Open Questions

- [ ] How many live scheduled campaigns are affected by #422's interval bug?
- [ ] Has any campaign performance been judged against an assumed audience size that #423 made wrong?
- [ ] Are `FoodType`/`FoodTypes` and `StoreType`/`StoreTypes` both live?
- [ ] Is there any audit trail for campaign changes, given X1 permits anonymous ones?
- [ ] What happens to items classified by a deleted brand or category (R4)?
- [ ] Is `InAppMessagingController` a fourth messaging mechanism or a view over an existing one?
