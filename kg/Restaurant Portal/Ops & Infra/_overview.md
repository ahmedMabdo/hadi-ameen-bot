---
id: 8orders/restaurant-portal/ops-and-infra/overview
title: Ops & Infra (Restaurant Portal) — Overview
note_type: overview
context: Restaurant Portal
feature: Ops & Infra
audience: Business
last_updated: 2026-08-23
tags: [restaurant-portal, ops-and-infra, business]
---
# Ops & Infra (Restaurant Portal) — Overview

## What is this? (for everyone)

Three small things that keep the Restaurant Portal running rather than doing anything a restaurant
would recognise as a task.

**Is the portal up?** A monitoring system asks the portal once a minute whether it is alive. Worth
knowing: the answer is "yes" as soon as the application is running, even if the database behind it is
unavailable. So a green light means "the lights are on", not "everything works".

**Which features are switched on?** 8Orders can turn parts of the portal on and off per release without
deploying new software. When a merchant loads the portal, it asks which of those switches are on and
hides the rest. Two different endpoints answer that same question, for historical reasons.

**Support chat.** The portal shows a chat widget so a merchant can reach 8Orders support. This is where
the link to that widget comes from.

## The Feature at a Glance

| # | Step (Screen) | Who | Purpose |
|---|---|---|---|
| 1 | (no screen) | Monitoring system | Ask whether the portal is alive |
| 2 | Portal load | Every merchant user | Find out which features are switched on |
| 3 | Support button | Every merchant user | Get the support-chat widget |

## Business Flow (plain language)

1. The hosting platform checks the portal is alive and keeps sending merchants to it while it answers.
2. A merchant opens the portal; the portal asks which features are enabled and draws only those.
3. If the merchant needs help, the support-chat widget opens with links fetched from the server.

## What a business reader should know

Two honest caveats, both recorded as findings:

- **The health check is shallow.** It cannot tell that the database is down. During an incident, "the
  health check is green" is not evidence that merchants can work.
- **The feature-switch question can be asked by anyone**, without signing in — and it is answered by
  two near-identically named endpoints, in this portal alone. The same duplicated file also exists in
  two other 8Orders services. Nothing sensitive leaks, but the list of switches is effectively a map of
  what is being built next, and the duplication means a change to one copy does not reach the others.

Register rows: #35 (the two endpoints in this portal), #39 and #48 (the copies elsewhere).

## Key Concepts

- **Health check** — a one-line "are you alive" endpoint used by the hosting platform.
- **Feature switch (flag)** — a per-release on/off toggle, administered in the Admin back-office.
- **Support widget** — the third-party chat window (Tawk.to) embedded in the portal.

## Detailed Notes

- [[Restaurant Portal/Ops & Infra/_knowledge-graph|Technical Knowledge Graph]] — every endpoint, and
  the full table of the four feature-flag mechanisms.
- [[Restaurant Portal/Ops & Infra/_scenarios|Scenario Catalog]] — what happens if…
