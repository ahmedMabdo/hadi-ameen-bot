---
id: 8orders/identity-and-access/customer-identity/wallettransaction
note_type: single
rule_count: 8
context: Identity & Access
feature: Customer Identity
entity: WalletTransaction
entity_type: child
sources:
  - path: Shared/TalabatkLogic/TalabatkModels/WalletTransaction.cs
    sha1: d49b022e33d0
last_updated: 2026-08-23
tags: [identity-access, customer, financial, child, technical, backend-domain]
---
# WalletTransaction

A customer wallet ledger row (credit/debit against a customer's in-app wallet balance) — child of
[[Customer.technical|Customer]]. `Shared/TalabatkLogic/TalabatkModels/WalletTransaction.cs`.

## Notes
- No validation anywhere — `Instance` (`:30-56`) doesn't check `amount` is non-zero/non-negative, and
  `UpdateWalletAmount` (`:58-61`) reassigns `Amount` with no guard at all. Contrast the richer
  validation on other financial ledger entities in this pass (`LoyaltyPoints`, `DeliverymanTransaction`'s
  `Instance` gate).
- `Withdrawal` (bool) and `Type` (`WalletTransactionType` enum) both encode direction/kind — not
  confirmed how they combine (e.g. whether every `Withdrawal=true` row also has a specific `Type`).
- `CompensationId` links a wallet credit back to a [[Compensation\|Compensation]] payout — one of several places compensation money can land, alongside `DeliverymanTransaction`.

## Rule / Decision Matrix

One movement in a customer wallet. Three methods, no guards, and the direction of the money is a boolean.

| # | Rule | Where | Notes |
|---|---|---|---|
| 1 | `Instance` returns `Result<WalletTransaction>` and cannot fail | `Shared/TalabatkLogic/TalabatkModels/WalletTransaction.cs:30` | No check on amount, so zero and negative movements are representable |
| 2 | Direction is the `Withdrawal` boolean, not the sign of the amount | `Shared/TalabatkLogic/TalabatkModels/WalletTransaction.cs:30` | A negative amount with `Withdrawal = true` would double-negate, and nothing prevents it |
| 3 | Every movement carries a bilingual description | `Shared/TalabatkLogic/TalabatkModels/WalletTransaction.cs:30` | `TransactionDescriptionAr`/`En` are what the customer reads in their wallet history — and #499-family findings are about the wrong text being chosen |
| 4 | `Type` classifies the movement | `Shared/TalabatkLogic/TalabatkModels/WalletTransaction.cs:30` | `WalletTransactionType` — Refund, OnlineRefund and so on; the value the PayMob callback branches on |
| 5 | `UpdateWalletAmount` can change a posted amount | `Shared/TalabatkLogic/TalabatkModels/WalletTransaction.cs:58` | `void`, unguarded — a ledger row is mutable after the fact |
| 6 | A recharge reason can be attached after creation | `Shared/TalabatkLogic/TalabatkModels/WalletTransaction.cs:62` | `SetRechargeReason` |
| 7 | A movement can point at an order, a compensation, or neither | `Shared/TalabatkLogic/TalabatkModels/WalletTransaction.cs:30` | `OrderId` and `CompensationId` are both optional, so a wallet credit need not be traceable to a cause |
| 8 | Creation is attributed | `Shared/TalabatkLogic/TalabatkModels/WalletTransaction.cs:30` | `CreatedBy` is a free-text string — the PayMob callback writes "PayMob CallBack" into it |

## Related
- [[Customer.technical|Customer]] — owning entity
- [[Compensation|Compensation]] — one funding source

## Open Questions
- [ ] Whether `Amount` is ever negative in practice (direction encoded by `Withdrawal`/`Type` instead), or whether validation is genuinely absent by design.
- [ ] `WalletTransactionRechargeReason` not opened in full.
