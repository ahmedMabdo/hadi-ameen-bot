---
id: 8orders/customer-ordering/support-and-chat/scenarios
title: Support & Chat — Scenario Catalog
note_type: scenarios
context: Customer Ordering
feature: Support & Chat
audience: Business · QA · Developer
last_updated: 2026-08-23
sources:
  - path: TalabatkAPIs/Controllers/CustomerAdminChat/CustomerAdminChatController.cs
    sha1: 63a1d0eb75b3
  - path: TalabatkAPIs/Controllers/CustomerDeliveryChat/CustomerDeliveryChatController.cs
    sha1: b2971777d747
  - path: TalabatkAPIs/Controllers/ContactUs/ContactUsController.cs
    sha1: b82911562a40
  - path: TalabatkAPIs/Controllers/TawkTo/TawkToController.cs
    sha1: 55a9ce8de87b
  - path: Shared/TalabatkApplication/Queries/GetAdminChatMessagesQuery/GetAdminChatMessagesQuery.cs
    sha1: 89e17484040c
  - path: Shared/TalabatkApplication/Queries/GetCustomerDeliveryChatHistoryQuery/GetCustomerDeliveryChatHistoryQuery.cs
    sha1: b26e9f51b1c1
  - path: Shared/TalabatkApplication/Commands/SaveImageForCustomerAdminChatCommand/SaveImageForCustomerAdminChatCommand.cs
    sha1: c556f8cf9e5e
  - path: Shared/TalabatkApplication/Commands/SaveImageForCustomerDeliveryChatCommand/SaveImageForCustomerDeliveryChatCommand.cs
    sha1: d67a2d14d3ec
  - path: Shared/TalabatkApplication/Commands/EndCustomerAdminChatCommand/EndCustomerAdminChatCommand.cs
    sha1: 2f88432584f4
  - path: Shared/TalabatkApplication/Commands/RateCustomerAdminChatCommand/RateCustomerAdminChatCommand.cs
    sha1: 809f52738c20
  - path: Shared/SharedWeb/Helpers/UploadImages/UploadImage.cs
    sha1: 096208f448d6
  - path: Shared/TalabatkApplication/Services/GuestCustomerResolver/ResolveGuestCustomerService.cs
    sha1: 03427d4e316d
tags: [customer-ordering, support-and-chat, scenarios]
---
# Support & Chat — Scenario Catalog

> Four surfaces reach support from the customer app: the in-house **customer↔support** chat (with its
> bot), the **customer↔driver** chat tied to a live order, the **TawkTo** third-party widget, and the
> **Contact Us** forms. The bot mechanics live in `docs/CHAT_FEATURE_REFERENCE.md`; what this catalog adds
> is the API-surface behaviour that document does not cover — who is allowed to do what, and where the
> identity checks are missing.

## The one thing to know first

`CustomerAdminChatController` is **inconsistently scoped**, and the split is exactly along read/write
lines. Four actions resolve the caller's customer id and pass it down; three do not:

| Action | Passes a customer identity? | Consequence |
|---|---|---|
| `GetChatConfig` | yes, `TalabatkAPIs/Controllers/CustomerAdminChat/CustomerAdminChatController.cs:78` | scoped |
| `CanOpenOrderChat` | yes, and `[Authorize(Roles = "Customer")]` at `:97` | scoped |
| `History` | yes, `:174`, and the query compares the chat's `CustomerId` against it at `Shared/TalabatkApplication/Queries/GetAdminChatMessagesQuery/GetAdminChatMessagesQuery.cs:113` | scoped |
| `Escalate` | yes, `:281` | scoped |
| `SaveImage` | **no** — `:234-240` sends only the session id | see X4 |
| `EndChat` | **no** — `:254-260` sends only the session id | see X2 |
| `Rate` | **no** — `:304-310` sends only the session id | see X3 |

The read path is the one that *is* protected, which is the point: the ownership check exists in this
codebase (`GetAdminChatMessagesQuery.cs:111-114`), so its absence on the three write paths is an omission
rather than an unconsidered case. Those three are already recorded in
[[_idor-instances|_idor-instances.md]] under "Write-side, chat lifecycle" and "Write-side, chat rating".

`CustomerDeliveryChatController` splits the same way: `GenerateToken` and `ChangeOnlineValueForCustomer`
pass `seesionInfo.CusomerId` (`TalabatkAPIs/Controllers/CustomerDeliveryChat/CustomerDeliveryChatController.cs:46`, `:70`),
while `History` and `SaveImage` pass only an order id (`:91`, `:113`).

## Happy path

