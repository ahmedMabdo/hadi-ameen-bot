---
id: 8orders/restaurant-portal/merchant-finance-and-reporting/scenarios
title: Merchant Finance & Reporting — Scenario Catalog
note_type: scenarios
context: Restaurant Portal
feature: Merchant Finance & Reporting
audience: Business · QA · Developer
last_updated: 2026-08-23
sources:
  - path: TalabatkRestaurants/Controllers/Reports/ReportController.cs
    sha1: 57825548cd87
  - path: TalabatkRestaurants/Controllers/RestaurantPayment/RestaurantPaymentController.cs
    sha1: c78922cebba4
  - path: TalabatkRestaurants/Controllers/MerchantDashboardControllers/MerchantDashboardController.cs
    sha1: 5a24efe5f1ef
  - path: Shared/TalabatkApplication/Queries/GetRestaurantMenuItemActivityQuery/GetRestaurantMenuItemActivityQuery.cs
    sha1: 51cbba0c63e6
tags: [restaurant-portal, merchant-finance-and-reporting, scenarios]
---
# Merchant Finance & Reporting — Scenario Catalog

> Precondition → action → what the code does today. Rows marked 🔴 describe behaviour that is a
> recorded finding: they are in the catalog because a regression suite must know the current
> behaviour, not the wished-for one.

## Happy path

| # | Precondition | Action | Expected outcome | Rule / source |
|---|---|---|---|---|
| H1 | Merchant admin of store 12, unsettled lines exist | open Balance | Balance for store 12 only — the id comes from the session, never the request | `TalabatkRestaurants/Controllers/RestaurantPayment/RestaurantPaymentController.cs:38` |
| H2 | Same | open Payments history | Settlements for store 12, session-scoped | `TalabatkRestaurants/Controllers/RestaurantPayment/RestaurantPaymentController.cs:64` |
| H3 | Same | open the orders behind a settlement | Orders for store 12, session-scoped | `TalabatkRestaurants/Controllers/RestaurantPayment/RestaurantPaymentController.cs:92` |
| H4 | Same | open Merchant Performance report | Report scoped by session `CityId` **and** `RestaurantId` | `TalabatkRestaurants/Controllers/Reports/ReportController.cs:64-65` |
| H5 | Merchant admin whose `userRestaurants` = `"12,13"`, requests store 13 | open Menu Item Activity report | Allowed: 13 is in the accessible list | `GetRestaurantMenuItemActivityQuery.cs:59-62` |
| H6 | Same, requests store 13 | open Rejected Orders report | Allowed, same handler-side check | `TalabatkRestaurants/Controllers/Reports/ReportController.cs:235-240` |
| H7 | Same, requests store 13 | open Sales Item report | Allowed, same handler-side check | `TalabatkRestaurants/Controllers/Reports/ReportController.cs:279-284` |
| H8 | Merchant admin, ad slots available | open Ad cards, reserve one for own store | Slot reserved | `AdsController.cs:113` |
| H9 | Merchant admin | export menu to Excel, edit prices, preview, confirm | Preview shows the diff; confirm applies it | `ExportImportExcelController.cs` (`PreviewPriceUpdateFromExcel` → `ConfirmPriceUpdateFromExcel`) |

## Partial / incremental

| # | Precondition | Action | Expected outcome | Rule / source |
|---|---|---|---|---|
| P1 | Excel upload larger than one request | `POST UploadChunk` repeatedly, then `UploadFiles` | Chunks are written to a configured server path and reassembled | `ExportImportExcelController.cs`; ⚠️ this endpoint is `[AllowAnonymous]` — `_conflicts.md` #42 |
| P2 | Price sheet contains some invalid rows | `PreviewPriceUpdateFromExcel` | Preview returns the parsed set for confirmation rather than applying it — a two-step commit | `ExportImportExcelController.cs` |
| P3 | Merchant admin with 2 branches, no id supplied | `MerchantTotalReport` | Falls back to `sessionInfo.UserRestaurants` — both branches | `TalabatkRestaurants/Controllers/Reports/ReportController.cs:112` |

## Negative / guard

| # | Precondition | Action | Expected outcome (rejection) | Rule / source |
|---|---|---|---|---|
| N1 | Plain `restaurant` role | any `api/Report/*` action with a role gate | 403 | `TalabatkRestaurants/Controllers/Reports/ReportController.cs:51,73,106,127,178,206,253,297` |
| N2 | Merchant admin of store 12 asks the **Menu Item Activity** report for store 99 | pattern-B report | **Empty page, HTTP 200**, and a `LogWarning` naming both ids — not a 403 | `GetRestaurantMenuItemActivityQuery.cs:62-74` |
| N3 | `userRestaurants` claim is an **empty string** | any pattern-B report | Every request returns empty: `"".Split(',')` contains no id, so nothing is ever accessible | `GetRestaurantMenuItemActivityQuery.cs:59` |
| N4 | `userRestaurants` claim is **null** | any pattern-B report | Falls back to the single `UserRestaurantId` — different behaviour from N3 | `GetRestaurantMenuItemActivityQuery.cs:59-60` |
| N5 | No token | `api/RestaurantPayment/*` | 401 — class-level role gate | `TalabatkRestaurants/Controllers/RestaurantPayment/RestaurantPaymentController.cs:18` |

