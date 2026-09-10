---
id: 8orders/customer-ordering/payments/fawry-technical
note_type: technical
rule_count: 7
context: Customer Ordering
feature: Payments
sources:
  - path: AdminUi/Controllers/ReportsController/ReportsController.cs
    sha1: e68231848fc9
  - path: AdminUi/Helper/ERPIntegration/GlApiServices/GlApiService.FawryJournal.cs
    sha1: 2c25f6af98b8
  - path: Shared/TalabatkApplication/Commands/AddFawryTransactionCommand/AddFawryTransactionCommand.cs
    sha1: ecafc93dc442
  - path: Shared/TalabatkApplication/Commands/FawryPaymentCallbackCommand/FawryPaymentCallbackCommand.cs
    sha1: af10b2e928f9
  - path: Shared/TalabatkApplication/DomainEventsHandlers/FawryEventHandlers/AddDeliveryManStatementEventHandler.cs
    sha1: 9c053d643398
  - path: Shared/TalabatkApplication/DomainEventsHandlers/FawryEventHandlers/NotifyDeliveryManFawryStatusEventHandler.cs
    sha1: cf0786852165
  - path: Shared/TalabatkApplication/Queries/GetFawryPaidTransctionsByDate/GetFawryPaidTransctionsByDate.cs
    sha1: d76d0fdaae1e
  - path: Shared/TalabatkApplication/Queries/GetFawryTransactionReportQuery/GetFawryTransactionReportQuery.cs
    sha1: 50a595ca2edf
  - path: Shared/TalabatkData/FawryCashCollectionService/FawryCashCollectionService.cs
    sha1: fb2c3d4c4d3d
  - path: Shared/TalabatkData/FawryService/FawryService.cs
    sha1: c8ddebf907c3
  - path: Shared/TalabatkData/Mapping/DeliveryMenMap.cs
    sha1: b94b33c2dab5
  - path: Shared/TalabatkData/Mapping/FawryCashCollectionTransactionMapping.cs
    sha1: 88489d0f27a8
  - path: Shared/TalabatkData/Mapping/FawryTransactionMapping.cs
    sha1: 8543e8bac875
  - path: Shared/TalabatkData/Migrations/20250410165206_addGetFawryTransactionsPermission.cs
    sha1: 1edf4af211a3
  - path: Shared/TalabatkLogic/Enum/AccountingEntriesTypes.cs
    sha1: 77e6d7dff40f
  - path: Shared/TalabatkLogic/Enum/FawryMethod.cs
    sha1: eec56b735731
  - path: Shared/TalabatkLogic/Enum/PaymentMethods.cs
    sha1: 720541e222b5
  - path: Shared/TalabatkLogic/TalabatkModels/DeliverymanTransaction.cs
    sha1: ad9f630f0b02
  - path: Shared/TalabatkLogic/TalabatkModels/FawryCashCollectionTransaction.cs
    sha1: e279ee39b54e
  - path: Shared/TalabatkLogic/TalabatkModels/FawryTransaction.cs
    sha1: c2c956b22702
  - path: TalabatkDelivery/Controllers/Apis/Fawry/FawryController.cs
    sha1: a90c899e3ce5
  - path: TalabatkDelivery/appsettings.json
    sha1: f64d0fc469c9
last_updated: 2026-08-23
tags: [delivery, payments, financial, technical, backend-application]
---
# Fawry — Technical

> **Layer:** Spans four layers, no single owner — `FawryTransaction`/`FawryCashCollectionTransaction`
> (Backend-Domain, `TalabatkLogic`), `FawryService`/`FawryCashCollectionService` (Backend-Data,
> outbound HTTP + EF), the `*Command`/`*Query` handlers (Backend-Application), and `FawryController`
> (Backend-API, hosted only in `TalabatkDelivery`).
> **Context:** Not a Customer Ordering payment path despite this note's filing location (see
> Correction below) — functionally this is Delivery: how a delivery man remits/settles the cash they
> collected on behalf of the platform, using Fawry as a payment rail.
> **Source Path:** `Shared/TalabatkLogic/TalabatkModels/FawryTransaction.cs`,
> `Shared/TalabatkLogic/TalabatkModels/FawryCashCollectionTransaction.cs`,
> `Shared/TalabatkData/FawryService/FawryService.cs`,
> `Shared/TalabatkData/FawryCashCollectionService/FawryCashCollectionService.cs`,
> `TalabatkDelivery/Controllers/Apis/Fawry/FawryController.cs`   **Last Updated:** 2026-08-21