| # | Precondition | Action | Expected outcome | Rule / source |
|---|---|---|---|---|
| H1 | Customer opens support | `GET api/CustomerAdminChat/GetChatConfig` | Chat configuration for that customer, optionally for one order | `TalabatkAPIs/Controllers/CustomerAdminChat/CustomerAdminChatController.cs:67-93` |
| H2 | Config obtained | `POST api/CustomerAdminChat/GenerateToken` | A Centrifugo token so the app can connect | `TalabatkAPIs/Controllers/CustomerAdminChat/CustomerAdminChatController.cs:113-128` |
| H3 | Connected | messages flow over Centrifugo | Persisted by the proxy endpoint on this host | [[Customer Ordering/Ops & Infra/_knowledge-graph\|Ops & Infra]] |
| H4 | Customer reopens the app | `GET api/CustomerAdminChat/History?sessionId=` | Their own messages for that session | `TalabatkAPIs/Controllers/CustomerAdminChat/CustomerAdminChatController.cs:168-190` |
| H5 | Customer wants the list | `GET api/CustomerAdminChat/GetAllChats` | Their conversations; `Customer` role required | `TalabatkAPIs/Controllers/CustomerAdminChat/CustomerAdminChatController.cs:193-206` |
| H6 | Bot cannot help | `POST api/CustomerAdminChat/Escalate` | Handed to a human agent | `TalabatkAPIs/Controllers/CustomerAdminChat/CustomerAdminChatController.cs:272-295` |
| H7 | Conversation over | `POST api/CustomerAdminChat/EndChat` | Ended, and the admin browser is notified | `TalabatkAPIs/Controllers/CustomerAdminChat/CustomerAdminChatController.cs:248-269` |
| H8 | Chat ended | `POST api/CustomerAdminChat/Rate` | Rating and comment stored | `TalabatkAPIs/Controllers/CustomerAdminChat/CustomerAdminChatController.cs:298-315` |
| H9 | Order is on the way | `POST api/Order/GenerateToken?orderId=` | A token for the customer↔driver channel | `TalabatkAPIs/Controllers/CustomerDeliveryChat/CustomerDeliveryChatController.cs:36-50` |
| H10 | Driver chat open | `GET api/Order/History?orderId=` | The conversation for that order | `TalabatkAPIs/Controllers/CustomerDeliveryChat/CustomerDeliveryChatController.cs:82-92` |
| H11 | Customer prefers the widget | `GET api/TawkTo/GetChatWidgetLinks` | Widget link and config for the `Customer` chat type | `TalabatkAPIs/Controllers/TawkTo/TawkToController.cs:23-30` |
| H12 | Customer wants to complain in writing | `POST api/AddComplaintsAndSuggestions` | Stored, attributed to them if they hold the `Customer` role | `TalabatkAPIs/Controllers/ContactUs/ContactUsController.cs:83-100` |
| H13 | Someone wants to work with 8Orders | `POST api/addWorkUsAsDelivery` or `…AsRestaurant` | Recruitment lead stored | `TalabatkAPIs/Controllers/ContactUs/ContactUsController.cs:32-37`, `:57-62` |
| H14 | Customer wants a phone number | `GET api/GetContactUsNubers` | The published contact numbers | `TalabatkAPIs/Controllers/ContactUs/ContactUsController.cs:113-121` |

## Partial / incremental

| # | Precondition | Action | Expected outcome | Rule / source |
|---|---|---|---|---|
| P1 | Guest (no customer identity on the token) opens support | `GetChatConfig?guestDeviceId=` | Allowed — a provisional customer is resolved or created from the device id | `TalabatkAPIs/Controllers/CustomerAdminChat/CustomerAdminChatController.cs:59-62`, `Shared/TalabatkApplication/Services/GuestCustomerResolver/ResolveGuestCustomerService.cs` |
| P2 | Guest asks for **order** chat | `GetChatConfig?orderId=` | **Refused** — "Order chat is not available for guest users"; guests have no orders | `TalabatkAPIs/Controllers/CustomerAdminChat/CustomerAdminChatController.cs:75-76` |
| P3 | Guest wants to end or rate their own chat | `EndChat` / `Rate` | Works, because those actions never look at identity at all — the same gap that lets them act on anyone else's chat | `TalabatkAPIs/Controllers/CustomerAdminChat/CustomerAdminChatController.cs:252`, `:302` |
| P4 | Customer attaches a photo in support chat | `POST api/CustomerAdminChat/SaveImage` | An image is uploaded and a URL returned — the image is **not** attached to the chat by this call | `Shared/TalabatkApplication/Commands/SaveImageForCustomerAdminChatCommand/SaveImageForCustomerAdminChatCommand.cs:49-65` |
| P5 | Same, in driver chat | `POST api/Order/SaveImage` | Same, but the order must be `OnWay` first | `Shared/TalabatkApplication/Commands/SaveImageForCustomerDeliveryChatCommand/SaveImageForCustomerDeliveryChatCommand.cs:48-51` |
| P6 | Anonymous visitor submits a complaint | `POST api/AddComplaintsAndSuggestions` | Stored with `customerId = 0` — the role check degrades rather than rejects | `TalabatkAPIs/Controllers/ContactUs/ContactUsController.cs:90-94` |

