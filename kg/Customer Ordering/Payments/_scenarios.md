---
id: 8orders/customer-ordering/payments/scenarios
title: Payments — Scenario Catalog
note_type: scenarios
context: Customer Ordering
feature: Payments
audience: Business · QA · Developer
last_updated: 2026-08-23
sources:
  - path: TalabatkAPIs/Controllers/Wallet/WalletController.cs
    sha1: e76da84651f6
  - path: TalabatkAPIs/Controllers/PaymentMethod/PaymentMethodController.cs
    sha1: 9eadf93be946
  - path: Shared/TalabatkLogic/Enum/PaymentMethods.cs
    sha1: 720541e222b5
tags: [customer-ordering, payments, scenarios]
---
# Payments — Scenario Catalog

> The money-moving steps are catalogued here at the level a tester can act on. The full internal
> sequence (which ledger row is written when) is in [[Money-Path.technical|The Money Path]]'s
> "Data written" list; gateway specifics are in [[PayMob.technical|PayMob]] and [[Fawry.technical|Fawry]].

## Happy path

| # | Precondition | Action | Expected outcome | Rule / source |
|---|---|---|---|---|
| H1 | Customer with an address in a country where cash and online exist | open checkout | Only that country's methods are offered | `PaymentMethodController.cs`; `PaymentMethodCountries` |
| H2 | Customer chooses Cash | place order | Order accepted; no money moves yet; the driver will collect | `PaymentMethods.Cash = 1` |
| H3 | Customer chooses Wallet with sufficient balance | place order | Wallet entry written; balance (a sum of entries) falls | [[WalletTransaction\|WalletTransaction]] |
| H4 | Customer chooses Online | place order | `PayMobTransaction` created as `Pending`, customer redirected to the gateway page | `PayMobTransaction.cs`; `PaymentOnlineController.cs:15-20` |
| H5 | Gateway confirms success | callback arrives | HMAC verified, transaction captured, order proceeds | [[PayMob.technical\|PayMob]] |
| H6 | Signed-in customer | `GET api/Wallet/GetBalance` | Their own balance — id taken from the session | `TalabatkAPIs/Controllers/Wallet/WalletController.cs:35-41` |
| H7 | Signed-in customer | `GET api/Wallet/GetMyWelletTransaction` | Their own wallet history | `TalabatkAPIs/Controllers/Wallet/WalletController.cs:68-73` |
| H8 | Cash order delivered | driver completes it | Driver ledger debited for collected cash, merchant statement credited for the food | [[Money-Path.technical\|The Money Path]] steps 6-7 |
| H9 | Driver hands cash to Fawry | remittance recorded | `FawryTransaction` created, then `FawryCashCollectionTransaction` confirms what was actually collected | `FawryTransaction.cs`, `FawryCashCollectionTransaction.cs` |
| H10 | End of period | admin runs the GL batch | Statement lines posted to AccFlex; online money posts a treasury receipt | `_integrations.md` row 20 |

## Partial / incremental

| # | Precondition | Action | Expected outcome | Rule / source |
|---|---|---|---|---|
| P1 | Wallet balance smaller than the order total | choose Wallet | Whether a split wallet+cash payment is allowed was **not traced** — unverified | Open question |
| P2 | Online payment started, customer abandons the gateway page | nothing | `PayMobTransaction` stays `Pending` until `ExpirationDate` / `UnixTimeStampExpiration` passes | `PayMobTransaction.cs` |
| P3 | Driver remits less than they owe | partial remittance | The collection row records what was collected; the driver's balance keeps the remainder | [[Driver-Cash-Cycle.technical\|Driver Cash Cycle]] |
| P4 | Fawry retries a collection | second callback | `IsRetry = true` distinguishes it, so one collection is not credited twice | `FawryCashCollectionTransaction.cs` |
| P5 | Order partly rejected after payment | refund path | Handled by the online-payment refund service, not by this feature's endpoints | [[Cancellation-and-Refund.technical\|Cancellation & Refund]] |

## Negative / guard

