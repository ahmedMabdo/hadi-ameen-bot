---
id: 8orders/identity-and-access/ops-and-infra/overview
title: Ops & Infra (Identity & Access) — Overview
note_type: overview
context: Identity & Access
feature: Ops & Infra
audience: Business
last_updated: 2026-08-23
tags: [identity-and-access, ops-and-infra, business]
---
# Ops & Infra (Identity & Access) — Overview

## What is this? (for everyone)

The parts of the sign-in service that have nothing to do with signing in: an "are you alive" check, the
switches that turn features on and off, a set of maintenance tools 8Orders staff use to move or clean up
data, and the page a customer lands on after paying.

It looks like the least interesting corner of the system and is not, for one reason: **this is the
service that issues everyone's pass.** A tool here protected only by "you must be signed in" is
reachable by anyone at all who is signed in — a customer, a driver, a restaurant employee — because this
service is what signs all of them in. On any other service, "signed in" means a narrower group.

## The Feature at a Glance

| # | Step (Screen) | Who | Purpose |
|---|---|---|---|
| 1 | (no screen) | Monitoring system | Ask whether the service is alive |
| 2 | (no screen) | Every app | Read which features are switched on |
| 3 | Feature switch | 8Orders operators | Turn a feature on or off for everyone |
| 4 | Maintenance page | 8Orders staff | Move chat data, rebuild chat reports, clean up images |
| 5 | Job trigger | 8Orders staff | Run a scheduled job immediately |
| 6 | Payment result page | Customer | The page shown after returning from the payment provider |

## Business Flow (plain language)

1. The hosting platform checks the service is alive and keeps sending traffic while it answers.
2. Apps ask which features are switched on and adjust what they show.
3. An operator flips a switch; the change goes to the external service that stores the switches.
4. Staff occasionally run maintenance work — moving chat history to its long-term store, rebuilding chat
   reports, or generating and deleting reduced-size images.
5. A customer who has just paid is returned to a simple page telling them whether it worked, in their
   own language.

## What a business reader must know

**A feature switch can report success and do nothing.** If the external switch service is unreachable
or errors, the failure is written to a log and the operator is still told the change worked. Since these
switches control real behaviour — whether stock is checked against the warehouse system, whether
accounting entries are sent, which parts of the merchant portal appear — an operator can believe a
change took effect when it did not.

**Maintenance tools are open to anyone who is signed in.** No role is required. The tools include moving
chat data between stores, rebuilding chat reports, and **deleting image files** under a folder the
caller names. A customer's login is enough to reach them. There is protection against being tricked
into it by a malicious web page, but not against someone calling them deliberately.

One thing that is **not** a problem, recorded so nobody spends time on it: the payment result page has
no sign-in requirement, and does not need one. It only displays a message; it does not confirm payments
or move money. The real payment confirmation happens elsewhere and is cryptographically signed.

We also **corrected an existing record** while documenting this: a previously reported finding about an
unauthenticated financial batch job was attributed to this service, but the endpoint is actually in the
Admin service. Two services have a file with the same name, and the line number happened to exist in
both — so the wrong reference looked right. The finding stands, in the right place, and the checking tool
now flags this class of ambiguity instead of skipping it.

Register rows: #614 (switch reports false success), #615 (maintenance open to any signed-in user),
#39/#48 (the duplicated switch-reading endpoints), and the correction to #375.

## Key Concepts

- **Feature switch (flag)** — an on/off control that changes behaviour without new software. Stored in
  an external service.
- **Health check** — a one-line "are you alive" answer. It does not check the database, so a green
  answer does not mean the service can do its job.
- **Maintenance job** — a one-off data task run on demand rather than on a schedule.
- **Payment result page** — the page shown after returning from the payment provider. Informational
  only.

## Detailed Notes

- [[Identity & Access/Ops & Infra/_knowledge-graph|Technical Knowledge Graph]] — every endpoint, why a
  roleless gate is wider here, and the four feature-switch mechanisms.
- [[Identity & Access/Ops & Infra/_scenarios|Scenario Catalog]] — what happens if…
- [[Restaurant Portal/Ops & Infra/_overview|Ops & Infra (Restaurant Portal)]] — the equivalent corner of
  the merchant portal.
