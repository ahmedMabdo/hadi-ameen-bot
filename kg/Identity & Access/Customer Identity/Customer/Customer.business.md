---
id: 8orders/identity-and-access/customer-identity/customer-business
note_type: business
context: Identity & Access
feature: Customer Identity
entity: Customer
entity_type: child
last_updated: 2026-08-23
tags: [identity-access, customer, transactional, business]
---
# Customer

The record of a person ordering food through the app — either a **Guest** (browsing/ordering without
registering) or a fully registered account.

## What it is
Every cart, order, saved address, payment card, and loyalty-point balance belongs to a Customer row.
A person can start as a Guest (identified only by their device) and later become a full account once
they register with a phone number. The system is careful about what happens to a Guest's in-progress
work (cart, chosen address, any discount they'd picked) when that transition happens.

## Business rules (plain words)
- A Guest is identified by their device, not a phone number, and can browse/build a cart before
  registering.
- If a Guest registers with a phone number nobody has used before, their same account row is
  upgraded in place — nothing is lost.
- If a Guest instead logs into an account that **already exists** (e.g. they'd registered before on
  a different device), the Guest's most recent cart, delivery address, and discount **replace**
  whatever was on the existing account — they are not combined. See
  [[CustomerCart.technical|CustomerCart]] for the
  full merge rules.
- A customer can only have one default delivery address at a time — saving a new default
  automatically un-defaults the previous one.
- Deleting an account doesn't erase it — it's marked deleted and its phone number is freed up
  (suffixed internally) so the same number could register again later.
- Loyalty points are earned from orders, can expire, and can be redeemed — each a separate
  transaction on the customer's point history.
- A customer can be blocked (with a recorded reason), independent of being deleted.

## Who uses it
- **Roles:** Customer (self-service via the mobile app — registration, profile, addresses, cards,
  points). Admin back-office likely has some customer-management view — not yet confirmed by this
  pass (see Open Questions on the technical note).
- **Screens:** Customer mobile app (not in this repo — inferred from the API contract), Talabatk.IDS
  registration/OTP screens.

## Related
- [[CustomerCart.technical|CustomerCart]] — the guest-to-real merge policy
- [[CartItem|CartItem]]
- Technical detail: [[Customer.technical|Customer — technical]]
