---
id: 8orders/admin/context
note_type: context
context: Admin
last_updated: 2026-08-23
tags: [context, admin]
---
# Admin — Overview

Internal back-office administration (`AdminUi`, Angular SPA).

> No `CONTEXT.md` exists yet for this context (per `CONTEXT-MAP.md`). This hub is a **stub** —
> created only because [[Customer Ordering/_context|Customer Ordering]] links here as an
> integration target (Admin owns Tiered Discount campaign management). Not yet documented
> feature-by-feature by this skill.

## Features
- [[Admin/Admin Back-Office/_knowledge-graph|Admin Back-Office]] — controller inventory (~85 controllers,
  mostly write-side management for entities already documented from the shared-layer side); confirms
  `Restaurant.UpdateRestaurant` is reachable via `RestaurantController.SaveEditRestaurant`.
  Tiered Discount's write/management path also lives here; its canonical note is under
  [[TieredDiscount.technical|Customer Ordering/Tiered Discount]]
  since that's where the business glossary and consumption logic live.

## Shared Entities Owned Here (reference/config data, no single natural context owner)
- [[City.business|City]] · [[City.technical|technical]] — per-city tax/fee/scoring/financial config
- [[Area-and-Country|Area (+ Country)]] — geographic hierarchy siblings of City

## Integrates With
- [[Customer Ordering/_context|Customer Ordering]] — receives order/review/chat/cancel-payment
  relay (`ApiClientHandler` → `OperationHub` SignalR, `/AdminHub`); also writes the `TieredDiscount`
  entity Customer Ordering reads, via the same shared Application/Data code against the same DB
- <see [[_integrations|integration register]] for details>
