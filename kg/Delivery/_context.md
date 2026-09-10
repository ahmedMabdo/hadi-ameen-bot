---
id: 8orders/delivery/context
note_type: context
context: Delivery
sources:
  - path: Talabatk.IDS/Views/DeliveryMan/EditDeliveryMan.cshtml
    sha1: bf80f8426aa9
last_updated: 2026-08-23
tags: [context, delivery]
---
# Delivery — Overview

Delivery-man-facing app for accepting and fulfilling deliveries (`TalabatkDelivery`). Server-rendered
Razor MVC, no Angular; SignalR is used (see `CentrifugoController`/chat controllers documented under
Delivery Man Operations), so "no SignalR" above is superseded.

> No `CONTEXT.md` exists yet for this context (per `CONTEXT-MAP.md`) — noted as an Open Question, not
> invented here. This hub starts from the **shared entities** this context operationally owns even
> though `DeliveryMen`'s identity record itself is homed at
> [[Identity & Access/_context|Identity & Access]] (per `CONTEXT-MAP.md`'s explicit ownership
> statement). **Update 2026-08-03: the full controller pass is now complete** — all 21 files in
> `TalabatkDelivery/Controllers/` have been read (see
> [[Delivery/Delivery Man Operations/_knowledge-graph|Delivery Man Operations]]), and all 17 Razor views in
> `TalabatkDelivery/Views/` have been read too (see Phase 6 section below) — both superseding the
> "pending" note this stub originally carried.

## Features
- [[Delivery/Delivery Man Operations/_overview|Delivery Man Operations (business)]] · [[Delivery/Delivery Man Operations/_knowledge-graph|technical]] — the delivery man's self-service app: shifts, breaks, requests, order lifecycle, multi-delivery-man money exchange, earnings, announcements/notifications

## Shared Entities Owned Here (operational, not identity)
- [[DeliveryMan-Attendance|DeliveryMan Attendance & Shifts]] — `DeliverymanShiftLog`,
  `DeliveryMenShifts`, `DeliverymanBreakLog`. The identity record they attach to,
  [[DeliveryMen.technical|DeliveryMen]], carries the actual
  activation/shift-window/break business rules; these three are the records that log/configure it.

## Integrates With
- [[Identity & Access/_context|Identity & Access]] — `DeliveryMen` identity issuance/validation.
- <see [[_integrations|integration register]] for details>

## Phase 6 — Razor views (2026-08-03)
All 17 `.cshtml` files in `TalabatkDelivery/Views/` read (DeliveryManShift: Index/List/NewMap/Add/Edit;
DeliveryReasons: Create/DeleteReason/EditReason/Index; DeliveryMenLocation; Home/Index; Error; Privacy;
Shared: _Layout/_DevExtremeLayout/_ValidationScriptsPartial; _ViewImports/_ViewStart). All thin,
DevExtreme-grid-backed or plain Bootstrap CRUD forms with AJAX calls straight to already-documented
controller actions — no embedded business logic, no confirmed bugs. Matches the plan's "expect this to
be light" prediction with no exceptions (contrast `Talabatk.IDS/Views/DeliveryMan/EditDeliveryMan.cshtml`,
which was the one exception found in that host).

## Open Questions
- [ ] No `CONTEXT.md` exists for this context yet.
