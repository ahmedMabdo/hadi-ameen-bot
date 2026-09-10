---
id: 8orders/delivery/delivery-man-operations/driver-operations-business
note_type: business
context: Delivery
feature: Delivery Man Operations
group: Driver-Operations
last_updated: 2026-08-23
tags: [flow, business]
---
# Driver Operations — A Delivery Man's Working Day

## What this process is

This is the full arc of a delivery driver's shift: logging in and being marked "attended," going
online and available for work, being tracked and dispatched orders, taking a break and returning,
ending the shift, and being scored at week's end on rating, acceptance rate, and delivered-order
count. It is the operational spine that pay, bonuses, and discipline all hang off of.

## The steps, in plain words

1. **Login.** When a driver logs into the delivery app, the system silently tries to record that
   they "attended" today, based on whether the current time falls inside their assigned shift.
2. **Going online.** Logging in is not the same as being available. The driver actively switches
   "online." The system checks: are they inside their shift window (with a small grace period)? Are
   they starting from one of the shift's approved locations, if any are configured? Do they have an
   unfinished order or an open break blocking them? Only then are they eligible for delivery work.
3. **Being tracked.** While online, the app periodically reports GPS location — this both builds a
   location trail and separately triggers a check for any waiting delivery job.
4. **Getting dispatched.** Once online and in a delivery zone, the driver becomes eligible for order
   assignment (covered fully elsewhere). A parallel office/operations dispatch process also exists,
   with its own known shift-check defect described below.
5. **Taking a break.** A driver can request a break (rest, maintenance, or accident) with a chosen
   duration. Starting a break takes them off the available list immediately, like going offline. If
   they don't return on their own in time, the system ends the break for them automatically, checked
   about once a minute.
6. **Returning from break.** Coming back re-activates the driver.
7. **Ending the shift.** A driver can voluntarily go offline, provided no order is in progress.
   Separately, the system also forcibly logs out **every driver still online**, company-wide, once a
   day at a fixed time — regardless of what shift they're actually on.
8. **Counting hours and scoring the week.** Once a day, the system closes the day's online/offline
   sessions and tallies actual hours online. Once a week, it recalculates each driver's rating from a
   weighted mix of: customer star-ratings, hours worked, orders delivered, how often they accepted
   offered orders, and how close to on-time they arrived at the restaurant and the customer.

## Who is involved

- **The driver**, through the delivery mobile app, at every step above.
- **Office/operations staff**, who set up shifts and starting locations, and who run their own
  parallel login/attendance/dispatch cycle.
- **Automated background jobs**, unattended, handling the minute-by-minute break timeout, the daily
  forced logout and hour tally, and the weekly rating recalculation.

## What can go wrong, in business terms — the night-shift blind spot

The single biggest risk is **shifts that cross midnight**. Several checks above compare "is it
currently inside the shift window" using only the clock hour, in a way that breaks the moment a
shift starts before midnight and ends after it:

- A driver on a night shift who logs in **is never marked as attended**, even though they show up
  and work the whole night — and the login still reports success, so nothing surfaces the problem
  (finding #430). Since attendance underpins pay, this is a direct payroll risk, silently.
- The same mistake against the office/operations-staff shift model is even more damaging: a
  night-shift staff member is invisible not just to attendance but to order dispatch, late-order
  escalation, and four other processes (finding #432) — so night-shift drivers waiting on staff to
  route work to them can be affected too.
- A night-shift driver's location trail can also be miscounted as "offline the whole time," from the
  same kind of date-arithmetic mistake applied elsewhere (finding #393).
- Reassuringly, not everything gets this wrong: the checks that let a driver go online, and that
  decide whether to still show an "end shift" button, both handle midnight-crossing shifts
  correctly. This isn't a case of nobody knowing how to do it right — the fix simply isn't applied
  everywhere it's needed, which is arguably worse: the failure is inconsistent and easy to miss in
  testing that only ever happens during the day.
- The system also force-logs-out every online driver, company-wide, at one fixed time daily, with no
  exception for a shift still running. A driver whose shift extends past that cutoff is logged off
  mid-shift by the system itself, not by choice.

## What the company should know

- Night-shift coverage is a structural weak spot, not an isolated bug: attendance, dispatch
  eligibility, and location-based accountability all fail the same way for overnight shifts, and the
  daily forced-logout job compounds it by cutting late shifts short outright.
- None of these failures produce an error message — they fail silently and report success, so the
  business only learns about them through downstream symptoms (missing pay, drivers who "didn't get
  orders," disputes over hours), not through the system itself.
- Separately, a driver's live GPS location and shift hours can currently be read by anyone without
  logging in (finding #412) — a privacy exposure independent of the scheduling issue, but touching
  the same tracking data.
