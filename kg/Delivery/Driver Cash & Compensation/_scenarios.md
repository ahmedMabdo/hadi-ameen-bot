---
id: 8orders/delivery/driver-cash-and-compensation/scenarios
title: Driver Cash & Compensation — Scenario Catalog
note_type: scenarios
context: Delivery
feature: Driver Cash & Compensation
audience: Business · QA · Developer
last_updated: 2026-08-23
sources:
  - path: TalabatkDelivery/Controllers/Apis/Fawry/FawryController.cs
    sha1: a90c899e3ce5
  - path: Shared/TalabatkData/FawryCashCollectionService/FawryCashCollectionService.cs
    sha1: fb2c3d4c4d3d
  - path: Shared/TalabatkApplication/Commands/FawryPaymentCallbackCommand/FawryPaymentCallbackCommand.cs
    sha1: af10b2e928f9
tags: [delivery, driver-cash-and-compensation, scenarios]
---
# Driver Cash & Compensation — Scenario Catalog

> The money side of a driver's day. Ledger mechanics are in
> [[DeliverymanTransaction.technical|DeliverymanTransaction]] and the end-to-end movement in
> [[Driver-Cash-Cycle.technical|The Driver Cash Cycle]]; this catalog is the observable behaviour.

## Happy path

| # | Precondition | Action | Expected outcome | Rule / source |
|---|---|---|---|---|
| H1 | Driver delivers a cash order | order reaches `Delivered` | Two ledger lines: collection (debit) and delivery profit (credit); balance recalculated | [[Money-Path.technical\|The Money Path]] step 6 |
| H2 | Driver wants to check their position | `GET api/DeliveryMan/GetDeliverymanStatement` | Statement of ledger lines | `TalabatkDelivery/Controllers/Apis/DeliveryManController.cs:1030` |
| H3 | Driver holds cash and wants to deposit | `POST api/Fawry/InitiateFawryTransaction` | A Fawry reference number to present at the point of sale; **driver id taken from the session** | `TalabatkDelivery/Controllers/Apis/Fawry/FawryController.cs:32-42` |
| H4 | Fawry asks what this driver owes | `POST api/Fawry/BillFawryInqiryRequest` | Amount owed, after signature verification | `Shared/TalabatkData/FawryCashCollectionService/FawryCashCollectionService.cs:53-59` |
| H5 | Driver pays at the counter | `POST api/Fawry/FawryPaymentCallback` | Deposit recorded after signature verification; balance falls | `Shared/TalabatkApplication/Commands/FawryPaymentCallbackCommand/FawryPaymentCallbackCommand.cs:63-79` |
| H6 | Fawry confirms the collection | `POST api/Fawry/FawryPaymentNotify` | Recorded; Fawry-protocol status returned | `Shared/TalabatkData/FawryCashCollectionService/FawryCashCollectionService.cs:111` |
| H7 | Driver earns a bonus | bonus scheme evaluated | Credit line added | [[DeliveryBouns.technical\|DeliveryBouns]] |
| H8 | Delivery went wrong, not the driver's fault | compensation approved | Credit line added | [[Compensation\|Compensation]] |
| H9 | Driver hands cash to the office instead | cashier posts a receipt | Credit line added from the Admin ERP screen | `_integrations.md` row 20 |
| H10 | End of day | nightly Hangfire job | Runs for every driver who delivered that working day | [[Driver-Cash-Cycle.technical\|The Driver Cash Cycle]] |

## Partial / incremental

| # | Precondition | Action | Expected outcome | Rule / source |
|---|---|---|---|---|
| P1 | Driver deposits less than they owe | partial payment at Fawry | Balance falls by the deposited amount; the rest stays owed | `Shared/TalabatkData/FawryCashCollectionService/FawryCashCollectionService.cs:104-125` |
| P2 | Two drivers split one order's cash | request → send → confirm handshake | Settled only after the third step | `TalabatkDelivery/Controllers/Apis/DeliveryManController.cs:880`, `:903`, `:926` |
| P3 | Fawry retries a notification | `isRetry` flag set on the payload | Logged with the retry flag; whether the deposit is de-duplicated is **not traced** | `Shared/TalabatkData/FawryCashCollectionService/FawryCashCollectionService.cs:97-102` |
| P4 | Balance is near the limit | one more cash delivery | Crosses the limit and assignment stops mid-shift | see Status/State in the technical note |

## Negative / guard

