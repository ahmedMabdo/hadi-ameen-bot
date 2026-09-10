---
id: 8orders/delivery/delivery-man-operations/scenarios
title: Delivery Man Operations — Scenario Catalog
note_type: scenarios
context: Delivery
feature: Delivery Man Operations
audience: Business · QA · Developer
last_updated: 2026-08-23
sources:
  - path: TalabatkDelivery/Controllers/Apis/DeliveryManController.cs
    sha1: f6730a77316a
  - path: TalabatkDelivery/Controllers/Apis/AutoAssignController.cs
    sha1: ae7b2e3e5fa5
  - path: TalabatkDelivery/Controllers/Apis/ShiftController.cs
    sha1: 4819f858c03f
  - path: TalabatkDelivery/Controllers/Apis/DeliveryManMaps/DeliveryManMapsController.cs
    sha1: 4a323bfac4f7
  - path: Shared/TalabatkLogic/Enum/DeliveryManStatus.cs
    sha1: 5668801a8889
  - path: Shared/TalabatkLogic/Enum/AutoAssignRequestStatus.cs
    sha1: f60ff15d4118
  - path: Shared/TalabatkLogic/Enum/AssignOrderTaskStatus.cs
    sha1: 897cf8d5f29b
tags: [delivery, delivery-man-operations, scenarios]
---
# Delivery Man Operations — Scenario Catalog

> The driver's working day, as the code implements it. Rule detail lives in
> [[Delivery/Delivery Man Operations/_knowledge-graph|the technical note]] and on
> [[DeliveryMen.technical|DeliveryMen]] / [[OrderDelivery.technical|OrderDelivery]]; this catalog is the
> behaviour a regression suite has to hold.

## The three status vocabularies in play

| Enum | Values | Where |
|---|---|---|
| `DeliveryManStatus` | `Available`(1) · `Busy`(2) · `Unavailable`(3) · `OffLine`(4) | `Shared/TalabatkLogic/Enum/DeliveryManStatus.cs:5-10` |
| `AutoAssignRequestStatus` | `Pending` · `Accepted` · `Rejected` (implicit 0,1,2) | `Shared/TalabatkLogic/Enum/AutoAssignRequestStatus.cs:5-9` |
| `AssignOrderTaskStatus` | `Active`(1) · `Resolved`(2) | `Shared/TalabatkLogic/Enum/AssignOrderTaskStatus.cs:5-8` |

`AutoAssignRequestStatus` has **no explicit values**, so it is 0/1/2 — the only status enum in the
delivery domain that relies on declaration order. Reordering its members silently changes stored data.

## Happy path

| # | Precondition | Action | Expected outcome | Rule / source |
|---|---|---|---|---|
| H1 | Driver signed in, shift active | `GET api/DeliveryManController/GetActiveShifts` | The driver's current shift(s) | `TalabatkDelivery/Controllers/Apis/DeliveryManController.cs:237` |
| H2 | Driver on shift, near a restaurant | `GET api/DeliveryMan/Requests` with lat/long | Nearby available delivery requests | `TalabatkDelivery/Controllers/Apis/DeliveryManController.cs:134` |
| H3 | Request offered | `POST api/DeliveryMan/AssignToDeliveryRequest` | The order is assigned to this driver | `TalabatkDelivery/Controllers/Apis/DeliveryManController.cs:532` |
| H4 | Assigned | `POST api/DeliveryMan/ViewOrderDelivery` | Driver marked as having seen it | `TalabatkDelivery/Controllers/Apis/DeliveryManController.cs:587` |
| H5 | Driver at the restaurant | `GET api/DeliveryMan/DeliveryManAroundTheRestaurant` with lat/long | Geofence-style arrival confirmation | `TalabatkDelivery/Controllers/Apis/DeliveryManController.cs:998` |
| H6 | Food ready | `POST api/DeliveryMan/PickUpOrder` | Order picked up; branches on the `MultipleDeliveries` flag to choose the command | `TalabatkDelivery/Controllers/Apis/DeliveryManController.cs:687`, flag branch at `:692-725` |
| H7 | En route | `POST api/DeliveryMan/ChangeDeliveryManOrderStatusToOnWay` | Status moves to on-way; customer tracking updates | `TalabatkDelivery/Controllers/Apis/DeliveryManController.cs:805` |
| H8 | Delivered | `POST api/DeliveryManController/ChangeDeliveryManOrderStatusToDelivered` | Delivery completed; driver ledger and cash position recalculated | `TalabatkDelivery/Controllers/Apis/DeliveryManController.cs:766`; [[Money-Path.technical\|The Money Path]] step 8 |
| H9 | Driver moving | `POST …/DeliveryManMaps/AddDeliveryManLocation` | Location recorded for live tracking | `TalabatkDelivery/Controllers/Apis/DeliveryManMaps/DeliveryManMapsController.cs` (`AddDeliveryManLocation`) |
| H10 | Auto-assign offers a request | `POST api/AutoAssign/AcceptRequest` | `AutoAssignRequestStatus` → `Accepted` | `TalabatkDelivery/Controllers/Apis/AutoAssignController.cs` |
| H11 | Driver ends the day | `POST api/DeliveryMan/ChangeDeliveryManActivation` | Driver goes unavailable/offline | `TalabatkDelivery/Controllers/Apis/DeliveryManController.cs:832` |

