---
id: 8orders/delivery/delivery-man-operations/delivery-fee-and-assignment-business
note_type: business
context: Delivery
feature: Delivery Man Operations
last_updated: 2026-08-23
tags: [flow, business]
---
# How the Delivery Fee Is Set, and How a Driver Gets an Order

## What this process is
Every order goes through two related but separate decisions: what the customer pays for delivery,
and which driver ends up carrying it. This note covers both, because a bug in one quietly changes the
outcome of the other — for example, how a driver is scored feeds directly into what bonus they earn.

## How the delivery fee is set
- When a customer builds their cart, the system looks up the price the delivery zone charges for the
  restaurant(s) in the cart, for the customer's own area, and charges the **highest** of those zone
  prices if the cart spans more than one zone — not an average, not the cheapest.
- Ordering from more than one restaurant at once adds a flat "extra restaurant" surcharge per
  additional restaurant, the same everywhere in the city regardless of which zones are involved.
- This price is recalculated, independently, at the moment the order is actually placed — the system
  does not simply trust whatever number the app last showed the customer.
- If a restaurant's zone has no price configured for the customer's specific area, the customer is
  currently charged **nothing** for delivery. There is no "delivery not available here" message — just
  a free delivery, which is worth checking against real order data as a possible revenue leak.

## How much the driver earns for that order
- The driver's payout comes from a **separate** pricing table than the one used for the customer's
  charge, configured independently by the same city administrators. Nothing in the system checks the
  two tables against each other, so a driver payout larger than what the customer was charged is
  possible and would go unflagged.
- On top of that base payout, a driver's own performance rating can add or subtract a percentage
  bonus, from a rating-tier table each city sets. That rating comes from six weighted factors —
  customer satisfaction, hours worked, orders delivered, acceptance rate, and punctuality reaching the
  restaurant and the customer — which city admins must configure to add up to exactly 100%.
- **A real inconsistency exists here**: depending on which internal process assigns the order — the
  automatic system, a driver picking it off a map, or an admin by hand — the rating bonus is calculated
  by one of two formulas that do not agree in general, so the same driver on the same order could earn
  a different bonus purely from which path handled it. Not confirmed as a real-world payout
  discrepancy, but the formulas are provably different and nobody appears to have noticed the second
  one exists.
- External (outsourced) deliveries are priced differently again — a fixed percentage split between
  company and delivery partner from system configuration, bypassing the zone/rating math above.

## How a driver is chosen
Each delivery zone is configured as either **automatic** or **manual**:
- **Automatic zones** offer the order to one driver at a time from a queue, roughly in turn, with
  better-rated drivers getting a slight edge. Outsourced deliveries are ranked differently: every
  available external driver is scored on a mix of proximity (60%) and rating (40%), closest well-rated
  one first.
- **Manual zones** broadcast the order to every available driver in the zone at once; whoever accepts
  first gets it.
- Drivers can also take orders themselves — via a map of nearby orders, or by order id directly — and
  an admin can assign one by hand. That is five different ways an order can end up with a driver, not
  one, each with its own rules.
- A driver can be blocked if they already hold too much uncollected cash (see the cash-and-settlement
  note) or are too far from the restaurant. A confirmed defect (**#389**) makes the distance check
  unreliable specifically on the map-pick path — it compares against the wrong order's location most of
  the time, so the rule meant for a driver with nothing else on the way almost never actually runs
  there. A second confirmed defect (**#390**) lets a deactivated driver still grab an order through the
  plain "assign to myself" path, even though the admin-driven path correctly blocks them — a real gap
  in taking a problem driver off the road.
- If nobody accepts in time, the order is handed to operations staff for manual handling. Two confirmed
  defects (**#430**, **#432**) make overnight staff invisible to that hand-off and to overnight
  attendance records, so an order stalling at night may have no visibly available staff member to pick
  it up.

## What can go wrong, in business terms
- A coverage gap can silently become a free delivery instead of a blocked order.
- A driver's rating bonus can vary by internal plumbing rather than performance — a pay-trust risk.
- Nothing calculates or protects delivery margin, so a driver could in principle be paid more than the
  customer was charged for the same trip.
- A deactivated driver can still self-assign through one specific path.
- Overnight operations carry two independent blind spots at once, exactly when supervision is thinnest.

## What the company should know
The fee formula and the assignment logic are both real and traceable, but built from several
independently-configured pieces — two separate zone-price tables, a rating-tier table, a global
surcharge, an external-delivery split — that no single control reconciles. Assignment itself is not one
process but five, which is why the gaps above show up on some paths and not others.
