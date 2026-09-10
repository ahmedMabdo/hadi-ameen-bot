---
id: 8orders/system/glossary
note_type: system
last_updated: 2026-08-23
---
# 8Orders — Business Glossary

> Business term → what it maps to in the model, and where it is authoritatively defined. A
> cross-context index, not a replacement for each context's own `CONTEXT.md`: where a term is already
> defined there, this table links rather than redefines.
>
> **Two kinds of entry, deliberately mixed.** Most rows map a term the business uses to the field that
> implements it. Some rows exist because the *name is misleading* — a word that means something
> narrower, wider, or simply other than it sounds. Those are marked ⚠️ and are the rows worth reading
> even if you know the system.

## Orders and fulfilment

| Term (as the business says it) | Means | Maps to | Where |
|---|---|---|---|
| "Order" | One customer checkout, which may span several restaurants | `Order` — the hub entity, 6,285 lines | [[Customer Ordering/Order & Fulfilment/Order/Order.technical\|Order]] |
| "Order portion" | One restaurant's share of a multi-restaurant order — what that restaurant sees, accepts and cooks | `OrderRestaurantDetails` | [[Customer Ordering/Order & Fulfilment/OrderRestaurantDetails\|OrderRestaurantDetails]] |
| ⚠️ "Order status" | There are **two** status vocabularies: the customer-facing `OrderStatus` and the per-restaurant `RestaurantOrderStatus`. An order can be "cooking" for one restaurant and "ready" for another | `Order.StatusId` vs `OrderRestaurantDetails.RestaurantOrderStatusId` | [[Customer Ordering/Order & Fulfilment/_knowledge-graph\|Order & Fulfilment]] |
| "Daily Pickup Tag" | Per-city, per-working-day sequence number identifying a pickup | `OrderRestaurantDetails.PickupTag`, sequenced by `CityDailyPickupTagCounter` | [[../../../Talabatk.IDS/CONTEXT\|Customer Ordering CONTEXT.md]] |
| "Cost holder" | Who absorbs the loss when an order goes wrong — driver, 8Orders, the agent, or the restaurants, in any combination | `OrderCostHolder` + `OrderCostHolderRestaurant` | [[Customer Ordering/Order & Fulfilment/Order-Lifecycle.technical\|Order Lifecycle]] |
| "Replacement" | An out-of-stock item swapped for another, with the customer's consent | `MenuItemReplacement`, `OrderDetailReplacement`, reported in `ItemReplacementReport` | [[Customer Ordering/Order & Fulfilment/Order-Lifecycle.technical\|Order Lifecycle]] |
| "Robocall" | An automated phone call chasing a restaurant that has not responded | `RoboCall` + `RoboCallOrder` | [[Delivery/Delivery Man Operations/Delivery-Requests-and-Suppliers\|Delivery Requests and Suppliers]] |

## Discounts, money and who pays

