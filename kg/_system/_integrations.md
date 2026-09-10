---
id: 8orders/system/integrations
note_type: system
sources:
  - path: AdminUi/Controllers/AiThirdPartyController/AiThirdPartyController.cs
    sha1: 812d747ab027
  - path: AdminUi/Controllers/CustomerAdminChat/CustomerAdminChatController.cs
    sha1: 517e95099d3b
  - path: AdminUi/Controllers/DeliveryManChat/DeliveryManChatController.cs
    sha1: a84c7664040f
  - path: AdminUi/Controllers/ErpController/ERPController.cs
    sha1: 4bbd53e5672e
  - path: AdminUi/Controllers/TieredDiscountController/TieredDiscountController.cs
    sha1: 62614ed5fb65
  - path: AdminUi/Helper/ERPIntegration/AccflexERPConfigurations.cs
    sha1: 51cfe329fb93
  - path: Shared/SharedWeb/Helpers/Extenstions/IdentityProvider.cs
    sha1: fba0a620c391
  - path: Shared/TalabatkApplication/DomainEventsHandlers/OrderEventsHandlers/CalculateGoogleMapDeliveryTimeEvent.cs
    sha1: cc2bd8771ec2
  - path: Shared/TalabatkApplication/DomainEventsHandlers/OrderEventsHandlers/NewOrderForRestaurantEventhandler.cs
    sha1: 4422e1686e76
  - path: Shared/TalabatkApplication/DomainEventsHandlers/OrderEventsHandlers/OrderRejectionRoboCallEventHandler.cs
    sha1: 6a4563db93a4
  - path: Shared/TalabatkApplication/Helper/HangFire/RestaurantRoboCallCheckJob.cs
    sha1: 616914311400
  - path: Shared/TalabatkApplication/Helper/HangFire/UpdateBitrixStatusLeadJob.cs
    sha1: c03669b60a77
  - path: Shared/TalabatkApplication/Helper/RobocallScheduler.cs
    sha1: 580cd25cee01
  - path: Shared/TalabatkApplication/Queries/GetCustomerTieredDiscountQuery/GetCustomerTieredDiscountQuery.cs
    sha1: 6b071f1b5edb
  - path: Shared/TalabatkApplication/Services/MartQuantityValidationService.cs
    sha1: 085c128a5b0d
  - path: Shared/TalabatkData/BitrixIntegration/BitrixIntegrationService.cs
    sha1: 1e9cc67150a0
  - path: Shared/TalabatkData/FawryCashCollectionService/FawryCashCollectionService.cs
    sha1: fb2c3d4c4d3d
  - path: Shared/TalabatkData/FawryService/FawryService.cs
    sha1: c8ddebf907c3
  - path: Shared/TalabatkData/GoogleMapServices/GoogleMapService.cs
    sha1: a29d0c367e04
  - path: Shared/TalabatkData/HangfireBridge.cs
    sha1: 526f96ee4cc0
  - path: Shared/TalabatkData/OTPServices/OtpAuthService.cs
    sha1: e3a33e303aa9
  - path: Shared/TalabatkData/RoboCallService/RoboCallService.cs
    sha1: 627f2570f291
  - path: Shared/TalabatkData/WhatAppService/WhatsAppService .cs
    sha1: 5e2b5cefc827
  - path: Talabatk.IDS/Controllers/FeaturesController.cs
    sha1: 987c2188e807
  - path: Talabatk.IDS/Helper/HangFire/SyncMartItemStockFromERPJob.cs
    sha1: c8ad8e604615
  - path: Talabatk.IDS/Startup.cs
    sha1: 32fc90149757
  - path: TalabatkAPIs/Controllers/MenuItem/ItemController.cs
    sha1: be53936a10f9
  - path: TalabatkAPIs/Helper/Extension/IDentityProvider.cs
    sha1: 66e1a01952d2
  - path: TalabatkDelivery/Controllers/Apis/CentrifugoController.cs
    sha1: 31932d0044dd
  - path: TalabatkDelivery/Controllers/Apis/DeliveryManAdminChatController.cs
    sha1: 0438b5c7a06f
  - path: TalabatkDelivery/Helpers/Extensions/IdentityProvider.cs
    sha1: 3b3fd9708a4b
  - path: TalabatkRestaurants/Helpers/Extenstions/IdentityProvider.cs
    sha1: f71980c59eea
last_updated: 2026-08-23
---
# 8Orders — Cross-Context Integration Register