| # | Precondition | Action | Expected outcome (rejection) | Rule / source |
|---|---|---|---|---|
| N1 | No token | `GET api/Wallet/GetBalance` | 401 — JWT bearer scheme required at class level | `TalabatkAPIs/Controllers/Wallet/WalletController.cs:15` |
| N2 | Token whose role is not `Customer` | either wallet endpoint | 403 — `Roles = "Customer"` on both actions | `TalabatkAPIs/Controllers/Wallet/WalletController.cs:30,62` |
| N3 | Customer tries to read another customer's wallet | no such parameter exists | Impossible by construction: the id comes from `sessionInfo.CusomerId` and no endpoint accepts a customer id | `TalabatkAPIs/Controllers/Wallet/WalletController.cs:41,73` |
| N4 | Gateway callback with a bad HMAC | callback arrives | Payload is not trusted; the gateway is re-queried before anything is captured | [[PayMob.technical\|PayMob]] |
| N5 | Method not available in the customer's country | attempt to use it | Not offered by the lookup; enforcement beyond the lookup was not traced | Open question |
| N6 | Online payment fails before the gateway accepts it | initiation error | `InitiationFailure` — distinct from `MarkFailed`, which is failure after the attempt started | `PayMobTransaction.cs` |

## Returns / cancellation / reversal

| # | Precondition | Action | Expected outcome | Rule / source |
|---|---|---|---|---|
| R1 | Paid online, order cancelled | refund | Online refund service issues it; ledger entries reverse | [[Cancellation-and-Refund.technical\|Cancellation & Refund]] |
| R2 | Wallet-paid order cancelled | wallet credited back | A new entry, not an edit — the ledger is append-only | [[WalletTransaction\|WalletTransaction]] |
| R3 | Admin credits a wallet by hand | recharge | A reason from `WalletTransactionRechargeReason` is required; retired reasons are soft-deleted so old entries stay readable | `WalletTransactionRechargeReason.cs` |
| R4 | Merchant overpaid | correction | `Merchant_Payment` / `Merchant_Receivement` statement rows | [[Money-Path.technical\|The Money Path]] step 10 |

## Integration (cross-side / cross-context)

| # | Precondition | Action | Expected outcome | Rule / source |
|---|---|---|---|---|
| I1 | Online payment | customer redirected | MVC view `PaymentOnline` renders the gateway hand-off — the only view-serving controller in a pure-API host | `PaymentOnlineController.cs:15-20` |
| I2 | Gateway result | inbound webhook | `PayMobCallBackCommand`, HMAC-signed, with an outbound inquiry fallback | `_integrations.md`; [[PayMob.technical\|PayMob]] |
| I3 | Driver remittance | Fawry rail | Two entities: the remittance attempt and the confirmed collection | [[Fawry.technical\|Fawry]] |
| I4 | Period close | AccFlex ERP | GL journals + treasury receipts | `_integrations.md` row 20 |
| I5 | Order completes | domain events | Driver and merchant ledger rows are written by event handlers, not by an API call | [[Money-Path.technical\|The Money Path]] |
| I6 | Wallet credit by admin | Admin context | Reason list administered in [[Admin/Order & Customer Administration/_knowledge-graph\|Order & Customer Administration]] | |

## Known-issue scenarios — current behaviour

| # | Precondition | Action | Actual outcome today | Finding |
|---|---|---|---|---|
| X1 | Restaurant has no configured ERP account | GL batch runs | Journal entries are posted against `AccountId = 0` rather than rejected | `_conflicts.md` #418(a), via [[Money-Path.technical\|The Money Path]] "Failure modes" |
| X2 | Fawry reports a collected amount | reconciliation | `FawryCashCollectionTransaction.Amount` is a **string** while `FawryTransaction.Amount` is a `decimal`; the conversion point is untraced | technical note Open Questions |
| X3 | Code checks only `Success` on a PayMob transaction | any state read | "Not started" and "finished unsuccessfully" both read as `Success = false`; both flags must be read together | `PayMobTransaction.cs` |
| X4 | A member is inserted into `PaymentMethods` | deployment | Implicit numbering renumbers every later member; any persisted numeric value silently shifts | `PaymentMethods.cs` |

## Open Questions

- [ ] P1: is a split wallet + cash/online payment supported at all?
- [ ] N5: is country availability enforced server-side at checkout, or only by the lookup the client calls?
- [ ] Are `Orange` and `OnlineWallet` both live, and do both route through PayMob?
- [ ] Is the `PaymentMethods` numeric value persisted anywhere (an `OrderPayments` column, an ERP map)?
- [ ] Where is `FawryCashCollectionTransaction.Amount` parsed, and what happens on a malformed value?
