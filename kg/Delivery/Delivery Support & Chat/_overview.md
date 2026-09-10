---
id: 8orders/delivery/delivery-support-and-chat/overview
title: Delivery Support & Chat — Overview
note_type: overview
context: Delivery
feature: Delivery Support & Chat
audience: Business
last_updated: 2026-08-23
tags: [delivery, delivery-support-and-chat, business]
---
# Delivery Support & Chat — Overview

## What is this? (for everyone)

The two conversations a delivery driver can have inside the app, plus the customer details they need to
complete a delivery.

**With the customer.** Tied to one specific order: "I'm at the gate", "which building?", a photo of the
door. It exists only for that order and both sides can see the history.

**With 8Orders support.** Not tied to an order — a driver can start it any time. Used for problems the
app cannot solve on its own: a payment dispute, a damaged bag, a customer who will not answer.

Alongside those, a driver can look up the customer's contact details and chosen address for the order
they are delivering, and reach the support-chat widget.

Messages travel through a realtime service (Centrifugo) so they arrive instantly rather than when the
app next refreshes. This is the only part of 8Orders that uses that service — everywhere else uses a
different realtime technology.

## The Feature at a Glance

| # | Step (Screen) | Who | Purpose |
|---|---|---|---|
| 1 | Customer details | Driver | Name, phone and chosen address for the delivery |
| 2 | Chat with customer | Driver, customer | Coordinate the drop-off for one order |
| 3 | Send a photo | Driver | Show the door, the receipt, the problem |
| 4 | Chat history | Driver, customer | What was already said about this order |
| 5 | Chat with support | Driver, 8Orders staff | Anything not tied to a single order |
| 6 | Availability | Driver | Whether they can be reached on chat |
| 7 | Support widget | Driver | Reach 8Orders through the third-party chat tool |

## Business Flow (plain language)

1. A driver picks up an order and looks up the customer's contact details and address.
2. Either side can start a chat about that order; messages arrive instantly.
3. Photos can be attached — commonly a picture of where the order was left.
4. Separately, a driver can open a support conversation with 8Orders at any time, with or without an
   order attached.
5. A driver can mark themselves unavailable for chat. There are **two** such switches, one per
   conversation type.

## What a business reader must know

**Anyone on the internet can inject a message into a driver-support conversation.** The endpoint the
realtime service uses to hand messages over to 8Orders performs no authentication whatsoever — no
password, no key, no signature. A message inserted this way is stored and shown in the history as if a
real person had sent it. The practical risk is a driver being given false instructions that appear to
come from 8Orders support, and a support history that cannot be trusted as evidence in a dispute.

What makes this worth fixing rather than accepting: **the same service already does it correctly
elsewhere.** The three payment callbacks in the same delivery app verify a cryptographic signature
before acting on anything. The technique is present in the codebase; it simply was not applied to the
chat path.

**A driver can look up any customer's details.** The two customer-lookup screens take an identifier
from the app and return the customer's information without checking that this driver is actually
delivering that customer's order. In effect any driver has a directory of the customer base. Both of
these were already on record before this note.

**It is not confirmed that driver-to-customer messages are being stored at all.** The hand-over
endpoint only has handling for the driver-to-support conversation. Whether customer chat history is
saved by another route, or silently dropped, has not been established — and "history is missing"
looks identical to "history was never written".

Register rows: #616 (unauthenticated message injection), #40 (the possible missing storage path), #421
(a customer can join another order's driver chat), plus two recorded customer-lookup issues.

## Key Concepts

- **Order chat** — a conversation attached to one delivery, visible to the driver and that customer.
- **Support chat** — a conversation between a driver and 8Orders, not tied to an order.
- **Realtime service** — the external component that delivers messages instantly.
- **Availability switch** — whether a driver can be reached on chat; there is one per conversation type.

## Detailed Notes

- [[Delivery/Delivery Support & Chat/_knowledge-graph|Technical Knowledge Graph]] — every endpoint, the
  realtime path, and the authentication gap in detail.
- [[Delivery/Delivery Support & Chat/_scenarios|Scenario Catalog]] — what happens if…
- [[Admin/Chat Administration/_knowledge-graph|Chat Administration]] — the 8Orders side of the same
  conversations.
- [[Customer Ordering/Support & Chat/_overview|Support & Chat]] — the customer's side.
