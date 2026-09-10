---
id: 8orders/restaurant-portal/menu-and-order-management/merchant-menu-and-orders-technical
note_type: technical
context: Restaurant Portal
feature: Menu & Order Management
group: Merchant-Menu-and-Orders
covers: [MerchantCapacityHours, MerchantInstructionsVideos, MerchantLoyaltyConfig, MerchantReceivement, MerchantRejectionReasons, MerchantStatementTransaction, MerchantKpiScoreConfiguration]
sources:
  - path: Shared/TalabatkLogic/TalabatkModels/MerchantCapacityHours.cs
    sha1: b24bd4903c54
  - path: Shared/TalabatkLogic/TalabatkModels/MerchantInstructionsVideos.cs
    sha1: 32885a9f87e2
  - path: Shared/TalabatkLogic/TalabatkModels/MerchantLoyaltyConfig.cs
    sha1: d65cfabbca6f
  - path: Shared/TalabatkLogic/TalabatkModels/MerchantReceivement.cs
    sha1: b1c0c6db5544
  - path: Shared/TalabatkLogic/TalabatkModels/MerchantRejectionReasons.cs
    sha1: 8fdfc6d4ff1a
  - path: Shared/TalabatkLogic/TalabatkModels/MerchantStatementTransaction.cs
    sha1: 950a66f2f1c5
  - path: Shared/TalabatkLogic/OrderComplaintAggregate/MerchantKpiScoreConfiguration.cs
    sha1: ee3d81368326
  - path: AdminUi/Helper/HangFire/Jobs/AutoBusyResturantJob.cs
    sha1: cf5f659a62a0
  - path: Shared/TalabatkApplication/Commands/AddNewCartItemCommand/AddNewCartItemCommand.cs
    sha1: c3cb69f77a84
  - path: Shared/TalabatkApplication/Commands/AddNewCartItemCommand/AddNewCartItemCommand_V1.cs
    sha1: 48c497cb1c32
  - path: Shared/TalabatkApplication/Commands/AddRestaurantBusyCommand/AddRestaurantBusyCommand.cs
    sha1: 60ad49668a1d
  - path: Shared/TalabatkApplication/Commands/ChangeOrderToCashCommand/ChangeOrderToCashCommand.cs
    sha1: d771a058a231
  - path: Shared/TalabatkApplication/Commands/ChangePaymentOnlineStatusCommand/CaptureOnlinePaymentAfterPaidatBank.cs
    sha1: e3978ed3a3dc
  - path: Shared/TalabatkApplication/Commands/EndRestaurantBusyCommand/EndRestaurantBusyCommand.cs
    sha1: 4ee0471ab2a8
  - path: Shared/TalabatkApplication/Commands/ManageOptionGroupsFromExcelCommand/ManageOptionGroupsFromExcelCommand.cs
    sha1: 17e58ef92597
  - path: Shared/TalabatkApplication/Commands/MangeCatgoriesFromExcelSheetCommand/MangeCatgoriesFromExcelSheetCommand.cs
    sha1: 3dcc0abbe365
  - path: Shared/TalabatkApplication/Commands/RejectRestaurantItemsCommand/RejectRestaurantItemsCommand.cs
    sha1: 00c25b3ac2e9
  - path: Shared/TalabatkApplication/Commands/RestaurantStartCookingCommand/RestaurantStartCookingCommand.cs
    sha1: 674e1ff37cca
  - path: Shared/TalabatkApplication/Commands/SaveResturantBusyTimeCommand/SaveResturantBusyTimeCommand.cs
    sha1: 75af1c8f3cf7
  - path: Shared/TalabatkApplication/DomainEventsHandlers/OrderEventsHandlers/NewOrderForRestaurantEventhandler.cs
    sha1: 4422e1686e76
  - path: Shared/TalabatkApplication/DomainEventsHandlers/OrderEventsHandlers/OrderNificationsEventHandler.cs
    sha1: e8501b1db140
  - path: Shared/TalabatkApplication/DomainEventsHandlers/OrderEventsHandlers/ResendOrderToRestaurantEventHandler.cs
    sha1: 511b522c63f2
  - path: Shared/TalabatkApplication/Queries/GetAllRestaurantBusyQuery/GetAllRestaurantBusyQuery.cs
    sha1: c95765ab9377
  - path: Shared/TalabatkApplication/Queries/RestaurantOrderSummaryV2Query/RestaurantOrderSummaryV2Query.cs
    sha1: 8e1b328996c4
  - path: Shared/TalabatkApplication/Services/MartQuantityValidationService.cs
    sha1: 085c128a5b0d
  - path: TalabatkRestaurants/Controllers/MerchantDashboardControllers/MerchantDashboardController.cs
    sha1: 5a24efe5f1ef
  - path: TalabatkRestaurants/Controllers/Orders/OrdersController.cs
    sha1: 1f87b4a80401