## Negative / guard

| # | Precondition | Action | Expected outcome (rejection) | Rule / source |
|---|---|---|---|---|
| N1 | No token | any endpoint in this feature | 401 — every controller here carries a class-level `[Authorize]` | `TalabatkAPIs/Controllers/CustomerAdminChat/CustomerAdminChatController.cs:32`, `TalabatkAPIs/Controllers/CustomerDeliveryChat/CustomerDeliveryChatController.cs:20`, `TalabatkAPIs/Controllers/ContactUs/ContactUsController.cs:16`, `TalabatkAPIs/Controllers/TawkTo/TawkToController.cs:13` |
| N2 | Token without the `Customer` role | `GetAllChats` / `GetActiveChats` / `CanOpenOrderChat` | 403 — the only three role-gated actions | `TalabatkAPIs/Controllers/CustomerAdminChat/CustomerAdminChatController.cs:97`, `:195`, `:212` |
| N3 | Image over 3 MB, or a payload that is not a decodable image | attach it in either chat | **Rejected** — `Upload` caps `MaxImageSizeInBytes` and re-encodes through `Image.FromStream` | `Shared/SharedWeb/Helpers/UploadImages/UploadImage.cs:34`, `:40` |
| N4 | Order not `OnWay` | `POST api/Order/SaveImage` | **Rejected** — with a hard-coded Arabic message in the application layer | `Shared/TalabatkApplication/Commands/SaveImageForCustomerDeliveryChatCommand/SaveImageForCustomerDeliveryChatCommand.cs:48-51` · cf. #621 |
| N5 | Unknown order id | `POST api/Order/SaveImage` | **Rejected** — "Order Not Found" | `Shared/TalabatkApplication/Commands/SaveImageForCustomerDeliveryChatCommand/SaveImageForCustomerDeliveryChatCommand.cs:43-46` |
| N6 | Session id belonging to another customer | read that chat's history | **Rejected** — `chat.CustomerId` is compared against the caller's | `Shared/TalabatkApplication/Queries/GetAdminChatMessagesQuery/GetAdminChatMessagesQuery.cs:111-114` |
| N7 | Session id belonging to another customer | `EndChat`, `Rate`, `SaveImage` | **Accepted** — no ownership check exists on these paths | 🔴 [[_idor-instances\|_idor-instances.md]] |
| N8 | Order id belonging to another customer | `GET api/Order/History` | **Accepted** — the query filters on order id only | 🔴 `_conflicts.md` #364 |

## Returns / cancellation / reversal

| # | Precondition | Action | Expected outcome | Rule / source |
|---|---|---|---|---|
| R1 | Chat ended by the customer | `EndChat` | `EndedBy` is hard-coded to `"Customer"` on this host regardless of who actually called | `TalabatkAPIs/Controllers/CustomerAdminChat/CustomerAdminChatController.cs:257` |
| R2 | Chat ended | admin browser notified | Only when the command returns a value to notify about | `TalabatkAPIs/Controllers/CustomerAdminChat/CustomerAdminChatController.cs:265-267` |
| R3 | Rating submitted twice | `Rate` again | Last write wins; the command loads the chat by session id and sets the rate | `Shared/TalabatkApplication/Commands/RateCustomerAdminChatCommand/RateCustomerAdminChatCommand.cs:57` |
| R4 | Image uploaded in error | — | No delete path; the file stays on disk and the URL keeps resolving | `Shared/TalabatkApplication/Commands/SaveImageForCustomerAdminChatCommand/SaveImageForCustomerAdminChatCommand.cs:63` |
| R5 | Complaint submitted in error | — | No customer-facing withdrawal; it is handled in Admin | [[Admin/Order & Customer Administration/_knowledge-graph\|Order & Customer Administration]] |

## Integration (cross-side / cross-context)

