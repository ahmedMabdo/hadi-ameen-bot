---
id: 8orders/delivery/delivery-man-operations/knowledge-graph
note_type: knowledge-graph
context: Delivery
feature: Delivery Man Operations
sources:
  - path: TalabatkDelivery/Controllers/MVC/DeliveryReasons/DeliveryReasonsController.cs
    sha1: cb1eb0f54d20
  - path: TalabatkDelivery/Controllers/MVC/DeliveryMenShift/DeliveryMenShiftController.cs
    sha1: 2fb9e64df60b
  - path: TalabatkDelivery/Controllers/MVC/DeliveryManMaps/DeliveryMenLocationController.cs
    sha1: 37b5ce31cd5b
  - path: TalabatkDelivery/Controllers/MVC/DeliveryManMaps/DeliveryManShiftController.cs
    sha1: 80ddaec715f6
  - path: TalabatkDelivery/Controllers/MVC/DeliveryManMaps/DeliveryManMapsController.cs
    sha1: bc040712d392
  - path: TalabatkDelivery/Controllers/Apis/Restaurant/RestaurantController.cs
    sha1: 00a386220113
  - path: TalabatkDelivery/Controllers/Apis/NonDeliveryReasons/NonDeliveryReasonsController.cs
    sha1: ddd483560d20
  - path: TalabatkDelivery/Controllers/Apis/DeliveryManMaps/DeliveryManMapsController.cs
    sha1: 4a323bfac4f7
  - path: Shared/TalabatkApplication/Commands/SuperVisorReAssignOrderToAnotherDeliveryManCommand/SuperVisorReAssignOrderToAnotherDeliveryManCommand.cs
    sha1: 06bb3647d2a0
  - path: TalabatkDelivery/Controllers/Apis/AutoAssignController.cs
    sha1: ae7b2e3e5fa5
  - path: TalabatkDelivery/Controllers/Apis/DeliveryManController.cs
    sha1: f6730a77316a
  - path: TalabatkDelivery/Controllers/Apis/ShiftController.cs
    sha1: 4819f858c03f
last_updated: 2026-08-23
---
# Delivery Man Operations — Knowledge Graph

> **Context:** Delivery (`TalabatkDelivery`)
> **Source Project:** `TalabatkDelivery/Controllers/`
> **Last Updated:** 2026-08-03

## Controller Inventory

### ShiftController (`Apis/ShiftController.cs`) — shift definitions (admin/supervisor-facing)
`GetShifts`, `GetShiftById`, `AddShift`, `UpdateShift`. **Confirmed bug:** `ValidateStartEndTime`
(`:112-130`) enforces an **18-hour** cap (`duration.TotalHours > 18` fails) but its own message says
"within 12 hours" (`:122`) — see `_system/_conflicts.md` #30. Overnight-crossing shifts are handled
by adding a day to the end time before computing duration (`:117`).

### DeliveryManController (`Apis/DeliveryManController.cs`) — the delivery man's main self-service API, ~45 routes
Grouped by area (not every route individually cited — the underlying business rules for most of these
live on [[DeliveryMen.technical|DeliveryMen]],
[[OrderDelivery.technical|OrderDelivery]], and
[[DeliverymanTransaction.technical|DeliverymanTransaction]], already
documented from the shared-entity side):
- **Requests & assignment:** `Requests` (nearby available requests by lat/long), `AssignToDeliveryRequest`,
  `NewDeliveryRequest` (gated by the `MultipleDeliveries` feature flag, `:621-633` — rejects with an
  Arabic message if the flag is off), `CheckOrderDistance`, `AssigneOrderToDeliveryMan`,
  `SuperVisorReAssignOrder`. **Application layer, `SuperVisorReAssignOrderToAnotherDeliveryManCommand`
  (now opened, Phase 8) — confirmed bug:** dereferences `order` (`FirstOrDefaultAsync`) with **no
  null-check at all**, not even wrapped in a try/catch — an invalid `OrderId` throws unhandled.
  **Source:** `SuperVisorReAssignOrderToAnotherDeliveryManCommand.cs:33-34`.
- **Order lifecycle:** `ChangeOrderStatus`, `ChangeStatusToDeliveryManView`, `ViewOrderDelivery`,
  `DeliveryManReceiveOrder`/`PickUpOrder` (`PickUpOrder` branches on the same `MultipleDeliveries` flag
  to pick which command to dispatch, `:692-725`), `ChangeDeliveryManOrderStatusToDelivered` (accepts a
  not-delivered reason + flag), `ChangeDeliveryManOrderStatusToOnWay`, `DeliveryManAroundTheRestaurant`
  (geofence-style arrival check by lat/long).
  **Application layer, `PickUpOrderCommand` (now opened, Phase 8) — confirmed bug:** `restLocation`
  (`order.OrderRestaurantDetails.FirstOrDefault(x => x.RestaurantId == request.RestaurantId).RestaurantLocation`,
  `:113-114`, used only for a log statement) dereferences the `FirstOrDefault` result with no
  null-check — a mismatched `RestaurantId` throws here. The command's own pickup-image branch just a
  few lines later (`:135-139`) does the identical lookup and correctly null-checks it before use,
  confirming this earlier one is a genuine gap rather than an intentional non-null invariant. Same
  shape as `_conflicts.md` #58/#59/#61/#65/#66/#67/#82/#83/#86/#91.