> How the contexts depend on each other (or on a mobile client outside this repo). Mechanisms:
> `ApiClientHandler` HTTP call, SignalR hub push, Hangfire background job, Firebase Cloud Messaging
> push (mobile clients, not in this repo), or a shared Application/Data library invoked
> independently by two hosts against the same database (no network call between them — discovered
> while documenting Tiered Discount; not in the skill's original repo-map list, added here as a
> recognized shape). Last updated: 2026-08-20 ("True Zero-Gap Closure, Round 2" Phase 8 — added rows
> 19-20, the AccFlex ERP mart-stock-sync mechanism and the separate AccFlex ERP GL financial-journal
> integration, documented properly per this round's plan). Prior update: 2026-08-13 (Phase 14 —
> added rows 13-18).

| # | From context | To context | Via (what) | Mechanism | Source ref | Feature(s) |
|---|----------------|--------------|-------------|-----------|-------------|------------|
| 1 | Customer Ordering | Restaurant Portal | New order notification | `ApiClientHandler` → `StoresHub` (SignalR) | `NewOrderForRestaurantEventhandler.cs` | Order Fulfilment (not yet documented) |
| 2 | Customer Ordering | Admin | New order / bad review / chat / cancel-payment relay | `ApiClientHandler` → `OperationHub` (SignalR) | `Shared/SharedWeb/.../ApiClientHandler.cs` | Order Fulfilment (not yet documented) |
| 3 | Identity & Access | Customer Ordering | Token issuance/validation | JWT (`IdentityProvider.cs`, duplicated) | `Talabatk.IDS`, `TalabatkAPIs/Helper/Extension/IDentityProvider.cs` | all |
| 4 | Identity & Access | Restaurant Portal | Token issuance/validation | JWT (`IdentityProvider.cs`, duplicated) | `Talabatk.IDS`, `TalabatkRestaurants/Helpers/Extenstions/IdentityProvider.cs` | all |
| 5 | Identity & Access | Delivery | Token issuance/validation | JWT (`IdentityProvider.cs`, duplicated) | `Talabatk.IDS`, `TalabatkDelivery/Helpers/Extensions/IdentityProvider.cs` | all |
| 6 | Identity & Access | Admin | Token issuance/validation | JWT (`IdentityProvider.cs`, `Shared/SharedWeb` copy) | `Talabatk.IDS`, `Shared/SharedWeb/Helpers/Extenstions/IdentityProvider.cs` | all |
| 7 | Admin | Customer Ordering | Tiered Discount campaigns created/edited/activated/deleted in Admin, read and applied in Customer Ordering | Shared `TalabatkApplication`/`TalabatkData` library, each host's own `IMediator`, same database — **no HTTP call** | `AdminUi/Controllers/TieredDiscountController/TieredDiscountController.cs` ↔ `Shared/TalabatkApplication/Queries/GetCustomerTieredDiscountQuery/GetCustomerTieredDiscountQuery.cs` | Tiered Discount |
| 8 | Customer Ordering | Customer mobile app (not in this repo) | Order/notification push | Firebase Cloud Messaging | `TalabatkApplication.Helper.NotificationHelper` | Order Fulfilment (not yet documented) |
| 9 | Identity & Access | External "Esquio" feature-management service | Feature-flag state read/write, a 3rd distinct mechanism alongside `IFeatureManager` and MediatR `GetFeatureFlagQuery` | HTTP call (`ChangeState` route) | `Talabatk.IDS/Controllers/FeaturesController.cs` | Login & Activation |
| 10 | External AI review-moderation service | Admin (Restaurant Portal data) | Publish/unpublish a `RestaurantReview` comment, attributed to `"System"` | API-key-authenticated webhook (`ReviewCommentCallBack`) → same `PublishRestaurantReviewCommand`/`UnPublishRestaurantReviewCommand` a human admin action also dispatches | `AdminUi/Controllers/AiThirdPartyController/AiThirdPartyController.cs` | Admin Back-Office |
| 11 | Delivery (`TalabatkDelivery`) | Delivery man's own app | Real-time chat (delivery man ↔ customer, delivery man ↔ admin) | Centrifugo pub/sub, tokens generated per session; inbound webhook only routes `DeliveryManAdmin_`-prefixed channels (see `_conflicts.md` #40 for the customer-chat routing gap) | `TalabatkDelivery/Controllers/Apis/CentrifugoController.cs`, `ChatController.cs`, `DeliveryManAdminChatController.cs` | Delivery Man Operations |
| 12 | Admin | Delivery man / customer chat sessions | Real-time chat notifications relayed to the admin browser dashboard | `IChatNotificationService` (internal relay) fed by `[AllowAnonymous]` `Notify*` endpoints on `CustomerAdminChatController`/`DeliveryManChatController` — plausibly server-to-server from a background service, not confirmed | `AdminUi/Controllers/CustomerAdminChat/CustomerAdminChatController.cs`, `DeliveryManChat/DeliveryManChatController.cs` | Admin Back-Office |
| 13 | Customer Ordering | External Fawry payment gateway | Online card/wallet payment capture at order checkout, plus an inbound webhook for async payment/cash-collection status | HTTP `POST` (`IFawryService`) + inbound webhook | `Shared/TalabatkData/FawryService/FawryService.cs`, `FawryCashCollectionService/FawryCashCollectionService.cs`; consumed by `Commands/AddFawryTransactionCommand` | Cart & Checkout / Checkout Payment Processing |
| 14 | Customer Ordering | External Google Maps Directions API | Delivery distance/duration estimate, triggered by an `Order` domain event and a reporting query | HTTP call via the official Google Maps .NET client (`IGoogleMapService`) | `Shared/TalabatkData/GoogleMapServices/GoogleMapService.cs`; consumed by `DomainEventsHandlers/OrderEventsHandlers/CalculateGoogleMapDeliveryTimeEvent.cs`, `Queries/CalculateDistanceBetweenCustomersInOrdersQuery` | Order & Fulfilment |
| 15 | Identity & Access | External SMS gateway | OTP code delivery for phone verification/login (a fixed `"1111"` OTP is hardcoded for iOS review builds — `OtpAuthService.IosFixedOtp`) | HTTP call via an injected SMS-sender abstraction (`IOtpAuthService`) | `Shared/TalabatkData/OTPServices/OtpAuthService.cs` | Login & Activation |
| 16 | Customer Ordering | External WhatsApp Business Cloud API | Notifies a customer that some of their order's items are being replaced | HTTP call (`messaging_product: "whatsapp"`) via `IWhatsAppService` | `Shared/TalabatkData/WhatAppService/WhatsAppService .cs`; consumed by `Commands/NotifyCustomerToReplaceItemsCommand` | Order & Fulfilment |
| 17 | Restaurant Portal + Customer Ordering + Admin | External **Ziwo** cloud-telephony provider (robo-call / IVR) — named in `ZiwoSettings`, `Click2AudioRequest` | Automated voice calls in **five** distinct scenarios, one per storage-name setting on `ZiwoSettings`: (1) `RestaruantPendingStorageName` — a restaurant sitting on a pending order (misspelt in the source); (2) `OrderRejectStorageName` — a restaurant that rejected or ignored an order, on a Hangfire-scheduled check; (3) `ItemReplacementStorageName` — calling the **customer** to approve an item replacement; (4) `ChatExpediteMerchantStorageName` and (5) `ChatExpediteDriverStorageName` — chasing a stalled chat on the merchant and driver sides respectively. Escalation is bounded by `MaximumRestaurantRobocall` / `MaximumCustomerRobocall` with `DurationBetweenRestaurantRobocallInSeconds` / `DurationBetweenCustomerRobocallInSeconds` between attempts, read from `Configuration`. **Bidirectional**: outbound calls are placed via `IRoboCallService`, and Ziwo calls back inbound to report the outcome — `POST api/RoboCall/WebHook` → `HandleRoboCallWebHookCommand`, which writes the result onto the `RoboCall` record and schedules the next attempt if the ladder is not exhausted. ⚠️ That inbound endpoint is **anonymous and unsigned** — see `_conflicts.md` #643 | Outbound: HTTP form `POST` (`IRoboCallService`) + Hangfire background job + MediatR command. Inbound: unauthenticated HTTP webhook | Outbound: `Shared/TalabatkData/RoboCallService/RoboCallService.cs`, `Shared/TalabatkApplication/Helper/RobocallScheduler.cs`, `Shared/TalabatkApplication/Helper/HangFire/RestaurantRoboCallCheckJob.cs`, `AdminUi/Helper/HangFire/Jobs/RestaurantPendingRoboCallsJob.cs`, fired from `Shared/TalabatkApplication/DomainEventsHandlers/OrderEventsHandlers/OrderRejectionRoboCallEventHandler.cs` and `Shared/TalabatkApplication/Commands/NotifyCustomerToReplaceItemsCommand/NotifyCustomerToReplaceItemsCommand.cs`. Inbound: `AdminUi/Controllers/RoboCall/RoboCallController.cs:36`, `Shared/TalabatkApplication/Commands/HandleRoboCallWebHookCommand/HandleRoboCallWebHookCommand.cs:20`. Settings: `Shared/TalabatkLogic/RoboCall/ZiwoSettings.cs:22`-29; payload shapes in the same folder (`CallContent`, `Click2AudioRequest`, `RoboCallContent`, `RoboCallResponse`, `RoboCallWebHook`) | Menu & Order Management (restaurant-facing calls); Order & Fulfilment (customer item-replacement calls); Delivery Administration (the webhook endpoint lives in AdminUi, and chat-expedite covers the driver side) |
| 18 | Admin | External Bitrix24 CRM | "Work with us" restaurant-signup lead creation, plus a Hangfire job that polls Bitrix and syncs lead status back | HTTP `POST`/`GET` (`IBitrixService`) + Hangfire background job | `Shared/TalabatkData/BitrixIntegration/BitrixIntegrationService.cs`, `Helper/HangFire/UpdateBitrixStatusLeadJob.cs`; consumed by `Commands/AddWorkUSRestaurantCommand` | Admin Back-Office |