last_updated: 2026-08-23
tags: [flow, technical]
---
# Merchant Menu and Order Management — Technical Flow

> Hub note for the `TalabatkRestaurants` portal. Entities it manages are documented from the customer
> side at [[Restaurant.technical|Restaurant]],
> [[MenuItem.technical|MenuItem]] and
> [[Offers.technical|Offers]] — not restated
> here. Controller-by-controller inventory lives in [[_knowledge-graph|Menu & Order Management KG]];
> this note is the narrative that walks through it end to end.

## Trigger
Six independent triggers converge on this flow:
1. Merchant staff sign into the Angular portal (JWT bearer, roles `Merchant`/`MerchantAdmin`/
   `RestaurantAdmin`/`restaurant`) and land on the dashboard.
2. Staff open the busy/hours screen to pause or resume order intake.
3. Staff edit the menu catalog directly (categories, items, prices, option groups, availability, stock).
4. Staff upload an Excel workbook to bulk-create/update categories+items+prices, option groups, or
   (for Mart-type stores) item price/activation/stock.
5. A customer completes and pays for an order elsewhere in the platform, firing a domain event that
   pushes a live "new order" notification into the connected portal session.
6. Staff open the reporting screens to see their own orders/rejections/revenue.

## Step-by-step

### A. Session and restaurant scope
1. `OrdersController` and siblings resolve `sessionInfo.RestaurantId` / `sessionInfo.UserRestaurants`
   from the authenticated session for most "V1" routes — e.g. `GetRestaurantNewOrders`
   (`TalabatkRestaurants/Controllers/Orders/OrdersController.cs:136-144`), `StartCooking` (`:275-289`).
2. A parallel "V2" sibling of the same operation instead accepts an explicit `restaurantId`/
   `restaurantIds` parameter from the caller with no ownership check against the session. Six such
   pairs exist in this one controller: `ConfirmOrder` (`:416-437`) / `ConfirmOrderV2` (`:445-466`);
   `StartCooking` (`:275-289`) / `StartCookingV2` (`:297-311`); `ReadyToPickupOrder` (`:598-616`) /
   `ReadyToPickupOrderV2` (`:624-642`); `GetOrderDetails` (`:319-339`) / `GetOrderDetailsV2`
   (`:347-372`); `RejectSomeItemsRestaurant` (`:841-856`) / `RejectSomeItemsRestaurantV2`
   (`:864-879`); `RejectRestaurantOrderOverall` (`:887-902`) / `RejectRestaurantOrderOverallV2`
   (`:911-930`). **#404** — see [[_idor-instances|_idor-instances.md]] for the full
   15-instance register; `MerchantDashboardController`'s five KPI-chart actions bind a caller-supplied
   `RestaurantIds` the same way, with `SessionInfo` injected and unused (`MerchantDashboardController.cs:28-122`).

