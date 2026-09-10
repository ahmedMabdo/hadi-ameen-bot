---
id: 8orders/admin/chat-administration/scenarios
title: Chat Administration — Scenario Catalog
note_type: scenarios
context: Admin
feature: Chat Administration
audience: Business · QA · Developer
last_updated: 2026-08-23
sources:
  - path: AdminUi/Controllers/ChatDashboard/ChatDashboardController.cs
    sha1: 14ee1506ee9f
  - path: AdminUi/Controllers/ChatSettings/ChatSettingsController.cs
    sha1: 37c0eafef948
  - path: AdminUi/Controllers/ChatReports/ChatReportsController.cs
    sha1: 0a5c8e0fd27c
  - path: Shared/TalabatkData/ChatContext/ChatContext.cs
    sha1: c4745ce3f24a
  - path: Shared/TalabatkData/Cassandra/ChatReportRepository.cs
    sha1: 540820122447
tags: [admin, chat-administration, scenarios]
---
# Chat Administration — Scenario Catalog

> Three duplicated chat models, two realtime transports, three storage technologies. Most rows below
> exist in three variants in reality — where that matters, the row says so.

## Happy path

| # | Precondition | Action | Expected outcome | Rule / source |
|---|---|---|---|---|
| H1 | Customer starts a support chat | conversation opens | Appears on the support dashboard in real time | `AdminUi/Controllers/ChatDashboard/ChatDashboardController.cs`; `_integrations.md` row 2 |
| H2 | Staff member picks it up | reply sent | Delivered to the customer app instantly | `_integrations.md` row 2 |
| H3 | Driver starts a support chat | conversation opens | Same dashboard, **different underlying model** | see the three-pair table in the technical note |
| H4 | Customer and driver coordinate a delivery | messages exchanged | Third model again; realtime to the driver via Centrifugo | [[Delivery/Delivery Support & Chat/_knowledge-graph\|Delivery Support & Chat]] |
| H5 | Conversation ends | customer rates it | Rating stored against the conversation | `AdminUi/Controllers/ChatRateController/ChatRateController.cs` |
| H6 | Management wants volumes | open chat reports | Read from the Cassandra reporting store, not the operational tables | `Shared/TalabatkData/Cassandra/ChatReportRepository.cs` |
| H7 | Operations change chat behaviour | update settings | Applied to the configured chat kind | `AdminUi/Controllers/ChatSettings/ChatSettingsController.cs` |
| H8 | Customer sends a contact-us message | message stored | Appears for support to work | `AdminUi/Controllers/ContactUsAdmin/ContactUsController.cs` |

## Partial / incremental

| # | Precondition | Action | Expected outcome | Rule / source |
|---|---|---|---|---|
| P1 | Bot handles the opening exchange | escalation | A human takes over the same conversation; bot performance recorded separately | `Shared/TalabatkData/Cassandra/BotPerformanceReportRepository.cs` |
| P2 | Conversation ages | archive migration | History moved into Cassandra by a job | `_conflicts.md` #615 (who can trigger it) |
| P3 | A chat change is requested | implement it | **Three** implementations must change, or the pairs diverge | technical note, three-pair table |
| P4 | An order and its chat both change | single operation | **Not transactional** — `TalabatkContext` and `ChatContext` are separate contexts | `Shared/TalabatkData/ChatContext/ChatContext.cs` |

## Negative / guard

| # | Precondition | Action | Expected outcome (rejection) | Rule / source |
|---|---|---|---|---|
| N1 | Not signed in | any Admin chat screen | 401 | class-level attributes on the chat controllers |
| N2 | Signed in, no particular role | most chat screens | **Allowed** — most Admin controllers carry no `[Permission]` | ⚠️ #617/#618 |
| N3 | Error path in chat | error returned | Uses a **localised key** rather than an inline message — one of only two such classes in the codebase | `Shared/TalabatkApplication/ChatErrorKeys.cs` |
| N4 | Cassandra unavailable | open chat reports | Reporting fails; live conversations are unaffected because they are in SQL Server | `Shared/TalabatkData/Cassandra/ChatReportRepository.cs` |