- **Multi-delivery-man money exchange:** `SendDeliveryManRequestMoney`, `SendMoneyToDeliveryMan`,
  `ConfirmReceivingMoney` — a three-step handshake (request → send → confirm) between delivery men
  splitting one order, distinct from the customer-facing cash flow.
- **Shift/activation/break:** `GetActiveShifts`, `ChangeDeliveryManActivation` (+ a `V1` variant —
  same versioned-route pattern seen elsewhere in this codebase), `StartBreak`, `EndBreak`,
  `GetBreakOptions`, `GetCurrentBreak`, `InternetOffline`.
- **Earnings/profile:** `Balance`, `Rate`, `GetDeliverymanStatement`, `GetCompletedOrdersByDeliveryManId`,
  `GetAllDeliveryMoneyRequests`, `GetAllNeedMoneyReceivingConfirmation`, `DeliveryInfo`,
  `SaveDeliverymanAttributes`, `ChangePreferredLanguage`, `AddDeviceIds`/`RemoveDeviceIds`.
- **Announcements/notifications:** `GetAllDeliveryAnnouncementsForMob`, `Notifications`,
  `MarkNotifcationAsRead`, `DeleteAllNotifications`, `DeleteNotification` — the mobile-facing
  read side of [[DeliveryAnnouncement-and-Notification\|DeliveryAnnouncement &
  DeliveryManNotification]].
- **Paging/optimization:** three near-parallel "get assigned orders" routes
  (`GetAssignedOrderPaging`, `GetAssignedOrderOptimized`, and the older non-paged `GetAssignedOrder`)
  — `GetAssignedOrderPaging` itself branches on a `DeliverymenOrdersV1` feature flag between two query
  versions (`:292-315`). Three overlapping ways to fetch the same data, at different maturity stages —
  not confirmed which the current app build actually calls.

### AutoAssignController (`Apis/AutoAssignController.cs`)
A separate accept/reject queue distinct from `DeliveryManController`'s direct request flow:
`GetPendingRequests`, `AcceptRequest`, `RejectRequest` — thin MediatR wrappers, no embedded business
logic in the controller itself.

### Other controllers (route lists not individually inventoried — light per this pass's depth budget)
`RestaurantController`, `CustomerUserController` (delivery-man-side customer lookups during a
delivery, distinct from `TalabatkAPIs`'/`TalabatkDelivery`'s own of the same name), `FawryController`
(payment-provider integration), `NonDeliveryReasonsController`, `DeliveryReasonsController` (MVC),
`DeliveryMenShiftController`/`DeliveryManShiftController`/`DeliveryMenLocationController`/
`DeliveryManMapsController` (MVC/API pairs, presumably supervisor-facing maps/shift views),
`DeliveryManAdminChatController`, `ChatController`, `CentrifugoController` (real-time chat transport),
`FeatureMangamentController`, `TawkToController`, `HealthController`, `HomeController`.

## Entity Index
| Entity | Layer | Type | Responsibility |
|--------|-------|------|-----------------|
| `DeliveryMen` | Backend-Domain | Hub | Already documented, Identity & Access |
| `OrderDelivery` | Backend-Domain | Transactional | Already documented, Delivery |
| `DeliverymanTransaction` | Backend-Domain | Ledger | Already documented, Delivery |

## Related
- [[DeliveryMan-Attendance|DeliveryMan Attendance & Shifts]]
- [[Delivery-Assignment-Strategies|Delivery Assignment Strategies]]

## Phase 2 gap-fill (2026-08-03)
- **`DeliveryManShiftController` (MVC, admin-facing shift management) confirmed to have the exact
  same 18-hour/"12 hours" message bug as the API `ShiftController`** — see `_system/_conflicts.md`
  #30 (now cites both copies). This is the MVC counterpart admins use to create/edit shifts;
  `ShiftController` (API) is presumably used by a different (older or mobile-admin) client — not
  confirmed which is actually live.
- `RestaurantController` (API) — thin, versioned pair (`GetRestaurantInfoByRestaurantId` v1 /
  `GetRestaurantInfo` v2), no embedded logic.
