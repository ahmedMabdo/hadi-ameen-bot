---
id: 8orders/customer-ordering/support-and-chat/overview
title: Support & Chat — Overview
note_type: overview
context: Customer Ordering
feature: Support & Chat
audience: Business
sources:
  - path: TalabatkAPIs/Controllers/ContactUs/ContactUsController.cs
    sha1: b82911562a40
  - path: TalabatkAPIs/Controllers/FAQ/FaqController.cs
    sha1: c5df7635da25
  - path: TalabatkAPIs/Controllers/TawkTo/TawkToController.cs
    sha1: 55a9ce8de87b
last_updated: 2026-08-02
---
# Support & Chat — Overview

## What is this? (for everyone)
How a customer gets help: three separate chat/contact surfaces, plus static contact info and FAQs.

**Important:** the real-time chat system (Customer↔Delivery, Support↔Delivery, Admin↔Customer,
Admin↔Merchant) already has **excellent, extensive documentation** in this repo's own `docs/`
folder — this note deliberately does not duplicate it, only bridges it into the knowledge graph and
adds what's missing (the Coupon/discount-style cross-reference discipline this graph applies
elsewhere).

## The Three Chat/Contact Surfaces
| Surface | What it is | Where it's documented |
|---------|------------|------------------------|
| **Centrifugo-based chat** (Customer↔Delivery, Support↔Delivery, Admin↔Customer, Admin↔Merchant) | The real, in-house chat system: WebSocket real-time, Cassandra + legacy SQL storage, includes an automated bot for Customer↔Admin | [[../../../CHAT_BUSINESS_OVERVIEW\|CHAT_BUSINESS_OVERVIEW.md]] (business), [[../../../CHAT_FEATURE_REFERENCE\|CHAT_FEATURE_REFERENCE.md]] (technical, 1,363 lines — single source of truth), [[../../../CUSTOMER_ADMIN_CHAT_BOT_FILES\|CUSTOMER_ADMIN_CHAT_BOT_FILES.md]] (bot mechanics), [[../../../BOT_PERFORMANCE_CONTAINMENT\|BOT_PERFORMANCE_CONTAINMENT.md]] (bot reporting), [[../../../GUEST_CHAT_MOBILE_INTEGRATION\|GUEST_CHAT_MOBILE_INTEGRATION.md]] (guest-mode chat) |
| **TawkTo widget** (`TalabatkAPIs/Controllers/TawkTo/TawkToController.cs`) | A **third-party** chat widget — one endpoint, `GetChatWidgetLinks`, hands the mobile app a link/config for the embedded TawkTo widget | Not documented elsewhere; light note only, this pass |
| **Contact Us forms** (`TalabatkAPIs/Controllers/ContactUs/ContactUsController.cs`) | Static forms, not chat: work-with-us (delivery/restaurant recruitment), complaints & suggestions, contact numbers lookup | Light note only, this pass |

Plus `FAQ` (`TalabatkAPIs/Controllers/FAQ/FaqController.cs`) — a straightforward FAQ content lookup.

## A confirmed cross-reference to Cart & Checkout's Guest Mode work
`GUEST_CHAT_MOBILE_INTEGRATION.md` states guest chat "reuses the **same `guestDeviceId` mechanism**
you already use for the guest cart" — this independently confirms the guest-mode mechanism this
knowledge graph already documented in
[[CustomerCart.technical|CustomerCart's guest-cart-merge coverage]]
is the same one other features build on. Good signal that this graph's Cart & Checkout note is
accurate and load-bearing beyond just its own feature.

## Detailed Notes
See the linked `docs/CHAT_*.md` files for full technical depth on the real chat system — this
knowledge graph does not maintain a separate technical note or entity index for it to avoid two
documents drifting out of sync.