| # | Precondition | Action | Expected outcome | Rule / source |
|---|---|---|---|---|
| I1 | Any message sent | Centrifugo delivers, then proxies to this host to persist | The proxy endpoint is unauthenticated — the other half of this feature's exposure | 🔴 `_conflicts.md` #616 · [[Customer Ordering/Ops & Infra/_knowledge-graph\|Ops & Infra]] |
| I2 | Customer↔support conversation | appears in Admin | The same conversation is served to agents | [[Admin/Chat Administration/_knowledge-graph\|Chat Administration]] |
| I3 | Driver↔support conversation | shares the storage and the query | `GetAdminChatMessagesQuery` handles both module types; the driver branch has **no** ownership predicate | 🔴 `_idor-instances.md` instance 5 · `Shared/TalabatkApplication/Queries/GetAdminChatMessagesQuery/GetAdminChatMessagesQuery.cs:60-79` |
| I4 | Chat escalated | agent picks it up | Escalation and agent availability are governed by `ChatSetting` | `Shared/TalabatkLogic/TalabatkModels/ChatSetting.cs` |
| I5 | Bot in FAQ mode | reads FAQ content | The same `FAQItem` rows the FAQ endpoint serves | `Shared/TalabatkLogic/TalabatkModels/FAQItem.cs` |
| I6 | Guest starts a chat | a provisional `Customer` row is created | The guest-cart mechanism, reused; creation is not rate-limited | 🟡 `_conflicts.md` #341 |
| I7 | TawkTo widget requested | third-party service | An external chat provider alongside the in-house one | `TalabatkAPIs/Controllers/TawkTo/TawkToController.cs:30` |

## Correctness and exposure scenarios — current behaviour

| # | Precondition | Action | Actual outcome today | Finding |
|---|---|---|---|---|
| X1 | Any authenticated customer, another customer's order id | `GET api/Order/History?orderId=N` | The full customer↔driver conversation for that order, including whatever personal detail was typed into it | 🔴 **#364** · `Shared/TalabatkApplication/Queries/GetCustomerDeliveryChatHistoryQuery/GetCustomerDeliveryChatHistoryQuery.cs:25` |
| X2 | Any authenticated caller, another customer's session id | `POST api/CustomerAdminChat/EndChat` | Their chat is ended with an attacker-supplied reason, and the admin browser is notified as though the customer did it | 🔴 `_idor-instances.md` · `Shared/TalabatkApplication/Commands/EndCustomerAdminChatCommand/EndCustomerAdminChatCommand.cs:42` |
| X3 | Same | `POST api/CustomerAdminChat/Rate` | An arbitrary score and comment are attached to someone else's conversation | 🔴 `_idor-instances.md` · `Shared/TalabatkApplication/Commands/RateCustomerAdminChatCommand/RateCustomerAdminChatCommand.cs:57` |
| X4 | Same | `POST api/CustomerAdminChat/SaveImage` | Accepted — though the image is not attached to the chat, so the practical effect is an upload, not an injection | ⚠️ `Shared/TalabatkApplication/Commands/SaveImageForCustomerAdminChatCommand/SaveImageForCustomerAdminChatCommand.cs:41-47` |
| X5 | Two customers attach a photo in the **same second** | both uploads succeed | Both get the **same URL**; the second write overwrites the first, so one customer's chat shows the other's photo. No attacker required | 🔴 **#628** · `Shared/SharedWeb/Helpers/UploadImages/UploadImage.cs:41-42` |
| X6 | A guest device id is known to someone else | any guest chat call with it | That guest's chat identity is assumed — the device id is the whole credential, and it travels in the **query string** | ⚠️ #341 · `TalabatkAPIs/Controllers/CustomerAdminChat/CustomerAdminChatController.cs:73` |
| X7 | `CustomerId` is null on a history request | `GetAdminChatMessagesQuery` | The ownership check is skipped — it is guarded by `request.CustomerId.HasValue`. The controller always supplies it, so this is latent, not live | ⚠️ `Shared/TalabatkApplication/Queries/GetAdminChatMessagesQuery/GetAdminChatMessagesQuery.cs:113` |
| X8 | Anyone | `POST api/centrifugo/publish` with a `CustomerAdmin_` channel | A message is inserted into a customer↔support conversation with **no credential at all** | 🔴 **#616** · [[Customer Ordering/Ops & Infra/_scenarios\|Ops & Infra scenarios]] |
| X9 | Chat image uploaded | file written | Stored under a second-resolution timestamp with no chat or customer component, in a folder shared by every conversation of that type | 🔴 **#628** |

## Open Questions

- [ ] Should `EndChat`, `Rate` and `SaveImage` take the resolved customer id, exactly as their four
      siblings in the same controller already do? The change is mechanical and the pattern is local.
- [ ] Should `GET api/Order/History` filter on the order's customer? #364 has been open long enough that
      the answer may be a deliberate one; nothing in the code says so.
- [ ] Chat image filenames: is there any reason not to use the chat id plus a random component?
- [ ] Is the guest `guestDeviceId` expected to be secret? The ADR that introduced it scoped it to carts
      and discount locking and does not discuss message confidentiality.
- [ ] Is TawkTo still in use alongside the in-house chat, and which customers see which?
- [ ] `EndedBy` is hard-coded to `"Customer"` — is there a path where this host ends a chat on behalf of
      someone else?
- [ ] Do complaints submitted with `customerId = 0` get triaged differently, or do they simply lose their
      attribution?
