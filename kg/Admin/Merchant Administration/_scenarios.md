---
id: 8orders/admin/merchant-administration/scenarios
title: Merchant Administration — Scenario Catalog
note_type: scenarios
context: Admin
feature: Merchant Administration
audience: Business · QA · Developer
last_updated: 2026-08-23
sources:
  - path: Shared/TalabatkLogic/OrderComplaintAggregate/OrderComplaint.cs
    sha1: e2151a2ca10b
  - path: Shared/TalabatkLogic/OrderComplaintAggregate/MerchantKpiScoreConfiguration.cs
    sha1: ee3d81368326
  - path: AdminUi/Controllers/MerchantController/MerchantController.cs
    sha1: bd49e82a3347
  - path: AdminUi/Controllers/Complaints/ComplaintsController.cs
    sha1: b7b732003697
  - path: AdminUi/Controllers/RestaurantController/RestaurantController.cs
    sha1: f2ffa50b40de
tags: [admin, merchant-administration, scenarios]
---
# Merchant Administration — Scenario Catalog

## Happy path

| # | Precondition | Action | Expected outcome | Rule / source |
|---|---|---|---|---|
| H1 | A restaurant enquires | sign-up application recorded | Lead created and pushed to Bitrix24 | `_integrations.md` row 18 |
| H2 | Lead progresses | polling job runs | Local status mirrored from Bitrix | `_integrations.md` row 18 |
| H3 | Deal agreed | restaurant record created and profile completed | Only reachable here — 47 routes | `AdminUi/Controllers/RestaurantController/RestaurantController.cs` |
| H4 | A store must stop taking orders | force busy from Admin | Store unavailable to customers | `AdminUi/Controllers/RestaurantBusyController/RestaurantBusyController.cs` |
| H5 | Customer complains about an order | complaint recorded | `OrderComplaint` created with `ActionBy`/`ActionDate` still null | `Shared/TalabatkLogic/OrderComplaintAggregate/OrderComplaint.cs:29-58` |
| H6 | Complaint justified | compensation raised and linked | `CompensationId` set on the complaint | `Shared/TalabatkLogic/OrderComplaintAggregate/OrderComplaint.cs:14` |
| H7 | Staff act on a complaint | resolution recorded | `ActionBy` and `ActionDate` filled — the only "handled" signal | `Shared/TalabatkLogic/OrderComplaintAggregate/OrderComplaint.cs:21-22` |
| H8 | Thresholds need tuning | update KPI configuration | Weights and bands validated before saving | `Shared/TalabatkLogic/OrderComplaintAggregate/MerchantKpiScoreConfiguration.cs:33-47` |
| H9 | Finance settles a merchant | `POST api/Merchant/AddTransaction` | Transaction written | `AdminUi/Controllers/MerchantController/MerchantController.cs:40` |
| H10 | Finance reviews a merchant | `GET api/Merchant/GetTransactions` | Account movements | `AdminUi/Controllers/MerchantController/MerchantController.cs:28` |

## Partial / incremental

| # | Precondition | Action | Expected outcome | Rule / source |
|---|---|---|---|---|
| P1 | Complaint created with a blank description | create it | Accepted — `ComplaintOn` is null-coalesced to an empty string rather than refused | `Shared/TalabatkLogic/OrderComplaintAggregate/OrderComplaint.cs:46` |
| P2 | Outgoing-delivery id supplied as `0` | create it | Stored as `null` — a non-positive id is normalised away | `Shared/TalabatkLogic/OrderComplaintAggregate/OrderComplaint.cs:51` |
| P3 | Outgoing-delivery code with surrounding spaces | create it | Trimmed; blank becomes `null` | `Shared/TalabatkLogic/OrderComplaintAggregate/OrderComplaint.cs:52-54` |
| P4 | Linked compensation deleted while in review | compensation removed | `DetachCompensationLink` clears the foreign key rather than leaving it dangling | `Shared/TalabatkLogic/OrderComplaintAggregate/OrderComplaint.cs:61-64` |
| P5 | New environment, no KPI configuration | first use | `CreateDefault()` seeds the singleton | `Shared/TalabatkLogic/OrderComplaintAggregate/MerchantKpiScoreConfiguration.cs:19` |

## Negative / guard

