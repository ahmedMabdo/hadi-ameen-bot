---
id: 8orders/customer-ordering/cart-and-checkout/customercart-business
note_type: business
context: Customer Ordering
feature: Cart & Checkout
entity: CustomerCart
entity_type: legacy-poco-root
last_updated: 2026-08-23
tags: [customer-ordering, cart-checkout, transactional, business]
---
# Customer Cart

The customer's shopping basket — what they've picked, from which restaurant(s), before they check out.

## What it is
Every customer (including guests) has one active cart. Items get added from one or more
restaurants, the cart keeps a running total, and it survives things a lesser cart wouldn't: a price
changing underneath an item, a guest logging in mid-shop, or a discount being locked in early.

## Business rules (plain words)
- Adding the same item with the same choices again just bumps the quantity — it doesn't create a
  second line.
- If a restaurant changes an option's price while it's already sitting in someone's cart, that line
  gets flagged so the customer can see and accept the new price before checking out.
- A cart can span multiple restaurants at once, up to a configured limit.
- When a guest who's been building a cart logs into an existing account, **their guest cart wins** —
  whatever was in the real account's cart before is dropped, and the guest's items, delivery
  address, and any locked-in discount move over to the real account instead.
- At checkout, a long list of things gets checked before an order is created: no item still has an
  unacknowledged price change, delivery timing falls within business hours with enough lead time,
  the address and delivery area are valid and not overloaded, and a promo code or a voucher can be
  used — never both in the same order.

## Who uses it
- **Roles:** Customers and guests, via the mobile app's cart/checkout screens.
- **Screens:** Restaurant menu (add to cart), cart summary, checkout.

## Related
- [[CartItem|Individual cart items]] — what's actually inside the cart.
- Technical detail: [[CustomerCart.technical|CustomerCart — technical]]
