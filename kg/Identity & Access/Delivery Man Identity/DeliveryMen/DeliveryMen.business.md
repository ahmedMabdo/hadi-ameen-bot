---
id: 8orders/identity-and-access/delivery-man-identity/deliverymen-business
note_type: business
context: Identity & Access
feature: Delivery Man Identity
entity: DeliveryMen
entity_type: child
last_updated: 2026-08-23
tags: [identity-access, delivery-man, transactional, business]
---
# DeliveryMen

The record of a delivery man — their identity, work status, cash-handling limits, rating, and shift
assignment.

## What it is
Every delivery man has an account tracking whether they're currently active/online, which shift
they're assigned to, how much cash they're allowed to be holding before they must settle up, their
rating, and their financial history (insurance deposit, equipment payments, transactions).

## Business rules (plain words)
- A delivery man is created already active (unlike a Customer, who must verify an OTP first) —
  accounts are provisioned by an operator, not self-registered.
- Each delivery man has a **cash limit** — the most cash they can be holding from collected orders
  before the system requires a payment/settlement. Internal and external delivery work can each carry
  their own separate cash limit, combined when both apply.
- Going online/offline is logged as a shift entry — starting a break also takes the delivery man
  offline, and cannot be resumed until the break is properly ended.
- If an admin deactivates a delivery man, they cannot simply reactivate themselves — they're told to
  contact the admin.
- A delivery man has two different rating figures tracked side by side: a recent (rolling) rating and
  an overall rating — see the technical note for the discrepancy this creates.
- Dismissing a delivery man clears their outstanding insurance/asset balances and records a final
  settlement amount; rehiring resets those balances and restores the account.

## Who uses it
- **Roles:** Delivery Man (self-service via `TalabatkDelivery` — shift, break, profile), Admin
  (provisioning, financial settings, dismissal/rehire — via `AdminUi`, not yet confirmed which exact
  screens).
- **Screens:** `TalabatkDelivery`'s Razor views (shift/break management), `AdminUi`'s Angular delivery
  management (not yet confirmed by this pass).

## Related
- Technical detail: [[DeliveryMen.technical|DeliveryMen — technical]]
- Shift/break history: `DeliverymanShiftLog`, `DeliveryMenShifts`, `DeliverymanBreakLog` (not yet
  documented — next in this batch)
- Cash accounting: `DeliverymanTransaction` (not yet documented)
