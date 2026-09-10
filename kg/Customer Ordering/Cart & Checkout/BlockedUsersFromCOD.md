---
id: 8orders/customer-ordering/cart-and-checkout/blockedusersfromcod
note_type: single
context: Customer Ordering
feature: Cart & Checkout
entity: BlockedUsersFromCOD
entity_type: legacy-poco-root
rule_count: 6
sources:
  - path: Shared/TalabatkLogic/TalabatkModels/BlockedUsersFromCOD.cs
    sha1: b0716f1933af
last_updated: 2026-08-23
tags: [customer-ordering, cart-checkout, financial, technical, backend-domain]
---
# BlockedUsersFromCOD

Cash-on-delivery abuse prevention — a customer (keyed by **phone number**, not `CustomerId`) who
racks up undelivered COD orders can be blocked from using Cash-on-Delivery as a payment method.
`Shared/TalabatkLogic/TalabatkModels/BlockedUsersFromCOD.cs`.

## Business rules
- **Keyed by phone number, not customer id** — `Instance(phoneNumber, ...)` (`:21-34`) means the block
  follows the phone number even across a delete/recreate of the `Customer` row (see
  [[Customer.technical|Customer]] Rule 7's soft-delete-and-suffix
  behavior) — worth noting as a deliberate design choice for a fraud-prevention mechanism, not an
  oversight, though not explicitly confirmed as intentional in-code.
- A block starts `IsStillBlocked=true`, `NumberOfTimesBanned=1`.
- **Repeat offense increments a counter rather than creating a new row**:
  `IncrementNumberOfTimesBanned(...)` (`:43-51`) re-blocks and bumps `NumberOfTimesBanned` — implies
  one row per phone number, reused across multiple ban cycles (not verified against a DB unique
  constraint in this pass).
- `UnblockUser(...)` (`:35-42`) records who unblocked, when, why (`UnBlockReasonId`), and free-text
  comments — but does **not** reset `NumberOfTimesBanned`, so history of repeat offenses persists
  across unban/reban cycles.

## Key Fields
| Field | Meaning |
|-------|---------|
| `PhoneNumber` | The block key — not `CustomerId` |
| `IsStillBlocked` | Current state |
| `NumberOfTimesBanned` | Cumulative, never reset by unblocking |
| `BlockedReason` (`NonDeliveryReason`) / `UnBlockReason` (`UnbanReason`) | Typed reason enums |

## Rule / Decision Matrix

A phone number barred from cash on delivery, usually after undelivered orders. Keyed on the number rather than the customer, which is the fact worth knowing.

| # | Rule | Where | Notes |
|---|---|---|---|
| 1 | The block is on a **phone number**, not a customer id | `Shared/TalabatkLogic/TalabatkModels/BlockedUsersFromCOD.cs:21` | So it survives account deletion and re-registration, and follows the number to any new account |
| 2 | `Instance` has no guard | `Shared/TalabatkLogic/TalabatkModels/BlockedUsersFromCOD.cs:21` | No format check on the number |
| 3 | Blocking records both a reason and who did it | `Shared/TalabatkLogic/TalabatkModels/BlockedUsersFromCOD.cs:21` | `BlockedReasonId` and `BlockedBy`, with the mirror pair for unblocking |
| 4 | Undelivered-order blocks are distinguished from manual ones | `Shared/TalabatkLogic/TalabatkModels/BlockedUsersFromCOD.cs:21` | `IsBlockedDueToUnDeliveredOrder` separates the automatic case from an operator decision |
| 5 | Unblocking keeps the history | `Shared/TalabatkLogic/TalabatkModels/BlockedUsersFromCOD.cs:35` | `UnblockUser` flips `IsStillBlocked` and stamps `UnBlockedBy`/`UnBlockedDate` rather than deleting the row |
| 6 | Repeat offences are counted, not overwritten | `Shared/TalabatkLogic/TalabatkModels/BlockedUsersFromCOD.cs:43` | `IncrementNumberOfTimesBanned` — so the third ban is visible as the third |

## Related
- [[Customer.technical|Customer]] — the phone-number-keyed design interacts with Customer's soft-delete/phone-reuse behavior (Rule 7 there)
- [[CustomerCart.technical|CustomerCart]] / [[Wallet-and-PaymentMethod|Wallet and Payment Method]] — presumably checked at checkout when COD is selected, not traced to the actual checkout guard in this pass

## Open Questions
- [ ] Not traced to the actual checkout-time check (`CreateOrderFromCartCommand` or similar) that
  consults this table before allowing COD — this pass only documents the entity itself.
- [ ] Whether there's a DB unique constraint on `PhoneNumber` (one row per phone number) — not confirmed.