## Returns / cancellation / reversal

| # | Precondition | Action | Expected outcome | Rule / source |
|---|---|---|---|---|
| R1 | Reserved ad slot no longer wanted | (no endpoint in this feature) | Reservations are created, not cancelled, from the portal — cancellation is an Admin action | `AdsController.cs` has `Reserve` and two read actions only |
| R2 | Excel price update previewed but wrong | do not call `Confirm…` | Nothing is applied — the preview step is the reversal | `ExportImportExcelController.cs` |
| R3 | Settlement already paid | — | Statement lines are append-only; corrections come from Admin, not the portal | See [[Delivery/Driver Cash & Compensation/Merchant-Accounting-and-Order-Cost\|Merchant Accounting & Order Cost]] |

## Integration (cross-side / cross-context)

| # | Precondition | Action | Expected outcome | Rule / source |
|---|---|---|---|---|
| I1 | Any report opened | DevExpress engine renders it | Rendering runs through `ConfigureReportingServices`, registered with **no authorization callback** | `_conflicts.md` #571; viewer at `TalabatkRestaurants/Controllers/ReportController.cs:14` (#580) |
| I2 | Day closes (Admin) | GL batch runs | The same settlement lines are posted to AccFlex ERP's general ledger | `_integrations.md` row 20 |
| I3 | Order completes (Customer Ordering) | settlement line written | Every figure in this feature derives from `Order`; no write-back to Customer Ordering | [[Order.technical\|Order]] |
| I4 | Menu changed via Excel | menu entities updated | Writes land on the same items/prices/options that [[Restaurant Portal/Menu & Order Management/_knowledge-graph\|Menu & Order Management]] owns | `ExportImportExcelController.cs` |

## Cross-tenant scenarios — current behaviour

| # | Precondition | Action | Actual outcome today | Finding |
|---|---|---|---|---|
| X1 | Any authenticated portal user (no role needed) | `GET api/Report/MerchantDailyReportDetails?resturantId=99` | Store 99's daily statement | 🔴 `_conflicts.md` #582 · `TalabatkRestaurants/Controllers/Reports/ReportController.cs:90,99` |
| X2 | Merchant admin of store 12 | `GET api/Report/GetFinancialSummary?restaurantIds=99` | Store 99's financial summary, rendered by the report engine | 🔴 `_conflicts.md` #583 · `TalabatkRestaurants/Controllers/Reports/ReportController.cs:131,146` |
| X3 | Merchant admin of store 12 | `GET api/Report/MerchantTotalReport?resturantIds=99` | Store 99's totals — the session value is only the default | 🔴 `_conflicts.md` #584 · `TalabatkRestaurants/Controllers/Reports/ReportController.cs:112` |
| X4 | Merchant admin of store 12 | any of the 5 `MerchantDashboard` charts with `RestaurantIds=99` | Store 99's performance charts | 🔴 `_conflicts.md` #593 · `MerchantDashboardController.cs:34` |
| X5 | Merchant admin of store 12 | `POST api/Ads/Reserve` with `RestaurantId: 99` | Ad slot reserved in store 99's name | 🔴 `_conflicts.md` #603 · `AdsController.cs:113` |
| X6 | `restaurant`-role user | `GET …/ExportImportExcel/Export?restaurantId=99` | Store 99's **full menu and options** exported | 🔴 `_idor-instances.md` #9 · `ExportImportExcelController.cs:52-60` |
| X7 | **No token at all** | `POST …/ExportImportExcel/UploadChunk` | File content written to the configured server path | 🔴 `_conflicts.md` #42 |
| X8 | No token | open the DevExpress designer/viewer endpoints | Report document actions respond | 🟡 `_conflicts.md` #580, #571 |
| X9 | Merchant admin | `GET api/Ads/GetAdCards` | Response may contain literal `null` array entries, breaking strict clients | 🔴 `_conflicts.md` #437 · `GetAdCardsForMerchantQuery.cs:44-63` |

## Open Questions

- [ ] N2's silent-empty behaviour: is any Angular page treating "empty report" as "no sales"? A fix to
      403 would change that page's UX.
- [ ] `GetTransactions` and `GetItemsTurnoverRateReport` handlers were not opened — which scoping
      pattern do they use?
- [ ] Do the five dashboard queries enforce anything handler-side (pattern B) despite #593 finding no
      session use in the controller?
- [ ] Is `UploadChunk`'s anonymity an intentional integration entry point? If yes it needs a shared
      secret; if no it is a straightforward hole.
- [ ] Are ad reservations ever cancelled, and if so from where? No endpoint here does it.
