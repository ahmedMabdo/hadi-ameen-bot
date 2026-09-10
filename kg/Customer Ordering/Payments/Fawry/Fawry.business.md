---
id: 8orders/customer-ordering/payments/fawry-business
note_type: business
context: Customer Ordering
feature: Payments
last_updated: 2026-08-23
tags: [delivery, payments, business]
---
# Fawry

A way for delivery men to pay back the cash they've collected from customers — not a way for
customers to pay for their order.

## What it is
Delivery men who collect cash-on-delivery build up a running balance they owe the company. Fawry —
the Egyptian bill-payment network — is one of the channels they can use to settle that balance. A
delivery man can either pay from inside the delivery app (picking a Fawry retail reference number or
paying straight from a Fawry mobile wallet), or walk into any physical Fawry retail location and pay
cash there, with Fawry telling this system afterward that the payment happened. Either way, the
result is the same: the amount the delivery man owes goes down, and once a day the total collected
through Fawry gets recorded in the company's accounting books.

Despite the name, **Fawry is not one of the payment options a customer sees at checkout** — customers
pay by cash, wallet, online card, Orange Money, or online wallet, and Fawry isn't among them.

## Business rules (plain words)
- A delivery man's Fawry payment is checked against a security signature before it's trusted — a
  payment confirmation that doesn't carry a matching signature is rejected outright, whichever of the
  two Fawry channels it came through.
- Confirming a Fawry payment as successful does two things for the delivery man: it adds an entry to
  their financial history showing the payment, and it sends them a notification saying the payment
  went through (or failed, if it didn't).
- Paying at a physical Fawry outlet also recalculates whether the delivery man still owes more toward
  their daily minimum deposit, and locks or unlocks their account for further deliveries based on
  whether they've paid enough.
- Once a day, everything collected through both Fawry channels together is posted as a single
  accounting entry — if nothing was collected that day, no entry is created at all.
- One known configuration issue: the production system is currently pointed at Fawry's *test*
  environment for the push-payment channel, meaning charges initiated that way don't reach Fawry's
  real payment processing (see `_conflicts.md` #358 — a known, flagged, not-yet-fixed issue).

## Who uses it
- **Roles:** Delivery men (the ones actually paying); Admin/back-office (viewing Fawry transaction
  reports).
- **Screens:** The delivery app's cash-settlement/payment screen (where a delivery man initiates a
  push payment); AdminUi's Fawry transactions report.

## Related
- [[DeliveryMen.technical|DeliveryMen]] — whose cash balance this feature settles
- [[DeliverymanTransaction.technical|DeliverymanTransaction]] — the financial history entry a Fawry payment creates
- Technical detail: [[Fawry.technical|Fawry — technical]]
