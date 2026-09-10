---
id: 8orders/restaurant-portal/menu-and-order-management/scenarios
title: Menu & Order Management — Scenario Catalog
note_type: scenarios
context: Restaurant Portal
feature: Menu & Order Management
audience: Business · QA · Developer
last_updated: 2026-08-23
sources:
  - path: TalabatkRestaurants/Controllers/Orders/OrdersController.cs
    sha1: 1f87b4a80401
  - path: TalabatkRestaurants/Controllers/Category/CategoryController.cs
    sha1: 054668a7b620
  - path: TalabatkRestaurants/Controllers/RestaurantNotification/RestaurantNotificationController.cs
    sha1: 3d78948418ba
  - path: TalabatkRestaurants/Helpers/HUBS/StoresHub.cs
    sha1: 0d1beb98c858
  - path: Shared/TalabatkLogic/Enum/RestaurantOrderStatus.cs
    sha1: 0a57e324d4fb
tags: [restaurant-portal, menu-and-order-management, scenarios]
---
# Menu & Order Management — Scenario Catalog

> Precondition → action → what the code does today, with the rule it exercises. The status values are
> `RestaurantOrderStatus` (`New`=100 … `ItemsUnderReplacement`=200); see the technical note for the
> full transition table and for why `OrderStatus` numbers differently.

## Happy path