## Returns / cancellation / reversal

| # | Precondition | Action | Expected outcome | Rule / source |
|---|---|---|---|---|
| R1 | Message sent in error by staff | — | No delete or edit path observed in the Admin chat controllers | `AdminUi/Controllers/CustomerAdminChat/CustomerAdminChatController.cs` |
| R2 | Conversation closed too early | a new message arrives | **Reopens automatically** — `SendChatMessageCommand` calls `OrderChat.MakeChatActive()`, so there is no explicit reopen action to find | `Shared/TalabatkApplication/Commands/SendChatMessageCommand/SendChatMessageCommand.cs:92`, `Shared/TalabatkLogic/TalabatkModels/OrderChat.cs:72` |
| R2b | Order status changes | the chat closes | `ChangeOrderStatusCommand` calls `MakeChatClosed()`, so closure is a side effect of the order moving on, not an agent action | `Shared/TalabatkApplication/Commands/ChangeOrderStatusCommand/ChangeOrderStatusCommand.cs:162`, `Shared/TalabatkLogic/TalabatkModels/OrderChat.cs:67` |
| R2c | Agent lists chats by status | active ones are marked disconnected | `GetChatsByUserAndStatusCommand` calls `MakeDisconnected()` on every active chat it returns — a read with a write side effect | `Shared/TalabatkApplication/Commands/GetChatsByUserAndStatusCommand/GetChatsByUserAndStatusCommand.cs:28` |
| R3 | Archive migration ran on a live conversation | — | Behaviour mid-migration is unverified | `_conflicts.md` #615 |

## Integration (cross-side / cross-context)

| # | Precondition | Action | Expected outcome | Rule / source |
|---|---|---|---|---|
| I1 | Any message on a customer conversation | SignalR push | Reaches the Admin SPA via `OperationHub` at `/AdminHub` | `_integrations.md` row 2 |
| I2 | Any message on a driver conversation | Centrifugo | Reaches the driver app — a **different** realtime technology | [[Delivery/Delivery Support & Chat/_knowledge-graph\|Delivery Support & Chat]] |
| I3 | Reporting | Cassandra | Separate store, own migrations and mappers | `Shared/TalabatkData/Cassandra/ChatReportRepository.cs` |
| I4 | Archive | migration job | Triggerable from the identity host by any authenticated principal | 🔴 `_conflicts.md` #615 |
| I5 | Chat about an order | order data | The order-scoped chat variant is folded into [[Order-Lifecycle.technical\|Order Lifecycle]] | |

## Trust scenarios — current behaviour

| # | Precondition | Action | Actual outcome today | Finding |
|---|---|---|---|---|
| X1 | Any authenticated customer, some order is on the way | request a chat token for it | **Joins that order's customer↔driver conversation** | 🔴 `_conflicts.md` **#421** |
| X2 | **No credential at all** | post to the driver realtime proxy with a `DeliveryManAdmin_` channel | Message **persisted** and shown in history as genuine | 🔴 `_conflicts.md` **#616** |
| X3 | Dispute over what support told a driver | read the history | The history may contain injected messages (X2) and cannot alone be treated as evidence | 🔴 #616 |
| X4 | Any authenticated principal | trigger the chat archive migration | It runs | 🔴 `_conflicts.md` **#615** |
| X5 | A chat fix applied to one pair | the other two pairs | Unchanged — three separate implementations | ⚠️ three-way duplication |

## Open Questions

- [ ] What exactly is stored in Cassandra versus `ChatContext` — reports only, or message bodies too?
- [ ] Do all three chat pairs share the bot, or only customer↔support?
- [ ] Which pair does `ChatSetting` configure?
- [ ] Is there a retention policy for chat content? Two stores plus a migration path imply an intent.
- [ ] Can staff edit or delete a message? Nothing in the Admin controllers suggests so.
- [ ] Are chat ratings attributed to an individual agent, and is that used in any review process?
