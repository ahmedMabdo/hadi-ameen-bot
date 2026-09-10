---
id: 8orders/restaurant-portal/merchant-account-and-access/overview
title: Merchant Account & Access — Overview
note_type: overview
context: Restaurant Portal
feature: Merchant Account & Access
audience: Business
last_updated: 2026-08-23
tags: [restaurant-portal, merchant-account-and-access, business]
---
# Merchant Account & Access — Overview

## What is this? (for everyone)

Every restaurant that sells through 8Orders gets its own login to the Restaurant Portal. This part of
the system decides **who that person is, which branches they are allowed to see, and what they are
allowed to do** — and it lets a restaurant's own manager create logins for their staff without
involving anyone at 8Orders.

A chain with eight branches has one manager who needs all eight, and eight shift supervisors who each
need exactly one. That distinction is the heart of this feature: when someone signs in, the system
records both "the store you are signed in as" and "the stores you may act on". Every other screen in
the portal — menus, incoming orders, settlement reports — is expected to show only what that answer
allows.

It also holds the restaurant's own account settings: opening hours, temporary "we're too busy"
closures, the reasons staff may pick when they reject an order, how the store receives orders, and
whether it takes part in the loyalty-points scheme.

## The Feature at a Glance

| # | Step (Screen) | Who | Purpose |
|---|---|---|---|
| 1 | Sign in | Restaurant staff | Proves who they are and which branches they may act on |
| 2 | My restaurants | Merchant admin | Lists the branches this login covers |
| 3 | Store users | Merchant admin, Restaurant admin | Create, edit and remove logins for their own staff |
| 4 | User permissions | Restaurant staff | Shows what the signed-in user is allowed to do |
| 5 | Working days | Restaurant admin | Sets the opening hours the customer app respects |
| 6 | Busy / closed | Restaurant staff | Temporarily stops taking orders, with a reason and an end time |
| 7 | Store profile & devices | Restaurant staff | Register the tablet/phone that receives new-order alerts |
| 8 | Reviews | Merchant admin | Reads what customers said about their branches |

## Business Flow (plain language)

1. A restaurant user signs in. The sign-in service issues a pass that names their branch and the full
   list of branches they may act on.
2. Every screen they open afterwards carries that pass. The portal is supposed to narrow everything
   it shows to the branches on it.
3. A merchant admin can add a colleague as a portal user. The new user is always attached to the
   admin's own branch — the system fills that in rather than trusting the form.
4. Staff set opening hours and, when the kitchen is overwhelmed, mark the store busy for a stated
   period. The customer app stops offering the store for that window.
5. The store registers the device that should receive new-order alerts, so orders reach a real screen
   in the kitchen rather than an empty browser tab.

## Where this feature is currently not safe

Stated plainly, because it is the reason this feature is documented before the rest of the portal:
**seven of its endpoints accept a branch identifier from whoever is calling, instead of taking it
from the signed-in user's pass.** In practice that means a signed-in merchant can, by changing a
number in a request, read or change data belonging to a restaurant that is not theirs:

| What can happen today | Severity |
|---|---|
| Read any restaurant's opening hours | Confidential-ish, low harm |
| **Change any restaurant's opening hours**, including switching the whole working-days feature off for them | High — a competitor's store can be made to look closed |
| Read any restaurant's customer reviews, **including the reviewing customer's first name** | High — customer data of another tenant |
| Read any restaurant's "busy" history with the staff names who set and cleared it | Medium |
| Delete a store user belonging to another restaurant | High |
| Read any portal user's permission list | Medium |

These are recorded as findings #604, #605, #606, #607, #608 in the conflict register and #11 in the
IDOR register. They are **documentation, not fixes** — the knowledge graph's job is to make them
impossible to lose track of. Sizing the fix is a change-request question, and the technical note
gives a change surface for it.

## Key Concepts

- **Branch (restaurant)** — one physical store. The unit everything in the portal is scoped to.
- **The pass (token)** — issued at sign-in by the Identity & Access service; carries the branch and
  the branch list. See [[Identity & Access/_context|Identity & Access]].
- **Merchant admin vs. restaurant admin vs. staff** — three levels of portal role. Only the first two
  may manage other users.
- **Busy** — a temporary, reasoned closure with an end time; different from being outside opening
  hours, and different from being deactivated by 8Orders.
- **Working day** — one opening window in the weekly schedule the customer app reads.

## Detailed Notes

- [[Restaurant Portal/Merchant Account & Access/_knowledge-graph|Technical Knowledge Graph]] — the
  endpoint-by-endpoint scoping table, for developers and CR work.
- [[Restaurant Portal/Merchant Account & Access/_scenarios|Scenario Catalog]] — what happens if…
- [[Merchant-Menu-and-Orders.business|Merchant Menu & Orders]] — the merchant entities this feature protects.