| # | Precondition | Action | Expected outcome | Rule / source |
|---|---|---|---|---|
| H1 | Store 12 open, menu published | customer places an order | Store's portion created at `New`(100); order pushed to the store's SignalR group | `_integrations.md` rows 1–2; `StoresHub.cs:88-92` |
| H2 | Order at `New` | staff open it | `RestaurantView`(120) | `RestaurantOrderStatus.cs` |
| H3 | Order at `RestaurantView` | `POST ConfirmOrder` (V1) | `Confirmed`(130); `StartCookingForHoldOrder` pushed to the store group | `TalabatkRestaurants/Controllers/Orders/OrdersController.cs:410-466` |
| H4 | Order confirmed | `POST StartCooking` (V1) | `Cooking`(150), restaurant id taken from the session | `OrdersController.cs` (V1 sibling of #585) |
| H5 | Food ready | `POST ReadyToPickupOrder` (V1) | `ReadyToPickUp`(160); driver can collect | `OrdersController.cs` (V1 sibling of #588) |
| H6 | Driver collects | driver app marks pickup | `PickedUp`(170) — terminal for the merchant | [[Delivery/Delivery Man Operations/_knowledge-graph\|Delivery Man Operations]] |
| H7 | Merchant admin, empty category | `POST Category/Add` with own restaurant id | Category created; `GetCurrentRestarunt` confirms the caller may use that restaurant | `TalabatkRestaurants/Controllers/Category/CategoryController.cs:234-280` |
| H8 | Category exists | `POST MenuItems/Insert`, then `ItemPrice/Insert` | Item and its price rows created; visible to customers | `MenuItemsController`, `ItemPriceController` |
| H9 | Item exists | `POST ChangeItemAvailability` | Item hidden from customers without deleting it | `MenuItemsController` |
| H10 | Mart store, ERP holds new quantity | ERP webhook `POST UpdateItemStock` | Stock quantity updated via `EditMartItemQuantityCommand` | `StoreMenuItemsController.cs:241-255`; `_integrations.md` row 19 |
| H11 | Merchant takes a phone order | `POST ExternalDelivery/Requests` | External delivery request raised for one of the caller's own restaurants | `ExternalDeliveryRequestsController.cs` |

## Partial / incremental

| # | Precondition | Action | Expected outcome | Rule / source |
|---|---|---|---|---|
| P1 | Order has 5 lines, 1 unavailable | `POST NotifyCustomerToReplaceItems` | `ItemsUnderReplacement`(200); customer is asked to choose | `OrdersController.cs`; status enum |
| P2 | Customer accepts a replacement | order returns to the cooking path | `Confirmed`(130) → `Cooking`(150) | transition table |
| P3 | Order has 5 lines, 1 unavailable | `POST RejectSomeItemsRestaurant` (V1) | Those lines rejected, the rest proceeds; `OrderDetails.RejectSomeItemsOrderByAvailability` applies | `TalabatkRestaurants/Controllers/Orders/OrdersController.cs:811-879`; [[OrderDetails.technical\|OrderDetails]] Rule 4 |
| P4 | Two restaurants on one customer order | each store works its own portion | Statuses are per `OrderRestaurantDetails`, not per `Order` | technical note ERD |
| P5 | Bulk price change | Excel export → edit → `PreviewPriceUpdateFromExcel` → `Confirm…` | Two-step commit; preview alone changes nothing | `ExportImportExcelController` |
| P6 | Menu reorganisation | `POST MoveItemsToAnotherCategory` | Items move; prices and options follow the item | `MenuItemsController` |

## Negative / guard

| # | Precondition | Action | Expected outcome (rejection) | Rule / source |
|---|---|---|---|---|
| N1 | Staff role without menu rights | any menu write | 403 — 7-role gate on every menu controller | e.g. `MenuItemsController` class attribute |
| N2 | Order already `PickedUp`(170) | `POST StartCooking` | Rejected — no transition out of a terminal merchant state | transition table |
| N3 | Whole order cannot be made | `POST RejectRestaurantOrderOverall` (V1) | `Rejected`(190), reason recorded, store's rejection rate rises | `OrdersController.cs`; feeds `MerchantRejectedReport` |
| N4 | Same, V2 variant fails | `POST RejectRestaurantOrderOverallV2` | Failure is **logged** (`_logger.LogWarning`) — the only action in the controller that does | `TalabatkRestaurants/Controllers/Orders/OrdersController.cs:924-926` |
| N5 | Non-admin merchant, `Category/Add`, id outside `UserRestaurants` | `POST Category/Add` | Rejected by `GetCurrentRestarunt` | `TalabatkRestaurants/Controllers/Category/CategoryController.cs:234-280` |
| N6 | Esquio flag `StoresOptionsCategoryState` off | `GET OptionCategory/OptionsCategoryFeature` | Action filtered out by `[FeatureFilter]` | `OptionCategoryController.cs:51-56`; `_conflicts.md` #44 |
| N7 | External-delivery ids outside the caller's list | `GET ExternalDelivery/ExternalCustomers` | Rejected: "Unauthorised restaurant IDs" | `ExternalDeliveryRequestsController.cs:317-322` |

## Returns / cancellation / reversal

| # | Precondition | Action | Expected outcome | Rule / source |
|---|---|---|---|---|
| R1 | Order at any pre-pickup state | customer or Admin cancels | `Canceled`(180) — the store observes it, does not cause it | transition table |
| R2 | Order confirmed by mistake | `POST UnConfirmOrder` | Returns the order to the pre-confirmation queue | `OrdersController.cs` (`UnConfirmOrder`) |
| R3 | Item deleted in error | no undo | Menu deletes are hard; recovery is re-creation | `MenuItemsController.Delete` |
| R4 | External customer added in error | `POST DeleteExternalCustomer` | Deleted — and see `_conflicts.md` #458: this path has a destructive cross-tenant variant | `ExternalDeliveryRequestsController.cs` |
| R5 | Excel import previewed, not wanted | do nothing | Nothing applied | `ExportImportExcelController` |

## Integration (cross-side / cross-context)

| # | Precondition | Action | Expected outcome | Rule / source |
|---|---|---|---|---|
| I1 | Customer places an order | Customer Ordering raises a domain event | `ApiClientHandler.SendNewOrderForRestaurant` → `RestaurantNotificationController` → `StoresHub` group push → Angular dashboard updates | `_integrations.md` rows 1–2 |
| I2 | Merchant confirms | `_operationHub.Clients.Groups(...).StartCookingForHoldOrder()` | The one hub method that is wired correctly | `StoresHub.cs:88-92`; `TalabatkRestaurants/Controllers/Orders/OrdersController.cs:410-466` |
| I3 | Auto-confirm or reservation cancel fires | `StoresHub.SendAutoConfirmOrder` / `SendCancelReservationRestaurant` | **Both call the wrong client method**; the working path is the controller relay at `RestaurantNotificationController.cs:69-83` | `_conflicts.md` #33 · `StoresHub.cs:95-106` |
| I4 | Order state changes | Admin relay | Same events mirrored to `AdminUi`'s `OperationHub` | `_integrations.md` row 2 |
| I5 | Mart stock changes in ERP | HMAC-signed webhook, scheduled pull, manual sync, or cart-time pull | Four paths converge on `MenuItem.MaintainStock(...)`; path 4 is dormant while `Features.ValidateQuantitiesLocally` is `true` | `_integrations.md` row 19 |
| I6 | Store goes offline | `SendOfflineAlertToResturant` | Pushed through the unauthenticated relay | `_conflicts.md` #41 |
| I7 | Merchant raises external delivery | request enters the delivery pipeline | Picked up by [[Delivery-Requests-and-Suppliers\|Delivery Requests & Suppliers]] | |

## Cross-tenant scenarios — current behaviour

| # | Precondition | Action | Actual outcome today | Finding |
|---|---|---|---|---|
| X1 | Signed in as store 12 | `POST StartCookingV2` with `restaurantId=99` | Store 99's order starts cooking | #585 |
| X2 | Same | `GET GetOrderDetailsV2?restaurantId=99` | Store 99's order detail, incl. a customer-data flag | #586 |
| X3 | Same | `POST ConfirmOrderV2` with `restaurantId=99` | Store 99's order confirmed | #587 |
| X4 | Same | `POST ReadyToPickupOrderV2` with `restaurantId=99` | Store 99's order marked ready | #588 |
| X5 | Same | `POST RejectSomeItemsRestaurantV2` / `RejectRestaurantOrderOverallV2` with another `RestaurantId` | Store 99's order partly or wholly **rejected** — and its rejection rate damaged | #589, #590 |
| X6 | Same | `GET GetRestaurantCookingOrdersV2?restaurantIds=99` | Store 99's live kitchen queue | IDOR #13 |
| X7 | Same | `GET GetOrdersByRestaurantIds?restaurantIds=99` | Store 99's orders — while 10+ siblings scope correctly | IDOR #14 |
| X8 | Same | `GET RestaurantOrdersDailySummaryV2?restaurantIds=99` | Store 99's daily summary | IDOR #31 |
| X9 | Same | `POST MenuItemOptionGroup/Delete` with another store's id | **Another store's option group is deleted** | #595 |
| X10 | Same | `POST ItemPrice/DeleteMenuItemPrice` with another store's id | **Another store's price row is deleted** | #600 |
| X11 | Same | `POST CategoryItemsPrices/ChangeAvalibilty` with another store's id | Another store's item is switched off — a competitor can be hidden from customers | #598 |
| X12 | Same | `POST Category/InsertMenuCategory` with `RestaurantId: 99` | Category created **in store 99's menu** (the sibling `Add` would have refused) | #43 · `TalabatkRestaurants/Controllers/Category/CategoryController.cs:195-230` |
| X13 | Same | `GET Category/AvailableCategoriesToTransfer?menuItemId=<any>` | Resolves any item to its owner and returns that store's categories | IDOR #15 |
| X14 | Same | `GET ItemOption/GetCategoryNamesByRestaurantIdV2?restaurantId=99` | Store 99's category names (the V1 at `:101-103` is scoped) | IDOR #16 |
| X15 | Same | `GET ExternalDelivery/Requests?resturantIds=99` | Another store's external customers — **name, phone, address** | IDOR #4 |
| X16 | **No token** | `POST RestaurantNotification/NewOrder` (or `RejectOrder`, `DelayOrder`, `StartCooking`) | A fake real-time alert is pushed to a restaurant's dashboard; `StartCooking` broadcasts to `Clients.All` | #41 |
| X17 | No token | `GET RestaurantNotification/ReportDetails?orderId=<guess>` | An order's report image | #41 |
| X18 | No token | `POST ExportImportExcel/UploadChunk` | File content written to the server's configured upload path | #42 |
| X19 | No token | `POST StoreMenuItems/UpdateItemStock` | A Mart item's stock quantity is changed | #42 |

## Open Questions

- [ ] Which availability-toggle route does the Angular client use? Three of the four may be dead — and
      dead write endpoints with unscoped ids are still reachable (X11).
- [ ] Is the notification relay reachable from outside the cluster? That single fact decides whether
      X16–X17 are critical or merely wrong.
- [ ] Do `UpdateItemStock` / `UploadChunk` sit behind a gateway allowlist? The ERP webhook on the same
      integration **is** HMAC-signed, so the pattern existed and was not applied.
- [ ] After `PickedUp`(170), can the merchant still act on the order at all? No endpoint observed that
      does, but no guard was read either.
- [ ] `OrderStatus` values 7 and 9 are unused — retired or reserved?