## Partial / incremental

| # | Precondition | Action | Expected outcome | Rule / source |
|---|---|---|---|---|
| P1 | `MultipleDeliveries` flag **on** | `POST api/DeliveryMan/NewDeliveryRequest` | A second order can be added to a driver already carrying one | `TalabatkDelivery/Controllers/Apis/DeliveryManController.cs:616`, flag check at `:621-633` |
| P2 | `MultipleDeliveries` flag **off** | same | **Rejected with an Arabic message** rather than a status code a client can branch on | `TalabatkDelivery/Controllers/Apis/DeliveryManController.cs:621-633` |
| P3 | Two drivers split one order's cash | `SendDeliveryManRequestMoney` → `SendMoneyToDeliveryMan` → `ConfirmReceivingMoney` | A three-step handshake; the money is only settled after the third step | `TalabatkDelivery/Controllers/Apis/DeliveryManController.cs:880`, `:903`, `:926` |
| P4 | Driver takes a break mid-shift | `StartBreak` … `EndBreak` | Break logged; a reminder push is scheduled for shortly before the break ends | `_integrations.md` row 21 |
| P5 | Break ends early | `EndBreak` | The scheduled reminder is cancelled using the job id stored on the break log | `_integrations.md` row 21 |
| P6 | Driver's app is on a slow connection | `GET api/DeliveryMan/GetAssignedOrderPaging` | Branches on the `DeliverymenOrdersV1` flag between two query versions | `TalabatkDelivery/Controllers/Apis/DeliveryManController.cs:283`, flag branch at `:292-315` |
| P7 | Supervisor sees a stuck order | `POST api/DeliveryMan/SuperVisorReAssignOrder` | Re-assigned to another driver | `TalabatkDelivery/Controllers/Apis/DeliveryManController.cs:983` |

## Negative / guard

| # | Precondition | Action | Expected outcome (rejection) | Rule / source |
|---|---|---|---|---|
| N1 | No token | any driver API action | 401 — JWT bearer at class level | `TalabatkDelivery/Controllers/Apis/DeliveryManController.cs` class attribute |
| N2 | Token without the `deliveryman` role | role-gated driver actions | 403 | `TalabatkDelivery/Controllers/Apis/DeliveryManController.cs` (role-gated subset) |
| N3 | Order too far from the driver | `GET api/DeliveryMan/CheckOrderDistance` | Distance check answers before assignment is attempted | `TalabatkDelivery/Controllers/Apis/DeliveryManController.cs:560` |
| N4 | Delivery failed | `ChangeDeliveryManOrderStatusToDelivered` with a not-delivered reason + flag | Recorded as not delivered with a reason from the active reason list | `TalabatkDelivery/Controllers/Apis/DeliveryManController.cs:766`; reasons at `TalabatkDelivery/Controllers/Apis/NonDeliveryReasons/NonDeliveryReasonsController.cs` |
| N5 | Invalid `OrderId` | `POST api/DeliveryMan/SuperVisorReAssignOrder` | **Unhandled exception** — the handler dereferences a `FirstOrDefaultAsync` result with no null check | 🔴 `SuperVisorReAssignOrderToAnotherDeliveryManCommand.cs:33-34` |
| N6 | `RestaurantId` mismatched against the order | `POST api/DeliveryMan/PickUpOrder` | **Unhandled exception** in a logging-only lookup, while the same lookup ten lines later is correctly null-checked | 🔴 `PickUpOrderCommand.cs:113-114` vs `:135-139` |
| N7 | `AutoAssignRequestStatus` already `Accepted` | `POST api/AutoAssign/RejectRequest` | Transition validity not traced in this pass — treat as unverified | `TalabatkDelivery/Controllers/Apis/AutoAssignController.cs` |

## Returns / cancellation / reversal

