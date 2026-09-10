---
id: 8orders/customer-ordering/order-and-fulfilment/order-business
note_type: business
context: Customer Ordering
feature: Order & Fulfilment
entity: Order
entity_type: child
last_updated: 2026-08-23
tags: [customer-ordering, order-fulfilment, transactional, business]
---
# Order (Customer Ordering view)

What a checked-out cart becomes — and everything the customer sees happen to it afterward, up to
the point where the restaurant/delivery side takes over.

## What it is
An Order is created the moment checkout succeeds. It carries a snapshot of what was in the cart,
who's paying and how, and where it's going. From there, restaurants, delivery staff, and internal
admin/support all interact with the *same* order record as it moves toward delivery — this note
only covers what matters from the customer's side: how it gets paid for, whether it needs manual
review before the restaurant even sees it, and when it can still be cancelled.

## Business rules (plain words)
- You can pay with cash, wallet balance, online payment, or a combination — except cash and online
  can't be combined with each other. Wallet can top up either one.
- The online payment amount is double-checked on the server, not just trusted from the app — a
  mismatch (beyond a small tolerance) is rejected.
- Most repeat-customer cash orders at a single restaurant go straight through to the restaurant. A
  handful of situations trigger an extra review step first: it's your very first order ever, you're
  paying online or with Apple Pay, you already have another open order at the same restaurant, your
  order spans multiple restaurants, or the order is unusually large.
- Once a restaurant has confirmed your order, you can no longer cancel it yourself.

## Who uses it
- **Roles:** Customers place and (conditionally) cancel; restaurants, delivery staff, and admin all
  interact with the same order afterward (not covered by this note).
- **Screens:** Checkout, order tracking, order history.

## Related
- [[OrderRestaurantDetails|Order Portion]] — if your order spans multiple restaurants, each gets its own tracking number (Daily Pickup Tag).
- Technical detail: [[Order.technical|Order — technical]] (Customer Ordering slice only)