| # | Precondition | Action | Expected outcome (rejection) | Rule / source |
|---|---|---|---|---|
| N1 | No token | `POST api/Fawry/InitiateFawryTransaction` | 401 — class-level JWT bearer | `TalabatkDelivery/Controllers/Apis/Fawry/FawryController.cs:21` |
| N2 | Forged callback, wrong signature | `POST api/Fawry/FawryPaymentCallback` | **Rejected** — signature mismatch logged with calculated vs received | `Shared/TalabatkApplication/Commands/FawryPaymentCallbackCommand/FawryPaymentCallbackCommand.cs:72-79` |
| N3 | Forged notify, wrong signature | `POST api/Fawry/FawryPaymentNotify` | **Rejected** with `Message_Authentication_Error` in the Fawry protocol, not an HTTP error | `Shared/TalabatkData/FawryCashCollectionService/FawryCashCollectionService.cs:111`, `:120-124` |
| N4 | Billing account maps to no driver | `POST api/Fawry/FawryPaymentNotify` | `Billing_Account_NotExisted` returned | `Shared/TalabatkData/FawryCashCollectionService/FawryCashCollectionService.cs:138-141` |
| N5 | Driver over the cash limit | new order assignment | Not offered — the limit is a hard gate on work, not a warning | technical note, Status/State |

## Returns / cancellation / reversal

| # | Precondition | Action | Expected outcome | Rule / source |
|---|---|---|---|---|
| R1 | A ledger line was wrong | — | **No edit and no delete.** A correcting line is added instead | [[DeliverymanTransaction.technical\|DeliverymanTransaction]] |
| R2 | Deposit initiated but never paid | reference expires unused | No ledger effect until Fawry confirms | `TalabatkDelivery/Controllers/Apis/Fawry/FawryController.cs:32-42` |
| R3 | Compensation approved in error | — | Reversed by an opposite line, not by deletion | [[Compensation\|Compensation]] |
| R4 | Driver leaves owing money | dismissal | Whether an outstanding balance blocks dismissal is **not traced** | [[Identity & Access/Delivery Man Identity/_scenarios\|Delivery Man Identity]] R2 |

## Integration (cross-side / cross-context)

| # | Precondition | Action | Expected outcome | Rule / source |
|---|---|---|---|---|
| I1 | Order delivered | domain event | Ledger written and `RequiredPayment` / `ExceededCashLimit` recalculated | [[Money-Path.technical\|The Money Path]] step 8 |
| I2 | Any deposit or receipt | daily batch | Movements posted to AccFlex ERP's general ledger | `_integrations.md` row 20 |
| I3 | Driver at a Fawry point of sale | Fawry → 8Orders | Three signature-verified webhooks | `TalabatkDelivery/Controllers/Apis/Fawry/FawryController.cs:55`, `:89`, `:101` |
| I4 | Cashier posts at the office | Admin ERP screen | Fourth independent trigger on the same balance | `_integrations.md` row 20 |
| I5 | Merchant side of the same order | statement lines | The merchant's mirror of the same money | [[Merchant-Accounting-and-Order-Cost\|Merchant Accounting & Order Cost]] |

## Consistency scenarios — worth testing explicitly

| # | Precondition | Action | Actual outcome today | Source |
|---|---|---|---|---|
| X1 | Two triggers write the same money (e.g. a Fawry deposit and a cashier receipt for one hand-over) | both run | **Both lines exist.** Nothing reconciles the four triggers against each other | technical note, "Four independent triggers" |
| X2 | Nightly job runs twice in one day | job re-run | Idempotence **not established** — the job is described as running unconditionally | [[Driver-Cash-Cycle.technical\|The Driver Cash Cycle]] |
| X3 | Fawry retries a notify for a deposit already recorded | `isRetry` payload | De-duplication **not traced**; the retry flag is logged but its effect is unverified | `Shared/TalabatkData/FawryCashCollectionService/FawryCashCollectionService.cs:97-102` |
| X4 | Driver declares an arbitrary deposit amount | `InitiateFawryTransaction` with any `Amount` | Accepted as given; whether it is validated against what they owe is **not traced** | `TalabatkDelivery/Controllers/Apis/Fawry/FawryController.cs:32-42` |
| X5 | Bonus or compensation credited | — | Whether these recalculate `ExceededCashLimit` (as delivery does) is **not traced** | technical note, Open Questions |

## Open Questions

- [ ] X1: should the four triggers reconcile? Today the ledger can hold two lines for one hand-over.
- [ ] X2: is the nightly job idempotent?
- [ ] X3: is a retried Fawry notify de-duplicated?
- [ ] X4: is the deposit amount validated against the driver's actual balance?
- [ ] X5: do bonus and compensation credits re-evaluate the cash limit?
- [ ] Where is the per-city cash limit configured, and who may change it? It gates driver availability.
