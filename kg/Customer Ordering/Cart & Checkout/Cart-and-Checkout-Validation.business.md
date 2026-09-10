---
id: 8orders/customer-ordering/cart-and-checkout/cart-and-checkout-validation-business
note_type: business
context: Customer Ordering
feature: Cart & Checkout
last_updated: 2026-08-23
tags: [flow, business]
---
# Cart & Checkout Validation

## What this process is

Everything that happens between a customer tapping "add to cart" and an order actually being
created — every check the system runs, in order, and what the customer sees if one fails. This is
the process support needs when a customer says "it won't let me order."

## The steps, in plain words

1. **Adding an item to the cart.** Checks the restaurant delivers to the customer's address, is
   open, and isn't temporarily busy; if the cart already has another restaurant's items, checks that
   mixing restaurants is allowed (some opt out of being combined). Re-adding the same item with the
   same choices just bumps the quantity.
2. **Item and option checks.** The item must be active and not inside a restaurant-declared
   "unavailable" window (e.g. breakfast item at midnight); its price tier must still be offered; any
   chosen add-ons must belong to that item and respect min/max choice rules. For a store/mart item,
   stock is checked and an over-large request is silently capped rather than rejected.
3. **Multi-restaurant rules.** A cart can span multiple restaurants up to a per-city limit. If the
   city restricts it, those restaurants also can't be farther apart than a configured distance (so
   one driver can still collect from all of them), and all must share the same delivery zone.
4. **Cart totals.** Every change fully recalculates the running totals from what's actually in the
   cart, so they can't drift out of sync. Delivery and service fees are computed separately, when the
   customer views the cart summary, not stored on the cart.
5. **The pre-checkout gauntlet.** Before an order is created: cart not empty; no unacknowledged price
   change; a scheduled delivery time is far enough out and inside business hours; the address is
   valid; the area isn't overloaded ("rush time"); every restaurant in the cart delivers there;
   purchase-quantity limits aren't exceeded; store stock is re-checked. A promo code and a voucher
   can never both apply — supplying a promo code makes any voucher simply ignored.
6. **Payment method selection.** Cash, wallet balance, and online payment (card, PayMob, wallet, or
   Apple Pay) can be split across one order; which online provider is used depends on configuration.
   A customer blocked from Cash-on-Delivery (for undelivered cash orders) has that option hidden from
   the payment list — whether it's also blocked if they submit cash anyway wasn't confirmed here.
7. **Order creation.** The order is built, saved, the cart emptied, and an online-payment session
   started if needed. A voucher's or promo's minimum order amount is checked *again*, after the order
   is built, against the real total — so it can still be rejected here even after passing the
   earlier ownership/existence check.

## Who is involved

- **Customer:** builds the cart, resolves flagged issues, chooses a payment method, checks out.
- **Restaurant:** involved implicitly through hours, busy status, area coverage, and whether it
  allows being combined with other restaurants in one order.
- **Support / Ops:** field "why can't I check out" complaints — this document exists for them.

## What can go wrong (in business terms)

- A customer can add an option belonging to a deactivated or currently-unavailable menu item: the
  dedicated check screen catches this correctly, but the actual "add to cart" action is less strict.
- An item the restaurant declared unavailable for a time window can still pass the final checkout
  check, because that specific check only looks at the item's general on/off switch, not the window
  — even though two other checks elsewhere in the system do look at it.
- Customers on the "quick checkout" app do not get their fast-checkout exemption for large orders — a
  plumbing mistake holds every large order from that app for manual review regardless.
- A checkout with no delivery address selected can crash with a raw error on the older, still-live
  "MakeOrder" path; the newer cart-based checkout shows a normal "invalid address" message instead.
- Store stock is checked at add-to-cart and again at checkout, but the checkout recheck only runs for
  single-restaurant carts — a multi-restaurant cart with a store item skips it entirely.
- A guest's cart, address, and any discount carry over automatically on login to a real account — and
  if that account already had its own cart, it is discarded, not merged, in favor of the guest's.

## What the company should know

The system protects restaurant and delivery logistics (hours, distance, area coverage) more strictly
than the cart's own content (options, availability windows) — the stricter checks exist in the code,
just not all wired to the path that actually gates checkout. "It won't let me order" is usually one
specific, nameable step above, and a customer slipping through a check that should have blocked them
is a known possibility today, not a hypothetical.
