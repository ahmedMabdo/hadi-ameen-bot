---
id: 8orders/delivery/delivery-support-and-chat/knowledge-graph
title: Delivery Support & Chat — Knowledge Graph
note_type: knowledge-graph
context: Delivery
feature: Delivery Support & Chat
last_updated: 2026-08-23
sources:
  - path: TalabatkDelivery/Controllers/Apis/ChatController.cs
    sha1: 0c3811f6e647
  - path: TalabatkDelivery/Controllers/Apis/DeliveryManAdminChatController.cs
    sha1: 0438b5c7a06f
  - path: TalabatkDelivery/Controllers/Apis/CentrifugoController.cs
    sha1: 31932d0044dd
  - path: TalabatkDelivery/Controllers/Apis/CustomerUser/CustomerUserController.cs
    sha1: 26a35295ef6f
tags: [delivery, delivery-support-and-chat, technical, api-host]
---
# Delivery Support & Chat — Knowledge Graph

> **Context:** Delivery
> **Source Project:** `TalabatkDelivery` (4 controllers)
> **Entities:** the driver-side view of the three parallel chat aggregates (canonical detail in
> [[Admin/Chat Administration/_knowledge-graph|Chat Administration]]) plus
> [[Customer.technical|Customer]] read access
> **Register findings open here:** #616 (new), #40, #421, plus two registered IDOR instances

Two conversations a driver can be in — **with the customer** about the order in hand, and **with
8Orders support** about anything — plus the read access a driver needs to the customer's contact
details, and the support-chat widget. Realtime transport is **Centrifugo**, not SignalR: this context
is the only one that uses it.

## Two chat channels, one transport

| Channel | Endpoint set | Token | History |
|---|---|---|---|
| Driver ↔ Customer, scoped to an order | `api/Chat/*` | `GenerateToken(orderId)` — `TalabatkDelivery/Controllers/Apis/ChatController.cs:35-37` | `api/Chat/History?orderId=` — `:106-108` |
| Driver ↔ Admin support | `api/DeliveryManAdminChat/*` | `GenerateToken(int? orderId)` — order is **optional** — `TalabatkDelivery/Controllers/Apis/DeliveryManAdminChatController.cs:58-62` | `History(sessionId, orderId, guidNumber)` — three identifiers — `:100-104` |

Both are `[Authorize]` with the JWT bearer scheme at class level (`TalabatkDelivery/Controllers/Apis/ChatController.cs:19`,
`TalabatkDelivery/Controllers/Apis/DeliveryManAdminChatController.cs:29`). The difference in shape is informative: the customer chat is
always about an order, while support chat can exist without one — which is why its history takes a
session id and a `guidNumber` as well.

A driver also toggles their own chat availability: `ChangeChatOnlineValueForDeliveryMan`
(`TalabatkDelivery/Controllers/Apis/ChatController.cs:61-63`) and `ChangeOnlineStatus` (`TalabatkDelivery/Controllers/Apis/DeliveryManAdminChatController.cs:79-83`) — two
separate online flags, one per channel.

## The realtime path, and its hole

```
driver app ──token──> Centrifugo (external realtime server)
                          │
                          │ proxy: POST api/centrifugo/publish
                          v
              CentrifugoController.HandlePublish  ── NO AUTH ATTRIBUTE ──> persists the message
                          │
                          ├── Data null / type contains "typing" / empty payload -> acknowledged, ignored
                          └── Channel starts with "DeliveryManAdmin_" -> HandleDeliveryManAdminProxyMessagesCommand
```

> ⚠️ **CONFIRMED — the proxy webhook has no authentication at all**
> `POST api/centrifugo/publish` carries no `[Authorize]`, no `[AllowAnonymous]`, and no shared-secret or
> signature check (`TalabatkDelivery/Controllers/Apis/CentrifugoController.cs:19-40`). For channels named `DeliveryManAdmin_*` it
> dispatches a command that **persists the message**, so an unauthenticated caller who learns a channel
> name can inject messages that the stored history will present as genuine.
> `_conflicts.md` **#616**.
>
> What makes this an omission rather than a decision: **the same host secures its other anonymous
> webhooks properly.** All three `[AllowAnonymous]` Fawry callbacks verify a SHA-256 signature against a
> configured secret before acting (`Shared/TalabatkData/FawryCashCollectionService/FawryCashCollectionService.cs:104-125`).
> The pattern exists here and was not applied.