- `FawryController` — Fawry cash-collection payment integration relay (`InitiateFawryTransaction`,
  `FawryPaymentCallback`, `BillFawryInqiryRequest`, `FawryPaymentNotify`), thin MediatR wrappers.
- `CustomerUserController` (delivery-man-side) — two thin read-only endpoints for looking up
  customer info/address during a delivery, no embedded logic.
## Phase 2 gap-fill, part 2 (2026-08-03) — remaining 14 files, now genuinely 100% read
- **`FeatureMangamentController` (`Apis/FeatureMangamentController/`)** — an **exact duplicate** of the
  same thin `features?featureName=X` → `GetFeatureFlagQuery` pattern already confirmed in
  `Talabatk.IDS` and `TalabatkRestaurants`. This is now the **4th confirmed copy** of this identical
  duplicate endpoint across hosts — see `_system/_conflicts.md` #39 (updated).
- **Two structurally distinct, non-overlapping delivery-man chat systems**, both real-time via
  Centrifugo tokens but serving different counterparties:
  - `DeliveryManAdminChatController` (`Apis/`) — delivery man ↔ **admin dispatch** chat.
    `GetChatConfig`, `GenerateToken` (via `GenerateDeliveryManAdminTokenCommand`),
    `ChangeOnlineStatus`, `History`, `GetAllChats`/`GetActiveChats`, `SaveImage`, `EndChat` (notifies
    admin browser via `INotifyAdminInBrowser` on delivery-man-initiated end), `RateChat`.
  - `ChatController` (`Apis/`) — delivery man ↔ **customer** chat (the delivery-man side of the
    customer-facing delivery chat). `GenerateToken` (via `GenerateCentrifugalTokenCommand`, a
    *different* token-generation command than the admin-chat one), `ChangeChatOnlineValueForDeliveryMan`,
    `SaveChatImage`, `History` (via `GetCustomerDeliveryChatHistoryQuery`).
  - **`CentrifugoController`'s inbound webhook (`api/centrifugo/publish`) only routes messages on
    channels prefixed `"DeliveryManAdmin_"`** into `HandleDeliveryManAdminProxyMessagesCommand` — there
    is no equivalent routing branch for whatever channel prefix the customer-chat (`ChatController`)
    side uses. Not confirmed whether customer-chat proxy messages are handled by a different webhook
    entirely, silently dropped, or handled by Centrifugo's own default relay without needing a custom
    command — worth a follow-up rather than assuming either way.
