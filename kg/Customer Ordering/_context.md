---
id: 8orders/customer-ordering/context
note_type: context
context: Customer Ordering
last_updated: 2026-08-23
tags: [context, customer-ordering]
---
# Customer Ordering — Overview

The customer-facing browsing, cart, and checkout API (`TalabatkAPIs`) — restaurants/stores, cart,
discounts, coupons, order creation.

> Business-term glossary: [[../../../Talabatk.IDS/CONTEXT|CONTEXT.md]] — read that first (it covers
> Guest mode, Cart, Discounts & coupons, Order fulfilment/Pickup Tag language). This hub only
> indexes features and technical entry points; it does not redefine terms already there. Note:
> `CONTEXT.md`'s Guest mode section currently says guest mode is "not implemented yet" — the
> codebase shows it has since shipped (see the Tiered Discount technical note's Related section) —
> flag this to whoever owns `CONTEXT.md` for an update.

## Features
- [[Customer Ordering/Tiered Discount/_overview|Tiered Discount (business)]] · [[Customer Ordering/Tiered Discount/_knowledge-graph|technical]]
- [[Customer Ordering/Cart & Checkout/_overview|Cart & Checkout (business)]] · [[Customer Ordering/Cart & Checkout/_knowledge-graph|technical]]
- [[Customer Ordering/Discounts & Coupons/_overview|Discounts & Coupons (business)]] · [[Customer Ordering/Discounts & Coupons/_knowledge-graph|technical]] — PromoCodes + Vouchers; resolves `CONTEXT.md`'s "Coupon" ambiguity as far as the code shows
- [[Customer Ordering/Order & Fulfilment/_overview|Order & Fulfilment (business)]] · [[Customer Ordering/Order & Fulfilment/_knowledge-graph|technical]] — **Customer Ordering slice only**; `Order` itself is a 6,000+ line hub shared with Restaurant Portal/Delivery/Admin, only partially covered here
- [[Customer Ordering/Restaurant & Menu Discovery/_overview|Restaurant & Menu Discovery (business)]] · [[Customer Ordering/Restaurant & Menu Discovery/_knowledge-graph|technical]] — browsing slice only; Restaurant Portal owns full profile/menu management
- [[Customer Ordering/Customer Account/_overview|Customer Account (business)]] · [[Customer Ordering/Customer Account/_knowledge-graph|technical]] — profile/address/loyalty; includes a confirmed bug (User Preferences always returns empty) and the real source of Vouchers
- [[Customer Ordering/Support & Chat/_overview|Support & Chat (business)]] — bridges to this repo's already-excellent `docs/CHAT_*.md` docs rather than duplicating them; independently confirms the Cart & Checkout guest-mode mechanism
- [[Customer Ordering/Marketing & Content/_overview|Marketing & Content]] — light tier (Ads, Announcements, static pages)
- [[Customer Ordering/Ops & Infra/_knowledge-graph|Ops & Infra]] — liveness, feature flags, the area lookup that gates the whole customer journey, and the Centrifugo proxy (#616).

## Coverage note
All 37 `TalabatkAPIs` controller-level feature areas have now been triaged: 6 feature groups
documented to full or partial "answer-grade" depth (Tiered Discount, Cart & Checkout, Discounts &
Coupons, Order & Fulfilment, Restaurant & Menu Discovery, Customer Account), 2 bridged to existing
excellent docs rather than duplicated (Support & Chat, part of Ops & Infra), and 2 covered at light/
controller-map tier by design (Marketing & Content, the rest of Ops & Infra). See
`_system/_system-index.md`'s "What this pass proved" section for the full accounting, including
what remains genuinely un-investigated (individual handler-level depth on ~30 lighter routes).
- *(Guest Mode as its own feature — not yet documented as a standalone note; `CONTEXT.md` already
  covers its business language, and guest-mode cart retention itself IS documented inside Cart &
  Checkout's `MergeGuestCartIntoCustomerCommand` coverage.)*

## Integrates With
- [[Restaurant Portal/_context|Restaurant Portal]] — pushes new-order notifications via SignalR
- [[Admin/_context|Admin]] — order/review/chat/cancel-payment relay via SignalR; Admin also
  writes the [[TieredDiscount.technical|TieredDiscount]] campaigns
  this context reads
- [[Identity & Access/_context|Identity & Access]] — issues/validates the JWTs this API trusts
- <see [[_integrations|integration register]] for details>