| # | Precondition | Action | Expected outcome (rejection) | Rule / source |
|---|---|---|---|---|
| N1 | Negative rejection-rate weight | update KPI configuration | **Rejected** — message is an Arabic literal in the domain layer | 🔴 `Shared/TalabatkLogic/OrderComplaintAggregate/MerchantKpiScoreConfiguration.cs:41` · #621 |
| N2 | Negative extra-deliveries weight | update KPI configuration | Rejected, Arabic message | 🔴 `Shared/TalabatkLogic/OrderComplaintAggregate/MerchantKpiScoreConfiguration.cs:44` · #621 |
| N3 | `GoodMax` zero or below | update KPI configuration | Rejected, Arabic message | 🔴 `Shared/TalabatkLogic/OrderComplaintAggregate/MerchantKpiScoreConfiguration.cs:47` · #621 |
| N4 | Complaint against a **non-existent order** | create it | **Accepted** — the aggregate performs no validation | 🔴 `Shared/TalabatkLogic/OrderComplaintAggregate/OrderComplaint.cs:29-58` · #620 |
| N5 | The compensation flag set true with no compensation id | create it | **Accepted** — the two fields are declared at `Shared/TalabatkLogic/OrderComplaintAggregate/OrderComplaint.cs:13-14` and never cross-checked by the factory at `Shared/TalabatkLogic/OrderComplaintAggregate/OrderComplaint.cs:42-57` | 🔴 #620 |
| N6 | Not signed in | `api/Merchant/*` | 401 — class-level `[Authorize]` | `AdminUi/Controllers/MerchantController/MerchantController.cs:17` |
| N7 | Not signed in | the merchant report list | **Accepted** — its `[Authorize]` is commented out | 🔴 `_conflicts.md` #570 |

## Returns / cancellation / reversal

| # | Precondition | Action | Expected outcome | Rule / source |
|---|---|---|---|---|
| R1 | Compensation removed | complaint keeps existing | Link cleared, complaint retained | `Shared/TalabatkLogic/OrderComplaintAggregate/OrderComplaint.cs:61-64` |
| R2 | Store forced busy in error | set it available | Reversible from the same screen | `AdminUi/Controllers/RestaurantBusyController/RestaurantBusyController.cs` |
| R3 | Merchant transaction posted wrongly | post an opposite entry | Settlement movements are append-only | [[Merchant-Accounting-and-Order-Cost\|Merchant Accounting & Order Cost]] |
| R4 | Lead rejected | — | Status mirrored from Bitrix; no local delete path traced | `_integrations.md` row 18 |
| R5 | KPI thresholds set badly | update again | Guarded on the way in (N1–N3) | `Shared/TalabatkLogic/OrderComplaintAggregate/MerchantKpiScoreConfiguration.cs:33-47` |

## Integration (cross-side / cross-context)

| # | Precondition | Action | Expected outcome | Rule / source |
|---|---|---|---|---|
| I1 | Sign-up enquiry | Bitrix24 | Lead created; a Hangfire job polls status back | `_integrations.md` row 18 |
| I2 | Store repeatedly rejects orders | RoboCall | Automated voice call to the restaurant | `_integrations.md` row 17 |
| I3 | Merchant settled | GL batch | Movements posted to AccFlex | `_integrations.md` row 20 |
| I4 | Profile edited here | the merchant portal | The portal cannot edit the profile itself, so Admin is the only writer | [[Restaurant Portal/Menu & Order Management/_knowledge-graph\|Menu & Order Management]] |
| I5 | Store forced busy | customer app | Store disappears from the customer's options | [[Customer Ordering/Restaurant & Menu Discovery/_knowledge-graph\|Restaurant & Menu Discovery]] |

## Consistency scenarios

| # | Precondition | Action | Actual outcome today | Finding |
|---|---|---|---|---|
| X1 | Two screens create complaints with different checks | both used | Both succeed; the aggregate imposes no common standard | 🔴 #620 |
| X2 | English-locale admin triggers a KPI validation error | update KPI configuration | Sees **Arabic** text it cannot localise | 🔴 #621 |
| X3 | Monitoring greps for English failure strings | KPI validation fails | The failure is invisible to that rule | 🔴 #621 |
| X4 | Business wants per-merchant scoring | — | Not expressible — the configuration is a platform-wide singleton | 🔴 #621 |
| X5 | No token | merchant report list | Reachable | 🔴 #570 |
| X6 | Complaint "handled" is queried | read the record | Inferred from `ActionDate` being non-null; there is no status field | ⚠️ `Shared/TalabatkLogic/OrderComplaintAggregate/OrderComplaint.cs:21-22` |

## Open Questions

- [ ] Which handlers create complaints, and do they validate consistently (X1)?
- [ ] Should KPI thresholds be per-merchant (X4)?
- [ ] Does `AddTransaction` carry a `[Permission]`? It writes money.
- [ ] Which of `RestaurantController`'s 47 routes does the Admin SPA still call?
- [ ] Is #570's commented-out `[Authorize]` deliberate?
- [ ] Is there any workflow state for a complaint beyond "acted on or not" (X6)?
