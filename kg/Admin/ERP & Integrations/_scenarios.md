---
id: 8orders/admin/erp-and-integrations/scenarios
title: ERP & Integrations — Scenario Catalog
note_type: scenarios
context: Admin
feature: ERP & Integrations
audience: Business · QA · Developer
last_updated: 2026-08-23
sources:
  - path: AdminUi/Controllers/ErpController/ERPController.cs
    sha1: 4bbd53e5672e
  - path: AdminUi/Helper/ERPIntegration/GlApiServices/GlApiService.cs
    sha1: cf3d51af02ae
  - path: AdminUi/Controllers/ErpIntegrationTrackingController.cs
    sha1: 41e729f28214
  - path: AdminUi/Controllers/ElasticSerach/ElasticSerachController.cs
    sha1: 78fd0dfb607e
tags: [admin, erp-and-integrations, scenarios]
---
# ERP & Integrations — Scenario Catalog

> Outbound plumbing. The money that flows through here is recorded elsewhere — see
> [[Money-Path.technical|The Money Path]] — so these rows are about **whether it leaves correctly**.

## Happy path

| # | Precondition | Action | Expected outcome | Rule / source |
|---|---|---|---|---|
| H1 | Finance needs the accounting structure | `GET api/ERP/GetAllActiveAccount` | Active accounts from AccFlex | `AdminUi/Controllers/ErpController/ERPController.cs:45` |
| H2 | Same | `GET api/ERP/GetAllActiveTreasuries` · `GetAllBanks` | Treasuries and banks | `AdminUi/Controllers/ErpController/ERPController.cs:57`, `:70` |
| H3 | A merchant is due a payment | `POST api/ERP/PayForMerchant` | Payment recorded against the treasury | `AdminUi/Controllers/ErpController/ERPController.cs:86` |
| H4 | A driver is due a payment | `POST api/ERP/PayForDeliveryMen` | Payment recorded | `AdminUi/Controllers/ErpController/ERPController.cs:103` |
| H5 | Day's movements recorded, flag on | journal batch runs | Fourteen journal kinds assembled and posted through the single private poster | `AdminUi/Helper/ERPIntegration/GlApiServices/GlApiService.cs:514`; `_integrations.md` row 20 |
| H6 | ERP holds a new Mart quantity | signed webhook, scheduled pull, or manual sync | Quantity updated locally | `_integrations.md` row 19 |
| H7 | Restaurant submits a sign-up enquiry | lead pushed to Bitrix24 | Lead created; a job polls its status back | `_integrations.md` row 18 |
| H8 | Menu changes | index refreshed | Search reflects the change | `AdminUi/Controllers/ElasticSerach/ElasticSerachController.cs` |
| H9 | Operations ask whether last night worked | open the tracking screen | Run history | `AdminUi/Controllers/ErpIntegrationTrackingController.cs` |

## Partial / incremental

| # | Precondition | Action | Expected outcome | Rule / source |
|---|---|---|---|---|
| P1 | Only some journal kinds enabled | batch runs | Only subscribed kinds are posted — the fourteen builders are a superset of what runs | `AdminUi/Controllers/ErpController/ERPController.cs` + journal-subscription controller |
| P2 | `Features.ValidateQuantitiesLocally` is **true** | cart validation | Stock is checked **locally**; the cart-time ERP pull stays dormant | `_integrations.md` row 19 |
| P3 | `Features.ERPIntegration` off, stock flag on | day ends | **Stock still syncs, journals do not post** — the two flags are independent | `_integrations.md` rows 19, 20 |
| P4 | Lead progresses in Bitrix | polling job | Local status mirrored to `BitirixLeadStatus` | `_integrations.md` row 18 |

## Negative / guard

