---
id: 8orders/customer-ordering/support-and-chat/support-and-chat-technical
note_type: technical
context: Customer Ordering
feature: Support & Chat
group: Support-and-Chat
covers: [ChatMessage, ChatSetting, ComplaintsAndSuggestions, CustomerAdminChat, CustomerAdminChatMessage, CustomerDeliveryChat, CustomerDeliveryChatMessage]
sources:
  - path: AdminUi/Controllers/Complaints/ComplaintsController.cs
    sha1: b7b732003697
  - path: AdminUi/Startup.cs
    sha1: 9b3cc183bae1
  - path: Shared/TalabatkApplication/Commands/GenerateCentrifugalTokenCommand/GenerateCentrifugalTokenCommand.cs
    sha1: 0a990ffc7bf2
  - path: Shared/TalabatkApplication/Commands/GenerateCustomerAdminTokenCommand/GenerateCustomerAdminTokenCommand.cs
    sha1: 942c24ad47d0
  - path: Shared/TalabatkApplication/Commands/HandleDeliveryManAdminProxyMessagesCommand/HandleDeliveryManAdminProxyMessagesCommand.cs
    sha1: 3d5343dc745d
  - path: Shared/TalabatkApplication/Commands/HandleProxyMessagesCommand/HandleProxyMessagesCommand.cs
    sha1: 885fade5d9f8
  - path: Shared/TalabatkApplication/Commands/SendChatMessageCommand/SendChatMessageCommand.cs
    sha1: 9df3a8d853ea
  - path: Shared/TalabatkApplication/Commands/UpdateUserChatFlagsCommand/UpdateUserChatFlagsCommand.cs
    sha1: 00169b1eb106
  - path: Shared/TalabatkApplication/Feature/Complaints/Commands/SaveOrderComplaintCommand.cs
    sha1: 3288dfbfcf94
  - path: Shared/TalabatkApplication/Helper/ChatAssignment/ChatReassignmentJobEnqueue.cs
    sha1: 7230d1c9e36f
  - path: Shared/TalabatkApplication/Helper/CustomerAdminChatBot/CustomerAdminChatBotOrchestrator.cs
    sha1: b2f65ea44a4e
  - path: Shared/TalabatkApplication/Queries/GetAdminChatMessagesQuery/GetAdminChatMessagesQuery.cs
    sha1: 89e17484040c
  - path: Shared/TalabatkApplication/Queries/GetAllComplaintsAndSuggestionsQuery/GetAllComplaintsAndSuggestionsQuery.cs
    sha1: b509f0a1de1f
  - path: Shared/TalabatkApplication/Queries/GetCustomerAdminChatConfigQuery/GetCustomerAdminChatConfigQuery.cs
    sha1: e800af863c7e
  - path: Shared/TalabatkApplication/Services/CustomerAdminChatBotServices/FAQBotServices/CustomerAdminFaqBotService.cs
    sha1: a2bf917c7112
  - path: Shared/TalabatkData/ChatContext/ChatContext.cs
    sha1: c4745ce3f24a
  - path: Shared/TalabatkData/ChatContextV2/ChatContextV2.CustomerAdminChat.cs
    sha1: 3ea3d8f655e6
  - path: Shared/TalabatkData/ChatContextV2/ChatContextV2.DeliveryManAdminChat.cs
    sha1: 2cbe644cd3a6
  - path: Shared/TalabatkData/ChatContextV2/ChatContextV2.cs
    sha1: 1f4b48ca3abb
  - path: Shared/TalabatkLogic/OrderComplaintAggregate/OrderComplaint.cs
    sha1: e2151a2ca10b
  - path: Shared/TalabatkLogic/TalabatkModels/CustomerAdminChat.cs
    sha1: f773c5c9ea97
  - path: TalabatkAPIs/Controllers/ContactUs/ContactUsController.cs
    sha1: b82911562a40
  - path: TalabatkAPIs/Controllers/CustomerDeliveryChat/CustomerDeliveryChatController.cs
    sha1: b2971777d747
  - path: TalabatkAPIs/Helper/Extension/DatabaseConfigurations.cs
    sha1: a1f67f7c6a12
  - path: TalabatkDelivery/Controllers/Apis/CentrifugoController.cs
    sha1: 31932d0044dd
  - path: TalabatkDelivery/Controllers/Apis/DeliveryManAdminChatController.cs
    sha1: 0438b5c7a06f