### B. Opening hours and busy periods
3. Staff (or an admin on their behalf) create a busy window: `AddRestaurantBusyCommand.Handle`
   (`AddRestaurantBusyCommand.cs:36-64`) constructs `ResturantBusyHistory.Instance(RestaurantId, now,
   BusyFrom, BusyEnd, Reason, CreatedBy, IsAdmin)` and saves it — no push notification on this path.
4. The busy state a customer/merchant actually sees is read back by `GetAllRestaurantBusyQuery.cs:37`,
   which filters **only** on the upper bound (`BusyEnd >= now`) — a future-dated `BusyFrom` still
   matches immediately, so a window scheduled to start later shows the restaurant busy right now.
   **#409**, already resolved in `_conflicts.md` against the correct siblings `AutoBusyResturantJob.cs:188`,
   `AddNewCartItemCommand.cs:118`/`AddNewCartItemCommand_V1.cs:197`, `ReportsController.cs:110`.
5. Ending a busy period: `EndRestaurantBusyCommand.Handle` (`EndRestaurantBusyCommand.cs:37-127`)
   re-fetches the row constrained to `BusyEnd >= now` (`:44-47`), lets only an admin end an
   admin-created busy row (`:55-64`), and — if the window hadn't started yet — simply deletes the row
   (`:66-77`, "harmless" per the #409 majority reading). Otherwise it calls
   `restaurantBusyHistory.EndRestaurantBusy(...)`, saves (`:80-81`), and pushes a GCM notification to
   every device of every user tied to the restaurant (`:83-117`) — **before** checking whether the save
   at `:81` actually succeeded (checked only at `:119`, purely to shape the return value). Same
   unconditional-notify-before-checking-save shape already flagged in [[_knowledge-graph|the KG note]]
   for `SaveResturantBusyTimeCommand.cs:70-106`; not independently numbered in `_conflicts.md`, so cited
   here by file:line rather than by finding number.

### C. Menu catalog management
6. Category/item/price/option-group CRUD is a thin MediatR pass-through across `CategoryController`,
   `ItemOptionController`/`OptionCategoryController`/`OptionsController`/`MenuItemOptionGroupController`,
   `ItemPriceController`, `MenuItemsController`, `StoreMenuItemsController` — routes enumerated, not
   re-listed, in [[_knowledge-graph|the controller inventory]]. `MenuItemsController` alone exposes four
   overlapping "toggle availability" routes (`ChangeMerchantMenuItemAvalibilty`,
   `UpdateMerchantMenuItemAvalibiltyAndPrice`, `ChangeItemAvailability`, `UpdateMenuItemActiveStatus`).
7. Stock for Mart-type stores is edited through `StoreMenuItemsController.UpdateItemStock` (`:241-255`,
   `[AllowAnonymous]` — flagged in the KG note as likely-but-unconfirmed ERP-webhook intent) and read
   back through `GetStoreMenuItemQuery`/`GetStoreMenuItemsQuery`
   (`Shared/TalabatkApplication/Feature/StoreMenuItems/Queries/`).

### D. Excel bulk-import path (three independent pipelines)
8. **Menu categories/items/prices**: `MangeCatgoriesFromExcelSheetCommand.Handle`
   (`MangeCatgoriesFromExcelSheetCommand.cs:41-202`) groups uploaded rows into category→item→price
   trees (`:64-105`), matches each category against `context.MenuCategory` scoped to
   `request.RestaurantId` (`:111-125,131`), creates new `MenuCategory`/`MenuItem`/`MenuItemPrice`
   aggregates for anything unmatched (`:135,204-221`) or grafts new items/prices onto an existing
   category (`:137-141,223-263`), and saves (`:149-150`) **before** the subsequent image-copy pass
   (`:152-196`) — an exception there is swallowed and still returns `Result.Success` (`:197-200`), so a
   failed image copy never surfaces even though the category/item/price data is already committed;
   not traced further whether this is deliberate ("data matters more than the picture") or an oversight.
9. **Option groups**: `ManageOptionGroupsFromExcelCommand.Handle`
   (`ManageOptionGroupsFromExcelCommand.cs:40-154`) validates required names, per-group field
   consistency (`IsRequired`/`Min`/`Max`/sorting all rows in a group must agree, `:241-293`), duplicate
   options within a group (`:295-327`), and `Min`/`Max` bounds against the actual option count
   (`:369-421`) — all validation is fail-closed, returning `Result.Failure` with the joined error list
   before any write (`:115-119`). Matching an existing group is by `OptionGroupReferenceName` (English)
   or Arabic description (`:137-139`), scoped to `request.RestaurantId` (`:132`); new options become
   both a `MenuItem` (`option: true`, `:202-222`) and a `MenuItemOptionGroupItem` (`:227-238`).
10. **Store (Mart) items**: two-phase — `PreviewStoreMenuItemUpdateFromExcelCommand.Handle`
    (`:32-181`) classifies each row (`Eligible`/`NotEligible`/`MissingInfo`/`Existing`/`ExistInOtherStore`)
    against brand/category/barcode lookups without writing anything, capped at 500 rows (`:177-178`);
    then `EditStoreMenuItemsByExcelCommand.Handle` (`:43-401`) applies the previewed rows — matches by
    barcode (`:117-120`), updates descriptions/brand/category/barcode/active-flag/price/quantity-limits
    on the tracked `MenuItem`/`MenuItemPrice` (`:137-312`), saves (`:323-327`), re-indexes changed items
    in Elasticsearch (`:329`), then copies staged images from `TempImages` into the permanent `Items`
    folder (`:331-373`). The whole handler is wrapped in one `try/catch` that returns `Result.Failure`
    with the exception message on any error (`:395-400`).

### E. Order lifecycle — push to handoff
11. **New order arrives**: order creation/payment-confirmation handlers (`ChangeOrderToCashCommand.cs:150`,
    `CaptureOnlinePaymentAfterPaidatBank.cs:157-158`, `NewOrderForRestaurantEventhandler.cs:80`,
    `OrderNificationsEventHandler.cs:173`, `ResendOrderToRestaurantEventHandler.cs:63`) call
    `IApiClientHandler.SendNewOrderForRestaurant`/`SendNewOrder`, which makes an **HTTP self-call** to
    `api/RestaurantNotification/NewOrderReceived` or `api/IdentityListener/NewOrder`
    (`Shared/SharedWeb/Helpers/AuthHelper/ApiClientHandler.cs:22-39,108-115`) rather than invoking
    SignalR in-process. `RestaurantNotificationController` (the receiving relay) then calls
    `hubContext.Clients.Group(...).NewOrder(...)` directly on `StoresHub`'s `IOperationHub`, pushing to
    every connection in that restaurant's SignalR group. Group membership is set on connect from the
    JWT's `RestaurantId`/`userRestaurants` claims (`StoresHub.cs:14-26,42-56`) — not from a database
    lookup, so a stale or forged claim would misroute the push (not confirmed exploitable; claims come
    from the same auth pipeline as the rest of the session).
12. `RestaurantNotificationController` has **no `[Authorize]` at all** on any of its 10 routes,
    including this relay — already documented in [[_knowledge-graph|the KG note]] (not independently
    numbered in `_conflicts.md`). Anyone who finds the route can push a fake `NewOrder`/`RejectOrder`/
    `DelayOrder` event to a restaurant's live screen.
13. **Accept**: `POST Orders/ConfirmOrder(V2)` → `ConfirmOrderRestaurantCommand.Handle`
    (`ConfirmOrderRestaurantCommand.cs:39-96`) loads the order with its status history/details/
    restaurant-details (`:42-47`), calls the aggregate method `order.ConfirmRestaurantOrderDetails(...)`
    (`:56-60`) which fails closed on bad state (`:63-70`), auto-confirms the whole order once every
    restaurant in a multi-restaurant order has confirmed (`:77-81`), saves (`:86`), and **only on
    success** notifies the portal via `_operationHub.Clients.Groups(...).StartCookingForHoldOrder()`
    (`TalabatkRestaurants/Controllers/Orders/OrdersController.cs:428-431`) — the one `StoresHub` push method that calls the right client
    method (see #14 below).
14. **Reject (whole order or per-item)**: `POST Orders/RejectSomeItemsRestaurant(V2)` /
    `RejectRestaurantOrderOverall(V2)` → `RejectRestaurantItemsCommand.Handle`
    (`RejectRestaurantItemsCommand.cs:49-138`). Guards: order must still be `Pending`/`RestaurantPending`
    (`:78-81`); per-item rejections call `order.RejectRestaurantOrderDetailByAvailability(...)` for each
    flagged item (`:92-99`) or `RejectRestaurantOrderDetailByAnotherReason` for a whole-restaurant reject
    (`:102-109`); either path then flips that restaurant's `OrderRestaurantDetails` row to `Rejected`
    (`:100,109`) and appends an action-record comment (`:114-115`). If the customer's
    `UnavailableItemsPreference` is `SuggestAlternatives` and the `ItemReplacement` feature flag is on,
    a background job (`NotifyCustomerForOrderActionJob`) is enqueued to offer alternatives (`:125-133`).
    This is the controller-level entry point for
    [[OrderDetails.technical|OrderDetails]]'s
    `RejectOrderByAvailability` rule already documented there — not restated.
15. **Start cooking**: `POST Orders/StartCooking(V2)` → `RestaurantStartCookingCommand.Handle`
    (`RestaurantStartCookingCommand.cs:36-98`) requires every restaurant on the order to already be
    `Confirmed` or `Cooking` (`:54-64`) and rejects a duplicate start (`:65-72`) before flipping this
    restaurant's row via `MarkOrderAsStartCooing` (`:74-75`) and saving — correctly fails closed if the
    save itself fails (`:84-92`).
16. **Ready for pickup**: `POST Orders/ReadyToPickupOrder(V2)` →
    `ConfirmResturantReadyToPickupOrderCommand.Handle` (`:38-73`). `ValidateOrderStatus` (`:76-111`)
    blocks the transition while the order is still `RestaurantPending`, already `OnWay`, already
    `ReadyToPickUp`/`PickedUp` for this restaurant, or before the cooking-time estimate has elapsed
    (`CookingTime` vs. `StartCookingDate`, `:99-108`, with a 5-minute early-allowance). On success,
    `order.OnReadyToPickup(...)` (`:58`) flips this restaurant's status and the save is checked before
    reporting success (`:67-71`) — this handler does **not** exhibit the #396 false-success pattern.
    This is the merchant side's last touch on the order: pickup/handoff to a driver (assignment,
    `OnWay`, delivered) is Delivery-context territory and **not traced in this pass** — see Open
    Questions.
17. **Merchant push-method bug (already documented, bridged not restated)**: of `StoresHub`'s three
    "push" hub methods only `StartCookingForHoldOrder` (`:88-92`) calls its own namesake client method;
    `SendAutoConfirmOrder` (`:95-99`) and `SendCancelReservationRestaurant` (`:102-106`) both
    mis-call `.StartCookingForHoldOrder()` instead. The feature still works because
    `RestaurantNotificationController` bypasses these two broken methods and calls the hub context
    directly — see [[_knowledge-graph|the KG note]] for the full analysis.

### F. Merchant performance visibility
18. Daily summary: `GET Orders/RestaurantOrdersDailySummary(V2/V3)` →
    `RestaurantOrderSummaryQuery`/`RestaurantOrderSummaryV2Query` (`TalabatkRestaurants/Controllers/Orders/OrdersController.cs:738-780,789-807`) —
    V2 takes a caller-supplied `restaurantIds` list, part of the same #404 family (finding #31 in
    `_conflicts.md`, which also flags the V3/`RestaurantOrderSummaryV2Query.cs:42-51` variant joining
    `AspNetUserRestaurants` on `sessionInfo.UserId` as the correct pattern by contrast).