| 19 | Restaurant Portal / Customer Ordering (mart stock) | External AccFlex ERP (logistics/inventory) | Mart `MenuItem` stock quantity kept in sync with AccFlex's live inventory via 4 distinct paths, all converging on `MenuItem.MaintainStock(...)`: (1) inbound webhook push (`POST /api/Item/ItemStockQuantityChangedInERP`, HMAC-signed); (2) scheduled daily pull, Hangfire job id `"SyncMartItemStockFromERPJob"`, default cron `0 5 * * *` Egypt time; (3) manual on-demand sync command (`SyncMartItemsQuantityFromErpCommand`, specific barcodes or "sync all mismatched"); (4) synchronous on-demand pull at cart-validation time when `Features.ValidateQuantitiesLocally` is `false` (currently `true` in production, so paths 1–3 are the active feed and path 4 is dormant) | HTTP webhook (in) + Hangfire recurring job (pull) + MediatR command (manual) + synchronous HTTP call (cart-time, gated) | `TalabatkAPIs/Controllers/MenuItem/ItemController.cs:217-224`, `Talabatk.IDS/Helper/HangFire/SyncMartItemStockFromERPJob.cs` + `Talabatk.IDS/Startup.cs:455`, `Shared/TalabatkApplication/Commands/SyncMartItemsQuantityFromErpCommand/`, `Shared/TalabatkApplication/Services/MartQuantityValidationService.cs` | Restaurant & Menu Discovery (Mart) — gated by `Features.ValidateQuantitiesLocally`, a **different** flag from row 20's `Features.ERPIntegration`, despite the naming similarity; see `_conflicts.md` #263/#272 for this mechanism's live-incident bug history (fail-open since fixed to fail-closed; the still-open gap is no stock reservation at checkout) |
| 20 | Admin (financial journals) | External AccFlex ERP (General Ledger) | Daily batch of double-entry GL journals (restaurant/delivery-man accruals, cash/wallet/promo-code, compensation, rejected-order penalties, Fawry, refunded online payments, etc.) posted to AccFlex's ledger, plus a separate cash-payment/treasury sub-integration for merchant cash settlements | HTTP `POST` to `{GLApiBaseUrl}/api/Journal` (`GlApiService`, ~13 partial-class journal builders) + a parallel `CashControllApiServices` for cash receipts/treasury | `AdminUi/Helper/ERPIntegration/GlApiServices/GlApiService.cs:71,519,525` (+ sibling `GlApiService.*.cs` files), `AdminUi/Helper/ERPIntegration/CashControllApiServices/`, `AdminUi/Controllers/ErpController/ERPController.cs`, `AdminUi/Helper/ERPIntegration/AccflexERPConfigurations.cs` | Admin Back-Office (ERP Financial Journals) — gated by `Features.ERPIntegration`; this integration is the source of `_conflicts.md`'s large `GlApiService`/`CompensationJournalDtoBuilder`/`CashControllApiServices` finding cluster (#293-296 among others) — thread-unsafe shared state, an unguarded lookup that can roll back a whole day's batch, and a dead `MarkOrderAsPaid` method |

Rows 1, 2, 8 are carried over from `references/repo-map.md` (established during skill authoring,
not re-verified against code in this pilot run beyond what repo-map.md already cites). Rows 3–7 are
directly verified during this run. Rows 9–12 added 2026-08-03 during Phases 1–6 gap-fill — all
directly verified against controller code. Rows 13–18 added 2026-08-13 (Phase 14) from the
non-mapping service folders individually read during Phase 10 (`Shared/TalabatkData`) — call-site
attribution confirmed via `grep -rl` against `Shared/TalabatkApplication` for each service interface,
not a full trace of every call path. `HangfireBridge.cs` (the shared "send a background job" entry
point used by most of the above) is infra shared by many features, not itself a single context-pair
relationship, so it isn't given its own row. Rows 19-20 added 2026-08-20 (Phase 8 of this round) —
verified directly against code, including catching and correcting an initial mis-scoped grep that
wrongly suggested row 19's scheduled sync job didn't exist (it does, just outside `Shared/`), and
distinguishing the two AccFlex ERP integrations' actually-different gating feature flags
(`Features.ValidateQuantitiesLocally` for row 19 vs. `Features.ERPIntegration` for row 20) — this
round's own plan document had conflated the two under a single flag name before verification.

| 21 | Delivery | Delivery Man mobile app (not in this repo) | Break-ending reminder push: when a driver starts a break, a notification row is created and a job is scheduled to fire `NotificationMinutesBeforeEnd` before the break ends; the job id is stored on the break log so it can be cancelled if the break ends early | Hangfire delayed job `SendDeliveryManNotificationJob` → `IDeliverymanNotificationProvider` (Firebase Cloud Messaging) | `Shared/TalabatkApplication/DomainEventsHandlers/DeliveryManEventsHandlers/BreakStartedEventHandler.cs:81`, `Shared/TalabatkApplication/Helper/HangFire/SendDeliveryManNotificationJob.cs:36` | Delivery Man Operations |
| 22 | Customer Ordering | Customer mobile app (not in this repo) | Back-in-stock push: when a mart/menu item becomes available again, one master `CustomerNotification` row is written for every waiting customer and a job fans it out, grouping identical payloads by `NotificationGroupKey` (type + entity + both languages + per-platform flags) so one push is built per group rather than per customer | Hangfire job `SendNotificationJob` → `ICustomerNotificationProvider` (Firebase Cloud Messaging) | `Shared/TalabatkApplication/DomainEventsHandlers/ItemBecameInStockEventHandlers/ItemBecameInStockEventHandler.cs:244`, `Shared/TalabatkApplication/Helper/HangFire/SendNotificationJob.cs:70` | Restaurant & Menu Discovery, Marketing & Content |
| 23 | Delivery | Admin (city rush-mode configuration) | Rush-mode exit check: entering rush mode for a city schedules a check `ThresholdCheckerInMunites` later; if the timed-out-delivery count is still above the exit threshold the job **re-schedules itself**, so rush mode ends only when the count actually falls — a self-perpetuating job chain, not a one-shot timer | Hangfire self-rescheduling job `RushModeEndCheckerService` reading the shared timeout counter cache (`ITimeOutOrderDeliveriesCashe`) | `Shared/TalabatkApplication/DomainEventsHandlers/OrderEventsHandlers/MangeRushTimeEvnetHandler.cs:64`, `Shared/TalabatkApplication/TimeOutRequestsCashing/RushModeEndCheckerService.cs:27,45` | Delivery Man Operations, City & Geography Administration |
| 24 | Admin | Delivery (shared timeout counter cache) | Counter warm-up at host boot: the Admin host enqueues a job that recounts timed-out `OrderDeliveries` per city straight from the database and seeds the shared cache the rush-mode logic reads. The counter is therefore rebuilt by whichever host starts, and rush-mode decisions depend on that cache being seeded | Hangfire fire-and-forget job `IntialTimeOutRequestCounterService` → `ITimeOutOrderDeliveriesCashe` | `AdminUi/Startup.cs:472`, `Shared/TalabatkApplication/TimeOutRequestsCashing/IntialTimeOutRequestCounterService.cs:26` | Delivery Man Operations, Admin Back-Office |

Rows 21-24 added 2026-08-23 (this round's Phase 1). They were found by `verify-notes.js`'s mechanical
integration scan, not by reading: the checker greps every `DomainEventsHandlers/*`, `Startup.cs` and
`ApiClientHandler` call site for `ApiClientHandler.*`, `MapHub<>` and `BackgroundJob.Schedule/Enqueue<>`,
then fails on any symbol this register does not name. Four wired jobs had never been registered, which
is the difference between a register maintained by memory and one maintained by a command. All four
call sites above were then read and cited individually.
