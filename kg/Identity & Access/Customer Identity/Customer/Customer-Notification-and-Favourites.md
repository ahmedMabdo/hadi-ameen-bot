---
id: 8orders/identity-and-access/customer-identity/customer-notification-and-favourites
note_type: single
rule_count: 9
context: Identity & Access
feature: Customer Identity
sources:
  - path: Shared/TalabatkLogic/TalabatkModels/CustomerNotification.cs
    sha1: 16940ee86722
  - path: Shared/TalabatkLogic/TalabatkModels/Favourites.cs
    sha1: 456585176416
last_updated: 2026-08-23
tags: [identity-access, customer, child, technical, backend-domain]
---
# CustomerNotification (+ Favourites)

Two thin, low-rule-density children of [[Customer.technical|Customer]] — noted briefly rather than
given full two-file treatment, per this graph's depth-scaled-to-rule-density approach.

## CustomerNotification
A push/in-app notification queued for a customer. `Shared/TalabatkLogic/TalabatkModels/CustomerNotification.cs`.
- No validation in `Instance(...)` or any setter — plain field assignment throughout.
- `NotificationType` and `EntityId` are raw `int`s (no enum in this file) — the notification's actual
  meaning/target is polymorphic and opaque from this class alone; the mapping presumably lives in
  whatever Application-layer code creates each specific notification type (not traced in this pass).
- Tracks per-platform delivery (`SendToIOS`/`SendToAndroid`) and an unregistered-customer path
  (`SetUnRegisteredCustomer` — flips `IsCustomerRegistered=false` and records
  `UnRegisteredCustomerId`), suggesting notifications can target a phone number that hasn't completed
  registration yet.

## Favourites
A customer's saved-favourite marker (restaurant, menu item, etc. — `FavouriteTypeId`/`Type`, both raw
`int`s, no enum in this file). `Shared/TalabatkLogic/TalabatkModels/Favourites.cs`. No behavior beyond
the `Instance` factory — pure reference row, no update/remove method on the class itself (removal is
presumably a delete, handled at the Application layer, not traced).

## Rule / Decision Matrix

Two thin children of [[Customer.technical|Customer]]: a queued notification and a saved favourite. Neither validates anything, and both use bare `int` type codes — but the notification's method list is unusually informative about how push delivery actually works here.

| # | Rule | Where | Notes |
|---|---|---|---|
| 1 | `CustomerNotification.Instance` validates nothing | `Shared/TalabatkLogic/TalabatkModels/CustomerNotification.cs:31` | Title, body, type and target are assigned as given |
| 2 | `NotificationType` and `EntityId` are bare `int`s, so the target is polymorphic and opaque | `Shared/TalabatkLogic/TalabatkModels/CustomerNotification.cs:31` | The entity cannot tell you whether `EntityId` is an order, an item or a restaurant — only the creating call site knows |
| 3 | Delivery is tracked per platform | `Shared/TalabatkLogic/TalabatkModels/CustomerNotification.cs:72-76` | `SetSendToIOS` and `SetSendToAndroid` are separate setters, so one platform can be targeted without the other |
| 4 | A notification can target someone who never registered | `Shared/TalabatkLogic/TalabatkModels/CustomerNotification.cs:55` | `SetUnRegisteredCustomer` flips `IsCustomerRegistered` to false and records an `UnRegisteredCustomerId` — this is how a marketing push reaches an install that never became an account |
| 5 | Send time is decoupled from creation | `Shared/TalabatkLogic/TalabatkModels/CustomerNotification.cs:60` | `SetSendDate` writes `ToBeSendDate`, which is what makes a scheduled campaign possible |
| 6 | `Sent` is a one-way flag with no guard | `Shared/TalabatkLogic/TalabatkModels/CustomerNotification.cs:80` | Nothing prevents marking an unsent notification as sent, or re-marking one |
| 7 | `MarkNotificationAsRead` is the only method returning `Result` | `Shared/TalabatkLogic/TalabatkModels/CustomerNotification.cs:25` | And it cannot fail |
| 8 | `Favourites` is one table for every kind of favourite | `Shared/TalabatkLogic/TalabatkModels/Favourites.cs:19` | `FavouriteTypeId` plus `Type` discriminates restaurant from item; `Instance` assigns and validates nothing |
| 9 | `Favourites` has no removal method | `Shared/TalabatkLogic/TalabatkModels/Favourites.cs:19` | Deletion is a row delete in the application layer — `api/Favourite/DeleteFavourite` and `DeleteFavouriteByType` |

## Related
- [[Customer.technical|Customer]] — owning entity for both

## Open Questions
- [ ] What `NotificationType`/`EntityId`/`FavouriteTypeId`/`Type` integer codes actually map to — not
  enumerated in this pass; would need the Application-layer creation call sites.
