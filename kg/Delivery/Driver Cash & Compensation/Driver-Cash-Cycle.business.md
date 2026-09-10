---
id: 8orders/delivery/driver-cash-and-compensation/driver-cash-cycle-business
note_type: business
context: Delivery
feature: Driver Cash & Compensation
group: Driver-Cash-Cycle
last_updated: 2026-08-23
tags: [flow, business]
---
# Driver Cash and Settlement Cycle

## What this process is
Delivery riders collect cash from customers on cash-on-delivery orders. That cash belongs to the
company, not the rider, so the system tracks a running "how much cash is this rider currently
holding" balance for every driver. Once that balance gets too big, the rider is required to hand
the cash back — either by depositing it through Fawry (a bill-payment kiosk/app network), by
handing it to the back office in person, or by having it settled at year-end/dismissal against
their security deposit. Riders also accrue bonuses and can incur deductions (for lost/damaged
equipment, or against their refundable security deposit) — all of this nets against the same
running balance.

## The steps, in plain words

1. **A cash order is delivered.** The moment a rider marks a cash-on-delivery order as delivered,
   two things are recorded at once: the rider now "owes" the company the cash they just collected,
   and the rider "earns" their delivery fee for that trip. These net against each other in the
   rider's running balance.

2. **The system checks whether the rider is over their cash limit.** Every rider has a cash limit
   (a base limit, plus an extra limit for external/outsourced deliveries). At or past that limit, a
   mandatory deposit is calculated — a percentage of the limit, plus anything they're over by. The
   formula and the per-city amounts feeding it are already documented for
   [[DeliveryMen.technical|DeliveryMen]] (Rule 3) and
   [[City.technical|City]] (Rule 2) — not restated here.

3. **Being over the limit blocks new work.** A flagged rider will not be handed new cash-paying
   orders by the automatic assignment system until they pay down their balance. There's an earlier
   warning too: once a rider's projected balance would reach 70% of their limit, their assignment
   message includes a nudge to settle up soon, before the hard block kicks in.

4. **The rider settles up one of three ways:**
   - **Fawry deposit** — the rider pays into their Fawry account (a third-party bill-collection
     network) at any Fawry point of sale; the confirmation arrives from Fawry's servers.
   - **Office cash handover** — the rider physically hands cash to a back-office cashier, who
     records it in the accounting (ERP) system.
   - **End-of-employment settlement** — if the rider leaves, any deposit they had on file, and any
     unpaid equipment cost, is settled in one final calculation rather than daily.
   Whichever path is used, the rider's held-cash balance drops and the "over limit" flag is
   re-evaluated — clearing the block on new orders if they've paid enough.

5. **Daily deductions chip away at two separate pots.** Once a day, for every rider who delivered
   that day, the system automatically deducts a small percentage toward their refundable security
   deposit and their equipment costs (e.g. a delivery bag, a phone mount). Both percentages, and
   the minimum each deduction must be, are configured per city.

6. **Shift bonuses are calculated per delivery.** Cities can run bonus campaigns that pay extra per
   order once a rider crosses an order-count threshold within a shift window. Each qualifying
   delivery can add a bonus credit to the rider's balance. **Known issue (#411):** the window's
   closing time doesn't actually cut off correctly, so orders delivered after the bonus period
   should have ended can still be counted — meaning bonuses can be calculated on more orders than
   intended, on both the number a rider is shown and the number that's actually paid.

7. **Manual adjustments happen too.** Back-office staff can manually credit or debit a rider's
   balance for a bonus, a penalty, an equipment charge, or a deposit settlement. **Known issue
   (#392):** when settling money out of a rider's security deposit specifically, the system does
   not check the amount entered against what the rider is actually owed — unlike the equivalent
   equipment-charge adjustment right next to it, which is checked. This is a control gap on money
   leaving a fund set aside to cover losses.

## Who is involved
- **The delivery rider** — collects cash, sees their own balance and limit status in their app, and
  performs the Fawry deposit or hands over cash at the office.
- **Back-office cashier / accountant (AdminUi)** — records office cash handovers and merchant cash
  receipts into the accounting system, and performs manual wallet adjustments (bonuses, penalties,
  deposit/equipment settlements).
- **The automatic order-assignment system** — reads each rider's "over limit" status before handing
  them a new cash order.
- **Fawry (external partner)** — collects the cash physically and notifies the platform once a
  payment lands.
- **The company's ERP/accounting system** — the system of record for cash actually received at the
  office, separate from the app's own running ledger.

## What can go wrong (business terms)
- **A rider blocked from new orders can't earn**, so the settlement step is time-pressured for
  them — the sooner they pay down, the sooner they're eligible for work again.
- **A rider over their limit but not yet flagged** could, in principle, keep collecting cash for a
  short window between an order being delivered and the flag being written — see the technical
  note's Open Questions and finding #419 for the exact mechanism.
- **The security-deposit settlement gap (#392)** means a back-office error (or worse, deliberate
  manipulation) crediting or debiting a rider's deposit account isn't caught by the system the way
  the equivalent equipment charge is — a rider's deposit could be over- or under-settled with no
  automatic check.
- **The bonus window bug (#411)** means bonus payouts calculated per shift may run slightly high,
  since orders delivered shortly after a bonus period was supposed to end can still be counted.
- **Merchant cash receipts into the ERP are not amount-checked at all (#417)**, while the equivalent
  rider cash receipt is checked against a configured tolerance — worth knowing since both flow
  through the same office cash-receipt screen.

## What the company should know
This cycle is the main financial-exposure control on the delivery fleet: it is what stops a rider
from accumulating an unbounded amount of the company's cash before anyone notices. The control
depends on the "over limit" flag being written promptly and correctly after every order and every
settlement — three known findings (#392, #411, #417) sit directly on this cycle's steps, and a
fourth (#419) affects the reliability of the flag itself when a save to the database fails partway
through the nightly deduction job. None of these are catastrophic on their own, but they cluster on
the same control, which is worth a single coordinated look rather than four separate tickets.