last_updated: 2026-08-23
tags: [flow, technical]
---
# Support & Chat — Technical

> Bridges [[_knowledge-graph|Support & Chat bridge note]] (entity-level pointer to
> `docs/CHAT_FEATURE_REFERENCE.md`), [[Customer.technical|Customer]],
> [[DeliveryMen.technical|DeliveryMen]],
> [[Order.technical|Order]], and
> [[Permission.technical|Permission]] (authorization-scope family,
> `_conflicts.md` **#404**). This note traces the *process* — trigger through completion — for five
> related sub-flows: (A) customer↔driver in-trip chat, (B) customer↔support chat with its bot layer,
> (C) driver↔support chat, (D) agent-offline reassignment, (E) complaints. Entity field-level detail
> (message shapes, DTOs) stays in the bridged reference doc; this note does not re-list it.

## Trigger

- `POST api/Order/GenerateToken` (`TalabatkAPIs/Controllers/CustomerDeliveryChat/CustomerDeliveryChatController.cs:41`) — customer opens the in-trip chat with their driver.
- `POST api/DeliveryManAdminChat/GenerateToken`-equivalent on the delivery app is actually the same order channel from the driver side, via `TalabatkDelivery`'s own chat controller (not opened in this pass; token issuance is symmetric through the same `GenerateCentrifugalTokenCommand`, `IsDeliveryMan=true`).
- `GET/POST api/CustomerAdminChat/GetChatConfig`, `GenerateToken` (`TalabatkAPIs/Controllers/CustomerAdminChat/CustomerAdminChatController.cs:70,117`) — customer opens/resumes a support conversation.
- `POST api/DeliveryManAdminChat/GenerateToken` (`TalabatkDelivery/Controllers/Apis/DeliveryManAdminChatController.cs:62`) — driver opens a support conversation.
- `POST api/centrifugo/publish` on both `TalabatkAPIs` and `TalabatkDelivery` (`CentrifugoController.cs`) — Centrifugo's own inbound proxy webhook, called on every message a connected client publishes; this is where messages are actually persisted, not on the token-issuance routes.
- `UpdateUserChatFlagsCommand`, `UpdateUserInRoundCommand`, `UpdateUserShiftCommand` — an admin going off-shift or turning off a chat-module flag while holding open chats (`Shared/TalabatkApplication/Commands/UpdateUserChatFlagsCommand/UpdateUserChatFlagsCommand.cs:65-80`).
- `POST api/AddComplaintsAndSuggestions` (`TalabatkAPIs/Controllers/ContactUs/ContactUsController.cs:83-108`) — customer/visitor complaint or suggestion intake.
- `POST api/Complaints/SaveOrderComplaint` (`AdminUi/Controllers/Complaints/ComplaintsController.cs:126-136`) — staff logs a formal complaint against a restaurant for a specific order.

## Step-by-step

### A. Customer↔Driver in-trip chat (order chat, SQL-backed)

1. `GenerateCentrifugalTokenCommand.Handle` loads the `Order` by id (`GenerateCentrifugalTokenCommand.cs:63-64`) and validates: order exists, `StatusId == OnWay` (`:251`), and — the driver-side check at `:255-257` and the **customer-side check at `:267-269`** — the caller owns the order. The customer-side check is the fix for **`#421`**: previously the clause at `:255` was gated on `isDeliveryMan`, so a customer caller fell straight through to success with only the `OnWay` constraint standing between them and a token for any in-flight order. `CustomerDeliveryChatController.cs:41-50` is the live customer-facing route; the code comment at `:259-266` documents the fix in place.
2. `GetOrCreateCustomerDeliveryChatAsync` (`:177-239`) fetches or creates a `CustomerDeliveryChat` row keyed by `OrderId`, requiring both `CustomerId` and `DeliveryManId` to be set on the order (`:192-201`).
3. **This chat is SQL Server, not Cassandra.** The handler depends on `IChatContext` (`GenerateCentrifugalTokenCommand.cs:28`), which DI binds to `ChatContext : DbContext` against connection string `ChatConnectionString` — a database separate from both the main app DB and Cassandra (`TalabatkAPIs/Helper/Extension/DatabaseConfigurations.cs:35-46`; tables `TA_CustomerDeliveryChat`/`TA_CustomerDeliveryChatMessage`, `Shared/TalabatkData/ChatContext/ChatContext.cs:19-22,32-46`). Centrifugo connect tokens (`CustomerToken`/`DeliveryManToken`) are generated once and cached on this row (`:99-139`).
4. **Sending a message** happens out-of-band from any of these controllers: Centrifugo calls back to `POST api/centrifugo/publish` with the published payload. On `TalabatkAPIs`, any channel not prefixed `DeliveryManAdmin_`/`CustomerAdmin_` falls through to `HandleProxyMessagesCommand` (`TalabatkAPIs/Controllers/CentrifugoController.cs:88-97`), which enqueues a Hangfire `alpha`-queue job (`HandleProxyMessagesCommand.cs:47-51`) rather than handling synchronously. That job re-validates the order is `OnWay` (`:99-103`), appends the message to the SQL-backed chat (`:112-137`), and pushes a mobile notification to whichever side didn't send it, gated by `should_send_notification` and device-token presence (`:150-424`).
5. **`TalabatkDelivery`'s own `api/centrifugo/publish` only implements the `DeliveryManAdmin_` branch** (`TalabatkDelivery/Controllers/Apis/CentrifugoController.cs:19-40`) — there is no branch there for the customer↔driver order-chat channel. **`#40`** flags this as an unconfirmed gap: not established whether Centrifugo's proxy config actually targets this host for that channel, or whether `TalabatkAPIs`'s complete implementation (which does have the fallback branch, step 4) is the one actually wired up. Not traced further in this pass — see Open Questions.
6. **A superseded, dead code path exists**: `SendChatMessageCommand` (`Shared/TalabatkApplication/Commands/SendChatMessageCommand/SendChatMessageCommand.cs`) writes to a wholly different table (`ctx.OrderChats`, the main SQL context) and is never constructed or sent from any controller in the repository (verified by repo-wide search). It is not part of the live flow.
7. `ChangeIsOnlineValueForCustomerChatCommand`/`...ForDeliverChatCommand` flip an online/typing-presence flag on the same SQL row, via the SQL-backed `IChatContext` (`ChangeIsOnlineValueForCustomerChatCommand.cs:18-19,40-44`), whose `GetCustomerDeliveryChatByOrderId` filters on `OrderId` alone (`ChatContext.cs:84-89`; the finding below cites `ChatContextV2.cs:45-50` for the equivalent shape — that is Cassandra's near-identical method of the same name, not the one this command actually calls, a citation slip in the source register worth flagging rather than repeating uncorrected). The customer-side command validates order status but never checks `order.CustomerId` against the caller before flipping the flag for the `OrderId` supplied — a write-side IDOR instance in [[_idor-instances|_idor-instances.md]] ("Write-side, chat flag"); its delivery-man sibling performs the equivalent check correctly.

### B. Customer↔Support chat (Cassandra-backed, bot-fronted)

1. `GET api/CustomerAdminChat/GetChatConfig` (optional pre-check) resolves working hours and available bot cards without creating anything (`GetCustomerAdminChatConfigQuery.cs:41-71`).
2. `POST api/CustomerAdminChat/GenerateToken` → `GenerateCustomerAdminTokenCommand.Handle` (`:82-217`): resolves the effective customer (real or guest, via `IResolveGuestCustomerService`, `CustomerAdminChatController.cs:59-62`), validates working hours (`:100-108`), and — for an order-scoped chat — checks `order.CustomerId == request.CustomerId` (`:236-237`), correctly, unlike the driver-chat command in A1 before its fix.
3. `ShouldUseBotRoutingAsync` (`CustomerAdminChatBotOrchestrator.cs:54-73`) reads `ChatSetting` and decides whether any bot entry card applies; if none do, the chat routes straight to a human (same as flow C).
4. `GetOrCreateChatAsync` (`GenerateCustomerAdminTokenCommand.cs:256-351`): reuses an active chat for the same customer+order if one exists; otherwise, when bot routing is **off**, immediately calls `ChatAssignmentService.AssignChatToAdminAsync` (sticky-admin-first, then least-loaded eligible admin — `ChatAssignmentService.cs:27-96,98-148,150-180`) and fails with `Chat_NoAvailableAdmin` if nobody is eligible.
5. **Persistence is Cassandra**, via `IChatContextV2`/`ChatContextV2` (`ChatContextV2.CustomerAdminChat.cs`), tables `customer_admin_chat` and `customer_admin_chat_messages`. New chats are inserted (`AddCustomerAdminChatAsync`, `:371-395`); most subsequent reads use `ALLOW FILTERING` (e.g. `:50-51,88-89,115-116`) since the table's primary lookup key is `session_id`, not `customer_id`/`admin_user_id`/`order_id`.
6. If bot routing applies and the chat is new, `CustomerAdminChatBotOrchestrator.InitializeSessionAsync` runs (`:75-113`): marks the chat `IsBotHandled` (`CustomerAdminChat.cs:95-99`), publishes a disclosure message, a welcome message, then `SendBotMenuAsync` (`:156-242`) which either auto-starts the order-status bot (if the chat is order-scoped, that bot is enabled, and the order is active) or publishes entry-option cards (FAQ / order status / talk to a person, depending on `ChatSetting`).
7. **Ongoing messages** arrive via `POST api/centrifugo/publish` → `HandleCustomerAdminProxyMessagesCommand.Handle` (`:88-117`). A customer message is processed **synchronously**, before Centrifugo's publish is acknowledged (`:104-110`); an admin message is enqueued to the Hangfire `alpha` queue (`:111-113`) — asymmetric by design, not a bug, but worth knowing when debugging message-ordering complaints.
8. Inside `HandleMessages` (`:257-485`): rejects a message from an admin token that isn't the chat's assigned admin (`:296-309`), claims a waiting chat for whichever admin/bot-assignment logic applies (`TryAssignAdminIfWaitingAsync`, `:589-624` — explicitly refuses to auto-assign a human while the bot still owns the chat, `:606-607`), re-checks admin ownership again just before persisting to reduce a reassignment race (`:365-387`), appends the message (`chat.AddNewMessage`, `CustomerAdminChat.cs:224-258`), and tracks first-response time (`:419-438`).
9. A plain customer text message (not a button selection) triggers `ProcessCustomerKeywordAsync` on the `alpha` queue (enqueued at `:482-484`, method at `:487-506`), which only acts if `CustomerAdminFaqBotService.CanHandleKeyword` is true (`CustomerAdminFaqBotService.cs:46-50`: not escalated, bot-handled, and either in FAQ phase or FAQ mode).
10. **FAQ search** (`CustomerAdminFaqBotService.SearchKeywordAsync`, `:129-182`): if agent-escalation-on-FAQ-exhaustion is enabled and the chat has used `MaxFaqRounds` (default 3, `ChatSetting.cs:16`) search rounds, publishes an escalation prompt with a "Contact Agent" button instead of searching further (`:145-157`). Otherwise searches a bilingual FAQ index (`FaqBilingualSearchHelper.SearchMergedAsync`, internals not opened) and offers up to 3 matches.
11. **Handoff to a human**, from any trigger (explicit "talk to a person," FAQ exhaustion, order-status bot failure): `CustomerAdminChatHandoffService.HandoffToHumanAgentAsync` (`:72-204`). Marks the chat escalated (`chat.MarkEscalated`, `CustomerAdminChat.cs:148-164`), assigns an admin via the same `ChatAssignmentService` if none is set (`:109-115`), publishes a "transferred to agent" status message and (if newly assigned) an "agent joined" message naming the admin, and notifies the admin's browser session (`INotifyAdminInBrowser.NotifyNewCustomerChatAsync`). If no admin is available at all, publishes an "agents busy" message instead and leaves the chat unassigned (`HandleNoAgentsAvailableAsync`, `:206-225`).
12. **Read receipts**: `MarkCustomerAdminChatMessagesAsReadAsync` (`ChatContextV2.CustomerAdminChat.cs:330-369`) batch-updates `is_read` on the relevant side's unread messages and stamps `CustomerViewAt`/`AdminViewAt`.
13. **Ending the chat**: `POST api/CustomerAdminChat/EndChat` → `EndCustomerAdminChatCommand.Handle` (`:38-71`): session must exist and not already be ended (`:42-47`); if order-scoped, refuses to end while `CustomerAdminOrderChatLifecycle.IsOrderInFlightForOrderChat` is true (`:49-60`). Delegates to `CustomerAdminChatEndService.EndChatAsync` (`:64-102`), which computes total chat duration from first/last message timestamps, marks the chat ended, syncs chat/bot-performance reports, and (if `notifyCustomer`) pushes an ended notification — including whether to show a rating prompt, gated on `ChatSetting.EnableCustomerRating` **and** the chat having had an assigned admin (`:193-212`). **`EndCustomerAdminChatCommand` takes no `CustomerId` at all** and resolves purely by `SessionId` — a write-side IDOR instance in [[_idor-instances|_idor-instances.md]] ("Write-side, chat lifecycle"); its sibling `EscalateCustomerAdminChatCommand` does check ownership.
14. **Rating**: `POST api/CustomerAdminChat/Rate` → `RateCustomerAdminChatCommand.Handle` (`:45-70`): requires `ChatSetting.EnableCustomerRating`, the session to exist, and the chat to already be ended; then `chat.SetRate(...)` (silently no-ops outside 1-5, `CustomerAdminChat.cs:316-324`). **The command declares no `CustomerId` field at all** (`:15-20`) and loads the chat by `SessionId` alone (`:56-61`) — a write-side IDOR instance in the same register ("Write-side, chat rating"), shared with the driver-side `RateDeliveryManAdminChatCommand`.

### C. Driver↔Support chat (Cassandra-backed, no bot)

1. `POST api/DeliveryManAdminChat/GenerateToken` → `GenerateDeliveryManAdminTokenCommand.Handle` (`:72-166`): validates the driver exists and (if order-scoped) that `order.DeliveryManId == request.DeliveryManId` (`:185-186`), then working hours.
2. `GetOrCreateChatAsync` (`:196-228`) reuses an active chat or, for a new one, **always** calls `ChatAssignmentService.AssignChatToAdminAsync` — there is no bot-routing branch here, so with no eligible/available admin the whole request fails with `Chat_NoAvailableAdmin` (`:220-223`) rather than falling back to any automated placeholder.
3. Persistence is Cassandra tables `delivery_man_admin_chat`/`delivery_man_admin_chat_messages` (`ChatContextV2.DeliveryManAdminChat.cs`), structurally identical to flow B's tables (same `ALLOW FILTERING` pattern on non-session-id lookups).
4. **The session-id lookup used for chat history has no `delivery_man_id` predicate** (`ChatContextV2.DeliveryManAdminChat.cs:35`: `SELECT * FROM delivery_man_admin_chat WHERE session_id = ?`), and `GetAdminChatMessagesQuery` never consults `request.DeliveryManId` (`GetAdminChatMessagesQuery.cs:56-85`) — **`#404`**, instance 5 in [[_idor-instances|_idor-instances.md]]: another driver's admin-chat history is readable given the session id, on a controller gated only by `[Authorize(JwtBearer)]` with no role check (`DeliveryManAdminChatController.cs:100-119`).
5. Ongoing messages route through `HandleDeliveryManAdminProxyMessagesCommand` (`Shared/TalabatkApplication/Commands/HandleDeliveryManAdminProxyMessagesCommand/HandleDeliveryManAdminProxyMessagesCommand.cs`, 281 lines) — always via the Hangfire `alpha` queue (no synchronous customer-analog path, since there is no bot to race against). Internals not traced to the same line-level depth as flow B's `HandleCustomerAdminProxyMessagesCommand` in this pass; the shape (persist message, notify, first-response tracking) is inferred to mirror it from shared dependencies (`IChatAssignmentService`, `IChatReportWriter`), not independently verified.
6. `MarkChatMessagesAsReadCommand` (driver/admin side) captures a caller-supplied `UserId` that `Handle` never reads (`MarkChatMessagesAsReadCommand.cs:9-13,33`) — reaches `IChatContextV2.MarkMessagesAsReadAsync` with no admin-scoping anywhere in the call chain, a `likely`-severity write-side instance in [[_idor-instances|_idor-instances.md]] ("Write-side, mark-as-read"); contrast the correctly-scoped `GetActiveChats` (`AgentId = _info.UserId`).
7. Ending (`EndDeliveryManAdminChatCommand`) takes no `DeliveryManId` and resolves by `SessionId` alone — the same "Write-side, chat lifecycle" instance as flow B step 13, driver-side sibling.

### D. Agent goes offline → chat reassignment

1. Trigger: `UpdateUserChatFlagsCommand.Handle` captures the pre-update flag values (`:45-46`), saves the user row, then detects an **on→off** transition for `ChatForCustomer`/`ChatForDelivery` and enqueues per module accordingly (`:65-80`), or the equivalent transitions in `UpdateUserInRoundCommand`/`UpdateUserShiftCommand` (not opened in this pass, same enqueue call confirmed by grep).
2. `ChatReassignmentJobEnqueue.EnqueueModule`/`EnqueueAllModules` (`ChatReassignmentJobEnqueue.cs:13-42`) enqueues a Hangfire job on the **`admin`** queue against `IChatReassignmentService`.
3. `ChatReassignmentService.ReassignActiveChatsOnModuleUnavailableAsync` (`:86-177`) loads every active chat still assigned to the outgoing admin for that module (`GetAllCustomerAdminChatsByAdminIdAsync`/`GetActiveDeliveryManAdminChatsByAdminIdAsync`) and, per chat, calls `TryReassignCustomerChatAsync`/`TryReassignDeliveryManChatAsync` (`:186-267`, `:269-350`).
4. Each attempt asks `ChatAssignmentService.AssignChatToAdminAsync` for a peer, **excluding** the outgoing admin and requiring availability (`:201-206`). No peer available → the chat is **kept** on the (now-unavailable) original admin (`:208-216`) — it is not forcibly unassigned. A peer found → `chat.AssignAdmin(...)`, persisted, both admins notified (old: unassigned; new: new-chat), an "agent joined" message published to the customer/driver, and the order-chat-assignment comment recorded — each of these three side effects independently try/caught so one failing does not roll back the reassignment itself (`:221-257`, `:306-340`).

### E. Complaints and suggestions

1. **Customer/visitor intake**: `POST api/AddComplaintsAndSuggestions` (`TalabatkAPIs/Controllers/ContactUs/ContactUsController.cs:83-108`, class-level `[Authorize(JwtBearer)]`) attaches `CustomerId` only if the caller holds the `Customer` role, else `0` (`:90-93`) — so an authenticated non-customer caller (e.g. a driver token) can submit with `CustomerId=0`. `AddComplaintsAndSuggestionsCommand.Handle` (`:32-54`) does no validation beyond what `ComplaintsAndSuggestions.Instance` enforces (not opened in this pass) and inserts directly.
2. **Staff review**: `GetAllComplaintsAndSuggestionsQuery` left-joins `Customer` (anticipating a non-matching `CustomerId`, e.g. the `0` from step 1) but then dereferences the joined customer's `FirstName`/`PhoneNumber` unconditionally — **`#131`**, a confirmed crash on exactly the row shape step 1 can produce (`GetAllComplaintsAndSuggestionsQuery.cs:34-47`).
3. **Staff-initiated order complaints** (a separate entity, `OrderComplaint`, feeding merchant KPI scoring — see [[OrderComplaint|OrderComplaint]]): `POST api/Complaints/SaveOrderComplaint` (`AdminUi/Controllers/Complaints/ComplaintsController.cs:121-136`). **The entire controller — all of `Sections`, `GetReasonById`, `AddNewReason`, `EditReason`, `DeleteReason`, `SaveOrderComplaint`, `GetOrderComplaints`, `KpiScoreConfiguration`, `SaveKpiScoreConfiguration` — carries no `[Authorize]` of any kind**, confirmed against `BaseController` (no attribute) and `AdminUi/Startup.cs` (no fallback policy) — **`#439`**: every action, including the state-changing ones, is reachable with no token at all.
4. `OrderComplaint.Create` performs zero business validation on `orderId`/`orderComplaintReasonId`/any field (**`#29`**, `OrderComplaint.cs:29-58`), and `SaveOrderComplaintCommand.GetOutgoingRestaurantDataAsync` has two confirmed null-reference/data-mismatch bugs on the "auto-discover a restaurant" path (**`#198`**, `SaveOrderComplaintCommand.cs:430-445`) — both reachable by the same unauthenticated caller from step 3.

## Data written

1. **`TA_CustomerDeliveryChat` / `TA_CustomerDeliveryChatMessage`** (SQL Server, `ChatConnectionString` DB) — order-chat row and messages (flow A steps 2-4).
2. **`customer_admin_chat` / `customer_admin_chat_messages`** (Cassandra) — customer-support chat row and messages, including all bot-authored messages (flow B).
3. **`delivery_man_admin_chat` / `delivery_man_admin_chat_messages`** (Cassandra) — driver-support chat row and messages (flow C).
4. **`ChatSetting`** (SQL, main app DB) — read everywhere in flows B/C/D as the single config row; written only via `UpdateChatSettingsCommand` (not traced in this pass).
5. **`ComplaintsAndSuggestions`** (SQL, main app DB) — one row per customer/visitor submission (flow E1).
6. **`OrderComplaint`** (SQL, main app DB) — one row per staff-logged restaurant complaint, feeding merchant KPI scoring (flow E3-4).
7. Chat/bot reporting side tables via `IChatReportWriter.SyncChatEventAsync` and `IBotPerformanceReportWriter` (created, first-response, ended, rated events; FAQ usage and containment outcomes) — internals not opened in this pass, referenced by call site only.

## External calls

- **Centrifugo** — connect-token generation (`ICentrifugoTokenGenerator.GenerateConnectToken`, all four token commands), the real-time pub/sub relay itself (client-to-client, outside application code), and the inbound "publish proxy" webhook (`POST api/centrifugo/publish`) that gates/observes every message and can override the broadcast payload (`HandleCustomerAdminProxyMessagesCommand`'s `BroadcastOverride`, used for button-selection echo).
- **Hangfire** — `alpha` queue for message persistence/notification (flows A, B, C), `admin` queue for reassignment jobs (flow D).
- **Push notifications** (`IAndroidGCMPushNotification.PushNotification`) — new message (both sides, flows A/B), chat-ended (flow B).
- **FAQ search** (`IFaqSearchService` via `FaqBilingualSearchHelper`) — bilingual keyword matching, internals not opened.
- **Working-hours validation** (`IWorkingHoursValidationService.ValidateChatAllowedAsync`) — gates chat opening in flows B and C, internals not opened.

## Failure modes

| Step | Trigger | Caller sees / effect | Finding |
|------|---------|------------------------|---------|
| A1 | Customer requests a token for another customer's on-way order | **Fixed**: now rejected (`Chat_DoesNotBelongToCustomer`) | **#421** |
| A5 | `TalabatkDelivery`'s centrifugo webhook has no branch for the order-chat channel | Unconfirmed — whether this host is even the configured proxy target for that channel is untraced | **#40** |
| A7 | Caller supplies another customer's `OrderId` to the online-flag toggle | Flag flipped on someone else's order chat | Write-side IDOR, `_idor-instances.md` |
| B11 | No admin eligible/available at handoff time | "Agents busy" message published, chat stays unassigned (not a hard failure) | — |
| B13 | Caller ends another customer's support chat | No ownership check — succeeds | Write-side IDOR ("chat lifecycle"), `_idor-instances.md` |
| B14 | Caller rates another customer's ended chat | No ownership check — succeeds; command has no `CustomerId` field | Write-side IDOR ("chat rating"), `_idor-instances.md` |
| C1/C2 | No admin eligible/available, driver-support chat (no bot fallback) | `Chat_NoAvailableAdmin` — hard failure, no automated placeholder | — |
| C4 | Any authenticated driver reads another driver's chat history by session id | Full message history disclosed | **#404** instance 5, `_idor-instances.md` |
| C6 | Mark-as-read called with someone else's `SessionId`/`IsAdmin` | Messages marked read with no admin-scoping check | Write-side IDOR ("mark-as-read", `likely`), `_idor-instances.md` |
| E1→E2 | Non-customer caller submits with `CustomerId=0`, staff later lists complaints | List query crashes on the unresolved join | **#131** |
| E3 | Any caller, no token, hits any of 9 actions incl. 5 POSTs | Full anonymous read/write over order complaints and KPI config | **#439** |
| E4 | `SaveOrderComplaint` with `selectedRestaurantId == 0` or a mismatched explicit id | `NullReferenceException`, or restaurant/menu-item/price mismatch persisted | **#198**; entity itself accepts any input, **#29** |

## Open Questions

- Which host's Centrifugo proxy configuration actually receives the customer↔driver order-chat
  channel's publish events — `TalabatkAPIs` has the complete branch, `TalabatkDelivery` does not (step
  A5, **#40**). Not traced in this pass; this is an infrastructure/Centrifugo-config question, not
  something resolvable by reading application code alone.
- `CustomerAdminOrderStatusBotService` / `ChatBotExpediteService` internals (the order-status bot's
  auto-start, expedite-attempt cooldown/limit, and "robocall failed" escalation logic) — not traced in
  this pass beyond their existence and the settings that gate them (`ChatSetting.Expedite*` fields).
- `HandleDeliveryManAdminProxyMessagesCommand` internals (flow C step 5) were not read at the same
  line-level depth as the customer-admin equivalent; its behavior is inferred from shared dependencies,
  not independently verified.
- `GenerateAdminChatTokenCommand`/`GenerateAdminCustomerChatTokenCommand` — separate, lighter token
  generators used by the admin browser console (`AdminTokenPrefix` subjects), distinct from the
  per-chat `AdminToken` already issued inside flows B/C. How/when the admin console calls these
  relative to opening a specific chat — not traced in this pass.
- `IChatReportWriter` and `IBotPerformanceReportWriter` internals (what tables back the reporting
  events referenced throughout flows B-D) — not opened; referenced by call site only.
- `FaqBilingualSearchHelper`/`IFaqSearchService` matching algorithm — not traced.
- `ComplaintsAndSuggestions.Instance`'s own validation (if any) — not opened; only the command that
  calls it was read.
- Whether `TalabatkRestaurants` has its own admin↔merchant chat surface analogous to flows B/C — out
  of scope for this pass; the existing bridge note's table lists "Admin↔Merchant" as part of the
  Centrifugo chat family but it was not independently traced here.
- TawkTo widget and the generic FAQ content controller are intentionally out of scope, per the existing
  [[_overview|_overview.md]] bridge note.
