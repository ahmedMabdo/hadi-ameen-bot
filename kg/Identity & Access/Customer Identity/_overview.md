---
id: 8orders/identity-and-access/customer-identity/overview
title: Customer Identity — Overview
note_type: overview
context: Identity & Access
feature: Customer Identity
audience: Business
last_updated: 2026-08-23
tags: [identity-and-access, customer-identity, business]
---
# Customer Identity — Overview

## What is this? (for everyone)

The customer's account: signing up, proving the phone number is theirs, signing in, and changing or
recovering a password. Nothing else — what a customer *does* once signed in (browsing, carts, orders,
addresses, preferences) belongs to Customer Ordering.

One design decision shapes the whole feature: a customer can **start using 8Orders before creating an
account**. They browse, build a cart, and only register when they check out. The system keeps a
provisional record for that person and merges it into a real account at registration, so nothing they
did as a guest is lost. That decision is written down as an architecture decision record, not folklore.

## The Feature at a Glance

| # | Step (Screen) | Who | Purpose |
|---|---|---|---|
| 1 | Browse as guest | Customer | Use the app before having an account |
| 2 | Sign up | Customer | Create the account with a phone number |
| 3 | Enter code | Customer | Prove the phone number is theirs |
| 4 | Resend code | Customer | Get a new code if the first did not arrive |
| 5 | Sign in | Customer | Get the pass the app carries everywhere |
| 6 | Forgot password | Customer | Request a reset code |
| 7 | Set new password | Customer | Change it after proving the number |
| 8 | Change password | Signed-in customer | Change it knowing the old one |

## Business Flow (plain language)

1. Someone uses the app without an account. A provisional customer record may exist for them.
2. They sign up with a phone number and receive a code by SMS.
3. Entering the code confirms the number; any guest activity merges into the new account.
4. Signing in issues the pass the app carries on every request.
5. If they forget the password, they request a code, and the system **checks that code** before
   allowing a new password.
6. A signed-in customer can change their password by supplying the old one.

## What a business reader should know about trust here

**The good news first, because it matters for the driver-side problem:** this feature does password
recovery **correctly**. It checks the code before changing anything, and it applies the password rules.
The delivery-driver side of the same service does neither — so when that gets fixed, there is a working
example to copy from inside the same system. That is why this note exists before the fix.

Two real problems here:

1. **Passwords are written into the logs in plain text.** When a customer changes their password, both
   the old and the new one are recorded in the system's log, clearly labelled. When they reset a
   forgotten password, the new one is recorded too, mislabelled as a phone number. Anyone who can read
   logs can read customer passwords.
2. **Two endpoints had their sign-in requirement switched off.** Registration (the newer version) and
   "send me a code" can be called by anyone, with no credential at all. The old requirement is still
   visible in the code as a comment, so this was a deliberate change. It may be necessary — someone who
   has not registered yet may have no credential to present — but as it stands, anyone can ask 8Orders
   to send an SMS code to any phone number, which costs money and can be used to harass a number.

Register rows: #611 (passwords in logs), #443 (the switched-off sign-in requirement), and #510 (the
shared data shape behind the reset-password log line).

## Key Concepts

- **Provisional (guest) customer** — a record for someone using the app before registering, merged
  into a real account at sign-up.
- **Activation code** — the SMS code proving a phone number belongs to the person signing up. The same
  field is reused for password resets.
- **The pass (token)** — issued at sign-in; carries the customer's identity, which is why "change my
  password" cannot be aimed at someone else.
- **Reset vs. change** — reset is for a forgotten password and needs a code; change is for a known
  password and needs the old one.

## Detailed Notes

- [[Identity & Access/Customer Identity/_knowledge-graph|Technical Knowledge Graph]] — every endpoint,
  and the side-by-side comparison with the driver implementation.
- [[Identity & Access/Customer Identity/_scenarios|Scenario Catalog]] — what happens if…
- [[Customer.business|Customer]] — the customer record in plain language.
- [[Identity & Access/Delivery Man Identity/_overview|Delivery Man Identity]] — the same job, done
  wrongly, and the reason this comparison is worth reading.
