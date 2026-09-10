---
id: 8orders/admin/chat-administration/overview
title: Chat Administration — Overview
note_type: overview
context: Admin
feature: Chat Administration
audience: Business
last_updated: 2026-08-23
tags: [admin, chat-administration, business]
---
# Chat Administration — Overview

## What is this? (for everyone)

The 8Orders side of every conversation on the platform, and the tools for running it: a live dashboard
of open chats, past conversations, settings, customer ratings of the service they received, the chat
bot's performance, and the "contact us" messages people send.

Three different conversations exist in 8Orders, and this is where staff handle their side of two of
them:

- **Customer ↔ 8Orders support** — a customer with a problem.
- **Customer ↔ driver** — coordinating a delivery in progress.
- **Driver ↔ 8Orders support** — a driver with a problem.

A chat bot can answer the first kind, and its performance is reported on separately.

## The Feature at a Glance

| # | Step (Screen) | Who | Purpose |
|---|---|---|---|
| 1 | Chat dashboard | Support staff | See and pick up open conversations |
| 2 | Chat history | Support staff | Read what was said before |
| 3 | Customer chat | Support staff | Reply to a customer |
| 4 | Driver chat | Support staff | Reply to a driver |
| 5 | Chat settings | Operations | Configure how chat behaves |
| 6 | Ratings | Management | How customers scored the help they got |
| 7 | Chat reports | Management | Volumes, response times, bot performance |
| 8 | Contact-us messages | Support staff | Inbound correspondence |

## Business Flow (plain language)

1. A customer or driver starts a conversation from their app, or the bot starts answering one.
2. It appears on the support dashboard in real time.
3A staff member picks it up and replies; the customer or driver sees the reply instantly.
4. When it ends, the customer can rate it.
5. Volumes, response times and bot performance are reported from a separate reporting store.
6. Old conversations are archived into that store.

## What a business reader must know

**The same chat mechanics are built three times.** Customer-to-support, customer-to-driver and
driver-to-support each have their own separate implementation with near-identical logic. That is worth
knowing whenever someone asks for a chat change: "add message deletion", "add an attachment type", "add
an auto-reply" is not one piece of work, it is three, and doing one and forgetting the others is the
likely failure. This is the same duplication habit that produced four copies of the login-checking code
and six copies of the feature-switch endpoint.

**Chat data lives in three different places** — the main database, a *second* database dedicated to chat
and notifications, and a separate reporting store. A practical consequence: a change that touches both
an order and its chat cannot be made in a single all-or-nothing operation, because they are in different
databases.

**Two problems already recorded affect the trustworthiness of chat history:**

- A customer can join **another** customer's conversation with their driver, if that order is currently
  on the way. So a conversation is not guaranteed private to its participants.
- The channel that hands driver messages over to 8Orders accepts messages **without any
  authentication**. A message inserted that way is stored and displayed as if a real person sent it. Chat
  history therefore cannot be treated as evidence in a dispute without corroboration.

Register rows: #421 (a customer can join another order's chat), #616 (unauthenticated message
injection), #615 (the archive migration can be triggered by any signed-in user).

## Key Concepts

- **Conversation (session)** — one thread between two parties, with its messages.
- **The three chat kinds** — customer-support, customer-driver, driver-support; separate systems.
- **Chat bot** — automated answering on the customer-support channel, reported on separately.
- **Reporting store** — the separate database where chat statistics and archived history live.
- **Rating** — the customer's score for a conversation.

## Detailed Notes

- [[Admin/Chat Administration/_knowledge-graph|Technical Knowledge Graph]] — the three duplicated
  models, the three storage technologies, and the two realtime transports.
- [[Admin/Chat Administration/_scenarios|Scenario Catalog]] — what happens if…
- [[Support-and-Chat.business|Support & Chat]] — the customer's side.
- [[Delivery/Delivery Support & Chat/_overview|Delivery Support & Chat]] — the driver's side.
