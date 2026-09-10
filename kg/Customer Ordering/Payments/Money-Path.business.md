---
id: 8orders/customer-ordering/payments/money-path-business
note_type: business
context: Customer Ordering
feature: Payments
group: Money-Path
last_updated: 2026-08-23
tags: [flow, business]
---
# The Money Path: How a Merchant Gets Paid

## What this is

The story of a single Egyptian pound from the moment a customer pays for an order to the moment the
restaurant sees that money reflected in its account with 8orders. It crosses four parties — customer,
delivery driver, 8orders, and the restaurant — and ends in the company's real accounting system
(AccFlex ERP), not just an internal app number.

The short version: **the customer's money almost never goes straight to the restaurant.** It is
collected, pooled, and split by formula into what the restaurant earned, what 8orders keeps as
commission, and what the driver keeps for the delivery. The restaurant's share accumulates as a
running statement balance that 8orders settles with the restaurant periodically, not order by order.

## The steps, in plain terms

1. **The customer pays** — cash, wallet balance, or an online card payment. Online payments are
   confirmed later by the payment gateway calling back to say "this succeeded" or "this failed" (see
   the existing PayMob and Fawry notes for that mechanism).
2. **The order's value is split, item by item.** Every item carries a commission rate — the
   restaurant's general rate or a special rate for its menu category — set aside as 8orders' cut the
   moment the item is priced. What's left is the restaurant's share.
3. **Discounts get divided up too.** A voucher, offer, or tiered discount isn't automatically the
   restaurant's loss — each discount type has its own configured split between "8orders absorbs this"
   and "the restaurant absorbs this."
4. **Some restaurants get paid cash on the spot.** A subset are configured to receive payment directly
   from the driver at pickup, in cash — but only when the customer is paying entirely in cash. The
   driver fronts that cash out of pocket, and it's later deducted from what 8orders still owes the
   restaurant.
5. **On delivery, the restaurant's statement gets five new lines**: what they earned, the commission
   taken from them, their share of the online-payment processing cost, their share of the discount
   cost, and 8orders' contribution toward the same discounts. Together these move the restaurant's
   running balance with 8orders.
6. **The driver's own tally is updated too** — credited for the delivery fee earned, debited for the
   cash now held that belongs to the platform, netted against anything already paid directly to a
   restaurant in step 4.
7. **Periodically, an accountant posts the day's activity into AccFlex**, the company's general
   ledger — where restaurant balances, driver balances, and cash movements become formal accounting
   entries the finance team can reconcile.
8. **The restaurant is actually paid out separately** — someone in finance manually records a payment
   (e.g., a bank transfer) against the restaurant's accumulated balance. A restaurant can also hand
   cash back to the company's cashier (e.g., to settle debts from step 4), recorded the same way.

## Who owes whom, at each stage

- Before delivery: the customer's payment is in transit — held by the gateway, still to be collected
  by the driver, or already left the wallet.
- At pickup (cash-on-pickup restaurants only): the **driver owes the restaurant** cash directly.
- At delivery: **8orders owes the restaurant** the order value minus commission minus the restaurant's
  discount share, plus 8orders' own discount contribution — this accumulates on the statement.
- Also at delivery: the **driver owes 8orders** the cash collected from the customer, minus their own
  earnings and minus anything already paid to a restaurant directly.
- Until payout (step 8), the restaurant's earned balance is just a number on a statement — it does not
  move anywhere by itself.

## What can go wrong, in business terms

- **A restaurant's statement can post against the wrong account, or none at all**, if its bank/
  liability account was never configured. Recorded finding #418: when that configuration is missing,
  the entry silently lands on a placeholder account instead of being rejected — surfacing only when
  finance tries to reconcile, by which point the trail is cold.
- **A restaurant can hand cash to the company's cashier with no check against what it actually owes.**
  Recorded finding #417: the same cash-handling path double-checks the amount for a driver, but not
  for a restaurant.
- **Financial history can be deleted along with its parent record** in certain admin deletion paths,
  instead of being preserved as a financial record must be. Recorded finding #340: this is a real,
  reachable path (restaurant deletion), not theoretical, and it also touches driver and customer
  wallet history.

## What the company should know

The commission and discount-sharing formula is applied consistently and automatically at pricing
time — that part is sound. The weak points sit at the edges: restaurants missing a payout account,
cash handed over in person without validation, and hard financial history still reachable by a delete
operation instead of being fully protected. None of this bites the everyday, correctly-configured
restaurant — but each is exactly the kind of gap that becomes a real discrepancy the one time a
setting is missing or a cashier mis-keys an amount. Also worth knowing: "the restaurant is owed money"
and "the restaurant has been paid" are two distinct states here, bridged only by a manual step.
