---
id: 8orders/delivery/driver-cash-and-compensation/compensation
note_type: single
rule_count: 9
context: Delivery
feature: Driver Cash & Compensation
entity: Compensation
entity_type: child
sources:
  - path: Shared/TalabatkLogic/TalabatkModels/Compensation.cs
    sha1: f6971b93f4eb
last_updated: 2026-08-23
tags: [delivery, financial, technical, backend-domain]
---
# Compensation

A payout owed to a delivery man (or restaurant/customer, per `CompensationPartyType`) for an
order-level problem — e.g. an undelivered order. Feeds
[[DeliverymanTransaction.technical|DeliverymanTransaction]]'s `Compensation`
type. `Shared/TalabatkLogic/TalabatkModels/Compensation.cs`.

## Business rules
- **Default state is `InReview`; can optionally be created pre-approved.** `Insance(...)` (sic — typo
  in the factory method name, `:37-78`) defaults `CompensationStateId` to `InReview`; passing
  `createAsApproved: true` instead sets it straight to `Approve`, stamps `ChangeStateBy = "Updated By
  System"`, and marks a pending approval event.
- **Approval event is deferred until after the database assigns an id.** `RaisePendingCompensationApprovedEventAfterPersist()`
  (`:85-95`) only fires `CompensationApprovedEvent` if `_pendingCompensationApprovedEvent` is set
  **and** `CompensationId > 0` — i.e. the persistence layer must call this explicitly after
  `SaveChanges`, since the id doesn't exist yet at construction time for a create-as-approved
  compensation. The doc comment (`:80-84`) confirms this is a deliberate "single-save friendly
  alternative" to going through `UpdateCompensationStatus` in a second round-trip.
- **Manually approving via `UpdateCompensationStatus`** (`:112-122`) fires the same
  `CompensationApprovedEvent` immediately (no deferral needed — the entity already has an id by the
  time this is called on an existing row).
- **Payment method can be redirected to Wallet** via `ChangeCompensationPaymentToWallet()` (`:123-126`)
  — a narrow, single-purpose setter (only Wallet, no general "set payment method" method exists).
- `CompensationPartyType` is a raw `int`, not a typed enum in this file — meaning "who this
  compensation is for" (customer/restaurant/delivery man) isn't self-documenting from the class alone.

## Key Fields
| Field | Meaning | Constraints |
|-------|---------|-------------|
| `CompensationStateId` | `CompensationStateEnum` (`InReview` default, `Approve`, presumably others) | drives `CompensationApprovedEvent` |
| `CompensationPartyType` | Who receives it | raw `int`, not a strongly-typed field here |
| `DeliverymanId` / `RestaurantId` | Nullable — whichever party applies | |
| `SalesDailyId` → `SalesDaily` | Links to a daily sales/settlement record | not yet documented |
| `Order` | The order this compensation is for | Order already partially documented (Customer Ordering) |

## Rule / Decision Matrix

Money given back to a customer after something went wrong, and the record of who decided it and who pays. Twenty properties, no guards — including on the amount.

| # | Rule | Where | Notes |
|---|---|---|---|
| 1 | The factory is misspelt `Insance` and is the only way in | `Shared/TalabatkLogic/TalabatkModels/Compensation.cs:37` | A search for `Compensation.Instance` finds nothing — worth knowing before tracing this flow |
| 2 | No validation on `CompensationAmount` | `Shared/TalabatkLogic/TalabatkModels/Compensation.cs:37` | Negative or zero compensation is representable |
| 3 | Who pays is a party type plus a named party | `Shared/TalabatkLogic/TalabatkModels/Compensation.cs:37` | `CompensationPartyType` with `RestaurantId`/`DeliverymanId`/`OperatorId` and their denormalised names, so the record survives a rename |
| 4 | Approval is an explicit state change, and it raises an event **after persistence** | `Shared/TalabatkLogic/TalabatkModels/Compensation.cs:85` | `RaisePendingCompensationApprovedEventAfterPersist` — deliberately after the save, so a listener cannot see a state that was rolled back |
| 5 | State changes are unguarded | `Shared/TalabatkLogic/TalabatkModels/Compensation.cs:112` | `UpdateCompensationStatus` assigns `CompensationStateId`; no transition table, so any state can follow any other |
| 6 | Switching payment to wallet is its own method | `Shared/TalabatkLogic/TalabatkModels/Compensation.cs:123` | `ChangeCompensationPaymentToWallet` — the path that moves a compensation from cash to wallet credit |
| 7 | `Update` re-assigns without checks | `Shared/TalabatkLogic/TalabatkModels/Compensation.cs:103` |  |
| 8 | The treasury day is attached separately | `Shared/TalabatkLogic/TalabatkModels/Compensation.cs:97` | `SetSalesDaily` links the compensation to the AccFlex accounting day |
| 9 | State changes are attributed | `Shared/TalabatkLogic/TalabatkModels/Compensation.cs:112` | `ChangeStateBy` and `ChangeStateDate` are recorded, so approvals are traceable even though they are unvalidated |

> The rule-driven counterpart is the `AutoCompensation*` family, which validates everything this
> entity does not — see [[Customer Ordering/Order & Fulfilment/Order-Lifecycle.technical|Order Lifecycle]].

## Related
- [[DeliverymanTransaction.technical|DeliverymanTransaction]] — consumes an approved compensation as a ledger entry (`AddCompensationTransaction`)

## Open Questions
- [ ] `CompensationStateEnum`'s full set of values wasn't enumerated (only `InReview`/`Approve` seen here).
- [ ] `SalesDaily` not yet documented.
- [ ] Who calls `RaisePendingCompensationApprovedEventAfterPersist` (the persistence layer's exact hook) wasn't traced.
