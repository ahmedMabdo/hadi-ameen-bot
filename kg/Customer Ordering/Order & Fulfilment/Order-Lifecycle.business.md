---
id: 8orders/customer-ordering/order-and-fulfilment/order-lifecycle-business
note_type: business
context: Customer Ordering
feature: Order & Fulfilment
group: Order-Lifecycle
last_updated: 2026-08-23
tags: [flow, business]
---
# Order Lifecycle

## What this process is

The journey of a single order from the moment a customer taps "checkout" to the moment it is
delivered, rejected, or cancelled. Every order passes through the same sequence of hand-offs between
customer, restaurant, and driver, with the system deciding at each step who needs to act next.

## The steps, in plain words

1. **Checkout.** The customer confirms their cart. The system creates the order, an order code, and a
   "pickup tag" per restaurant so the driver can identify the right bag at the counter.
2. **A quick risk check.** Low-risk orders — repeat customer, cash, one restaurant, below a set amount
   — go straight to the restaurant. Riskier orders (first-ever order, any online payment, more than
   one restaurant, a larger amount) are held in a review queue first.
3. **Held for review, if flagged.** A held order doesn't move itself — someone on the team has to
   approve it or send it to the restaurant. If nobody reviews it, it just sits there; there is
   currently no automatic timer that cancels or escalates a forgotten order at this stage.
4. **Sent to the restaurant.** The restaurant confirms the order, rejects it, or flags specific items
   as unavailable for the customer to swap. A slow restaurant gets an automated reminder phone call —
   but nothing forces a decision, so an order can, in principle, wait forever for a restaurant that
   never answers.
5. **Cooking.** Once every restaurant in the order has confirmed, it's officially accepted and the
   kitchen starts preparing it.
6. **Ready for pickup.** The restaurant marks it ready once prepared; the system also checks that a
   minimum cooking time has actually passed.
7. **A driver is assigned.** The system offers the order to a driver automatically through a
   fairness-based rotation. If a driver doesn't respond, it is meant to try someone else — this
   reassignment step has some known rough edges (see below).
8. **Pickup.** The driver collects the order, confirmed by being physically near the restaurant. A
   pickup photo can be required as proof.
9. **On the way.** Once the driver has collected everything for every restaurant in the order, it moves
   to "on the way" and the customer and driver are notified.
10. **Delivered.** The driver must be physically near the customer's address to mark it delivered. A
    delivery photo can be required as proof — important evidence for later disputes. A failed delivery
    attempt is recorded with a reason, but internally the order is still marked "Delivered"; the
    failure only shows up as a separate flag, not a distinct status.
11. **Cancellation, if it happens.** The customer can cancel only up until the restaurant confirms.
    After that, cancellation through the app is blocked.

## Who is involved

- **Customer** — places the order, can cancel early, gets notified throughout.
- **Review team / admin rules** — approves or forwards orders held for risk review.
- **Restaurant** — confirms, rejects, or adjusts the order; marks cooking, then ready.
- **Driver** — accepts the assignment, collects, delivers, photographs both handoffs when required.
- **Automated reminder calls** — nudge an unresponsive restaurant, without forcing a decision.

## What can go wrong, in business terms

- **An order can be forgotten in review** — no automatic timeout or escalation exists for this stage.
- **An order can be forgotten by a restaurant** — the reminder call nags but can't force a decision, so
  an unresponsive restaurant can strand an order indefinitely.
- **A delivery/pickup photo can be destroyed before its replacement is safely saved** — the old photo
  is deleted before the new one is confirmed uploaded and saved. A failure partway through leaves the
  order with no usable photo — the exact evidence needed to resolve "I never received my order"
  disputes.
- **A driver assignment can occasionally be skewed or lost** — the fairness rotation has a known timing
  gap under heavy load, and the fallback "assign someone else" mechanism can silently fail part of its
  own bookkeeping without anyone noticing.
- **A failed delivery is recorded the same as a successful one internally** — told apart only by a
  secondary flag, a labeling quirk worth knowing when reading raw order data.
- **A couple of steps are implemented twice** — "on the way" and "driver viewed the order" each exist
  as two independent pieces of code believed to do the same thing; a future fix to one might not reach
  the other.

## What the company should know

Two points in this lifecycle can stall with no automatic recovery: an order sitting unreviewed, and an
order sitting unanswered at a restaurant. The restaurant case at least gets a reminder call; the
review-queue case gets nothing. Any "orders that need attention" dashboard should watch both. The
delivery-photo handling is also worth revisiting given its role as dispute evidence — the safe order
(save the new photo first, only then discard the old one) is not the order the system currently follows.