19. Deeper reporting (performance, transactions, financial summary PDF/image export, rejected-orders,
    items-turnover) lives in `Reports/ReportController` — thin MediatR wrappers over DevExpress report
    definitions, not opened in this pass (per [[_knowledge-graph|the KG note]]).
20. Operational KPI charts (avoidable wait time, customer cancellations, rejection rate, unavailable
    time) are `MerchantDashboardController`'s five actions — the unscoped-`RestaurantIds` #404 instance
    noted in step A above.

## Data written
In the order a merchant would encounter them:
1. `RestaurantBusyHistory` — insert (`AddRestaurantBusyCommand`), update/delete (`EndRestaurantBusyCommand`).
2. `MenuCategory`, `MenuCategoryDescription`, `MenuItem`, `ItemDescription`, `MenuItemPrice`,
   `MenuItemPriceDescription`, `ImageBank` — insert/update via direct CRUD controllers or the categories
   Excel path (`MangeCatgoriesFromExcelSheetCommand`).
3. `MenuItemOptionGroup`, `MenuItemOptionGroupDescription`, `MenuItemOptionGroupItem`, plus a companion
   `MenuItem` per option — via `ManageOptionGroupsFromExcelCommand`.
4. `MenuItem`/`MenuItemPrice` (Mart) — update via `EditStoreMenuItemsByExcelCommand`/`UpdateItemStock`.
5. `Order`, `OrderDetails`, `OrderRestaurantDetails` (status flips), `OrderStatusHistory` (via
   `AddRestaurantOrderActionRecord`) — every accept/reject/start-cooking/ready-to-pickup action.