| Term | Means | Maps to | Where |
|---|---|---|---|
| "Tiered Discount" | A "spend more, save more" campaign with 1–3 reward thresholds | `TieredDiscount` aggregate | [[Customer Ordering/Tiered Discount/_overview\|Tiered Discount overview]] |
| "Merchant / 8Order contribution" | The percentage split of a discount's cost between the restaurant and 8Orders; must sum to 100 | `TieredDiscount.MerchantContributionPercentage` / `.EightOrderContribution`; for loyalty, `MerchantLoyaltyConfig.ContributionPct` | this glossary; the loyalty field is unvalidated — see [[Restaurant Portal/Menu & Order Management/Merchant-Menu-and-Orders.technical\|Merchant Menu and Orders]] |
| "Available to guests" | Whether a not-yet-logged-in guest can see and use a discount | `TieredDiscount.AvailableToGuests` | this glossary |
| ⚠️ "Promo code" vs "Voucher" | Mutually exclusive at checkout — supplying a promo code means the voucher id is never even read. A promo is typed by the customer; a voucher is issued to them | `PromoCodes` / `Vouchers` | [[Customer Ordering/Discounts & Coupons/Discount-Resolution.technical\|Discount Resolution]] |
| "Offer" | A discount attached to a specific menu item, chosen at add-to-cart rather than at checkout | `Offers` / `OfferItem`, and `ExclusiveOfferItem` for the mart rails | [[Customer Ordering/Discounts & Coupons/Discount-Resolution.technical\|Discount Resolution]] |
| "Loyalty points" | Earned per order, redeemed for a voucher — the voucher is created by the redemption, not by the campaign | `LoyaltyPoints`, `LoyaltyPointsSrc`, → `Vouchers` | [[Customer Ordering/Customer Account/_knowledge-graph\|Customer Account]] |
| "Merchant statement" | The restaurant's running financial ledger with 8Orders | `MerchantStatementTransaction` — ten named factories, one per reason money moved | [[Restaurant Portal/Merchant Finance & Reporting/_knowledge-graph\|Merchant Finance & Reporting]] |
| "Receivement" | Cash physically collected from a merchant or driver and booked against an AccFlex treasury day | `MerchantReceivement` / `DeliveryManDaily` | [[Restaurant Portal/Menu & Order Management/Merchant-Menu-and-Orders.technical\|Merchant Menu and Orders]] |
| ⚠️ "Payment method" | The **behaviour** comes from a hard-coded enum, not from the reference table an admin can edit. Adding a row produces a method every branch in the money path ignores | `PaymentMethod` table vs the `PaymentMethods` enum | [[Admin/Order & Customer Administration/PaymentMethod\|PaymentMethod]] · `_conflicts.md` #632 |
| "Compensation" | Money given back to a customer after something went wrong, either manually or by rule | `Compensation`, and the `AutoCompensation*` family for the rule-driven path | [[Delivery/Driver Cash & Compensation/_knowledge-graph\|Driver Cash & Compensation]] |

## Restaurants, menus and the mart

