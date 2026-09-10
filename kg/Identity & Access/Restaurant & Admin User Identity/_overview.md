---
id: 8orders/identity-and-access/restaurant-and-admin-user-identity/overview
title: Restaurant & Admin User Identity — Overview
note_type: overview
context: Identity & Access
feature: Restaurant & Admin User Identity
audience: Business
last_updated: 2026-08-23
tags: [identity-and-access, restaurant-and-admin-user-identity, business]
---
# Restaurant & Admin User Identity — Overview

## What is this? (for everyone)

Accounts for the two kinds of *staff* who use 8Orders: **restaurant staff** who work the merchant
portal, and **8Orders' own back-office people** who run the operation.

The two are handled very differently. A restaurant manager can create logins for their own team without
involving 8Orders — the portal calls this service to do it. 8Orders' internal users, by contrast, are
managed through a plain web page on this same service that staff open directly.

The most important thing this feature produces is not the account itself but the **branch list**
attached to it: which restaurants a given login may act on. That list becomes part of the pass issued at
sign-in, and every screen in the merchant portal narrows what it shows based on it. Get the list wrong
here and the portal shows the wrong restaurant's data everywhere.

## The Feature at a Glance

| # | Step (Screen) | Who | Purpose |
|---|---|---|---|
| 1 | Add team member | Restaurant admin | Create a login for their own restaurant |
| 2 | Add store user | Merchant admin | Create a login across their stores |
| 3 | Enter activation code | New staff member | Prove the phone number is theirs |
| 4 | Change password | Restaurant staff | Change their own password |
| 5 | Forgot password | Restaurant staff | Reset it after receiving a code |
| 6 | Edit / remove team member | Merchant admin | Maintain the team |
| 7 | Manage internal users | 8Orders back office | Create, edit, list and delete 8Orders staff logins |

## Business Flow (plain language)

1. A restaurant admin adds a colleague. The account is created against their own restaurant.
2. The colleague receives a code by SMS and confirms their phone number.
3. They sign in through the single 8Orders sign-in page and receive a pass carrying their role and their
   branch list.
4. From then on, every merchant screen shows only what that branch list allows.
5. If they forget their password, they request a code — and the system **checks that code** before
   letting them set a new one.
6. 8Orders' own staff accounts are managed separately, through an internal web page on this service.

## What a business reader must know

**Good news, and it is genuinely useful:** the merchant password reset is done **correctly** — it checks
the code before changing anything. Together with the customer flow, that means **two of the three**
password-reset implementations in this service are right. Only the delivery-driver one is broken. That
reframes the driver problem: it is not a hard design question, it is one implementation out of step with
its two siblings, both of which are in the same service and can be copied.

Three real problems:

1. **Removing a team member is not restricted to your own restaurant.** When a merchant admin deletes a
   store user, neither the portal nor this service checks that the user being deleted belongs to the
   caller's restaurant. Any merchant admin can delete any store user in the system. This one only
   becomes visible when you look at both halves together — each half looks reasonable alone, which is
   why it went unnoticed.
2. **The internal user-management page has no role restriction.** It requires that you are signed in,
   and nothing more. Anyone who is authenticated and can reach that page can list, create, edit and
   delete 8Orders staff accounts.
3. **Merchant passwords are written to the log** on reset, in plain text — the same defect already
   recorded for customer and driver accounts. All three user types are affected.

Register rows: #604 (unscoped delete, both halves), #611 (passwords in logs, third instance).

## Key Concepts

- **Branch list** — the set of restaurants a login may act on. Created here, carried in the pass,
  enforced by every merchant screen.
- **Restaurant admin vs. merchant admin** — the first manages one restaurant's team, the second manages
  users across stores.
- **Sub-user / store user** — the two kinds of staff account a merchant can create.
- **Activation** — proving the phone number after someone else created the account, which is why
  activation is open to an unauthenticated caller.
- **Back-office user** — an 8Orders employee's login, managed through the internal page rather than the
  portal.

## Detailed Notes

- [[Identity & Access/Restaurant & Admin User Identity/_knowledge-graph|Technical Knowledge Graph]] —
  every endpoint, the three reset implementations side by side, and the #604 analysis.
- [[Identity & Access/Restaurant & Admin User Identity/_scenarios|Scenario Catalog]] — what happens if…
- [[Permission.business|Permission]] — what permissions mean in plain language.
- [[Restaurant Portal/Merchant Account & Access/_overview|Merchant Account & Access]] — where the branch
  list is actually enforced.
