---
id: 8orders/delivery/ops-and-infra/overview
title: Ops & Infra (Delivery) — Overview
note_type: overview
context: Delivery
feature: Ops & Infra
audience: Business
last_updated: 2026-08-23
tags: [delivery, ops-and-infra, business]
---
# Ops & Infra (Delivery) — Overview

## What is this? (for everyone)

The plumbing of the delivery service: an "are you alive" check, the switches that turn features on and
off for the driver app, the sign-in and sign-out of the internal web console, and the endpoint the
realtime messaging service uses.

None of it is something a driver would recognise as a task, and all of it decides whether the rest of
the delivery app works.

One thing distinguishes this service from the merchant portal and the admin back-office: it serves
**ordinary web pages** for 8Orders staff — the operations map, shift screens, delivery-reason lists —
alongside the API the driver phones talk to. That means it has **two different ways of knowing who you
are**: a browser session for staff, and an app token for drivers.

## The Feature at a Glance

| # | Step (Screen) | Who | Purpose |
|---|---|---|---|
| 1 | (no screen) | Monitoring system | Ask whether the service is alive |
| 2 | (no screen) | Driver app | Find out which features are switched on |
| 3 | Landing page | 8Orders staff | Entry point to the internal screens |
| 4 | Sign in | 8Orders staff | Authenticate against the central sign-in service |
| 5 | Sign out | 8Orders staff | End both the browser session and the central one |
| 6 | (no screen) | Realtime service | Hand chat messages over to 8Orders |

## Business Flow (plain language)

1. The hosting platform checks the service is alive and keeps routing drivers to it while it answers.
2. A driver's app asks which features are switched on and adjusts accordingly — for example whether a
   driver may carry more than one order at a time.
3. A staff member opens the internal console and signs in through the central 8Orders sign-in service.
4. Signing out ends both the local browser session and the central one.

## What a business reader must know

**The health check cannot tell that anything is broken.** It answers "healthy" as long as the
application is running, without checking the database, the sign-in service, or the realtime service. In
an incident, a green light here means only that the process is up — and this is the service whose
failure stops drivers working.

**The feature switches can be read by anyone**, with no sign-in, exactly as in the other services. The
values are not secret, but the list of switches is a preview of what is being built.

**Two identical copies of the same switch-reading code exist in four services.** A change to one does
not reach the others. This is recorded, and it is the reason a "simple" change to how flags are read is
never simple.

One item that belongs to this service but is documented next to its effect: the endpoint the realtime
messaging service uses to hand over messages accepts requests **without any authentication**. That is
covered in [[Delivery/Delivery Support & Chat/_overview|Delivery Support & Chat]], because the
consequence — forged messages in a driver's support conversation — is a chat problem rather than an
infrastructure one.

Register rows: #39 and #48 (the duplicated switch controllers), #616 (the unauthenticated realtime
endpoint, documented under Delivery Support & Chat).

## Key Concepts

- **Health check** — a one-line "are you alive" answer used by the hosting platform.
- **Feature switch (flag)** — an on/off control that changes app behaviour without new software.
- **Two ways of signing in** — a browser session for 8Orders staff, an app token for drivers. This
  service accepts both, which is unusual and worth knowing before adding anything to it.
- **Realtime service** — the external component that carries chat messages instantly.

## Detailed Notes

- [[Delivery/Ops & Infra/_knowledge-graph|Technical Knowledge Graph]] — every endpoint, the two
  authentication schemes, and the login/logout asymmetry.
- [[Delivery/Ops & Infra/_scenarios|Scenario Catalog]] — what happens if…
- [[Restaurant Portal/Ops & Infra/_overview|Ops & Infra (Restaurant Portal)]] — the same corner of the
  merchant portal, where the full feature-switch picture is set out.