## External calls
- **SignalR** (`StoresHub`, hub path `/operationHub`) — restaurant-group push for new/rejected/updated/
  delayed orders and cooking-started events.
- **HTTP self-call** — `ApiClientHandler` → `api/RestaurantNotification/*`, `api/IdentityListener/NewOrder`
  (in-process service calling its own exposed API rather than an in-process event, `ApiClientHandler.cs:22-39,108-115`).
- **Android/iOS GCM push** — `IAndroidGCMPushNotification.PushNotification` (busy-ended, delivery-side
  notifications).
- **Elasticsearch** — `IEalsticSearchServices.IndexNewItems` after menu/Excel writes.
- **ERP** — `SyncMartItemsQuantityFromErp`, `GetIncompatibleItemsBetweenErpAnd8Orders` on
  `StoreMenuItemsController` (not opened this pass).
- **File system** — Excel image staging under `ImagePathUpload/TempImages`, copied into
  `ImagePathUpload/Items` or `.../Catogry` on successful save.
- **DevExpress reporting** — `Reports/ReportController`'s PDF/image exports.

## Failure modes
- **#404** (systemic, 15 instances) — six `V1`/`V2` route pairs in `OrdersController` plus all five
  `MerchantDashboardController` KPI actions accept a caller-supplied restaurant id/list with no
  ownership check; full list in [[_idor-instances|_idor-instances.md]]. Hits steps A, 18, 20.
