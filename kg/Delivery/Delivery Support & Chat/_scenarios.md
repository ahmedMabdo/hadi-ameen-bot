---
id: 8orders/delivery/delivery-support-and-chat/scenarios
title: Delivery Support & Chat — Scenario Catalog
note_type: scenarios
context: Delivery
feature: Delivery Support & Chat
audience: Business · QA · Developer
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
  - path: Shared/TalabatkData/FawryCashCollectionService/FawryCashCollectionService.cs
    sha1: fb2c3d4c4d3d
tags: [delivery, delivery-support-and-chat, scenarios]
---
# Delivery Support & Chat — Scenario Catalog

> Two conversations (order chat, support chat) over one realtime transport. Rows describe what the code
> does today; the security rows were each read at the cited line.

## Happy path

| # | Precondition | Action | Expected outcome | Rule / source |
|---|---|---|---|---|
| H1 | Driver assigned an order, needs contact details | `GET api/CustomerUser/GetCustomerInfo` | Customer info returned for the supplied id | `TalabatkDelivery/Controllers/Apis/CustomerUser/CustomerUserController.cs:28-31` |
| H2 | Driver needs the drop-off address | `GET api/CustomerUser/GetCustomerInfoWithSelectedAddress` | Customer + the chosen address | `TalabatkDelivery/Controllers/Apis/CustomerUser/CustomerUserController.cs:49-53` |
| H3 | Driver opens the order chat | `GET api/Chat/GenerateToken?orderId=` | Realtime token for that order's channel | `TalabatkDelivery/Controllers/Apis/ChatController.cs:35-37` |
| H4 | Message sent from either side | realtime publish | Delivered instantly through Centrifugo; proxied to 8Orders | `TalabatkDelivery/Controllers/Apis/CentrifugoController.cs:19-40` |
| H5 | Driver wants to show the door | `POST api/Chat/GetChatImageUrl` | Image stored, URL returned (the name says get, the action saves) | `TalabatkDelivery/Controllers/Apis/ChatController.cs:84-86` |
| H6 | Driver reopens the order later | `GET api/Chat/History?orderId=` | Prior messages for that order | `TalabatkDelivery/Controllers/Apis/ChatController.cs:106-108` |
| H7 | Driver needs 8Orders help, no order involved | `GET api/DeliveryManAdminChat/GenerateToken` with no order id | Support token issued — order id is optional here | `TalabatkDelivery/Controllers/Apis/DeliveryManAdminChatController.cs:58-62` |
| H8 | Driver returns to a support thread | `GET api/DeliveryManAdminChat/History` | History by session id, order id or guid | `TalabatkDelivery/Controllers/Apis/DeliveryManAdminChatController.cs:100-104` |
| H9 | Driver reviews all their support threads | `GET api/DeliveryManAdminChat/GetAllChats` | Their conversations | `TalabatkDelivery/Controllers/Apis/DeliveryManAdminChatController.cs:123` |
| H10 | Driver stops taking chats | `POST api/Chat/ChangeChatOnlineValueForDeliveryMan` | Customer-chat availability off | `TalabatkDelivery/Controllers/Apis/ChatController.cs:61-63` |
| H11 | Same, for support | `POST api/DeliveryManAdminChat/ChangeOnlineStatus` | Support availability off — a **separate** flag | `TalabatkDelivery/Controllers/Apis/DeliveryManAdminChatController.cs:79-83` |

## Partial / incremental

| # | Precondition | Action | Expected outcome | Rule / source |
|---|---|---|---|---|
| P1 | Someone is typing | realtime publish with a `typing` type | Acknowledged and **not persisted** — typing indicators are filtered out | `TalabatkDelivery/Controllers/Apis/CentrifugoController.cs:21-27` |
| P2 | Empty payload arrives | realtime publish with blank data | Acknowledged and ignored | `TalabatkDelivery/Controllers/Apis/CentrifugoController.cs:21-27` |
| P3 | Support conversation started, then an order becomes relevant | `GenerateToken(orderId)` on the support channel | The same channel can carry an order id | `TalabatkDelivery/Controllers/Apis/DeliveryManAdminChatController.cs:58-62` |
| P4 | Driver offline for customers, online for support | two flags set differently | Supported — the flags are independent | `TalabatkDelivery/Controllers/Apis/ChatController.cs:61-63`, `TalabatkDelivery/Controllers/Apis/DeliveryManAdminChatController.cs:79-83` |

## Negative / guard

