---
id: 8orders/delivery/driver-cash-and-compensation/deliverymantransaction-technical
note_type: technical
rule_count: 6
context: Delivery
feature: Driver Cash & Compensation
entity: DeliverymanTransaction
entity_type: child
sources:
  - path: Shared/TalabatkLogic/TalabatkModels/DeliverymanTransaction.cs
    sha1: ad9f630f0b02
last_updated: 2026-08-23
tags: [delivery, delivery-man, financial, technical, backend-domain]
---
# DeliverymanTransaction — Technical

> **Layer:** Backend-Domain — legacy entity with a private constructor and only static factory
> methods (`Instance` + ~15 named wrappers around it), no public mutators. Effectively a write-once
> ledger row.
> **Context:** Delivery (operational cash-accounting for a `DeliveryMen`).
> **Source Path:** `Shared/TalabatkLogic/TalabatkModels/DeliverymanTransaction.cs`   **Last Updated:** 2026-08-03

## Business Rules

### Rule 1: Core factory gate (`Instance`) — shared validation for every transaction
- **Plain language:** Every transaction needs a delivery man and a comment; `Penalty`/`Bonus`
  additionally require an account id, and `Order_Collection` additionally requires an order id.
- **Source:** `DeliverymanTransaction.cs:31-84`. Guards, in order: `accountId` required for
  `Penalty`/`Bonus` (:41-45); `deliveryMan` required (:47-50); `comment` required, **not** checked for
  empty-string, only `null` (:52-55); `entityId` required for `Order_Collection` (:57-60).
- **Side effect at creation:** `Equipment_Deduction` calls `deliveryMan.UpdatePaidFromAssets(amount)`
  (:62-65); `Deposit_Settlement` calls `deliveryMan.UpdatePaidFromInsurance(amount)` (:66-69) — these
  two types mutate the `DeliveryMen` aggregate's running balance the instant the transaction is
  constructed, before it's even saved. No other type does this.

### Rule 2: Fixed credit/debit mapping — the ledger's core rule
- **Plain language:** Every transaction type has one, unchanging direction.
- **Source:** `DeliverymanTransaction.cs:434-455` (`IsTransactionCredit`, exhaustive switch — throws
  `ArgumentException` on an unmapped type, so a new enum value added without updating this switch
  fails loudly rather than silently).

| Transaction Type | Credit (money owed to delivery man)? |
|---|---|
| `Order_Collection` | ❌ Debit — they collected cash, they owe it |
| `Merchant_Paid` | ✅ Credit |
| `Compensation` | ❌ Debit |
| `Bonus` | ✅ Credit |
| `Shift_Bouns` | ✅ Credit |
| `Penalty` | ❌ Debit |
| `Delivery_Receivement` | ✅ Credit |
| `Delivery_Payment` | ❌ Debit |
| `Delivery_Profit` | ✅ Credit |
| `Multi_Delivery_Paid` | ✅ Credit |
| `Multi_Delivery_Collection` | ❌ Debit |
| `Fawry_Payment` | ✅ Credit |
| `Deposit_Deduction` | ❌ Debit |
| `Deposit_Settlement` | ✅ Credit |
| `Equipment_Deduction` | ❌ Debit |
| `Order_Cash_Amount_Refund` | ✅ Credit |

### Rule 3: Amount-positivity validation is inconsistent across factory wrappers
- **Plain language:** Some of the ~15 named creation methods reject a zero/negative amount before
  ever calling the core factory; others don't check at all, relying on the caller to only ever pass a
  sensible value.
- **Guards `amount`/`accountId` explicitly (reject ≤0 / ==0):** `AddInternetOfflineDeductionTransaction`
  (:301-302), `AddInsuranceDailyDeductionTransaction` (:329-330), `AddAssetsDailyDeductionTransaction`
  (:384-385), `AddDeliveryShiftBounsTransaction` (:412-413, amount only),
  `AddInsuranceDepositSettlementTransaction` (:526-530), `AddEquipmentSettlementTransaction` (:557-561).
- **No such guard — trusts the caller/upstream data:** `AddCashOrderTransaction`,
  `AddMerchantCashPaymentTransaction`, `AddCompensationTransaction`, `AddCashRecievementTransaction`,
  `AddFawryTransaction`, `AddCashDeliverPaymentTransaction`, `MultipleDeliveryMoneyTransaction`,
  `AddCreditTransactionForOrderCashAmountRefundToDeliveryMan` — these derive their amount from
  order/compensation/payment data that's presumably already validated upstream, but that assumption
  isn't enforced here. Flagged as an inconsistency to be aware of, not asserted as a live bug.

### Rule 4: Duplicate-transaction prevention uses two different strategies
- **Plain language:** Two different code paths both need to avoid writing the same transaction twice
  for one order, but they check for that in two different ways.
- `AddCashOrderTransaction` (:87-172, handles the single-driver cash-collection + profit pair for one
  order) takes `hasAlreadyCollectionTransction`/`hasAlreadyProfitTransction` as **caller-supplied
  booleans** — the dedup check itself happens somewhere upstream, not in this class.
- `MultipleDeliveryMoneyTransaction` (:457-517, handles the split-delivery case where one delivery man
  hands off to another) instead **computes its own dedup check inline**, scanning
  `deliveryman.DeliverymanTransactions` for an existing row matching the same trimmed `OrderCode` and
  `TransactionType` (:464-468, :490-494) — which requires the caller to have that collection loaded.