- **`DeliveryMenLocationController` (MVC, `admin/DeliveryManMaps/DeliveryMenLocation`)** — the main
  admin dispatch map page. Resolves initial city/country/delivery-zone context two ways depending on
  whether an `orderCode` is passed in (`HandleCitiesAndCountriesWithOrderCode` vs.
  `...WithoutOrderCode`, falling back to the latter if the order code doesn't resolve). Surfaces two
  feature flags to the view: `DeliveryReAssignOrder` and `MultipleDeliveries`. Hardcodes
  `HurgahdaCItyId = 1` as the default city when no order context is available.
- **`DeliveryManMapsController` (MVC, `admin/DeliveryManMaps`)** — the actual admin dispatch/assignment
  API behind the map page above: `GetDeliveryManOrders`, `CountryCities`, `CityDeliveryZones`,
  `GetDeliveryMenLocation` (branches on the `CachedLocations` feature flag between
  `GetDeliveryMenLocationQueryV1`/non-V1 — **a versioned pair that's a live, intentional
  feature-flagged rollout**, unlike other versioned pairs in this codebase whose live/dead status is
  unclear), `GetDeliveryMenQuery`, `AdminOrderDeliveries`, `AssignDeliveryManToRequest`,
  `AssignOrdertoDeliveryMan`, `SwapOrderDelivery`, `ReAssignOrdertoDeliveryMan`, `ChangeAssignedOrder`,
  `GetAllDeliveryMenByOrderId`, `GetDeliveryManLocationById`, `GetOrderLocationsByOrderId`,
  `SearchOrderByCode` — all thin MediatR wrappers, ties directly into
  [[Delivery-Assignment-Strategies|Delivery Assignment Strategies]].
- **`DeliveryManMapsController` (Apis, `api/DeliveryManMaps`, delivery-man-side)** — distinct from the
  admin-side controller of the same class name above (different namespace/route prefix).
  `AddDeliveryManLocation` has an unflagged `_V1` sibling route (`AddDeliveryManLocation_V1`) — unlike
  the `CachedLocations`-gated pair above, no feature flag visibly selects between them; not confirmed
  whether `_V1` is legacy/dead or used by an older mobile app build still in the field. Also
  `GetZoneDeliveredOrderDensity` (a heatmap-style density query, not previously documented).
- `AutoAssignController`, `NonDeliveryReasonsController` (Apis), `TawkToController`, `HomeController`
  (standard IdentityServer4-cookie-auth login/logout page, thin), `DeliveryMenShiftController` (MVC,
  shift-to-delivery-man assignment CRUD — add/remove from shift, activation toggle/reverse), `DeliveryReasonsController`
  (MVC, plain CRUD for delivery-rejection reasons), `CentrifugoController` (webhook relay, see above),
  `HealthController` — all thin, no embedded business logic beyond what's noted above.

**Phase 2 is now complete: all 21 files in `TalabatkDelivery/Controllers/` have been read.**

<!-- BEGIN generated: endpoint index (insert-endpoints.js) -->

## Endpoint index — generated from the controllers

> Generated by `_system/insert-endpoints.js` from `_feature-map.tsv`; do not edit between the
> sentinels. Every row is anchored to a line, so `verify-citations.js` checks all of it and a
> controller that moves is caught on the next run. "Action gate" lists only attributes on the action
> itself — the class gate above each table still applies unless an action opts out of it.

**11 controller(s), 106 action(s)** — 2 carry `[AllowAnonymous]`; 56 have no action-level gate and rely entirely on the class attribute.

#### `TalabatkDelivery/Controllers/Apis/AutoAssignController.cs`

Class gate: JWT bearer — `TalabatkDelivery/Controllers/Apis/AutoAssignController.cs:19`

| Route | Verb | Action gate | Anchor |
|---|---|---|---|
| `api/AutoAssign/GetPendingRequests` | GET | — | `TalabatkDelivery/Controllers/Apis/AutoAssignController.cs:33` |
| `api/AutoAssign/AcceptRequest` | POST | — | `TalabatkDelivery/Controllers/Apis/AutoAssignController.cs:54` |
| `api/AutoAssign/RejectRequest` | POST | — | `TalabatkDelivery/Controllers/Apis/AutoAssignController.cs:84` |

#### `TalabatkDelivery/Controllers/Apis/DeliveryManController.cs`

Class gate: JWT bearer — `TalabatkDelivery/Controllers/Apis/DeliveryManController.cs:73`

| Route | Verb | Action gate | Anchor |
|---|---|---|---|
| `api/DeliveryManController/GetAllDeliveryMen` | GET | — | `TalabatkDelivery/Controllers/Apis/DeliveryManController.cs:95` |
| `api/DeliveryManController/zones` | GET | — | `TalabatkDelivery/Controllers/Apis/DeliveryManController.cs:115` |
| `api/DeliveryMan/Requests` | GET | — | `TalabatkDelivery/Controllers/Apis/DeliveryManController.cs:137` |
| `api/DeliveryMan/ActiveShiftBouns` | GET | — | `TalabatkDelivery/Controllers/Apis/DeliveryManController.cs:163` |
| `api/DeliveryMan/GetActiveDeliveryBounsMessage` | GET | — | `TalabatkDelivery/Controllers/Apis/DeliveryManController.cs:184` |
| `api/DeliveryManController/GetAssignedOrder` | GET | role `deliveryman` | `TalabatkDelivery/Controllers/Apis/DeliveryManController.cs:209` |
| `api/DeliveryManController/GetActiveShifts` | GET | role `deliveryman` | `TalabatkDelivery/Controllers/Apis/DeliveryManController.cs:239` |
| `api/DeliveryManController/GetAvalibleConfirmedOrder` | GET | role `deliveryman` | `TalabatkDelivery/Controllers/Apis/DeliveryManController.cs:258` |
| `api/DeliveryMan/GetAssignedOrderPaging` | GET | role `deliveryman` | `TalabatkDelivery/Controllers/Apis/DeliveryManController.cs:285` |
| `api/DeliveryMan/GetAssignedOrderOptimized` | GET | — | `TalabatkDelivery/Controllers/Apis/DeliveryManController.cs:333` |
| `api/DeliveryMan/GetDeliveredOrdersPaging` | GET | role `deliveryman` | `TalabatkDelivery/Controllers/Apis/DeliveryManController.cs:368` |
| `api/DeliveryMan/GetPrimmaryContactInfo` | GET | role `deliveryman` | `TalabatkDelivery/Controllers/Apis/DeliveryManController.cs:393` |
| `api/DeliveryMan/AddDeviceIds` | POST | role `deliveryman` | `TalabatkDelivery/Controllers/Apis/DeliveryManController.cs:417` |
| `api/DeliveryMan/RemoveDeviceIds` | POST | role `deliveryman` | `TalabatkDelivery/Controllers/Apis/DeliveryManController.cs:440` |
| `api/DeliveryManController/ChangeOrderStatus` | GET | role `deliveryman` | `TalabatkDelivery/Controllers/Apis/DeliveryManController.cs:464` |
| `api/DeliveryManController/ChangeStatusToDeliveryManView` | POST | role `deliveryman` | `TalabatkDelivery/Controllers/Apis/DeliveryManController.cs:497` |
| `api/DeliveryMan/AssignToDeliveryRequest` | POST | role `deliveryman` | `TalabatkDelivery/Controllers/Apis/DeliveryManController.cs:534` |
| `api/DeliveryMan/CheckOrderDistance` | GET | role `deliveryman` | `TalabatkDelivery/Controllers/Apis/DeliveryManController.cs:562` |
| `api/DeliveryMan/ViewOrderDelivery` | POST | role `deliveryman` | `TalabatkDelivery/Controllers/Apis/DeliveryManController.cs:589` |
| `api/DeliveryMan/NewDeliveryRequest` | POST | role `deliveryman` | `TalabatkDelivery/Controllers/Apis/DeliveryManController.cs:618` |
| `api/DeliveryManController/DeliveryManReceiveOrder` | POST | role `deliveryman` | `TalabatkDelivery/Controllers/Apis/DeliveryManController.cs:662` |
| `api/DeliveryMan/PickUpOrder` | POST | role `deliveryman` | `TalabatkDelivery/Controllers/Apis/DeliveryManController.cs:690` |
| `api/DeliveryMan/AssigneOrderToDeliveryMan` | POST | role `deliveryman` | `TalabatkDelivery/Controllers/Apis/DeliveryManController.cs:744` |
| `api/DeliveryManController/ChangeDeliveryManOrderStatusToDelivered` | POST | role `deliveryman` | `TalabatkDelivery/Controllers/Apis/DeliveryManController.cs:769` |
| `api/DeliveryMan/ChangeDeliveryManOrderStatusToOnWay` | POST | role `deliveryman` | `TalabatkDelivery/Controllers/Apis/DeliveryManController.cs:807` |
| `api/DeliveryMan/ChangeDeliveryManActivation` | POST | role `deliveryman` | `TalabatkDelivery/Controllers/Apis/DeliveryManController.cs:835` |
| `api/DeliveryMan/ChangeDeliveryManActivationV1` | POST | role `deliveryman` | `TalabatkDelivery/Controllers/Apis/DeliveryManController.cs:863` |
| `api/DeliveryMan/SendDeliveryManRequestMoney` | POST | role `deliveryman` | `TalabatkDelivery/Controllers/Apis/DeliveryManController.cs:883` |
| `api/DeliveryMan/SendMoneyToDeliveryMan` | POST | role `deliveryman` | `TalabatkDelivery/Controllers/Apis/DeliveryManController.cs:906` |
| `api/DeliveryMan/ConfirmReceivingMoney` | POST | role `deliveryman` | `TalabatkDelivery/Controllers/Apis/DeliveryManController.cs:929` |
| `api/DeliveryMan/Configuration` | GET | role `deliveryman` | `TalabatkDelivery/Controllers/Apis/DeliveryManController.cs:951` |
| `api/DeliveryMan/SuperVisorDeliveryMen` | GET | role `deliveryman` | `TalabatkDelivery/Controllers/Apis/DeliveryManController.cs:960` |
| `api/DeliveryMan/GetReadyToPickupOrders` | GET | role `deliveryman` | `TalabatkDelivery/Controllers/Apis/DeliveryManController.cs:972` |
| `api/DeliveryMan/SuperVisorReAssignOrder` | POST | role `deliveryman` | `TalabatkDelivery/Controllers/Apis/DeliveryManController.cs:985` |
| `api/DeliveryMan/DeliveryManAroundTheRestaurant` | POST | role `deliveryman` | `TalabatkDelivery/Controllers/Apis/DeliveryManController.cs:1000` |
| `api/DeliveryMan/DeliveryInfo` | GET | role `deliveryman` | `TalabatkDelivery/Controllers/Apis/DeliveryManController.cs:1018` |
| `api/DeliveryMan/GetDeliverymanStatement` | GET | role `deliveryman` | `TalabatkDelivery/Controllers/Apis/DeliveryManController.cs:1032` |
| `api/DeliveryMan/GetCompletedOrdersByDeliveryManId` | GET | role `deliveryman` | `TalabatkDelivery/Controllers/Apis/DeliveryManController.cs:1048` |
| `api/DeliveryMan/GetAllDeliveryMoneyRequests` | GET | role `deliveryman` | `TalabatkDelivery/Controllers/Apis/DeliveryManController.cs:1067` |
| `api/DeliveryMan/GetAllNeedMoneyReceivingConfirmation` | GET | role `deliveryman` | `TalabatkDelivery/Controllers/Apis/DeliveryManController.cs:1084` |
| `api/DeliveryMan/Balance` | GET | role `deliveryman` | `TalabatkDelivery/Controllers/Apis/DeliveryManController.cs:1102` |
| `api/DeliveryMan/Rate` | GET | role `deliveryman` | `TalabatkDelivery/Controllers/Apis/DeliveryManController.cs:1122` |
| `api/DeliveryMan/DeliveryReasons` | GET | role `deliveryman`, 🔓 **AllowAnonymous** | `TalabatkDelivery/Controllers/Apis/DeliveryManController.cs:1142` |
| `api/DeliveryMan/GetDeliveryMenLogs` | GET | 🔓 **AllowAnonymous** | `TalabatkDelivery/Controllers/Apis/DeliveryManController.cs:1152` |
| `api/DeliveryMan/SaveDeliverymanAttributes` | POST | role `deliveryman` | `TalabatkDelivery/Controllers/Apis/DeliveryManController.cs:1171` |
| `api/DeliveryMan/ChangePreferredLanguage` | POST | role `deliveryman` | `TalabatkDelivery/Controllers/Apis/DeliveryManController.cs:1194` |
| `api/DeliveryMan/Notifications` | GET | role `deliveryman` | `TalabatkDelivery/Controllers/Apis/DeliveryManController.cs:1219` |
| `api/DeliveryMan/MarkNotifcationAsRead` | POST | role `deliveryman` | `TalabatkDelivery/Controllers/Apis/DeliveryManController.cs:1245` |
| `api/DeliveryMan/DeleteAllNotifications` | POST | role `deliveryman` | `TalabatkDelivery/Controllers/Apis/DeliveryManController.cs:1268` |
| `api/DeliveryMan/DeleteNotification` | POST | role `deliveryman` | `TalabatkDelivery/Controllers/Apis/DeliveryManController.cs:1291` |
| `api/DeliveryMan/InternetOffline` | POST | role `deliveryman` | `TalabatkDelivery/Controllers/Apis/DeliveryManController.cs:1311` |
| `api/DeliveryMan/GetAllDeliveryAnnouncementsForMob` | GET | role `deliveryman` | `TalabatkDelivery/Controllers/Apis/DeliveryManController.cs:1332` |
| `api/DeliveryMan/StartBreak` | POST | role `deliveryman` | `TalabatkDelivery/Controllers/Apis/DeliveryManController.cs:1355` |
| `api/DeliveryMan/EndBreak` | POST | role `deliveryman` | `TalabatkDelivery/Controllers/Apis/DeliveryManController.cs:1384` |
| `api/DeliveryMan/GetBreakOptions` | GET | role `deliveryman` | `TalabatkDelivery/Controllers/Apis/DeliveryManController.cs:1408` |
| `api/DeliveryMan/GetCurrentBreak` | GET | role `deliveryman` | `TalabatkDelivery/Controllers/Apis/DeliveryManController.cs:1433` |

#### `TalabatkDelivery/Controllers/Apis/DeliveryManMaps/DeliveryManMapsController.cs`

Class gate: JWT bearer — `TalabatkDelivery/Controllers/Apis/DeliveryManMaps/DeliveryManMapsController.cs:15`

| Route | Verb | Action gate | Anchor |
|---|---|---|---|
| `AddDeliveryManLocation` | POST | — | `TalabatkDelivery/Controllers/Apis/DeliveryManMaps/DeliveryManMapsController.cs:27` |
| `AddDeliveryManLocation_V1` | POST | — | `TalabatkDelivery/Controllers/Apis/DeliveryManMaps/DeliveryManMapsController.cs:38` |
| `ZoneDeliveredOrderDensity` | GET | — | `TalabatkDelivery/Controllers/Apis/DeliveryManMaps/DeliveryManMapsController.cs:51` |

#### `TalabatkDelivery/Controllers/Apis/NonDeliveryReasons/NonDeliveryReasonsController.cs`

Class gate: JWT bearer — `TalabatkDelivery/Controllers/Apis/NonDeliveryReasons/NonDeliveryReasonsController.cs:16`

| Route | Verb | Action gate | Anchor |
|---|---|---|---|
| `activeDriverReasons` | GET | — | `TalabatkDelivery/Controllers/Apis/NonDeliveryReasons/NonDeliveryReasonsController.cs:31` |

#### `TalabatkDelivery/Controllers/Apis/Restaurant/RestaurantController.cs`

Class gate: JWT bearer — `TalabatkDelivery/Controllers/Apis/Restaurant/RestaurantController.cs:15`

| Route | Verb | Action gate | Anchor |
|---|---|---|---|
| `GetRestaurantInfoByRestaurantId` | GET | — | `TalabatkDelivery/Controllers/Apis/Restaurant/RestaurantController.cs:28` |
| `GetRestaurantInfo` | GET | — | `TalabatkDelivery/Controllers/Apis/Restaurant/RestaurantController.cs:51` |

#### `TalabatkDelivery/Controllers/Apis/ShiftController.cs`

Class gate: JWT bearer — `TalabatkDelivery/Controllers/Apis/ShiftController.cs:21`

| Route | Verb | Action gate | Anchor |
|---|---|---|---|
| `list` | GET | — | `TalabatkDelivery/Controllers/Apis/ShiftController.cs:37` |
| `{id}` | GET | — | `TalabatkDelivery/Controllers/Apis/ShiftController.cs:51` |
| `AddShift` | POST | — | `TalabatkDelivery/Controllers/Apis/ShiftController.cs:60` |
| `UpdateShift` | PUT | — | `TalabatkDelivery/Controllers/Apis/ShiftController.cs:90` |

#### `TalabatkDelivery/Controllers/MVC/DeliveryManMaps/DeliveryManMapsController.cs`

Class gate: JWT bearer — `TalabatkDelivery/Controllers/MVC/DeliveryManMaps/DeliveryManMapsController.cs:33`

| Route | Verb | Action gate | Anchor |
|---|---|---|---|
| `GetDeliveryManOrders` | GET | — | `TalabatkDelivery/Controllers/MVC/DeliveryManMaps/DeliveryManMapsController.cs:49` |
| `CountryCities` | GET | — | `TalabatkDelivery/Controllers/MVC/DeliveryManMaps/DeliveryManMapsController.cs:55` |
| `CityDeliveryZones` | GET | — | `TalabatkDelivery/Controllers/MVC/DeliveryManMaps/DeliveryManMapsController.cs:67` |
| `GetDeliveryMenLocation` | GET | — | `TalabatkDelivery/Controllers/MVC/DeliveryManMaps/DeliveryManMapsController.cs:85` |
| `GetDeliveryMen` | GET | — | `TalabatkDelivery/Controllers/MVC/DeliveryManMaps/DeliveryManMapsController.cs:111` |
| `AdminOrderDeliveries` | GET | — | `TalabatkDelivery/Controllers/MVC/DeliveryManMaps/DeliveryManMapsController.cs:135` |
| `AssignDeliveryManToRequest` | POST | — | `TalabatkDelivery/Controllers/MVC/DeliveryManMaps/DeliveryManMapsController.cs:147` |
| `GetAllDeliveryMenByOrderId` | GET | — | `TalabatkDelivery/Controllers/MVC/DeliveryManMaps/DeliveryManMapsController.cs:166` |
| `GetDeliveryManLocationById` | GET | — | `TalabatkDelivery/Controllers/MVC/DeliveryManMaps/DeliveryManMapsController.cs:176` |
| `GetOrderRelatedLocationsById` | GET | — | `TalabatkDelivery/Controllers/MVC/DeliveryManMaps/DeliveryManMapsController.cs:181` |
| `SearchOrderByCode` | GET | — | `TalabatkDelivery/Controllers/MVC/DeliveryManMaps/DeliveryManMapsController.cs:186` |
| `AssignOrdertoDeliveryMan` | POST | — | `TalabatkDelivery/Controllers/MVC/DeliveryManMaps/DeliveryManMapsController.cs:191` |
| `SwapOrderDelivery` | POST | — | `TalabatkDelivery/Controllers/MVC/DeliveryManMaps/DeliveryManMapsController.cs:204` |
| `ReAssignOrdertoDeliveryMan` | POST | — | `TalabatkDelivery/Controllers/MVC/DeliveryManMaps/DeliveryManMapsController.cs:222` |
| `ChangeAssignedOrder` | POST | — | `TalabatkDelivery/Controllers/MVC/DeliveryManMaps/DeliveryManMapsController.cs:239` |

#### `TalabatkDelivery/Controllers/MVC/DeliveryManMaps/DeliveryManShiftController.cs`

Class gate: roleless `[Authorize]` — `TalabatkDelivery/Controllers/MVC/DeliveryManMaps/DeliveryManShiftController.cs:26`

| Route | Verb | Action gate | Anchor |
|---|---|---|---|
| `List` | — | — | `TalabatkDelivery/Controllers/MVC/DeliveryManMaps/DeliveryManShiftController.cs:41` |
| `Add` | GET | — | `TalabatkDelivery/Controllers/MVC/DeliveryManMaps/DeliveryManShiftController.cs:73` |
| `Add` | POST | — | `TalabatkDelivery/Controllers/MVC/DeliveryManMaps/DeliveryManShiftController.cs:94` |
| `Edit` | GET | — | `TalabatkDelivery/Controllers/MVC/DeliveryManMaps/DeliveryManShiftController.cs:132` |
| `Edit` | POST | — | `TalabatkDelivery/Controllers/MVC/DeliveryManMaps/DeliveryManShiftController.cs:169` |

#### `TalabatkDelivery/Controllers/MVC/DeliveryManMaps/DeliveryMenLocationController.cs`

Class gate: roleless `[Authorize]` — `TalabatkDelivery/Controllers/MVC/DeliveryManMaps/DeliveryMenLocationController.cs:20`

| Route | Verb | Action gate | Anchor |
|---|---|---|---|
| `DeliveryMenLocation` | — | — | `TalabatkDelivery/Controllers/MVC/DeliveryManMaps/DeliveryMenLocationController.cs:42` |

#### `TalabatkDelivery/Controllers/MVC/DeliveryMenShift/DeliveryMenShiftController.cs`

Class gate: roleless `[Authorize]` — `TalabatkDelivery/Controllers/MVC/DeliveryMenShift/DeliveryMenShiftController.cs:24`

| Route | Verb | Action gate | Anchor |
|---|---|---|---|
| `GetAllShifts` | GET | — | `TalabatkDelivery/Controllers/MVC/DeliveryMenShift/DeliveryMenShiftController.cs:37` |
| `GetDeliveryMenByShiftId` | GET | — | `TalabatkDelivery/Controllers/MVC/DeliveryMenShift/DeliveryMenShiftController.cs:70` |
| `AddtoShift` | POST | — | `TalabatkDelivery/Controllers/MVC/DeliveryMenShift/DeliveryMenShiftController.cs:79` |
| `RemoveFromShift` | POST | — | `TalabatkDelivery/Controllers/MVC/DeliveryMenShift/DeliveryMenShiftController.cs:88` |
| `ReverseActivation` | POST | — | `TalabatkDelivery/Controllers/MVC/DeliveryMenShift/DeliveryMenShiftController.cs:97` |
| `GetDeliveryMennotinShift` | GET | — | `TalabatkDelivery/Controllers/MVC/DeliveryMenShift/DeliveryMenShiftController.cs:102` |
| `Shift` | GET | — | `TalabatkDelivery/Controllers/MVC/DeliveryMenShift/DeliveryMenShiftController.cs:111` |
| `Delete` | POST | — | `TalabatkDelivery/Controllers/MVC/DeliveryMenShift/DeliveryMenShiftController.cs:118` |
| `UpdateActivation` | POST | — | `TalabatkDelivery/Controllers/MVC/DeliveryMenShift/DeliveryMenShiftController.cs:126` |
| `GetDeliveryMenAsync` | GET | — | `TalabatkDelivery/Controllers/MVC/DeliveryMenShift/DeliveryMenShiftController.cs:135` |

#### `TalabatkDelivery/Controllers/MVC/DeliveryReasons/DeliveryReasonsController.cs`

Class gate: roleless `[Authorize]` — `TalabatkDelivery/Controllers/MVC/DeliveryReasons/DeliveryReasonsController.cs:13`

| Route | Verb | Action gate | Anchor |
|---|---|---|---|
| `Index` | GET | — | `TalabatkDelivery/Controllers/MVC/DeliveryReasons/DeliveryReasonsController.cs:25` |
| `Create` | POST | — | `TalabatkDelivery/Controllers/MVC/DeliveryReasons/DeliveryReasonsController.cs:39` |
| `EditReason` | GET | — | `TalabatkDelivery/Controllers/MVC/DeliveryReasons/DeliveryReasonsController.cs:53` |
| `EditReason` | POST | — | `TalabatkDelivery/Controllers/MVC/DeliveryReasons/DeliveryReasonsController.cs:65` |
| `DeleteReason` | GET | — | `TalabatkDelivery/Controllers/MVC/DeliveryReasons/DeliveryReasonsController.cs:77` |
| `DeleteConfirmed` | POST | — | `TalabatkDelivery/Controllers/MVC/DeliveryReasons/DeliveryReasonsController.cs:85` |

<!-- END generated: endpoint index -->

## Open Questions
- [ ] Which of the three "get assigned orders" route variants (paged/optimized/legacy) the current
  mobile app build actually calls.
- [ ] Whether `ShiftController` (API) or `DeliveryManShiftController` (MVC) is the actually-live path
  for shift management, given both have the same bug independently.
- [ ] Whether `AddDeliveryManLocation_V1` (unflagged) is dead code or still used by an older mobile
  build.
- [ ] How (or whether) customer-chat (`ChatController`) proxy messages get routed server-side, given
  `CentrifugoController`'s webhook only has a branch for `DeliveryManAdmin_`-prefixed channels.