| # | Precondition | Action | Expected outcome (rejection) | Rule / source |
|---|---|---|---|---|
| N1 | No token | any `api/Chat/*` action | 401 — class-level JWT bearer | `TalabatkDelivery/Controllers/Apis/ChatController.cs:19` |
| N2 | No token | any `api/DeliveryManAdminChat/*` action | 401 | `TalabatkDelivery/Controllers/Apis/DeliveryManAdminChatController.cs:29` |
| N3 | Token without the `deliveryman` role | `GET api/CustomerUser/*` | 403 | `TalabatkDelivery/Controllers/Apis/CustomerUser/CustomerUserController.cs:30` |
| N4 | No token | `POST api/centrifugo/publish` | **Accepted** — there is no authorisation attribute at all | 🔴 `TalabatkDelivery/Controllers/Apis/CentrifugoController.cs:19-40` |
| N5 | Channel name outside the known prefix | `POST api/centrifugo/publish` | Acknowledged with success and **nothing stored** — no error is returned | `TalabatkDelivery/Controllers/Apis/CentrifugoController.cs:29-40` |
| N6 | `CustomerId` omitted | `GET api/CustomerUser/GetCustomerInfo` | Defaults to `0`; the query runs with id 0 rather than rejecting the call | `TalabatkDelivery/Controllers/Apis/CustomerUser/CustomerUserController.cs:31` |

## Returns / cancellation / reversal

| # | Precondition | Action | Expected outcome | Rule / source |
|---|---|---|---|---|
| R1 | Message sent in error | — | No delete or edit endpoint exists in either chat controller | `TalabatkDelivery/Controllers/Apis/ChatController.cs`, `TalabatkDelivery/Controllers/Apis/DeliveryManAdminChatController.cs` |
| R2 | Driver went offline by mistake | set the flag back | Both availability flags are simple toggles | `TalabatkDelivery/Controllers/Apis/ChatController.cs:61-63` |
| R3 | Support thread resolved | — | No close/resolve action on the driver side; resolution is an Admin concern | [[Admin/Chat Administration/_knowledge-graph\|Chat Administration]] |

## Integration (cross-side / cross-context)

| # | Precondition | Action | Expected outcome | Rule / source |
|---|---|---|---|---|
| I1 | Any message | Centrifugo proxies it | `POST api/centrifugo/publish`; only `DeliveryManAdmin_*` channels are routed to a persisting command | `TalabatkDelivery/Controllers/Apis/CentrifugoController.cs:29-40` |
| I2 | Support conversation | Admin side | Same data read by the admin chat dashboards | [[Admin/Chat Administration/_knowledge-graph\|Chat Administration]] |
| I3 | Order chat | Customer side | The customer's half of the same conversation | [[Customer Ordering/Support & Chat/_knowledge-graph\|Support & Chat]] |
| I4 | Chat data ages | migration to Cassandra | Triggerable by any authenticated principal | 🔴 `_conflicts.md` #615; [[Identity & Access/Ops & Infra/_knowledge-graph\|Ops & Infra]] |
| I5 | Driver cash paid at Fawry | anonymous webhook | **Signature-verified** before acting — the pattern #616 is missing | `Shared/TalabatkData/FawryCashCollectionService/FawryCashCollectionService.cs:104-125` |

## Security scenarios — current behaviour

| # | Precondition | Action | Actual outcome today | Finding |
|---|---|---|---|---|
| X1 | **No credential of any kind**, knows a channel name | `POST api/centrifugo/publish` with `Channel: "DeliveryManAdmin_…"` and a message body | The message is **persisted** and appears in the driver↔support history as genuine | 🔴 `_conflicts.md` **#616** · `TalabatkDelivery/Controllers/Apis/CentrifugoController.cs:19-40` |
| X2 | Same | repeat with other channel names | Anything outside the known prefix is silently accepted and dropped, so probing is cheap and quiet | `TalabatkDelivery/Controllers/Apis/CentrifugoController.cs:29-40` |
| X3 | Any driver | `GET api/CustomerUser/GetCustomerInfo?CustomerId=<any>` | That customer's details, with no check that the driver is delivering their order | 🔴 registered IDOR · `TalabatkDelivery/Controllers/Apis/CustomerUser/CustomerUserController.cs:28-31` |
| X4 | Any driver | `GET api/CustomerUser/GetCustomerInfoWithSelectedAddress?userAddressId=<any>` | That customer's address | 🔴 `_idor-instances.md` · `TalabatkDelivery/Controllers/Apis/CustomerUser/CustomerUserController.cs:49-53` |
| X5 | Any authenticated **customer** | request a chat token for an order on the way | Joins that order's driver conversation | 🔴 `_conflicts.md` #421 |
| X6 | Driver↔customer messages sent | — | Whether they are persisted at all is **unconfirmed**; only the support prefix is routed | 🟡 `_conflicts.md` #40 |

## Open Questions

- [ ] Is `api/centrifugo/publish` restricted to the Centrifugo server's network? That is the only control
      standing between X1 and message forgery, and it is invisible in code.
- [ ] #40 / X6: are order-chat messages stored, and if so by what path?
- [ ] Should the customer lookups be scoped to the driver's active order (X3, X4)?
- [ ] `GetChatImageUrl` stores an uploaded image — what validates type and size, and where does it land?
- [ ] Why two availability flags rather than one, and does any screen show both?
- [ ] Is there any audit of who sent a support message, given X1 allows an unauthenticated sender?