- **#409** — a busy window scheduled for later shows the restaurant busy immediately, because
  `GetAllRestaurantBusyQuery.cs:37` omits the lower bound. Hits step B (busy-status read-back).
- **#396 family** (failure reported as success) — this flow's own instance is not separately numbered
  but matches the family shape twice: `SaveResturantBusyTimeCommand.cs:70-106` (documented in
  [[_knowledge-graph|the KG note]]) and `EndRestaurantBusyCommand.cs:81-119` (this note, step B.5) both
  push a notification before confirming the save succeeded.
- **#451** — for stores/Mart items specifically: a customer cart spanning more than one
  restaurant/store skips the checkout-time stock re-validation entirely and reports success anyway
  (`MartQuantityValidationService.cs:48-53`), so a merchant can receive an order for stock the portal's
  own `EditStoreMenuItemsByExcelCommand`/`UpdateItemStock` never confirmed as available. See
  [[CustomerCart.technical|CustomerCart]].
- **Zero authorization** on `RestaurantNotificationController` (all 10 routes, including the new-order
  relay in step E.11-12) and on `StoreMenuItemsController.UpdateItemStock`/`ExportImportExcelController`'s
  chunked upload (`[AllowAnonymous]`) — both already documented in [[_knowledge-graph|the KG note]],
  not independently numbered in `_conflicts.md`.