| # | Precondition | Action | Expected outcome (rejection) | Rule / source |
|---|---|---|---|---|
| N1 | Not signed in | any `api/ERP/*` action | 401 — class-level `[Authorize]` | `AdminUi/Controllers/ErpController/ERPController.cs:22` |
| N2 | Restaurant has no configured account | journal built for it | **Not rejected** — the entry posts against account `0` | 🔴 `_conflicts.md` #418(a) |
| N3 | One malformed row in a day's batch | batch runs | Can roll back the whole run | 🔴 `_conflicts.md` #295 |
| N4 | Stock check fails at cart time (when that path is active) | add to cart | **Blocked** — fail-closed since the #263 fix | 🔴 `_conflicts.md` #263, #272 |
| N5 | Two customers buy the last Mart item simultaneously | both check out | **Both succeed** — nothing reserves stock at checkout | 🔴 `_conflicts.md` #272 (still open) |

## Returns / cancellation / reversal

| # | Precondition | Action | Expected outcome | Rule / source |
|---|---|---|---|---|
| R1 | Online payment refunded | refund journal | A dedicated builder posts the reversal | `GlApiService.RefundedOnlinePayments.cs` |
| R2 | Journal posted in error | — | Accounting reversals are new entries, not deletions | `AdminUi/Helper/ERPIntegration/GlApiServices/GlApiService.cs:514` |
| R3 | Batch failed midway | re-run | Whether it resumes or restarts is **not traced** — see Open Questions | `_conflicts.md` #295 |
| R4 | Stock synced wrongly | manual sync, or the mismatch report | A reconciliation report exists on the merchant side | [[Restaurant Portal/Menu & Order Management/_knowledge-graph\|Menu & Order Management]] |

## Integration (cross-side / cross-context)

| # | Precondition | Action | Expected outcome | Rule / source |
|---|---|---|---|---|
| I1 | Day ends | journals posted | AccFlex GL receives 8Orders' books | `_integrations.md` row 20 |
| I2 | Cash taken or paid at the office | treasury rail | A **separate** service from the journal rail | `_integrations.md` row 20 |
| I3 | Mart quantity changes anywhere | four sync paths | All converge on `MenuItem.MaintainStock(...)` | `_integrations.md` row 19 |
| I4 | Restaurant enquiry | Bitrix24 | Lead pushed; status polled back by a Hangfire job | `_integrations.md` row 18 |
| I5 | Customer searches | Elasticsearch | Results come from the index, not the live tables | [[Search.technical\|Search]] |
| I6 | Driver or merchant movements | ledgers | Sourced from [[DeliverymanTransaction.technical\|DeliverymanTransaction]] and `MerchantStatementTransaction` | `_integrations.md` row 20 |

## Reliability scenarios — current behaviour

| # | Precondition | Action | Actual outcome today | Finding |
|---|---|---|---|---|
| X1 | Restaurant without an account mapping | nightly journal | Entry posted to **account 0**; nothing refuses or alerts | 🔴 #418(a) |
| X2 | Journal builders run in parallel | batch | Shared state inside the builders is **not thread-safe** | 🔴 #293–#294 |
| X3 | An unguarded lookup misses | batch | Can roll back a whole day of postings | 🔴 #295 |
| X4 | `MarkOrderAsPaid` called | — | Dead method; no effect | 🔴 #296 |
| X5 | Last Mart item, two simultaneous checkouts | both proceed | Oversold — no reservation at checkout | 🔴 #272 |
| X6 | Someone disables "ERP" expecting everything to stop | flip one flag | The other integration keeps running | ⚠️ two flags, confusable names |
| X7 | AccFlex and 8Orders drift apart | — | The tracking screen shows runs, **not agreement**; reconciliation is not automated | ⚠️ open question |

## Open Questions

- [ ] Does the batch resume or restart after a mid-run failure (R3, X3)?
- [ ] Which journal kinds are enabled in production? Fourteen builders exist; the subscription list
      decides what actually posts.
- [ ] Is `AccountId = 0` ever legitimate, or should the posting refuse (X1)?
- [ ] Who reconciles AccFlex against 8Orders, and how often (X7)?
- [ ] Do `PayForMerchant` / `PayForDeliveryMen` carry a `[Permission]`? They move money from the Admin UI,
      and roughly two-thirds of Admin controllers carry none (#617/#618).
- [ ] What triggers a search re-index, and what is the customer impact of a stale index?
