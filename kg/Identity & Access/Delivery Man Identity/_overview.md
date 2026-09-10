---
id: 8orders/identity-and-access/delivery-man-identity/overview
title: Delivery Man Identity — Overview
note_type: overview
context: Identity & Access
feature: Delivery Man Identity
audience: Business
last_updated: 2026-08-23
tags: [identity-and-access, delivery-man-identity, business]
---
# Delivery Man Identity — Overview

## What is this? (for everyone)

Everything about a delivery driver's **account**: signing up, confirming their phone number, signing
in, changing a forgotten password, and — when the working relationship ends — being dismissed and
possibly re-hired later.

It is deliberately separate from what a driver *does*. Shifts, accepting deliveries, GPS tracking and
cash handling are covered by
[[Delivery/Delivery Man Operations/_overview|Delivery Man Operations]] and
[[Delivery/Driver Cash & Compensation/Driver-Cash-Cycle.business|Driver Cash Cycle]]. This feature is
only about *who the driver is and whether they can get in*.

A driver signs up with their phone number, receives a code by SMS, and enters it to prove the number is
theirs. From then on, signing in gives their app a pass that every other part of 8Orders accepts.

## The Feature at a Glance

| # | Step (Screen) | Who | Purpose |
|---|---|---|---|
| 1 | Sign up | Driver | Create the account with a phone number |
| 2 | Enter code | Driver | Prove the phone number is theirs |
| 3 | Resend code | Driver | Get a new code if the first did not arrive |
| 4 | Sign in | Driver | Get the pass the driver app uses everywhere |
| 5 | Forgot password | Driver | Request a reset code |
| 6 | Enter reset code | Driver | Prove they own the number before changing the password |
| 7 | Set new password | Driver | Change the password |
| 8 | Edit driver | 8Orders admin | Correct a driver's details |
| 9 | Dismiss / re-hire | 8Orders admin | End or restart the working relationship, with a record |
| 10 | Asset transactions | 8Orders admin | Equipment and deposits held against a driver |

## Business Flow (plain language)

1. A driver signs up. 8Orders creates the account and sends a code to the phone number.
2. The driver enters the code; the number is marked confirmed and the account can be used.
3. Signing in issues the pass their app carries on every request.
4. If a driver forgets their password, they ask for a reset code, enter it to prove the number is
   theirs, and then set a new password.
5. Admins can correct driver details, and can dismiss a driver — which is recorded, not deleted, so a
   dismissal can be reversed by re-hiring.

## What a business reader must know — this feature has a live account-takeover hole

This needs stating plainly, because it is the most serious thing recorded anywhere in this knowledge
graph.

**Today, anyone on the internet who knows a driver's phone number can change that driver's password
and take over the account.** No code, no login, nothing else needed. Three separate mistakes line up
to make it possible:

1. The "set new password" step asks for a confirmation code — and then never looks at it.
2. Instead of checking a code the driver received, the system generates one for itself on the spot.
3. The step that actually changes the password ignores the code entirely.

There is a fourth, related problem: **the new password is written into the system's logs in plain
text**, under a label that says "phone", so anyone reading logs sees credentials and a search for
leaked passwords would not find them.

Two more holes were found in the same file while documenting this:

- An endpoint whose name begins with "Simulate" — a testing aid that reached production — will, for
  anyone at all, look up any driver by number, **send that driver a fake "you have a new order"
  alert**, and hand back the identifiers of the driver's phone.
- Another endpoint returns the **live list of which drivers are queued in which delivery zone**, again
  to anyone who asks.

There is also a side effect worth knowing at the support desk: because a reset attempt regenerates the
driver's code, **an attacker probing phone numbers will silently break the codes real drivers are
waiting for.** "My code stopped working" can be a symptom of this.

Finally, a note on why this is fixable with confidence: **the customer side of 8Orders does the same
password reset correctly**, in the same service, using the same data shape. There is a working example
to copy — this is not a hard design problem, it is an inconsistency.

Register rows: #509 (takeover), #510 (password in logs), #609 (simulate endpoint), #610 (queue
disclosure), plus #38, #375, #386, #412, #444, #573 and two IDOR entries. **The knowledge graph records
these; it does not fix them.** Whether fixing them is part of "done" is a decision for the team.

## Key Concepts

- **Activation code** — the SMS code proving a phone number belongs to the person signing up. The same
  field is reused for password resets, which is why one flow can disturb the other.
- **The pass (token)** — issued at sign-in; every 8Orders service accepts it. Each service checks it
  with its own copy of the checking code, so a change to the rules has to be made four times.
- **Dismissal** — ending a driver's engagement, recorded in a log rather than deleted, so it can be
  reversed.
- **Asset transaction** — equipment or deposit movements held against a driver.
- **Device token** — the identifier the driver's phone gives 8Orders so notifications can reach it.

## Detailed Notes

- [[Identity & Access/Delivery Man Identity/_knowledge-graph|Technical Knowledge Graph]] — the reset
  chain defect by defect, and every endpoint with its authorisation.
- [[Identity & Access/Delivery Man Identity/_scenarios|Scenario Catalog]] — what happens if…
- [[DeliveryMen.business|DeliveryMen]] — the driver record in plain language.
- [[Identity & Access/Customer Identity/_overview|Customer Identity]] — the same job, done correctly.