- **Inconsistent ownership enforcement** between near-duplicate endpoints doing the same operation —
  `CategoryController.InsertMenuCategory` (unchecked) vs. `.Add` (checked); `ExternalDeliveryRequestsController
  .ExternalCustomers` (checked) vs. `.GetRequests` (unchecked) — both in [[_knowledge-graph|the KG note]].

## Folded entities — the 7 satellites documented here

| Entity | What it is | Rules |
|---|---|---|
| `MerchantStatementTransaction` | Every line on a merchant's financial statement — the merchant money ledger | The most deliberately built entity in the Restaurant Portal, and the model the rest of the codebase's money handling is not. One private `Instance` with five guards — account, merchant, amount, comment and order id all required (`Shared/TalabatkLogic/TalabatkModels/MerchantStatementTransaction.cs:44-62`) — behind **ten named factories**, one per transaction kind: `AddCashOrOnlineOrderTransaction` (`:82`), `AddCompensationTransaction` (`:101`), `AddMerchantPaymentTransaction` (`:125`), `AddMerchantCollectionTransaction` (`:141`), `Add8OrderProfitTransaction` (`:166`), `AddOnlinePaymentContributionTransaction` (`:188`), `AddCompanyContributionTransaction` (`:212`), `AddMerchantContributionTransaction` (`:235`), `AddAdReservationTransaction` (`:259`) and `AddMerchantReceivementTransaction` (`:279`). Each returns `Result`, so a caller cannot post a malformed line, and the factory name records **why** the money moved — the ledger is self-documenting. `IsCredit` plus `TransactionType` gives direction and reason separately, and `AccountId`/`RestaurantSubAccountId`/`JournalSubscriptionId` tie each line to the ERP chart of accounts |
| `MerchantReceivement` | Cash collected from a merchant, tied to an AccFlex treasury day | `Instance` only, **no validation** on `AmountReceived` (`Shared/TalabatkLogic/TalabatkModels/MerchantReceivement.cs:17`) — in contrast to the ledger line it eventually produces via `AddMerchantReceivementTransaction`, which requires the amount. So the guard exists one step downstream of where the number is captured. The merchant-side twin of `DeliveryManDaily` |
| `MerchantKpiScoreConfiguration` | The thresholds and weights behind a merchant's KPI score band | `CreateDefault` seeds it (`Shared/TalabatkLogic/OrderComplaintAggregate/MerchantKpiScoreConfiguration.cs:19`); `Update` enforces five real invariants — both weights non-negative and the three band ceilings strictly increasing, `GoodMax < MonitorMax < HighRiskMax` (`:41-53`). Genuinely good validation, expressed entirely in **Arabic string literals inside the domain layer** — 🔴 `_conflicts.md` #621 |
| `MerchantRejectionReasons` | Why a merchant rejected an order, and whether it counts as an availability rejection | Both `Instance` and `Update` guard, and both messages are useless: "Failed" (`Shared/TalabatkLogic/TalabatkModels/MerchantRejectionReasons.cs:22`) and "Update Failed" (`:37`). A caller learns that something was rejected, not what. Same family as 🟡 #634 and `MenuItemPriceDescription`'s "Fail Update". `RejectForAvailability` is the consequential flag — it is what feeds the rejection-rate weight in `MerchantKpiScoreConfiguration` above |
| `MerchantLoyaltyConfig` | A merchant's participation in loyalty: contribution percentage, voucher expiry, display order, impressions | Private ctor, then `Create` (`Shared/TalabatkLogic/TalabatkModels/MerchantLoyaltyConfig.cs:22`), `Update` (`:42`), `IncrementImpressions` (`:50`) and `SetDisplayOrder` (`:55`) — all `void`, **none validating**. So `ContributionPct` is unbounded: nothing stops a negative or above-100 percentage on the row that decides how much of a voucher the merchant funds. Tracks `UpdatedBy`/`UpdatedAt`, so changes are attributable even though they are unchecked |
| `MerchantCapacityHours` | A merchant's estimated versus actual open hours for a day, with busy minutes and an opening percentage | `Instance` only, no guards (`Shared/TalabatkLogic/TalabatkModels/MerchantCapacityHours.cs:23`). Denormalises `restaurantName` and `cityId` onto the row, so the capacity report reads without joins |
| `MerchantInstructionsVideos` | The four onboarding-video URLs shown to merchants — web and app, Arabic and English | `Instance` and a `void Update`, neither validating (`Shared/TalabatkLogic/TalabatkModels/MerchantInstructionsVideos.cs:19`, `:35`). Four URL columns and no URL check, the same shape as `Webhook` in [[Admin/Admin Back-Office/Configuration/Configuration.technical\|Configuration]] |