## Correction: Fawry is not a customer/Order payment method in this codebase
The task that produced this note assumed Fawry is a customer-facing checkout option (the standard
wikilink template pointed at `Order.technical`). Tracing the code contradicts that:
- `PaymentMethods` (`Shared/TalabatkLogic/Enum/PaymentMethods.cs:5-17`) — the enum that drives
  customer checkout — has exactly five values (`Cash`, `Wallet`, `Online`, `Orange`,
  `OnlineWallet`). There is no `Fawry` member.
- `FawryTransaction` (`Shared/TalabatkLogic/TalabatkModels/FawryTransaction.cs:16-31`) has
  `DeliveryManId`, `FawryProfileId`, `SalesDailyId` — no `OrderId` or any FK to `Order`.
- `FawryCashCollectionTransaction` (`Shared/TalabatkLogic/TalabatkModels/FawryCashCollectionTransaction.cs:13-23`)
  likewise keys off `DeliveryManId`/`FawryProfileId` only.
- Every consumer of a Fawry transaction is delivery-man ledger code: `DeliverymanTransaction.AddFawryTransaction`
  (`Shared/TalabatkLogic/TalabatkModels/DeliverymanTransaction.cs:249-269`) creates a `Fawry_Payment`
  ledger row, which [[DeliverymanTransaction.technical|DeliverymanTransaction]]
  Rule 2 confirms is a **credit** (money the delivery man no longer owes) — the opposite direction of
  `Order_Collection` (a debit, cash the delivery man picked up from a customer).

So: **Fawry, here, is the payment rail delivery men use to pay their accumulated cash-in-hand
liability back to the platform** — either by pushing a payment (Fawry retail reference number or
Fawry mobile wallet) or by a Fawry outlet cashier reporting a cash deposit back to this system
(bill-payment/biller flow). It does not touch customer checkout or `Order` payment records — see
Open Questions.

## Business Rules

### Rule 1: Two independent Fawry flows exist, in opposite directions
- **Plain language:** A delivery man can either *push* a payment from inside the app (choosing a
  Fawry retail reference number or Fawry mobile wallet), or *walk into any Fawry retail outlet* and
  pay cash there, with Fawry notifying this system afterward as a bill-collection agent.
- **Source, push flow:** `AddFawryTransactionCommand.cs:48-110` creates a `FawryTransaction`
  (`CreateTransaction`, :128-149) then calls `IFawryService.PayByReferenceNumber` or `PayByWallet`
  (:67-93) depending on `FawryMethod` (`Shared/TalabatkLogic/Enum/FawryMethod.cs:11-12`:
  `ReferenceNumber=1`, `Wallet=2`).