- Not confirmed whether this split is deliberate (different call sites, different data-loading
  guarantees) or an inconsistency worth consolidating.

### Rule 5: Same `TransactionType` reused for both "ongoing" and "final settlement" operations
- **Plain language:** A day-to-day equipment deduction and a final equipment settlement when a
  delivery man is dismissed both get recorded as the exact same transaction type — likewise for
  insurance-deposit deductions vs. the final deposit settlement.
- **Source:** `AddAssetsDailyDeductionTransaction` (:378-403) and `AddEquipmentSettlementTransaction`
  (:550-580) both create `Equipment_Deduction` — meaning both trigger the same
  `UpdatePaidFromAssets(amount)` side effect (Rule 1) despite one being routine and the other being a
  final payout at dismissal. Similarly `AddInsuranceDepositSettlementTransaction` (:519-548) creates
  `Deposit_Settlement`, same as any other deposit-settlement transaction. Not confirmed whether
  reporting/reconciliation needs to distinguish "routine" from "final" — flagged as an Open Question.

### Rule 6: Arabic, order-context-aware transaction comments
- **Plain language:** Every transaction's description is composed in Arabic and mentions the order
  code, and for cash-collection/profit transactions also flags whether the delivery was re-routed
  mid-flight or is an external-delivery order.
- **Source:** `AddCashOrderTransaction:99-148` — appends "- إضافة توصيلة جديدة" (address changed) and/or
  "- طلب خارجي" (external order) to both the collection and profit-line comments independently.

## Key Fields
| Field | Meaning | Constraints |
|-------|---------|-------------|
| `DeliveryManId` | Owning delivery man | required (Rule 1) |
| `Amount` | Transaction amount | sign not enforced by type — direction comes from `IsCredit`, not `Amount`'s own sign |
| `IsCredit` | Direction | derived once at creation from `TransactionType` (Rule 2), never changes |
| `TransactionType` | One of 16 enum values | drives both `IsCredit` and, for 2 values, a side effect on `DeliveryMen` (Rule 1) |
| `EntityId` | Polymorphic reference — order id, compensation id, money-request id, etc. depending on type | nullable, meaning depends on `TransactionType` |
| `OrderCode` (`refNumber`) | Human-readable order reference | used for dedup lookups (Rule 4) |
| `AccountId` | Which financial account this nets against | required only for `Penalty`/`Bonus` at the `Instance` gate; several wrapper methods also require it explicitly |
| `CreatedBy` | Actor, defaults to `"System"` | some settlement paths pass a real operator name instead |

## Dependencies & Integrations
| Depends on / integrates | Side/Context | Via | Notes |
|--------------------------|---------------|-----|-------|
| `DeliveryMen` | Backend-Domain, Identity & Access | Required param to every factory method; 2 types mutate it directly (Rule 1) | |
| `OrderDelivery` | Backend-Domain | `AddCashOrderTransaction` reads `TotalCollectedFromCustomer`/`DeliveryManProfit` | Not yet documented in this pass |
| `Order` / `OrderRestaurantDetails` | Backend-Domain, Customer Ordering (partial) | Merchant-payment and cash-refund transactions | `Order` already partially documented |
| `Compensation` | Backend-Domain | `AddCompensationTransaction` | Not yet documented |
| `DeliveryManDaily` | Backend-Domain | `AddCashRecievementTransaction` | Not yet documented |
| `FawryCashCollectionTransaction` | Backend-Domain | `AddFawryTransaction` | Not yet documented |
| `DeliveryMenMoneyRequest` | Backend-Domain | `MultipleDeliveryMoneyTransaction` | Not yet documented |

## Change Surface
| Signal | Value | Notes |
|--------|-------|-------|
| Direct dependents (Ring 1) | 6+ | DeliveryMen, OrderDelivery, Order, Compensation, DeliveryManDaily, FawryCashCollectionTransaction, DeliveryMenMoneyRequest |
| Sides touched | 2/5 confirmed | Backend-Domain, Backend-Application (callers not yet traced) |
| Cross-context integrations | 0 confirmed | Purely internal to Delivery/Customer Ordering's shared order data |
| Domain events involved | 0 | Pure data write, no events raised from this class |
| Hub? | no (leaf ledger), but high fan-in from many order/financial flows |

## Related
- Business view: [[DeliverymanTransaction.business|DeliverymanTransaction]]
- [[DeliveryMen.technical|DeliveryMen]] — Rule 3 (cash-limit math) and Rule 5 (insurance/assets deduction bounds) consume the balances this ledger feeds

## Open Questions
- [ ] Whether reusing `Equipment_Deduction`/`Deposit_Settlement` for both routine and final-settlement
  transactions (Rule 5) causes any reporting ambiguity.
- [ ] Whether the two different dedup strategies (Rule 4) are intentional per call site or worth
  consolidating.
- [ ] `OrderDelivery`, `Compensation`, `DeliveryManDaily`, `FawryCashCollectionTransaction`,
  `DeliveryMenMoneyRequest` are all referenced here but not yet documented themselves.
- [ ] Which Application-layer commands/controllers call each of these factory methods — not yet
  traced (pending the Delivery/Admin context controller passes).