### What the split means

The Restaurant Portal contains both extremes at once. `MerchantStatementTransaction` is the best-designed
entity in the repository: a single guarded constructor behind ten intention-revealing factories, so every
line on a merchant's statement is both valid and explained. Two entities away, `MerchantLoyaltyConfig`
lets an unbounded contribution percentage decide how much of a customer's voucher the merchant pays for,
and `MerchantReceivement` captures a cash amount with no check at all. The same context therefore holds
the strongest and the weakest money handling in the codebase, and which one applies depends on whether
the value passes through the statement ledger.

## Open Questions

- [ ] `MerchantLoyaltyConfig.ContributionPct` is unbounded in the domain. Is it clamped in the command,
      the admin screen, or nowhere?
- [ ] `MerchantReceivement.AmountReceived` is unvalidated at capture and validated only when it becomes a
      statement line. Can a receivement exist without its ledger line?
- [ ] `MerchantRejectionReasons`' two guards report "Failed" and "Update Failed". What do they actually
      test — the reason names?
- [ ] Portal login/JWT-issuance flow itself (how `RestaurantId`/`userRestaurants` claims are minted) —
  not traced in this pass; taken as given from the session/claims already used throughout.
- [ ] The merchant-side flow ends at "ready for pickup" (`ConfirmResturantReadyToPickupOrderCommand`
    flips `RestaurantOrderStatus.ReadyToPickUp`/`PickedUp`); the actual driver assignment, pickup
    confirmation and `OnWay` transition are Delivery-context — not traced in this pass.
- [ ] Whether `MangeCatgoriesFromExcelSheetCommand`'s swallowed image-copy exception
    (`:197-200`, returns `Result.Success` after the category/item data is already committed) ever
    masks a real failure in production, or is intentional ("data matters more than the picture").
- [ ] Whether `StoresHub`'s SignalR group membership (from JWT claims, `:14-26,42-56`) can ever diverge
    from a user's actual current `AspNetUserRestaurants` rows (e.g. after a restaurant reassignment
    mid-session) — not traced in this pass.
- [ ] Which of the two independent feature-flag check endpoints
    (`FeatureMangementController` vs. `FeatureMangamentController`) the Angular portal actually calls —
    open question already carried in [[_knowledge-graph|the KG note]].
- [ ] Whether the two `[AllowAnonymous]` write endpoints (`UpdateItemStock`, Excel chunked upload) are
    deliberately public-facing (ERP webhook, pre-auth upload) or an oversight — open question already
    carried in [[_knowledge-graph|the KG note]].