- **Source, pull/biller flow:** `FawryCashCollectionService.FawryPaymentNotify`
  (`Shared/TalabatkData/FawryCashCollectionService/FawryCashCollectionService.cs:95-223`) is called
  by Fawry itself when a delivery man pays cash at any Fawry outlet, identified by the delivery man's
  `FawryProfileId` acting as a Fawry "billing account" (`FawryInqiryRequest`, same file :49-93, is
  Fawry's pre-payment account-lookup call).

### Rule 2: The push flow's outbound charge request is HMAC-signed, and its inbound webhook confirmation IS signature-verified
- **Plain language:** Every request this system sends to Fawry to initiate a charge, and every
  callback Fawry sends back, carries a SHA-256 signature built from a shared secret — the callback
  handler recomputes and compares it before trusting the callback.
- **Source, outbound signing:** `FawryService.cs:136-145` (`GenerateSignature`, hex SHA-256 of
  `merchantCode + merchantRefNum + profileId + paymentMethod + amount + [debitMobileWalletNo] +
  securityKey`), used building both request types (:91, :128) with `Fawry:MerchantCode` and
  `Fawry:SecurityKey` read from config (:63-64, :100-101).
- **Source, inbound verification:** `FawryPaymentCallbackCommand.cs:61-80` reads
  `Fawry:SecurityKey` (:61), recomputes the same hex-SHA-256 shape over the callback's own fields
  (`GenerateSignature`, :122-140) and **rejects the callback with `Result.Failure` if the signature
  doesn't match** (:72-80) — the transaction lookup happens first (:46-58), so a forged callback for a
  real `MerchantRefNumber` is still caught by the signature check before any state changes. This is
  the most important integrity control for a payment webhook, and it is present and enforced here.

### Rule 3: The pull/biller flow is separately signed with its own secret and a different encoding
- **Plain language:** The Fawry-outlet cash-collection callback uses a different shared secret and a
  different signature encoding (base64 of the SHA-256 hash, not hex) than the push-flow callback —
  the two are not interchangeable.
- **Source:** `FawryCashCollectionService.cs:226-275` (`GenerateSignature` overloads, base64-encoded
  SHA-256 of `serviceCode + billingAcct + extraBillingAcctValues + [amount] + securityKey`), keyed by
  `FawryCashCollection:SecurityKey` (read at :57, :109) — a **distinct** config value from
  `Fawry:SecurityKey`. Both `FawryInqiryRequest` (:59-64) and `FawryPaymentNotify` (:111-125) verify
  the incoming signature and return a `Message_Authentication_Error` status code on mismatch before
  touching any delivery-man data. Every success response is itself signed back to Fawry
  (`GenerateResponseInquirySignature`/`GenerateResponseNotifySignature`, :277-293).

### Rule 4: Both anonymous Fawry-facing controller endpoints are intentionally public, but one auth layer is JWT-gated
- **Plain language:** `FawryController` requires a logged-in delivery man's JWT for everything by
  default, except the three routes Fawry's own servers call, which must stay open since Fawry cannot
  present a delivery-man token.
- **Source:** `TalabatkDelivery/Controllers/Apis/Fawry/FawryController.cs:21`
  (`[Authorize(AuthenticationSchemes = JwtBearerDefaults.AuthenticationScheme)]`, class-level) vs.
  `[AllowAnonymous]` on `FawryPaymentCallback` (:56), `BillFawryInqiryRequest` (:89), and
  `FawryPaymentNotify` (:101). `InitiateFawryTransaction` (:32-33, the delivery man pushing a payment)
  keeps the class-level JWT requirement. Consistent with `_conflicts.md` #374, which lists the
  Fawry webhooks among the endpoints correctly left anonymous.

### Rule 5: A successful push-flow payment fans out into a ledger entry and a push notification, both best-effort
- **Plain language:** Once Fawry confirms a push-flow payment as `PAID`, this system records a
  matching accounting-ledger row for the delivery man and sends them a notification — but if either
  step fails, nothing rolls back and nothing surfaces the failure beyond a log line.
- **Source:** `FawryTransaction.UpdateStatus` (`FawryTransaction.cs:77-108`) raises
  `AddDeliveryManStatementEvent` only when the new status is `PAID` (:103-104), and always raises
  `NotifyDeliveryManFawryStatusEvent` (:106). The statement handler
  (`AddDeliveryManStatementEventHandler.cs:41-87`) dedups on `TransactionType == Fawry_Payment` for
  that `FawryTransactionId` (:58-59) then wraps the whole write in try/catch that only logs on
  failure (:82-85) — a failed ledger write is swallowed, matching the pattern `_conflicts.md` #213
  already flags for this feature's Hangfire job. The notification handler
  (`NotifyDeliveryManFawryStatusEventHandler.cs:24-31`) sends "تمت عملية الدفع" (payment succeeded) or
  "فشلت عملية الدفع" (payment failed) depending on status.

### Rule 6: The biller-flow cash job computes and locks/unlocks the delivery man's cash-limit state
- **Plain language:** When a Fawry cash-collection payment is confirmed, a background job recomputes
  how much more the delivery man still owes toward their mandatory daily deposit, and locks or unlocks
  their account accordingly.
- **Source:** `FawryCashCollectionService.CreateDeliveryStatementTransaction` (:321-391, a Hangfire job
  queued at :154/:189, retried up to 4 times per `[AutomaticRetry(Attempts = 4)]` at :319) computes
  `requiredPayment` from `MandatoryDailyDepositPercentage` and the delivery man's running balance
  (:328-348), writes a `Fawry_Payment` ledger row via `DeliverymanTransaction.AddFawryTransaction`
  (:350-354), then sets `ExceededCashLimit` in the delivery-man Redis cache and
  `UpdatePartialPaymentBlocked`/`UpdateRequiredPaymentToLockExceedCashLimit` (:367-388) depending on
  whether the payment covered what was required. The method's **final** save (:389) is a bare
  `await _context.SaveChangesAsync()`, not the `WithResult`-wrapped calls used everywhere else in the
  same method (:311, :358) — this is the exact call site `_conflicts.md` #213 cites: if this last save
  fails, the job still returns `Result.Success()`.

### Rule 7: Daily Fawry receipts (both flows combined) post as one ERP journal entry
- **Plain language:** Once a day, the total cash collected through both Fawry flows is posted to the
  accounting system as a single journal entry, skipped entirely if nothing was collected.
- **Source:** `GlApiService.FawryJournal.cs:13-78` (`CreateFawryTransctionsJournal`) sums
  `_fawryJournalTransactionsAmount + _fawryJournalCollectionsAmount` (:15) — i.e. both the push-flow
  and biller-flow totals — and returns `ErpJournalSendResult.Bypassed` if the total is zero (:17-20).
  Otherwise it credits `DeliveryMenTotalAccountId` and debits `FawryAccountId` (:41-62), and records
  the posted journal as an `AccountingEntry` of type `AccountingEntriesTypes.FawryReceivement`
  (`Shared/TalabatkLogic/Enum/AccountingEntriesTypes.cs:12`, value `8`) linked to that day's
  `SalesDaily` (:69-76).

## Key Fields
| Field | Meaning | Constraints |
|-------|---------|-------------|
| `FawryTransaction.FawryTransactionId` / `MerchantRefNumber` | Primary key / this system's reference sent to Fawry | `MerchantRefNumber` has a unique DB index (`FawryTransactionMapping.cs:26`), max length 20 (`FawryTransactionMapping.cs:23-25`) |
| `FawryTransaction.DeliveryManId` | Owning delivery man | Required FK (`FawryTransaction.cs:36-37`); no `OrderId` exists on this entity |
| `FawryTransaction.FawryProfileId` | The delivery man's Fawry customer-profile id used for the push flow | Required (`FawryTransaction.cs:39-40`) — distinct field from `FawryCashCollectionTransaction.FawryProfileId`, though both derive from `DeliveryMen.FawryProfileId` |
| `FawryTransaction.PaymentMethod` | `FawryMethod` — `ReferenceNumber` or `Wallet` | `FawryMethod.cs:11-12` |
| `FawryTransaction.FawryStatus` | `FawryPaymentStatus` — `NEW`/`PAID`/`CANCELED`/`REFUNDED`/`EXPIRED`/`PARTIAL_REFUNDED`/`FAILED` | Default `NEW` (`FawryTransactionMapping.cs:22`); transitions validated in `UpdateStatus` (`FawryTransaction.cs:77-108`), unrecognized status string ⇒ `Result.Failure` |
| `FawryTransaction.SalesDailyId` | Which daily settlement batch this transaction was rolled into | Nullable FK (`FawryTransactionMapping.cs:32`); set via `SetSalesDaily` (`FawryTransaction.cs:64-67`) |
| `DeliveryMen.FawryProfileId` | Delivery man's Fawry billing-account identifier | Unique index, max length 50 (`Shared/TalabatkData/Mapping/DeliveryMenMap.cs:59-60`) — contrast `UserName` on the same entity, indexed but **not** unique (`_conflicts.md` #12) |
| `FawryCashCollectionTransaction.TransactionId` | Fawry's own transaction id for a cash-collection payment | Used for app-level dedup (`FawryCashCollectionService.cs:145-146`), but **no unique DB index** on this column (`FawryCashCollectionTransactionMapping.cs:12-22` has no `HasIndex` at all) — see Open Questions |
| `FawryCashCollectionTransaction.IsRetry` | Whether this notify call is Fawry retrying a prior notification | Drives the create-vs-update branch in `FawryPaymentNotify` (`FawryCashCollectionService.cs:145-221`) |
| Config: `Fawry:MerchantCode`, `Fawry:SecurityKey` | Outbound push-flow credentials | `TalabatkDelivery/appsettings.json:105-106` — values not reproduced here per this pass's security handling; `_conflicts.md` #347, #358 already flag these as committed secrets |
| Config: `Fawry:FawryPaymentUrl` | Outbound charge endpoint | `TalabatkDelivery/appsettings.json:107` — **points at Fawry's staging host** (`atfawry.fawrystaging.com`) with a `//change to production url` comment on the line; `_conflicts.md` #358 |
| Config: `Fawry:FawryWebHookUrl` / `FawrySystemWebHookUrl` | Where Fawry should call back / the local route it maps to | `TalabatkDelivery/appsettings.json:108-109` |
| Config: `FawryCashCollection:SecurityKey`, `:FawryInqiryRequest`, `:FawryPaymentNotify` | Biller-flow secret and local route paths | `TalabatkDelivery/appsettings.json:119-121` |

## Dependencies & Integrations
| Depends on / integrates | Side/Context | Via | Notes |
|--------------------------|---------------|-----|-------|
| [[DeliveryMen.technical\|DeliveryMen]] | Backend-Domain, Identity & Access | `FawryProfileId` FK on both transaction types; feeds `MandatoryDailyDepositPercentage`, `CashLimit` math (Rule 6) | Same cash-limit machinery [[City.technical\|City]] Rule 2 configures the defaults for |
| [[DeliverymanTransaction.technical\|DeliverymanTransaction]] | Backend-Domain, Delivery | `AddFawryTransaction` factory (`DeliverymanTransaction.cs:249-269`) writes a `Fawry_Payment` (credit) ledger row | This note's Rule 2 documents the credit/debit table |
| Fawry (external gateway) | Third-party | Outbound HTTPS POST (`FawryService.cs:49-51`) to `Fawry:FawryPaymentUrl`; inbound webhooks to `FawryController` | Currently configured to staging (`_conflicts.md` #358) |
| AccFlex ERP (`GlApiService`) | Backend-Application (Admin) | `GlApiService.FawryJournal.cs:13-78` posts a daily journal entry | Not yet documented as its own note |
| `SalesDaily` | Backend-Domain | `FawryTransaction.SalesDailyId` FK; `AccountingEntry` linkage in the ERP journal (Rule 7) | Not yet documented as its own note |
| Hangfire (`delivery` queue) | Cross-cutting infra | `CreateDeliveryStatementTransaction` (`FawryCashCollectionService.cs:319-321`), `AddDeliveryManStatementEvent` job (`AddDeliveryManStatementEventHandler.cs:46-48`) | Both retried automatically on failure |
| Redis (`IDeliverymenCache`) | Cross-cutting infra | `SetField(..., ExceededCashLimit, ...)` (`FawryCashCollectionService.cs:369,375,382`) | Cash-limit lock flag read elsewhere in Delivery |
| `Order` / `PaymentMethods` | Customer Ordering | **Not integrated** — `PaymentMethods` enum has no `Fawry` value; no FK from either Fawry transaction type to `Order` | See Correction above |

## Change Surface
| Signal | Value | Notes |
|--------|-------|-------|
| Direct dependents (Ring 1) | 3 confirmed | `DeliveryMen`, `DeliverymanTransaction`, `SalesDaily`/ERP journal |
| Sides touched | 4/5 confirmed | Backend-Domain, Backend-Application, Backend-Data, Backend-API (`TalabatkDelivery` host only — not present in any other host's config) |
| Cross-context integrations | 1 external (Fawry gateway) + 1 ERP (AccFlex) | No integration with Customer Ordering/`Order` |
| Domain events involved | 2 | `AddDeliveryManStatementEvent`, `NotifyDeliveryManFawryStatusEvent` (`FawryTransaction.cs:110-120`) |
| Hub? | no | Narrow, delivery-man-only feature; high financial sensitivity, low fan-in |

## Related
- Business view: [[Fawry.business|Fawry]]
- [[DeliveryMen.technical|DeliveryMen]] — owns `FawryProfileId` and the cash-limit balances this feature settles
- [[DeliverymanTransaction.technical|DeliverymanTransaction]] — the ledger both Fawry flows write into (`Fawry_Payment`, a credit)
- `_conflicts.md` #12, #157, #213, #340, #347, #358, #374, #383 — prior findings on this feature, referenced above rather than re-investigated

## Open Questions
- [ ] `FawryCashCollectionTransaction.TransactionId` is used for dedup in application code
  (`FawryCashCollectionService.cs:145-146`) but has no unique database index
  (`FawryCashCollectionTransactionMapping.cs`) — whether two concurrent retry notifications for the
  same `TransactionId` could both pass the `AnyAsync` check and double-write was not traced in this
  pass.
- [ ] Whether `GetFawryTransactions` (`AdminUi/Controllers/ReportsController/ReportsController.cs:965-985`,
  gated only by the controller's class-level `[Authorize]` at :59) is further restricted by the
  dedicated permission the migration `20250410165206_addGetFawryTransactionsPermission.cs` suggests
  exists — the enforcement point wasn't traced.
- [ ] Whether the reporting bugs already logged in `_conflicts.md` #157
  (`GetFawryPaidTransctionsByDate.cs:35-39`, `GetFawryTransactionReportQuery.cs:45-46`) affect the
  `GetFawryTransactions` endpoint above.
- [ ] Whether `FawryTransaction` and `FawryCashCollectionTransaction`, being distinct tables covering
  the two Fawry flows for the same delivery man, are ever reconciled against each other (e.g. could
  the same real-world cash payment be recorded twice, once per flow) — not traced.
- [ ] `GlApiService`/AccFlex ERP integration and `SalesDaily` are not yet documented as their own
  notes.