> ⚠️ **Also open — the missing routing branch (#40)**
> The same action only branches on the `DeliveryManAdmin_` prefix. There is no branch for the
> driver↔customer channel that `ChatController.GenerateToken` issues tokens for
> (`TalabatkDelivery/Controllers/Apis/CentrifugoController.cs:29-40`). Whether customer-chat messages are persisted by another path, rely
> on Centrifugo's default relay, or are silently dropped is **not confirmed** — and that is worth
> resolving, because "chat history is missing" and "chat history was never written" look identical from
> the outside.

> ⚠️ **Inherited — live chat session hijack (#421)**
> Registered against [[Customer.technical|Customer]]: any authenticated customer can obtain a realtime
> token for **any order currently on the way** and join that order's customer↔driver conversation. The
> driver is on the other side of that conversation, so the exposure lands here too.

## Endpoint index

| Endpoint | Auth | What it does | Notes |
|---|---|---|---|
| `GET api/Chat/GenerateToken?orderId=` | JWT bearer | Realtime token for the order's customer chat | `TalabatkDelivery/Controllers/Apis/ChatController.cs:35-37`; the hijack path in #421 is the token-issuing logic |
| `POST api/Chat/ChangeChatOnlineValueForDeliveryMan` | JWT bearer | Driver's availability for customer chat | `TalabatkDelivery/Controllers/Apis/ChatController.cs:61-63` |
| `POST api/Chat/GetChatImageUrl` | JWT bearer | Stores a chat image and returns its URL | `TalabatkDelivery/Controllers/Apis/ChatController.cs:84-86` — despite the name, this **saves** (`SaveChatImage`) |
| `GET api/Chat/History?orderId=` | JWT bearer | Conversation history for an order | `TalabatkDelivery/Controllers/Apis/ChatController.cs:106-108` |
| `GET api/DeliveryManAdminChat/GetChatConfig` | JWT bearer | Client configuration for support chat | `TalabatkDelivery/Controllers/Apis/DeliveryManAdminChatController.cs:45-49` |
| `GET api/DeliveryManAdminChat/GenerateToken?orderId=` | JWT bearer | Support-chat token; order id **optional** | `TalabatkDelivery/Controllers/Apis/DeliveryManAdminChatController.cs:58-62` |
| `POST api/DeliveryManAdminChat/ChangeOnlineStatus` | JWT bearer | Driver's availability for support chat | `TalabatkDelivery/Controllers/Apis/DeliveryManAdminChatController.cs:79-83` |
| `GET api/DeliveryManAdminChat/History` | JWT bearer | Support history by session id / order id / guid | `TalabatkDelivery/Controllers/Apis/DeliveryManAdminChatController.cs:100-104` |
| `GET api/DeliveryManAdminChat/GetAllChats` | JWT bearer | The driver's support conversations | `TalabatkDelivery/Controllers/Apis/DeliveryManAdminChatController.cs:123` |
| `POST api/centrifugo/publish` | **none** | Realtime proxy — persists driver↔admin messages | 🔴 #616, #40 — `TalabatkDelivery/Controllers/Apis/CentrifugoController.cs:19-40` |
| `GET api/CustomerUser/GetCustomerInfo` | JWT bearer, role `deliveryman` | Customer details by **caller-supplied `CustomerId`** (default 0) | 🔴 registered IDOR — the query is `GetCustomerByIdQuery` with no order-scoping — `TalabatkDelivery/Controllers/Apis/CustomerUser/CustomerUserController.cs:28-31` |
| `GET api/CustomerUser/GetCustomerInfoWithSelectedAddress` | JWT bearer, role `deliveryman` | Customer + address by **caller-supplied `userAddressId`** | 🔴 registered in `_idor-instances.md` — `TalabatkDelivery/Controllers/Apis/CustomerUser/CustomerUserController.cs:49-53` |
| `GET api/TawkTo/*` | JWT bearer | Support-widget links | `TalabatkDelivery/Controllers/Apis/TawkTo/TawkToController.cs` |

Both `CustomerUser` endpoints are role-gated to `deliveryman` and then take an identifier from the
caller with **no check that the driver is actually delivering that customer's order**. A driver
therefore has a lookup tool for customer contact details across the whole customer base. Both are
already in the registers; they are listed here because this is the feature that owns them.

## Status / State

No status of its own. Two independent per-driver online flags (one per channel), and message state
lives on the chat aggregates documented in
[[Admin/Chat Administration/_knowledge-graph|Chat Administration]].

## Entity Index

| Entity | Layer | Type | Responsibility |
|---|---|---|---|
| `CustomerDeliveryChat` / `…Message` | Domain (Chat context) | Session + messages | Driver ↔ customer conversation, one of **three parallel chat aggregates** with near-identical shape |
| `DeliveryManAdminChat` / `…Message` | Domain (Chat context) | Session + messages | Driver ↔ support conversation |
| [[Customer.technical\|Customer]] | Domain | Hub | Read by the two `CustomerUser` endpoints |
| [[DeliveryMen.technical\|DeliveryMen]] | Domain | Hub | The driver; holds the chat-online flags |

## Feature Flow (Business Narrative)

```
1. DRIVER PICKS UP AN ORDER
   └── needs the customer's contact details -> api/CustomerUser/GetCustomerInfo
2. DRIVER OR CUSTOMER STARTS A CHAT
   └── GenerateToken(orderId) -> driver joins the order's Centrifugo channel
3. MESSAGES FLOW
   └── Centrifugo proxies each publish to api/centrifugo/publish, which persists it
       (driver<->admin only; the customer branch is unconfirmed — #40)
4. DRIVER NEEDS HELP FROM 8ORDERS
   └── DeliveryManAdminChat token (order optional) -> support conversation
5. DRIVER GOES OFF-CHAT
   └── two separate online flags, one per channel
```

## Key Cross-Cutting Relationships

| From | To | Relationship | Notes |
|---|---|---|---|
| This feature | [[Admin/Chat Administration/_knowledge-graph\|Chat Administration]] | the admin side of the same conversations | Dashboards, history, settings, bot |
| This feature | Centrifugo (external) | realtime transport | The only context using Centrifugo rather than SignalR |
| This feature | [[Customer.technical\|Customer]] | driver reads customer contact details | Two registered IDOR instances |
| This feature | [[Customer Ordering/Support & Chat/_knowledge-graph\|Support & Chat]] | the customer's side of the driver chat | #421 lives there |
| This feature | Cassandra | long-term chat storage | Migration triggered from [[Identity & Access/Ops & Infra/_knowledge-graph\|Ops & Infra]] |

## Change Surface

| Signal | Value | Notes |
|---|---|---|
| Direct dependents (Ring 1) | driver app chat UI, admin chat dashboard, Centrifugo | |
| Sides touched | 3/5 | API host · Application · Data (Chat context + Cassandra) |
| Cross-context integrations | 3 | Centrifugo, Admin chat, Cassandra |
| Register findings open | 4 | #616 (new), #40, #421, plus 2 IDOR rows |
| Hub? | no | |
| Risk flags | an unauthenticated write path into stored conversations; three duplicated chat aggregates mean a chat change is three changes |

## Open Questions

- [ ] Is `api/centrifugo/publish` reachable only from the Centrifugo server's network? That is the only
      thing standing between #616 and message forgery, and it is not visible in code.
- [ ] #40: are driver↔customer messages persisted at all? If they are, by which path?
- [ ] Why two separate chat-online flags rather than one? Can a driver be online for support and offline
      for customers, and is that intentional?
- [ ] `GetChatImageUrl` saves an image — what validates its type and size, and where is it stored?
- [ ] Should the two `CustomerUser` lookups be scoped to the driver's **current** order? Today they are
      a general customer directory for anyone with the `deliveryman` role.
