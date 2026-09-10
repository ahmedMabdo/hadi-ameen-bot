---
id: 8orders/identity-and-access/customer-identity/customeraddress-business
note_type: business
context: Identity & Access
feature: Customer Identity
last_updated: 2026-08-23
tags: [identity-access, customer, child, business]
---
# CustomerAddress

A saved delivery address on a customer's account — a home, work, or any other pinned drop-off point
they can pick from when placing an order.

## What it is
Every place a customer can have food delivered to lives as one row here: a map pin, an area/zone, a
building/floor/apartment description, and a friendly label ("Home", "Work"). A customer can save
several addresses but only one is ever the "default" — the one pre-selected the next time they open
the app. Addresses aren't hard-deleted when removed; they're flagged and hidden, the same soft-delete
pattern used elsewhere in the system.

Guests (people browsing or ordering before they register) get one of these too, created automatically
from wherever their pin lands, so the very first cart/checkout flow has an address to work with. If a
guest later completes registration into an existing account, their guest address is carried over onto
the real account and the guest's own copy is removed.

## Business rules (plain words)
- A customer can only have one default address at a time — saving a new default automatically
  un-defaults whichever one held that title before (enforced by [[Customer.technical|Customer]],
  Rule 6).
- An address's delivery zone/area is worked out from where the pin actually is, not just taken at face
  value — if the pin lands outside every zone the system currently covers, the address is still saved
  but with no zone attached, and it's then left out of the "addresses you can check out with" list.
- Several places that place or modify an order pull up the customer's saved address and assume it's
  there — when it isn't (an order placed for pickup, or one that never had an address attached), a
  handful of these break with a raw server error instead of a clean "no address selected" message. This
  has been independently confirmed multiple times across order creation, order editing, reordering, and
  removing a restaurant from an order (see the technical note's Business Rules 3-4 for the specific,
  already-verified spots).
- Several address-management actions look an address up **only by its own ID**, without checking that
  the address actually belongs to the person asking — meaning, in principle, one customer's saved
  address (or someone else's request to delete/edit an address) can be reached just by guessing or
  incrementing an ID. This has been confirmed as a real, exploitable gap, not just a theoretical one
  (see technical note, Business Rule 5).
- When a guest becomes a real account by logging into one that already exists, their guest address is
  re-saved under the real account as a brand-new address record (not simply re-labeled) and the old
  guest copy is deleted — so the address keeps its content but gets a new internal ID in the process.

## Who uses it
- **Roles:** Customer (save/edit/delete their own addresses, pick one at checkout); Admin/back-office
  staff (view and add addresses on a customer's behalf, e.g. when placing a phone order for them).
- **Screens:** the customer-facing app's address book and the checkout address picker; AdminUi's
  customer-detail/order-creation screens for staff-assisted address management.

## Related
- [[Customer.technical|Customer]] — the owning record; enforces the one-default rule
- [[CustomerAddresses|CustomerAddresses (entity detail)]] — an earlier, narrower note on
  the underlying data class itself
- [[Area-and-Country|Area]] — the geographic zone an address resolves to
- [[Order.technical|Order]] — the biggest consumer,
  and where most of the confirmed address-related bugs live
- [[CustomerCart.technical|CustomerCart]] — reads
  the selected address to price delivery before checkout
- Technical detail: [[CustomerAddress.technical|CustomerAddress — technical]]
