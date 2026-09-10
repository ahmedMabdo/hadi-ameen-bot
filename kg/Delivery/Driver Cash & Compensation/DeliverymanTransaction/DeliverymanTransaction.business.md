---
id: 8orders/delivery/driver-cash-and-compensation/deliverymantransaction-business
note_type: business
context: Delivery
feature: Driver Cash & Compensation
entity: DeliverymanTransaction
entity_type: child
last_updated: 2026-08-23
tags: [delivery, delivery-man, financial, business]
---
# DeliverymanTransaction

The full accounting ledger for a delivery man — every cash collection, payout, deduction, bonus,
penalty, and settlement is recorded here as one line.

## What it is
Whenever money moves between a delivery man and the company — collecting cash from a customer,
being paid their delivery profit, a penalty deduction, an insurance-deposit settlement when they
leave, a shift bonus, and many more — one `DeliverymanTransaction` row is written. Each row is marked
as either a credit (money owed to the delivery man) or a debit (money owed by them), so the running
balance can always be reconstructed from the ledger.

## Business rules (plain words)
- 16 distinct transaction types exist, each with a fixed credit/debit direction — a bonus is always a
  credit, a penalty is always a debit, and so on (see the technical note for the full table).
- Some transaction types (equipment deductions, insurance-deposit settlements) automatically update
  the delivery man's running balances the moment the transaction is recorded — not as a separate step.
- Certain flows guard against writing the same transaction twice for the same order (e.g. a
  multi-delivery-man order shouldn't double-charge or double-pay); this dedup logic is not applied
  the same way across every transaction type — see Open Questions.
- Comments are written in Arabic, describing the transaction in terms an operator/delivery man would
  recognize (order code, city, amounts).

## Who uses it
- **Roles:** Delivery Man (views their own balance/history), Admin/back-office (dismissal
  settlements, deductions, bonuses — via `AdminUi`, not yet confirmed which screens).
- **Screens:** Not yet confirmed — pending the Admin/Delivery context controller passes.

## Related
- [[DeliveryMen.technical|DeliveryMen]] — the account this ledger belongs to; cash-limit math (Rule 3) reads from balances this ledger feeds.
- Technical detail: [[DeliverymanTransaction.technical|DeliverymanTransaction — technical]]