| Term | Means | Maps to | Where |
|---|---|---|---|
| ⚠️ "Mart" | **Not a separate entity.** A mart is a `Restaurant` row with `IsStore = true`; the mart endpoints are a browsing layer over the same tables | `Restaurant.IsStore` | [[Customer Ordering/Restaurant & Menu Discovery/Mart\|Mart]] |
| ⚠️ "Category" | Three different tables, easily confused: `MainCategory` (food menu top level), `MartMainCategory` (grocery taxonomy), `MenuCategory` (one restaurant's menu section, which carries a key to *both*) | as listed | [[Customer Ordering/Restaurant & Menu Discovery/MenuItem/MenuStructure\|MenuStructure]] |
| "Option group" | A reusable set of choices ("size", "extras") attachable to items | `MenuItemOptionGroup` + `MenuItemOptionGroupItem`; the older per-item shape is `MenuItemOptions` + `MenuItemOptionsCategories`, and both are live | [[Customer Ordering/Restaurant & Menu Discovery/Discovery-Utilities\|Discovery Utilities]] |
| "Busy" | A restaurant temporarily pausing new orders, with a reason and a duration | `ResturantBusyHistory` (spelling is the real one) | [[Customer Ordering/Restaurant & Menu Discovery/Discovery-Utilities\|Discovery Utilities]] |
| "Unrevised item" | An ERP-imported product waiting for a human to classify it before it can be sold | `UnRevisedItem` | [[Customer Ordering/Order & Fulfilment/Order-Lifecycle.technical\|Order Lifecycle]] |
| "SKU" | The stock-keeping code the ERP matches on | `MenuItemPriceSku.Sku` | [[Customer Ordering/Restaurant & Menu Discovery/Discovery-Utilities\|Discovery Utilities]] |
| "Ad card" | A purchasable advertising slot a merchant books for whole weeks | `AdCard` + `AdReservation` | [[Customer Ordering/Marketing & Content/Notification-Delivery.technical\|Notification Delivery]] |

## Customers and identity

| Term | Means | Maps to | Where |
|---|---|---|---|
| "Guest Customer" | A provisional `Customer` row created from a device id before login, so a cart and its locked discount survive the sign-up | `Customer.IsGuest` + `DeviceId`, via `ResolveGuestCustomerService` | [[../../../Talabatk.IDS/CONTEXT\|Customer Ordering CONTEXT.md]] — which still describes this as unimplemented; it shipped |
| ⚠️ "Guest device id" | The **whole credential** for a guest. Anyone presenting it is that guest, and it travels in the query string | `guestDeviceId` request parameter | [[Customer Ordering/Support & Chat/_scenarios\|Support & Chat scenarios]] · `_conflicts.md` #341 |
| ⚠️ "External customer" | A **merchant's own** customer (walk-in or phone), not an 8Orders customer. Scoped to one restaurant | `ExternalCustomer` + `ExternalCustomerAdress` | [[Customer Ordering/Order & Fulfilment/Order.ExternalDelivery\|Order — External Delivery]] |
| "Unregistered customer" | A device that installed the app and never signed up — a marketing target, not a person with an account | `UnRegesteredCustomers` | [[Identity & Access/Customer Identity/Customer/Customer.technical\|Customer]] |
| "Permission" | A named capability granted to a role, checked by the `[Permission]` attribute | `RolePermission` joining `Permission` to `AspNetRole` | [[Identity & Access/Restaurant & Admin User Identity/Permission/Permission.technical\|Permission]] |
| "Audience" | A behavioural segment a campaign targets | `Audiance` + `AudianceFilter` + `AudienceCustomer` (spelling varies by table) | [[Customer Ordering/Marketing & Content/Notification-Delivery.technical\|Notification Delivery]] |

## Delivery

| Term | Means | Maps to | Where |
|---|---|---|---|
| "Delivery man" / "driver" / "rider" | The same person throughout; `DeliveryMen` is the entity, singular record despite the plural name | `DeliveryMen` | [[Identity & Access/Delivery Man Identity/DeliveryMen/DeliveryMen.technical\|DeliveryMen]] |
| "Shift" | A driver's working window; separately, back-office staff have their own `UserShift` model | `DeliveryMenShifts` / `DeliverymanShiftLog` vs `UserShift` | [[Delivery/Delivery Man Operations/Driver-Operations.technical\|Driver Operations]] |
| ⚠️ "Rest-break cap" | The share of a shift's drivers who may be away at once. **A configured 0 means "no limit", not "no breaks"** — and a city with no configuration row also has no cap | `CityBreakConfiguration.RestBreakMaxPercentage` | [[Admin/City & Geography Administration/CityBreakConfiguration\|CityBreakConfiguration]] · `_conflicts.md` #629 |
| "Zone" vs "Area" | `Country → City → Area` is the geography hierarchy; a *zone* is a named group of areas used for delivery pricing | `Area` / `RestaurantZone` + `RestaurantZoneArea` (which carries the fee) | [[Admin/City & Geography Administration/Area-and-Country\|Area and Country]] |
| "Auto-assign" | Offering an order to a driver with an expiry, rather than assigning it outright | `AutoAssignRequest` | [[Delivery/Delivery Man Operations/Delivery-Assignment-Strategies\|Delivery Assignment Strategies]] |
| "Asset" | Equipment issued to a driver — bag, box, phone — with the cost recorded at issue | `DeliveryAsset` + `DeliveryAssetDeliveryMan` | [[Delivery/Delivery Man Operations/Delivery-Requests-and-Suppliers\|Delivery Requests and Suppliers]] |
| "Non-delivery reason" | Why a delivery failed, and whether it costs the driver their account | `NonDeliveryReason.IsResultBan`; reinstatement reasons are `UnbanReason` | [[Delivery/Delivery Man Operations/Delivery-Requests-and-Suppliers\|Delivery Requests and Suppliers]] |
| "External delivery" | A delivery job a merchant sends 8Orders for its own customer | `ExternalDeliveryRequests` | [[Customer Ordering/Order & Fulfilment/Order.ExternalDelivery\|Order — External Delivery]] |

## Content, messaging and platform

| Term | Means | Maps to | Where |
|---|---|---|---|
| ⚠️ "Announcement" | Creating one **switches off every other active announcement** in the areas selected — or platform-wide if none are. One active at a time is the real rule, and nothing says so | `Announcement` | [[Customer Ordering/Marketing & Content/_knowledge-graph\|Marketing & Content]] · `_conflicts.md` #627 |
| "Hour window" | The "show only between these hours" setting shared by ads, announcements and home sliders | `HasTime` / `StartTime` / `EndTime` on `Ads`, `Announcement`, `SliderHome` | [[Customer Ordering/Marketing & Content/_knowledge-graph\|Marketing & Content]] |
| "Display days" | The weekdays a message may appear on; empty means every day | `Announcement.DisplayDays`, a comma-separated string | [[Customer Ordering/Marketing & Content/_scenarios\|Marketing & Content scenarios]] |
| "Scheduled campaign" | A push notification that recurs on an interval | `ScheduledNotification` + `NotificationTarget` + `NotificationExecutionHistory` | [[Customer Ordering/Marketing & Content/Notification-Delivery.technical\|Notification Delivery]] |
| ⚠️ "Chat" | Four distinct conversations share one word: customer↔support (with a bot), customer↔driver, driver↔support, and merchant↔support. Different tables, different hosts, different transports | `CustomerAdminChat`, `CustomerDeliveryChat`, `DeliveryManAdminChat`, `OrderChat` | [[Customer Ordering/Support & Chat/_knowledge-graph\|Support & Chat]] |
| ⚠️ "Realtime" | Two different technologies by audience: **SignalR** for Admin and the merchant portal, **Centrifugo** for the customer and driver apps | — | [[Customer Ordering/Ops & Infra/_knowledge-graph\|Ops & Infra]] |
| "Feature flag" | A switch changing behaviour without a release. Four mechanisms exist, including Esquio attributes and a database `Configuration` row | `Configuration`, Esquio `[FeatureFilter]`, `IFeatureManager` | [[Admin/Admin Back-Office/Configuration/Configuration.technical\|Configuration]] |
| "Webhook" | An outbound URL 8Orders posts events to. The URL is checked for emptiness, not for being a URL | `Webhook` + `WebhookEvent` + `WebhookSubscription` | [[Admin/Admin Back-Office/Configuration/Configuration.technical\|Configuration]] |
| "AccFlex" | The external ERP: stock quantities in, financial journals out | `_integrations.md` rows for the two integrations | [[_integrations\|Integrations]] |
| ⚠️ "Audit trail" | **Four** separate mechanisms with no shared abstraction: `Audit` (row-level), `EntityChangeHistory` (field-level, merchant-scoped), `ExcutionHistory` (per job), `LoyaltyConfigAuditLog` (loyalty settings). "Who changed this?" has four places to look | as listed | [[Admin/Admin Back-Office/Configuration/Configuration.technical\|Configuration]] |

## Spellings that are load-bearing

These names are misspelt in the code and must be reproduced exactly in any query or search. They are
listed because searching for the correct spelling silently finds nothing.

| In the code | The word it means |
|---|---|
| `Audiance`, `AudianceFilter` | Audience |
| `AreaDecription` | AreaDescription |
| `AvilableDeliveryMan` (mapped by `AvalibleDeliveryManMaping`) | Available — misspelt two different ways in one pair |
| `BitirixLeadStatus` | Bitrix |
| `DeliveryBouns`, `DeliveryBounsTier` | Bonus |
| `ExternalCustomerAdress` | Address |
| `ExcutionHistory` | Execution |
| `JournalSubuscriptions`, `SubuscriptionRepetion` | Subscriptions, Repetition |
| `MenuItemOptions.Update`'s "Refernce Name Can't be Empty" | Reference |
| `PromoCodeCity.Insatnce` | Instance |
| `ResturantBusyHistory` | Restaurant |
| `SliderHome.UpdateShourtCut` | ShortCut |
| `TermsAndConditions.LangaugeId` | Language |
| `CityRushTimeConfigHistory.StratAt` | StartAt |
| `RestaurantZone .cs` | a filename with a space before the extension |
| `ProbelemDetailes` (class), `CreateProplemDetails` (method), `CreateProblemDetail` (its body) | Problem — three spellings of one word, two of them wrong, inside a 28-line file. Used in 118 files |
| `AdminUi/Helper/BaseController.CreateProplemDetails` | see above; the base class of 54 AdminUi controllers |
| `DeliveryRequestAssignementStratgies/` (folder), `DeliveryAssignementStrategyFactory`, `PrimmaryDeliveryAssignementStrategy` | Assignment / Strategies / Primary — three misspellings in one folder name plus its types |
| `NotSupporterNorPrimmaryOrderDeliveryStrategy` | Primary |
| `ZiwoSettings.RestaruantPendingStorageName` | Restaurant |
| `GeomeryFactoryCustom` | Geometry |
| `UpdateHoldedOrderJob` | Held |
| `IDeliveryBounsService`, in folder `InterFaces/` | Bonus / Interfaces |
| `Shared/TalabatkLogic/Bitirix/` | Bitrix (the CRM) — the vendor's own name is spelt correctly everywhere except this folder |
| `Shared/TalabatkLogic/Enum/NewFolder/` | nothing — a placeholder folder name that shipped, holding a live `EnumExtensions` (see `_conflicts.md` #646) |
| `20230911101140_SalesDailt.cs` (migration) | SalesDaily |

## Names that mislead

| The name | What it suggests | What it actually is |
|---|---|---|
| `ProbelemDetailes` | ASP.NET Core's RFC 7807 `ProblemDetails` | A hand-rolled two-property class (`StatusCode`, `ErrorMessage`) whose three factories all hard-code `400 Bad Request`, so the status code is not a variable despite being a settable field. `Shared/SharedWeb/Helpers/ProbelemDetailes.cs:15`, `:25`, `:33` |
| `AdminUi.Helper.BaseController` | A base class that establishes session/tenant context for the 54 AdminUi controllers that inherit it | It takes `IMediator` and `SessionInfo` and its constructor body is empty — both are discarded. Every subclass injects and uses `sessionInfo` itself. See `_conflicts.md` #642 |
| `AutoCompensationSettingsEntity` | A distinct entity type | A `using` alias for `TalabatkLogic.TalabatkModels.AutoCompensation.AutoCompensationSettings`, declared in `Shared/TalabatkApplication/ITalabatkContext.cs:25`. Grepping the alias finds no class declaration, only the `DbSet<>` and two other files that re-declare the same alias |
| `EnumExtensions` | One static helper class | Two unrelated ones: `TalabatkLogic.Enum.EnumExtensions` (`List`, `ListLocalized`) and `TalabatkLogic.Enum.NewFolder.EnumExtensions` (`GetDescription`). Both live. See `_conflicts.md` #646 |
| `AccountingEntry` | A double-entry accounting record | A back-reference row holding the id AccFlex's GL assigned to a journal 8Orders already posted. Its factory validates nothing and `JournalTimeStamp` is a `string`. Two producers write it — payments and ad reservations. See `_conflicts.md` #645 |
| `TalabatkAPI/` (the project, not the repo root) | The current API host | The pre-.NET-Core legacy admin app (.NET Framework 4.6.2), excluded from documentation by user instruction — but still deployable via `Builds/MVCRelease.yml` and writing the same `TA_*` tables as the live stack. See `_conflicts.md` #641 |
