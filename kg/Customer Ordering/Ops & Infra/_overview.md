---
id: 8orders/customer-ordering/ops-and-infra/overview
title: Ops & Infra (Customer Ordering) — Overview
note_type: overview
context: Customer Ordering
feature: Ops & Infra
audience: Business
last_updated: 2026-08-23
tags: [customer-ordering, ops-and-infra, business]
---
# Ops & Infra (Customer Ordering) — Overview

## What is this? (for everyone)

The plumbing of the customer app's service: an "are you alive" check, the switches that turn features on
and off in the app, the lookup that works out **where the customer is**, and the endpoint that carries
chat messages.

One of these is not really plumbing at all. When a customer opens the app, the very first thing that has
to happen is turning their location into a serviceable area. Until that succeeds there is no city, no
delivery zone, no list of restaurants and no delivery fee — the app has nothing to show. So although it
sits among the technical endpoints, that lookup gates the entire customer journey.

Unlike the merchant portal and the back office, this service has **no web pages of its own**. Its only
consumer is the customer mobile app, which is not part of this codebase.

## The Feature at a Glance

| # | Step (Screen) | Who | Purpose |
|---|---|---|---|
| 1 | (no screen) | Monitoring system | Ask whether the service is alive |
| 2 | App launch | Every customer | Find out which features are switched on |
| 3 | Location permission granted | Every customer | Turn coordinates into a serviceable area |
| 4 | City lookup | Every customer | The city the customer is ordering in |
| 5 | (no screen) | Realtime service | Carry chat messages between customer and 8Orders |

## Business Flow (plain language)

1. The hosting platform checks the service is alive and keeps routing customers to it while it answers.
2. A customer opens the app. The app asks which features are enabled and adjusts what it shows.
3. The app sends the customer's coordinates and gets back the area they are in — or discovers that
   8Orders does not serve there.
4. From that point the customer can browse, order and chat.

## What a business reader must know

**The chat endpoint on this service is unprotected, and it is the more serious of the two such
endpoints in 8Orders.** It accepts messages with no sign-in and no shared key, and on this service it
handles **both** kinds of conversation — customer-to-support as well as driver-to-support. Worse, for
customer-support conversations it can also **change what other people are shown**: the response can
replace the message content, sender name, phone number and timestamp that get broadcast to connected
apps. So an unauthenticated party could both insert a message into a customer's support history and
alter what participants see.

It also writes **every chat message into the service log**, which is a privacy consideration
independently of the above.

For balance, and because it shows the fix is straightforward: the payment webhooks in this same codebase
verify a cryptographic signature before acting. The technique is present; it was not applied here.

**The health check cannot detect a database outage.** It answers "healthy" whenever the application is
running. This is the service every customer uses, so during an incident a green light here means less
than it appears to.

Register rows: #616 (unprotected chat endpoint, both instances), #39 and #48 (the duplicated
feature-switch endpoints).

## Key Concepts

- **Area resolution** — turning a customer's coordinates into a serviceable area. The first thing that
  must succeed.
- **Feature switch** — a toggle that changes app behaviour without a new app release.
- **Health check** — a shallow "are you alive" answer, not a system check.
- **Realtime service** — the external component that carries chat messages instantly.

## Detailed Notes

- [[Customer Ordering/Ops & Infra/_knowledge-graph|Technical Knowledge Graph]] — the Centrifugo proxy in
  full, including the broadcast override, and every endpoint.
- [[Customer Ordering/Ops & Infra/_scenarios|Scenario Catalog]] — what happens if…
- [[Customer Ordering/Ops & Infra/_knowledge-graph|Technical Knowledge Graph]] — the endpoint index and the Centrifugo proxy in full.
- [[Admin/City & Geography Administration/_overview|City & Geography Administration]] — where the
  geography this feature reads is maintained.