| # | Precondition | Action | Expected outcome | Rule / source |
|---|---|---|---|---|
| R1 | Driver rejects an offered request | `POST api/AutoAssign/RejectRequest` | `AutoAssignRequestStatus` → `Rejected`; the request returns to the pool | `TalabatkDelivery/Controllers/Apis/AutoAssignController.cs` |
| R2 | Order assigned to the wrong driver | `POST …/DeliveryManMaps/SwapOrderDelivery` or `ReAssignOrdertoDeliveryMan` | Re-assignment from the operations map | `TalabatkDelivery/Controllers/Apis/DeliveryManMaps/DeliveryManMapsController.cs` |
| R3 | Delivery attempted and failed | not-delivered reason (N4) | The order does not become delivered; compensation rules may apply | [[Compensation\|Compensation]] |
| R4 | Money handshake abandoned midway | — | No cancel step exists in the three-step flow; the request simply stays open | `TalabatkDelivery/Controllers/Apis/DeliveryManController.cs:880`, `:903`, `:926` |

## Integration (cross-side / cross-context)

| # | Precondition | Action | Expected outcome | Rule / source |
|---|---|---|---|---|
| I1 | Order ready at the restaurant | Restaurant Portal marks ready-to-pickup | The order becomes visible to drivers — see [[Restaurant Portal/Menu & Order Management/_knowledge-graph\|Menu & Order Management]] | `_integrations.md` rows 1–2 |
| I2 | Driver delivers | domain event | `RequiredPayment` / `ExceededCashLimit` recalculated on the driver record | [[Money-Path.technical\|The Money Path]] step 8 |
| I3 | Break started | Hangfire delayed job | Break-ending reminder pushed via FCM; job id stored for cancellation | `_integrations.md` row 21 |
| I4 | City exceeds its timed-out-delivery threshold | rush mode entered | A self-rescheduling job keeps checking until the count falls | `_integrations.md` rows 23–24 |
| I5 | Auto-assign job triggered manually | `POST api/BackgroundJobs/TriggerAutoAssignJob` on the identity host | Same assignment job Hangfire runs on a schedule — reachable by any authenticated principal | 🔴 `_conflicts.md` #615; [[Identity & Access/Ops & Infra/_knowledge-graph\|Ops & Infra]] |
| I6 | Announcement or notification published | Admin authors it | Driver reads it via `GetAllDeliveryAnnouncementsForMob` / `Notifications` | [[DeliveryAnnouncement.technical\|DeliveryAnnouncement]], [[DeliveryManNotification.technical\|DeliveryManNotification]] |
| I7 | Driver location recorded | live tracking | Feeds the operations map and the customer's tracking view | `TalabatkDelivery/Controllers/Apis/DeliveryManMaps/DeliveryManMapsController.cs` |

## Fragility scenarios — current behaviour worth testing

| # | Precondition | Action | Actual outcome today | Source |
|---|---|---|---|---|
| X1 | Supervisor re-assigns with a bad order id | `SuperVisorReAssignOrder` | Unhandled exception rather than a validation error | 🔴 `SuperVisorReAssignOrderToAnotherDeliveryManCommand.cs:33-34` |
| X2 | Pickup with a restaurant id not on the order | `PickUpOrder` | Unhandled exception in a **log-only** lookup — the feature fails for the sake of a log line | 🔴 `PickUpOrderCommand.cs:113-114` |
| X3 | `MultipleDeliveries` off, client expects a code | `NewDeliveryRequest` | Arabic prose message; a client branching on a code cannot tell this from other failures | `TalabatkDelivery/Controllers/Apis/DeliveryManController.cs:621-633` |
| X4 | Three overlapping "assigned orders" endpoints | `GetAssignedOrder`, `…Paging`, `…Optimized` | All three live at different maturity levels; which the current app build calls is unconfirmed | `TalabatkDelivery/Controllers/Apis/DeliveryManController.cs:207`, `:283`, `:332` |
| X5 | `AutoAssignRequestStatus` reordered in a future edit | — | Stored values shift meaning, because the enum has no explicit numbering | `Shared/TalabatkLogic/Enum/AutoAssignRequestStatus.cs:5-9` |

## Open Questions

- [ ] Which of the three "assigned orders" endpoints does the shipped driver app call (X4)? The other
      two are candidates for removal, and one of them branches on a feature flag.
- [ ] Are `AutoAssignRequestStatus` transitions guarded (N7)? Can a rejected request be accepted later?
- [ ] Is there any cancel step for the driver-to-driver money handshake (R4)?
- [ ] `DeliveryManStatus` has four values — which endpoint sets `Busy` versus `Unavailable`, and is
      `OffLine` set by the app or inferred from silence?
- [ ] Does the location endpoint's `_V1` variant differ in payload or in behaviour?
- [ ] How often does the driver app post its location, and is there a rate limit? An always-on tracker
      is the highest-volume write path in the system.
