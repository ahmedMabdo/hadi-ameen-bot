---
id: 8orders/system/entity-index
note_type: system
sources:
  - path: Shared/TalabatkApplication/Services/OnlinePaymentRefundService.cs
    sha1: 3fda660302d5
  - path: Shared/TalabatkLogic/TalabatkModels/NonDeliveryReason.cs
    sha1: 9b2e11255e05
  - path: Shared/TalabatkLogic/TalabatkModels/Order.Partial.cs
    sha1: 0ee58f302d71
  - path: Talabatk.IDS/Helper/HangFire/SyncMartItemStockFromERPJob.cs
    sha1: c8ad8e604615
  - path: Talabatk.IDS/Startup.cs
    sha1: 32fc90149757
  - path: Talabatk.IDS/Views/Maintenance/LowQualityImages.cshtml
    sha1: 40ef5cd156f3
  - path: TalabatkAPIs/Controllers/MenuItem/ItemController.cs
    sha1: be53936a10f9
last_updated: 2026-08-23
---
# 8Orders — Entity Registry

> Canonical note per entity + the features it appears in. One entity is documented once; other
> features link to its canonical note. Last updated: 2026-08-20 — "True Zero-Gap Closure, Round 2"
> Phase 8 sync (see the new closing note at the bottom for the 3 genuinely new domain concepts this
> round surfaced: the CustomerAdminChatBot subsystem, `OnlinePaymentRefundService`, and the AccFlex
> ERP quantity-sync flow). Prior closing note (2026-08-13, what Phases 8/10/11 added) preserved below.

| Entity | Context | Side | Type | Canonical note | Appears in features |
|--------|---------|------|------|------------------|-----------------------|
| TieredDiscount | Customer Ordering | Backend-Domain (aggregate root) | Aggregate Root | [[TieredDiscount.technical\|TieredDiscount]] | Tiered Discount |
| TieredDiscountTier | Customer Ordering | Backend-Domain (child) | Child | [[TieredDiscountTier\|TieredDiscountTier]] | Tiered Discount |
| TieredDiscountRestaurant | Customer Ordering | Backend-Domain (child) | Child (scope) | [[TieredDiscountTier\|TieredDiscountTier]] | Tiered Discount |
| TieredDiscountCustomer | Customer Ordering | Backend-Domain (child) | Child (allow-list) | [[TieredDiscountTier\|TieredDiscountTier]] | Tiered Discount |
| TieredDiscountSegment | Customer Ordering | Backend-Domain (child) | Child (allow-list) | [[TieredDiscountTier\|TieredDiscountTier]] | Tiered Discount |

| CustomerCart | Customer Ordering | Backend-Domain (legacy POCO, event-raising) | Root | [[CustomerCart.technical\|CustomerCart]] | Cart & Checkout |
| CartItem | Customer Ordering | Backend-Domain (child) | Child | [[CartItem\|CartItem]] | Cart & Checkout |
| CartItemOptions | Customer Ordering | Backend-Domain (child) | Child | [[CartItem\|CartItem]] | Cart & Checkout |
| PromoCodes | Customer Ordering | Backend-Domain (legacy POCO, event-raising) | Root | [[PromoCodes.technical\|PromoCodes]] | Discounts & Coupons |
| Vouchers | Customer Ordering | Backend-Domain (legacy POCO) | Root | [[Vouchers.technical\|Vouchers]] | Discounts & Coupons |
| Order | Customer Ordering (**partial** — Customer Ordering slice only, see technical note's scope warning) | Backend-Domain (legacy POCO, event-raising) | **Hub** | [[Order.technical\|Order]] + [[Order.ExternalDelivery\|External Delivery extension]] | Order & Fulfilment |
| OrderRestaurantDetails | Customer Ordering (partial) | Backend-Domain (child, event-raising) | Child ("Portion") | [[OrderRestaurantDetails\|OrderRestaurantDetails]] | Order & Fulfilment |

| Restaurant | Customer Ordering (partial — browsing slice only) | Backend-Domain (legacy POCO) | Master | [[Restaurant.technical\|Restaurant]] | Restaurant & Menu Discovery |
| MenuItem | Customer Ordering (partial — browsing slice only) | Backend-Domain (legacy POCO, event-raising) | Master | [[MenuItem.technical\|MenuItem]] | Restaurant & Menu Discovery |

| Customer | Identity & Access (owns identity record; heavily cross-touched by Customer Ordering) | Backend-Domain (legacy entity, event-raising, richer than typical POCO) | Hub | [[Customer.technical\|Customer]] | Cart & Checkout (guest merge), Customer Account |
| DeliveryMen | Identity & Access (owns identity record; heavily cross-touched by Delivery + Admin) | Backend-Domain (legacy entity, event-raising, richer than typical POCO) | Hub | [[DeliveryMen.technical\|DeliveryMen]] | Delivery Man Operations, Admin Back-Office |
| DeliverymanShiftLog | Delivery (operational; identity owner is Identity & Access) | Backend-Domain (legacy POCO) | Child | [[DeliveryMan-Attendance\|DeliveryMan Attendance & Shifts]] | Delivery Man Operations |
| DeliveryMenShifts | Delivery | Backend-Domain (legacy POCO) | Child (shift definition) | [[DeliveryMan-Attendance\|DeliveryMan Attendance & Shifts]] | Delivery Man Operations |
| DeliverymanBreakLog | Delivery | Backend-Domain (legacy POCO, event-raising) | Child | [[DeliveryMan-Attendance\|DeliveryMan Attendance & Shifts]] | Delivery Man Operations |
| DeliverymanTransaction | Delivery | Backend-Domain (legacy entity, write-once ledger) | Ledger/Child | [[DeliverymanTransaction.technical\|DeliverymanTransaction]] | Delivery Man Operations |
| City | Admin (no single owning context — reference/config data administered centrally) | Backend-Domain (legacy entity, richer than typical POCO) | Master, Hub | [[City.technical\|City]] | Admin Back-Office |
| Area | Admin | Backend-Domain (legacy POCO) | Master (child of City) | [[Area-and-Country\|Area (+ Country)]] | Admin Back-Office |
| Country | Admin | Backend-Domain (legacy POCO) | Master (parent of City) | [[Area-and-Country\|Area (+ Country)]] | Admin Back-Office |
| CustomerAddresses | Identity & Access (child of Customer) | Backend-Domain (legacy POCO) | Child | [[CustomerAddresses\|CustomerAddresses]] | Cart & Checkout (guest merge) |
| CustomerAdminChat, CustomerAdminChatMessage, ChatSetting | Customer Ordering (bridged, not re-documented) | Backend-Domain | Session state machine / config | [[Customer Ordering/Support & Chat/_knowledge-graph\|Support & Chat]] (bridge note, not a dedicated canonical file) | Support & Chat |
| DeliveryZone | Delivery | Backend-Domain (legacy entity, event-raising) | Master | [[DeliveryZone\|DeliveryZone]] | Delivery Man Operations |
| Compensation | Delivery | Backend-Domain (legacy entity, event-raising) | Transactional | [[Compensation\|Compensation]] | Delivery Man Operations |
| CustomerNotification, Favourites | Identity & Access (children of Customer) | Backend-Domain (legacy POCO, light) | Child | [[Customer-Notification-and-Favourites\|CustomerNotification (+ Favourites)]] | *(light — no dedicated feature pass)* |
| DeliveryMenLocations | Delivery | Backend-Domain (legacy POCO, light) | Child (GPS log) | [[DeliveryMan-Attendance\|DeliveryMan Attendance & Shifts]] | Delivery Man Operations |
| Ads, Announcement, Brand, AboutApp | Customer Ordering (light tier) | Backend-Domain (legacy POCO, light) | CMS-style content | [[Customer Ordering/Marketing & Content/_knowledge-graph\|Marketing & Content]] | Marketing & Content |
| ApiKey | Admin | Backend-Domain (legacy entity) | System credential | [[ApiKey\|ApiKey]] | Admin Back-Office |
| BlockedUsersFromCOD | Customer Ordering | Backend-Domain (legacy POCO) | Fraud-prevention | [[BlockedUsersFromCOD\|BlockedUsersFromCOD]] | Cart & Checkout |
| DeliveryBouns | Delivery | Backend-Domain (aggregate-style, event-free) | Transactional | [[DeliveryBouns.technical\|DeliveryBouns]] | Delivery Man Operations |
| ExternalDeliveryRequests, DeliveryZoneArea, DeliverySupplier | Delivery | Backend-Domain (legacy POCO) | Light/Master | [[Delivery-Requests-and-Suppliers\|ExternalDeliveryRequests, DeliveryZoneArea, DeliverySupplier]] | Delivery Man Operations |
| Audiance | Admin | Backend-Domain (legacy entity, validated) | Marketing segmentation | [[Audiance\|Audiance]] | Admin Back-Office |
| FAQItem | Customer Ordering (bridged) | Backend-Domain (legacy entity, validated) | CMS content | [[Customer Ordering/Support & Chat/_knowledge-graph\|Support & Chat]] (bridge note) | Support & Chat |
| CityRushTimeConfiguration | Admin | Backend-Domain (aggregate-style state machine) | Config/State machine, Hub-adjacent | [[CityRushTimeConfiguration.technical\|CityRushTimeConfiguration]] | Admin Back-Office |
| CityBreakConfiguration | Admin | Backend-Domain (legacy entity, light) | Config | [[CityBreakConfiguration\|CityBreakConfiguration]] | Admin Back-Office |
| Configuration | Admin | Backend-Domain (singleton config, ~130 fields) | Config, Hub-adjacent | [[Configuration.technical\|Configuration]] | Admin Back-Office |
| StoreTypes, StoreTypesDescription | Admin | Backend-Domain (legacy entity) | Master | [[StoreTypes.technical\|StoreTypes]] | Admin Back-Office |
| Offers, OfferItem | Customer Ordering | Backend-Domain (legacy entity) | Transactional | [[Offers.technical\|Offers]] | Restaurant & Menu Discovery |
| LoyaltyPoints | Identity & Access (child of Customer) | Backend-Domain (legacy entity) | Financial ledger | [[LoyaltyPoints\|LoyaltyPoints]] | Customer Account |
| MenuItemPrice | Customer Ordering (child of MenuItem) | Backend-Domain (AuditableEntity, event-raising) | Transactional | [[MenuItemPrice.technical\|MenuItemPrice]] | Restaurant & Menu Discovery |
| OrderDetails | Customer Ordering (partial — child of Order) | Backend-Domain (legacy entity) | Child (line item) | [[OrderDetails.technical\|OrderDetails]] | Order & Fulfilment |
| OrderDelivery | Delivery | Backend-Domain (legacy entity, event-raising) | Transactional, Hub-adjacent | [[OrderDelivery.technical\|OrderDelivery]] | Delivery Man Operations |
| WalletTransaction | Identity & Access (child of Customer) | Backend-Domain (legacy entity, light) | Financial ledger | [[WalletTransaction\|WalletTransaction]] | Customer Account |
| PaymentMethod | Admin | Backend-Domain (legacy entity, validated) | Master | [[PaymentMethod\|PaymentMethod]] | Admin Back-Office |
| MenuCategory, MenuItemOptions, MenuItemOptionsCategories, ImageBank | Customer Ordering | Backend-Domain (legacy entity / AuditableEntity) | Child/Master | [[MenuStructure\|Menu Structure]] | Restaurant & Menu Discovery |
| RestaurantReview, OrderRejectedReason | Customer Ordering | Backend-Domain (legacy entity, event-raising) | Transactional/Reference | [[RestaurantReview\|RestaurantReview]] | Restaurant & Menu Discovery |
| MerchantStatementTransaction, OrderCostHolder, RoboCall, Notification | Delivery | Backend-Domain (legacy entity, write-once ledger / reference) | Ledger/Reference | [[Merchant-Accounting-and-Order-Cost\|Merchant Accounting & Order Cost]] | Delivery Man Operations |
| MartMainCategory, RestaurantFinalScoreRate, Tag, UnRegesteredCustomers, RestaurantZoneArea, JournalSubuscriptions | Admin | Backend-Domain (legacy entity) | Master/Reference | [[Mart-and-Reference-Entities\|Mart & Reference Entities]] | Admin Back-Office |
| DeliveryAnnouncement, DeliveryManNotification | Admin | Backend-Domain (proper DDD aggregate, validated) | Transactional | [[DeliveryAnnouncement-and-Notification\|DeliveryAnnouncement & Notification]] | Admin Back-Office |
| OrderComplaint | Customer Ordering | Backend-Domain (aggregate-style, unvalidated) | Transactional | [[OrderComplaint\|OrderComplaint]] | Order & Fulfilment |
| (delivery assignment/creation strategies, DeliverymenProfitCalculator, CompanyProfitCalculator) | Delivery | Backend-Domain (Strategy pattern + domain services) | Application logic | [[Delivery-Assignment-Strategies\|Delivery Assignment Strategies]] | Delivery Man Operations |
| TieredDiscountAggregate | Customer Ordering | Backend-Domain (proper DDD aggregate) | Aggregate Root | [[TieredDiscount.technical\|TieredDiscount]] | Tiered Discount — re-confirmed unchanged in this pass, nothing new to add |
| (Online payment strategies: CIB/PayMob card/wallet/Apple Pay) | Customer Ordering | Backend-Application (Strategy pattern) | Application logic | [[Checkout-Payment-Processing\|Checkout Payment Processing]] | Cart & Checkout — closes the `CreateOrderFromCartCommand` back-half gap |
| TalabatkContext | *(no single owning context — the shared `DbContext` behind every host)* | Backend-Data (infra hub) | Hub | *(no dedicated technical note — documented inline in `_conflicts.md` #207-209)* | Every context — `SaveChanges`/`SaveChangesAsync` overrides, domain-event dispatch, and auditing sit here; the reversed `IsAssignableFrom` check in `Auditing()` (#207) means the audit trail has never recorded anything, system-wide, on any save |

**Spot-check of 8 more "bulk trivial" A/B-half entities (2026-08-03) — mostly confirmed trivial, 2
minor findings:** `NonDeliveryReason.UpdateAdminStatus`/`UpdateDriverStatus`
(`Shared/TalabatkLogic/TalabatkModels/NonDeliveryReason.cs:69-103`) enforce a real cross-field rule —
`IsForDriver=true` auto-sets `IsForAdmin=true`, and `IsForAdmin=false` auto-clears `IsForDriver` — a
reason can never be driver-visible without also being admin-visible. `MerchantCapacityHours.Instance`
(`:23-54`) subtracts one minute from `estimatedTime`/`actualTime` whenever either spans more than a
day — unexplained normalization, not investigated further. `DeliveryReason`, `Permission`,
`ComplaintsAndSuggestions`, `WorkingDay`, `CookingTimeCategory` (validated), `MerchantRejectionReasons`
(validated) confirmed genuinely light as assumed. This spot-check supports (but does not prove for
all 220 remaining files) that the naming-convention bulk-trivial sweep above was reasonably accurate.

Not yet in the registry (referenced by documented features but not themselves documented — each is
a large, separately-scoped entity of its own):
`Audiance`, `Offers`, `LoyaltyPoints`. **`Order` and `Restaurant`/`MenuItem` are only
partially documented** — their Restaurant Portal / Delivery / Admin management slices remain for
those contexts' own future passes; do not treat the current notes as complete coverage.

_Shared-layer documentation batch in progress (started 2026-08-03): entities from
`Shared/TalabatkLogic/TalabatkModels/` are being triaged by real-vs-trivial business logic and added
here one at a time as each is documented — this registry, not chat history, is the source of truth
for what's actually done._

**TalabatkModels A-half (139 files, alphabetically AboutApp.cs–HomeSearchDefaultRestaurantRow.cs) —
status: real-logic entities done.** All entities with meaningful Application-layer reference counts
(triaged via `grep -rl` count against `Shared/TalabatkApplication`) are now documented above. Not
individually documented — confirmed trivial/low-signal on inspection or by naming convention, not
skipped without basis: `AspNetUser*` tables (ASP.NET Identity plumbing), `*StoredProcure`/`*ReportRow`
result-shape classes (`AdminOrderHistoryStoredProcure`, `BotPerformanceReportRow`,
`CustomerInfoStoredProcure`, `DeliveryManOrderStoredProcure`, `ChatReportRow`, `CSTAppItemsCount`),
various `*Description`/`*Descption` lookup rows (`AreaDecription`, `BrandDescription`,
`CityDescription`, `FoodTypesDescription`), `EntityChangeHistory`/`Audit`/`ExcutionHistory` (audit-log
shape, no embedded rules), `CustomerTag`/`CustomerAds`/`AudienceCustomer`/`AudienceCustomerAds`
(pure join/reference rows), `DeliveryManReview`/`DeliveryManOrders`/`DeliveryManWorkingHours`/
`DeliveryMenAttendance`/`DeliveryMenReport`/`DeliveryMenTotalReport`/`DeliveryManStates`/
`DeliveryManPayments`/`DeliveryManPrice(Data)` (feed `DeliveryMen`'s rating/financial math, already
covered from the `DeliveryMen` side), `DeliveryManAdminChat(Message)`/`CustomerDeliveryChat(Message)`
(parallel chat channels, same shape as the bridged `CustomerAdminChat` — see Support & Chat's
knowledge graph), `FoodType` (Restaurant & Menu Discovery's own concern, browsing-slice already
partially covered there), `FawryTransaction`/`FawryCashCollectionTransaction`/`BitirixLeadStatus`
(third-party integration records, light), and a handful of single-purpose DTOs
(`DriverPerformanceReportDto`, `AvilableDeliveryMan`, `AvalibleAds`, `AspNetUserRestaurant`,
`AutoAssignRequest`, `DeliveryReason`, `DeliveryComment`, `DeliveryInstruction(Description)`,
`ExternalCustomer(Adress)`, `DeliverymanZone`, `DriverDismissalLog`, `CustomerSavedTipsConfiguration`,
`CustomerItemNotificationRequest`, `CustomerItemOrderStats`, `CustomerWalletHistory`,
`CustomerOrderWithReview`, `CustomerDeliveryInstruction`, `CookingTimeCategory`,
`ComplaintsAndSuggestions`, `AdCard`, `AreaDecription`, `DeletedOrderDetailsItemsHistory`). If a
future change request touches one of these, read it directly rather than expecting depth here.

**Phase 9 gap-closure sweep (2026-08-09) — all 288 `TalabatkModels/` files now accounted for.**
Built a fresh manifest (`find ... | sort`, 288 files, matches this doc's own count), then two bulk
greps across the whole folder: (1) `Result\.Failure|Result<|public Result |CSharpFunctionalExtensions`
→ 119 files with behavior signal; (2) `throw new|for \(|while \(|switch \(|TimeSpan\(|Math\.|Random|DateTime\.Now`
→ 36 files (mostly overlapping (1)) with logic signal outside the Result pattern. Cross-referenced
both lists against this registry's existing canonical-note and "confirmed trivial" coverage; **27
files were in neither bucket and got individually read this pass**: the 5-file `AutoCompensation/`
feature (`AutoCompensationQuestion/Reason/Settings/EvidenceRule/QuestionOption` — clean, well-validated
DDD-style aggregate, no findings), `ExclusiveOfferItem` (clean), `UnRevisedItem` (bug —
`UpdateDetails` silently drops its `barCode`/`changeSummary` parameters, `_conflicts.md` #205),
`DeliveryBounsTier`/`RestaurantJournalSubuscriptions`/`OrderDetailsOptions`/`LoyaltyPointsSrc`/
`DeliverySuppliersCities`/`CustomerActionsHistory`/`CustomerCard` (all clean), `DeliveryAsset` (clean),
`DeliveryInterval` (possible bug — `CheckValidDates` mutates `ReceivingTime` as a side effect of a
predicate-shaped method, #204), `ChatMessage`/`CityRushTimeConfigHistory`/`AspNetUserShift` (clean),
`AudianceFilter` (bug — `isRegesteredCustomer` parameter never used, #206), `Brand` (clean),
`AdReservation` (2 bugs — `UpdateAdReservation` passes raw days instead of weeks into
`AdCard.GetPrice`, #202; and skips the max-duration check `Instance` enforces, #203),
`ExternalCustomer` (clean), `OrderPayment` (clean), `SpecialMartCategorySetting` (clean),
`CustomerNotificationNewVersion`/`DeliveryAssetDeliveryMan`/`DeliveryBoxUnitSize` (clean, real logic
but no findings). Everything else surfaced by the two greps was already covered by a canonical note
or the "confirmed trivial" catalog below — **the "confirmed trivial by naming convention, not opened"
hedge on the remaining ~261 files now also carries this pass's two-grep verification**, not just the
original naming-convention guess.

**TalabatkModels B-half (139 files, ImageBank.cs–WorkingDay.cs) — status: highest-signal entities
done.** Documented above: OrderDetails, OrderDelivery, LoyaltyPoints, MenuItemPrice, WalletTransaction,
PaymentMethod, StoreTypes/StoreTypesDescription, Offers/OfferItem, MenuCategory/MenuItemOptions family,
RestaurantReview/OrderRejectedReason, MerchantStatementTransaction/OrderCostHolder/RoboCall/
Notification, MartMainCategory/RestaurantFinalScoreRate/Tag/UnRegesteredCustomers/RestaurantZoneArea/
JournalSubuscriptions — plus `Order`, `Restaurant`, `MenuItem`, `OrderRestaurantDetails`, `PromoCodes`,
`Vouchers` already covered in the original Customer Ordering pass. Not individually documented — light
by naming convention or confirmed trivial on inspection, same standard as A-half's closing note:
`*SpRow`/`*Dto` result-shape classes (`ItemReplacementReportSpRow`, `ItemReplacementResultStatusSpRow`,
`ItemReplacementTopItemSpRow`, `MartMainCategoryDto`, `MartProductCategoryDto`,
`MartSubCategoryDto`), `*Description` lookup rows (`ItemDescription`, `MenuCategoryDescription`,
`MenuItemOptionCategoryDescription`, `MenuItemOptionGroupDescription`,
`MenuItemOptionGroupItemDescription`, `MenuItemPriceDescription`, `RestaurantDescription`,
`OffersDescriptions`), the `MenuItemOptionGroup`/`MenuItemOptionGroupItem` template layer (already
covered from the consuming side in `MenuItemPrice.technical.md` Rule 5), report/history rows
(`MerchantAcceptanceReport`, `MerchantPerformanceReport`, `MerchantRejectedReport`,
`ResturantBusyHistory`, `ItemReplacementReport`, `LoyaltyConfigAuditLog`, `OrderStatusHistory`), join/
reference tables (`Restaurant_FoodTypes`, `RestaurantArea`, `RestaurantZone`, `StoreTypeCities`,
`PromoCodeArea`/`PromoCodeAudience`/`PromoCodeCity`/`PromoCodeCustomer`, `PaymentMethodCountries`),
static content entities (`TermsAndConditions`, `PrivacyPolicy`, `SliderHome`), third-party integration
records (`PayMobTransaction`, `Webhook(Event/Subscription)`), light CRUD/DTO order-adjacent entities
(`OrderChat`, `OrderComment`, `OrderList`, `OrderPayment(States)`, `OrderAgentAssignment`,
`OrderDeliveryRequest`, `OrderDetailReplacement`, `ReadyOrder`, `OrderCountTracking`,
`OrderCostHolderRestaurant`), shift/work-tracking light entities (`UserShift(Details)`,
`WorkUsDelivery(History/Status)`, `WorkUsRestaurant(Comment)`, `WorkingDay`), and single-purpose
lookups (`NonDeliveryReason`, `UnbanReasons`, `Permission`, `RolePermission`, `Request`, `TaskType`,
`Tasks`, `SearchHistory`, `RecommendationEventType`/`RecommendationInteractionEvent`,
`MerchantRejectionReasons`, `MerchantCapacityHours`, `MerchantInstructionsVideos`, `MerchantReceivement`,
`MerchantLoyaltyConfig`, `SpecialMartCategorySetting`, `RefreshToken`, `LastTaskUserView`,
`ScheduledNotification(CustomerGroupType)`, `NotificationExecutionHistory`/`NotificationTargets`,
`MenuItemReplacement`, `MenuItemPriceSku`, `MainCategory`, `ItemsByCategory`, `UpSellingCartItems`,
`SalesDaily`, `RushTimeAreaPriority` — this last one's business rules are already covered from the
`CityRushTimeConfiguration` side). `Order.Partial.cs` was checked and confirmed to be a real,
previously-unverified gap — now documented at
[[Order.ExternalDelivery\|Order — External Delivery Extension]].
If a future change request touches one of the still-undocumented entities above, read it directly
rather than expecting depth here.

**Phase 14 closing note (2026-08-13) — what Phases 8–13 added to this registry, and why most of them
added nothing:**
- **Phase 8** (`Shared/TalabatkApplication/Commands`+`Queries`+`Feature`, 1,850 files, Pile A):
  Application-layer handlers for entities already catalogued above (`Order`, `MenuItem`, `Customer`,
  `DeliveryMen`, etc.) — no new aggregate roots surfaced; every finding (repo-wide bug patterns like
  the save-before-upload-orphan and discarded-`SaveChangesAsyncWithResult` families) went to
  `_conflicts.md` #54-201, not here, per the standing "skip entity cross-writes unless free" rule.
- **Phase 9** (`TalabatkModels/`, Pile B sweep): already merged into this file's own "Phase 9
  gap-closure sweep" section above (2026-08-09) — no separate Phase 14 action needed.
- **Phase 10** (`Shared/TalabatkData/`, Pile B sweep): added the single `TalabatkContext` row above —
  the one genuinely registry-worthy discovery, given its system-wide blast radius. The other 33
  real-logic files read in full (Elastic, Cassandra, Fawry/Bitrix/GoogleMap/OTP/RoboCall/WhatsApp
  service wrappers, `HangfireBridge`, distributed-cache helpers) are infra/integration code, not
  domain entities — their findings and integration shapes live in `_conflicts.md` #207-216 and
  `_integrations.md` #13-18 respectively, not here. `Mapping/` (236 files) and `Migrations/` (1,844
  files) confirmed 100% declarative EF boilerplate, nothing to register.
- **Phase 11** (`TalabatkAPIs/Order.cs` + `CustomerUserController.cs` + 7 Razor views): `Order` was
  already the registry's one **partial**-coverage entity; this phase read its full 6,235-line handler
  body (not just route-mapped) but didn't change its documented scope or aggregate shape — the 10 new
  bugs found (`_conflicts.md` #217-226) and the 2 IDOR findings in `CustomerUserController` (#227-228)
  are behavior-level, not new entities.
- **Phases 12–13** (AdminUi + TalabatkRestaurants Angular, 964 `.ts` files combined): frontend
  component/service code — view models like `CategoryCardModel`/`ItemCardModel` are UI-layer DTOs,
  not backend domain entities, so nothing from these two phases belongs in this registry. Their ~50
  findings (`_conflicts.md` #229-254) are frontend-only bugs, already fully recorded there.

**"True Zero-Gap Closure, Round 2" Phase 8 closing note (2026-08-20) — 3 new domain concepts
surfaced across this round's Phases 1–7, none previously in this registry:**
- **CustomerAdminChatBot subsystem** (`Shared/TalabatkApplication/Helper/CustomerAdminChatBot/` +
  `Services/CustomerAdminChatBotServices/{FAQBotServices,OrderStatusBotServices}/`) — a genuine
  bot-driven layer sitting on top of the already-bridged `CustomerAdminChat`/`CustomerAdminChatMessage`
  entities (see the existing [[Customer Ordering/Support & Chat/_knowledge-graph\|Support & Chat]]
  bridge note above): `ICustomerAdminChatBotOrchestrator` drives session init/resume, FAQ-option and
  order-status-picker message construction (`IChatBotMessageFactory`), keyword/action processing, and
  escalation to a human agent (`ICustomerAdminChatHandoffService`); `ICustomerAdminFaqBotService` and
  `IChatOrderStatusQueryService`/`ICustomerAdminOrderStatusBotService`/`IChatBotExpediteService` are
  the two bot "skills"; messages publish over Centrifugo (`ICentrifugoPublisher`/
  `TalabatkData.CentrifugoService.CentrifugoPublisher`) — a separate real-time channel from the
  SignalR hubs used elsewhere in the codebase. `OrderStatusBotFollowUpJob` +
  `IOrderStatusBotFollowUpScheduler` add a Hangfire-scheduled follow-up loop. Registered consistently
  across `TalabatkAPIs`/`TalabatkDelivery`/`TalabatkRestaurants`' DI (`Services.cs`/`AddServices`).
  Not individually read file-by-file this round (out of this plan's defined scope) — flagged here so
  a future pass has a named entry point instead of rediscovering it from DI wiring.
- **`OnlinePaymentRefundService`** (`Shared/TalabatkApplication/Services/OnlinePaymentRefundService.cs`)
  — sibling service to the already-documented [[Checkout-Payment-Processing\|Checkout Payment Processing]]
  online-payment strategies (row above), but for the refund half of the lifecycle: resolves whether a
  refund goes to the customer's wallet or back to their bank (`ResolveDestinationAsync`, weighing
  customer preference, partial-cancel, and customer-vs-admin-initiated context), executes bank refunds
  (`TryRefundOnlineAmountToBankAsync`), converts a wallet-credited refund to a bank refund after the
  fact (`TryConvertWalletRefundToBankAsync`), and applies a bank refund after an order rejection when
  needed (`ApplyBankRefundAfterRejectIfNeededAsync`). Consumed by `OrderRejectService` and the
  `RefundOnlinePaymentCommand`/`GetCustomerRefundPreferenceQuery`/`UpdateCustomerRefundPreferenceCommand`
  trio; fires `NotifyCustomerForFallbackWalletRefundEvent`/`NotifyCustomerForExecutedBankRefundEvent`
  domain events. Not previously named in this registry despite being load-bearing for every online
  cancellation/rejection refund.
- **AccFlex ERP quantity-sync flow** (mart/store stock quantities) — 3 verified, distinct paths that
  all feed the same `MenuItem.CurrentStockQuantity` column via the same `MenuItem.MaintainStock(...)`
  domain method:
  1. **Inbound webhook (push)**: ERP calls `POST /api/Item/ItemStockQuantityChangedInERP`
     (`TalabatkAPIs/Controllers/MenuItem/ItemController.cs:217-224`, `[AllowAnonymous]` +
     `[WebHookHmacAuthorize]` — HMAC-signed, not a bare anonymous endpoint) with a batch of
     `MaterialCode`/`CurrentQuantityInMinimumUnit`/`IsOutOfStock` updates, dispatched as
     `ItemStockQuantityChangedInERPCommand` → per-matched-barcode `MaintainStock(...)`, saved via
     `SaveChangesAsyncWithResult()`.
  2. **Scheduled daily pull**: `Talabatk.IDS/Helper/HangFire/SyncMartItemStockFromERPJob.cs`,
     registered as a Hangfire recurring job in `Talabatk.IDS/Startup.cs:456` (`RecurringJob.AddOrUpdate`,
     job id `"SyncMartItemStockFromERPJob"`, default cron `"0 5 * * *"` Egypt time — configurable via
     `SyncMartItemStockFromERP:CronExpression`) — batches every mart `MenuItem` with a barcode (50 per
     ERP call), calls `ILogisticService.GetItemQuanaityAsync`, `MaintainStock`s each match, logs (but
     doesn't retry/dead-letter) per-batch ERP or save failures.
  3. **Manual on-demand sync**: `SyncMartItemsQuantityFromErpCommand` (accepts a specific barcode list,
     or an empty list to mean "sync every mismatched item") — calls `ILogisticService.GetAllItemQuantity`
     and reconciles with a `QuantityTolerance` of `0.1`; the admin-triggered path referenced by this
     registry's prior ERP-incident memory as a "manual per-store sync button."
  4b. *(see also the Low-Quality Image subsystem note below, added 2026-08-20 post-rebase — it shares
      the same `ImageBank` storage tree these mart items' images live in.)*
  4. **On-demand pull at cart-time**: `MartQuantityValidationService.ValidateCartQuantitiesAsync`/
     `GetAvailableQuantityAsync` branch on the `Features.ValidateQuantitiesLocally` feature flag — when
     `true` (the confirmed-live config as of the 2026-08-16 ERP incident), quantity comes from the
     locally-maintained `CurrentStockQuantity` (kept fresh by paths 1–3, none synchronous with
     checkout); when `false`, it calls `GetItemQuanaityAsync` synchronously against AccFlex live,
     failing closed (blocks checkout with a friendly message) on an ERP outage or missing barcode data
     — confirms the fail-open bug this registry's `_conflicts.md` history references (#263) has since
     been fixed to fail closed; the live-incident root cause remains #272's stock-reservation gap
     (checkout doesn't reserve/decrement, and the actual ERP debit fires later, asynchronously, only
     once the order reaches Confirmed status).

**Post-rebase addition (2026-08-20) — the Low-Quality Image ("`_low`" companion) subsystem.** Arrived
via PRs 63057/63529/63552/63561, entirely new, spanning `Shared/TalabatkApplication` and
`Talabatk.IDS`. Worth a registry entry because it introduces a new **storage-layer convention** that
nothing in the database records, so it is invisible to anyone reading only entities/schema:
- **The convention:** for an original at `{imageId}.{ext}`, a smaller sibling is written as
  `{imageId}_low.{storedFormat}` in the same folder. The companion keeps the original's dimensions
  and is stored as **WebP by default** (`LowQualityImage:Format`), *not* the original's format,
  because WebP is the only format that shrinks a PNG without resizing. **Nothing in the DB references
  the companion** — this is deliberate, so the stored format can change later without a migration.
- **Write paths (2):** (1) automatically on upload — all 5 hosts' own `UploadImage.Upload` now call
  `ILowQualityImageGenerator.GenerateAsync` after saving the original, gated by the new
  `Features.LowQualityImageGeneration` flag and wrapped in a swallow-all `try` so a companion failure
  can never fail an upload; (2) a manual bulk backfill, `LowQualityImageJob` (Hangfire, queue `ids`,
  **manual trigger only** — no recurring registration), driven from the new
  `Views/Maintenance/LowQualityImages.cshtml` maintenance page with a dry-run-by-default form, a
  `SelfCheck()` that renders a red banner if SkiaSharp's native libs fail to load, and a
  destructive "Remove all" undo path (see `_conflicts.md` #329).
- **Read path:** `ImageBankFallbackMiddleware` resolves a `_low` request by probing the companion in
  *any* stored format first, then the original, then the default image — so a `_low` URL is always
  valid even for images with no companion (unsupported format, wouldn't compress, or not yet
  backfilled). Cache TTLs are deliberately tiered: 24h for a real companion, 1h for an original
  standing in, 5min for the default-image fallback.
- **Cleanup:** `ImageBankPathHelper.DeleteLowQualityCompanion` is called wherever an original is
  replaced (`EditRestaurantCommand` ×3 sites, `PickUpOrderCommand`, `SaveAppDesignImagesCommand`),
  probing all candidate extensions so a companion left over from a previous configured format is
  also removed.
- **Sole third-party coupling:** `SkiaSharpImageCompressionService` is the only class touching
  SkiaSharp ("swapping image library = rewriting this file only"), and it bakes EXIF rotation in
  because Skia neither honours nor writes orientation.
- **Storage-root resolution** goes through `ImageBankRootResolver`, which is supposed to mirror
  `Startup.cs`'s static-file wiring but has already drifted from it — `_conflicts.md` #326.
- Code quality here is materially above this codebase's norm (atomic temp-file-then-move writes,
  path-traversal guards on every resolved path, read-before-respond so a failure can still fall
  through, documented fail-soft at every layer) — noted because it contrasts sharply with the
  finding density elsewhere in this registry.

---

<!-- BEGIN generated: entity registry (gen-entity-index.js) -->

## Every classified entity — generated from `_entity-classes.tsv`

> Generated by `_system/gen-entity-index.js`; do not edit between the sentinels. The hand-written
> sections above carry the judgement, this table carries the completeness. Regenerate after any
> change to `_entity-classes.tsv`, and `verify-notes.js` will fail if the two disagree.

**305 classified entities** — 242 documented, 63 excluded with stated evidence.

### Documented

| Entity | Class | Shape | Context | Feature | Note |
|---|---|---|---|---|---|
| `AboutApp` | lookup | covered-by | Customer Ordering | Marketing & Content | folded into [[Notification-Delivery.technical\|Notification-Delivery]] |
| `AdCard` | legacy-poco-root | covered-by | Customer Ordering | Marketing & Content | folded into [[Notification-Delivery.technical\|Notification-Delivery]] |
| `AdReservation` | child | covered-by | Customer Ordering | Marketing & Content | folded into [[Notification-Delivery.technical\|Notification-Delivery]] |
| `Ads` | legacy-poco-root | covered-by | Customer Ordering | Marketing & Content | folded into [[Notification-Delivery.technical\|Notification-Delivery]] |
| `Announcement` | legacy-poco-root | covered-by | Customer Ordering | Marketing & Content | folded into [[Notification-Delivery.technical\|Notification-Delivery]] |
| `AnnouncementDescription` | child | covered-by | Customer Ordering | Marketing & Content | folded into [[Notification-Delivery.technical\|Notification-Delivery]] |
| `ApiKey` | child | single | Admin | Admin Back-Office | [[ApiKey\|ApiKey]] |
| `Application` | lookup | covered-by | Identity & Access | Authentication & Tokens | folded into [[Identity.technical\|Identity]] |
| `Area` | child | covered-by | Admin | City & Geography Administration | folded into [[Area-and-Country\|Area-and-Country]] |
| `AreaDecription` | child | covered-by | Admin | City & Geography Administration | folded into [[Area-and-Country\|Area-and-Country]] |
| `AspNetUser` | child | covered-by | Identity & Access | Restaurant & Admin User Identity | folded into [[Identity.technical\|Identity]] |
| `AspNetUserAttendance` | legacy-poco-root | covered-by | Identity & Access | Restaurant & Admin User Identity | folded into [[Identity.technical\|Identity]] |
| `AspNetUserRestaurant` | child | covered-by | Identity & Access | Restaurant & Admin User Identity | folded into [[Identity.technical\|Identity]] |
| `AspNetUserShift` | legacy-poco-root | covered-by | Identity & Access | Restaurant & Admin User Identity | folded into [[Identity.technical\|Identity]] |
| `Audiance` | child | single | Customer Ordering | Marketing & Content | [[Audiance\|Audiance]] |
| `AudianceFilter` | child | covered-by | Customer Ordering | Marketing & Content | folded into [[Notification-Delivery.technical\|Notification-Delivery]] |
| `AudienceCustomer` | child | covered-by | Customer Ordering | Marketing & Content | folded into [[Notification-Delivery.technical\|Notification-Delivery]] |
| `AudienceCustomerAds` | child | covered-by | Customer Ordering | Marketing & Content | folded into [[Notification-Delivery.technical\|Notification-Delivery]] |
| `Audit` | lookup | covered-by | Admin | Admin Back-Office | folded into [[Configuration.technical\|Configuration]] |
| `AutoAssignRequest` | child | covered-by | Delivery | Delivery Man Operations | folded into [[Delivery-Assignment-Strategies\|Delivery-Assignment-Strategies]] |
| `AutoCompensationEvidenceRule` | legacy-poco-root | covered-by | Customer Ordering | Order & Fulfilment | folded into [[Order-Lifecycle.technical\|Order-Lifecycle]] |
| `AutoCompensationQuestion` | child | covered-by | Customer Ordering | Order & Fulfilment | folded into [[Order-Lifecycle.technical\|Order-Lifecycle]] |
| `AutoCompensationQuestionOption` | child | covered-by | Customer Ordering | Order & Fulfilment | folded into [[Order-Lifecycle.technical\|Order-Lifecycle]] |
| `AutoCompensationReason` | legacy-poco-root | covered-by | Customer Ordering | Order & Fulfilment | folded into [[Order-Lifecycle.technical\|Order-Lifecycle]] |
| `AutoCompensationRulesAuditLog` | legacy-poco-root | covered-by | Customer Ordering | Order & Fulfilment | folded into [[Order-Lifecycle.technical\|Order-Lifecycle]] |
| `AutoCompensationSettings` | legacy-poco-root | covered-by | Customer Ordering | Order & Fulfilment | folded into [[Order-Lifecycle.technical\|Order-Lifecycle]] |
| `AvilableDeliveryMan` | lookup | covered-by | Delivery | Delivery Man Operations | folded into [[Delivery-Assignment-Strategies\|Delivery-Assignment-Strategies]] |
| `BitirixLeadStatus` | legacy-poco-root | covered-by | Admin | ERP & Integrations | folded into [[Configuration.technical\|Configuration]] |
| `BlockedUsersFromCOD` | legacy-poco-root | single | Customer Ordering | Cart & Checkout | [[BlockedUsersFromCOD\|BlockedUsersFromCOD]] |
| `Brand` | legacy-poco-root | covered-by | Customer Ordering | Restaurant & Menu Discovery | folded into [[Discovery-Utilities\|Discovery-Utilities]] |
| `BrandDescription` | child | covered-by | Customer Ordering | Restaurant & Menu Discovery | folded into [[Discovery-Utilities\|Discovery-Utilities]] |
| `CartItem` | child | single | Customer Ordering | Cart & Checkout | [[CartItem\|CartItem]] |
| `CartItemOptions` | child | covered-by | Customer Ordering | Cart & Checkout | folded into [[CartItem\|CartItem]] |
| `ChatMessage` | child | covered-by | Customer Ordering | Support & Chat | folded into [[Support-and-Chat.technical\|Support-and-Chat]] |
| `ChatSetting` | legacy-poco-root | covered-by | Customer Ordering | Support & Chat | folded into [[Support-and-Chat.technical\|Support-and-Chat]] |
| `City` | legacy-poco-root | pair | Admin | City & Geography Administration | [[City.technical\|City]] |
| `CityBreakConfiguration` | legacy-poco-root | single | Admin | City & Geography Administration | [[CityBreakConfiguration\|CityBreakConfiguration]] |
| `CityDailyPickupTagCounter` | legacy-poco-root | covered-by | Admin | City & Geography Administration | folded into [[Area-and-Country\|Area-and-Country]] |
| `CityDescription` | child | covered-by | Admin | City & Geography Administration | folded into [[Area-and-Country\|Area-and-Country]] |
| `CityRushTimeConfigHistory` | child | covered-by | Admin | City & Geography Administration | folded into [[Area-and-Country\|Area-and-Country]] |
| `CityRushTimeConfiguration` | legacy-poco-root | pair | Admin | City & Geography Administration | [[CityRushTimeConfiguration.technical\|CityRushTimeConfiguration]] |
| `CitySuggestions` | legacy-poco-root | covered-by | Admin | City & Geography Administration | folded into [[Area-and-Country\|Area-and-Country]] |
| `Compensation` | child | single | Delivery | Driver Cash & Compensation | [[Compensation\|Compensation]] |
| `ComplaintsAndSuggestions` | legacy-poco-root | covered-by | Customer Ordering | Support & Chat | folded into [[Support-and-Chat.technical\|Support-and-Chat]] |
| `Configuration` | legacy-poco-root | pair | Admin | Admin Back-Office | [[Configuration.technical\|Configuration]] |
| `CookingTimeCategory` | legacy-poco-root | covered-by | Customer Ordering | Restaurant & Menu Discovery | folded into [[Discovery-Utilities\|Discovery-Utilities]] |
| `Country` | legacy-poco-root | covered-by | Admin | City & Geography Administration | folded into [[Area-and-Country\|Area-and-Country]] |
| `Customer` | legacy-poco-root | pair | Identity & Access | Customer Identity | [[Customer.technical\|Customer]] |
| `CustomerActionsHistory` | child | covered-by | Identity & Access | Customer Identity | folded into [[Customer.technical\|Customer]] |
| `CustomerAddresses` | child | single | Identity & Access | Customer Identity | [[CustomerAddresses\|CustomerAddresses]] |
| `CustomerAdminChat` | legacy-poco-root | covered-by | Customer Ordering | Support & Chat | folded into [[Support-and-Chat.technical\|Support-and-Chat]] |
| `CustomerAdminChatMessage` | child | covered-by | Customer Ordering | Support & Chat | folded into [[Support-and-Chat.technical\|Support-and-Chat]] |
| `CustomerAds` | legacy-poco-root | covered-by | Identity & Access | Customer Identity | folded into [[Customer.technical\|Customer]] |
| `CustomerCard` | child | covered-by | Identity & Access | Customer Identity | folded into [[Customer.technical\|Customer]] |
| `CustomerCart` | legacy-poco-root | pair | Customer Ordering | Cart & Checkout | [[CustomerCart.technical\|CustomerCart]] |
| `CustomerDeliveryChat` | legacy-poco-root | covered-by | Customer Ordering | Support & Chat | folded into [[Support-and-Chat.technical\|Support-and-Chat]] |
| `CustomerDeliveryChatMessage` | child | covered-by | Customer Ordering | Support & Chat | folded into [[Support-and-Chat.technical\|Support-and-Chat]] |
| `CustomerDeliveryInstruction` | child | covered-by | Identity & Access | Customer Identity | folded into [[Customer.technical\|Customer]] |
| `CustomerItemNotificationRequest` | legacy-poco-root | covered-by | Identity & Access | Customer Identity | folded into [[Customer.technical\|Customer]] |
| `CustomerItemOrderStats` | child | covered-by | Identity & Access | Customer Identity | folded into [[Customer.technical\|Customer]] |
| `CustomerMultiSearchKeyword` | legacy-poco-root | covered-by | Identity & Access | Customer Identity | folded into [[Customer.technical\|Customer]] |
| `CustomerNotification` | child | covered-by | Identity & Access | Customer Identity | folded into [[Customer.technical\|Customer]] |
| `CustomerNotificationCustomersData` | child | covered-by | Identity & Access | Customer Identity | folded into [[Customer.technical\|Customer]] |
| `CustomerNotificationNewVersion` | legacy-poco-root | covered-by | Identity & Access | Customer Identity | folded into [[Customer.technical\|Customer]] |
| `CustomerSavedTipsConfiguration` | legacy-poco-root | covered-by | Identity & Access | Customer Identity | folded into [[Customer.technical\|Customer]] |
| `CustomerTag` | child | covered-by | Identity & Access | Customer Identity | folded into [[Customer.technical\|Customer]] |
| `CustomerTipsConfig` | legacy-poco-root | covered-by | Identity & Access | Customer Identity | folded into [[Customer.technical\|Customer]] |
| `DeletedOrderDetailsItemsHistory` | child | covered-by | Customer Ordering | Order & Fulfilment | folded into [[Order-Lifecycle.technical\|Order-Lifecycle]] |
| `DeliveryAnnouncement` | aggregate-root | pair | Delivery | Delivery Man Operations | [[DeliveryAnnouncement.technical\|DeliveryAnnouncement]] |
| `DeliveryAsset` | legacy-poco-root | covered-by | Delivery | Delivery Man Operations | folded into [[Delivery-Requests-and-Suppliers\|Delivery-Requests-and-Suppliers]] |
| `DeliveryAssetDeliveryMan` | child | covered-by | Delivery | Delivery Man Operations | folded into [[Delivery-Requests-and-Suppliers\|Delivery-Requests-and-Suppliers]] |
| `DeliveryBouns` | legacy-poco-root | pair | Delivery | Driver Cash & Compensation | [[DeliveryBouns.technical\|DeliveryBouns]] |
| `DeliveryBounsTier` | child | covered-by | Delivery | Driver Cash & Compensation | folded into [[Driver-Cash-Cycle.technical\|Driver-Cash-Cycle]] |
| `DeliveryBoxUnitSize` | legacy-poco-root | covered-by | Delivery | Delivery Man Operations | folded into [[Delivery-Requests-and-Suppliers\|Delivery-Requests-and-Suppliers]] |
| `DeliveryComment` | child | covered-by | Delivery | Delivery Man Operations | folded into [[Delivery-Requests-and-Suppliers\|Delivery-Requests-and-Suppliers]] |
| `DeliveryInstruction` | legacy-poco-root | covered-by | Delivery | Delivery Man Operations | folded into [[Delivery-Requests-and-Suppliers\|Delivery-Requests-and-Suppliers]] |
| `DeliveryInstructionDescription` | child | covered-by | Delivery | Delivery Man Operations | folded into [[Delivery-Requests-and-Suppliers\|Delivery-Requests-and-Suppliers]] |
| `DeliveryInterval` | legacy-poco-root | covered-by | Customer Ordering | Order & Fulfilment | folded into [[Order-Lifecycle.technical\|Order-Lifecycle]] |
| `DeliveryInterval_Area` | child | covered-by | Customer Ordering | Order & Fulfilment | folded into [[Order-Lifecycle.technical\|Order-Lifecycle]] |
| `DeliveryIntervalsDescription` | child | covered-by | Customer Ordering | Order & Fulfilment | folded into [[Order-Lifecycle.technical\|Order-Lifecycle]] |
| `DeliveryManAdminChat` | legacy-poco-root | covered-by | Delivery | Delivery Man Operations | folded into [[Driver-Operations.technical\|Driver-Operations]] |
| `DeliveryManAdminChatMessage` | child | covered-by | Delivery | Delivery Man Operations | folded into [[Driver-Operations.technical\|Driver-Operations]] |
| `DeliverymanBreakLog` | child | covered-by | Delivery | Delivery Man Operations | folded into [[Driver-Operations.technical\|Driver-Operations]] |
| `DeliveryManDaily` | legacy-poco-root | covered-by | Delivery | Delivery Man Operations | folded into [[Driver-Operations.technical\|Driver-Operations]] |
| `DeliveryManLowRateReasons` | child | covered-by | Delivery | Delivery Man Operations | folded into [[Driver-Operations.technical\|Driver-Operations]] |
| `DeliveryManNotification` | aggregate-root | pair | Delivery | Delivery Man Operations | [[DeliveryManNotification.technical\|DeliveryManNotification]] |
| `DeliveryManNotificationDetail` | child | covered-by | Delivery | Delivery Man Operations | folded into [[DeliveryManNotification.technical\|Driver-Operations]] |
| `DeliveryManOfflineLog` | legacy-poco-root | covered-by | Delivery | Delivery Man Operations | folded into [[Driver-Operations.technical\|Driver-Operations]] |
| `DeliveryManPayments` | legacy-poco-root | covered-by | Delivery | Delivery Man Operations | folded into [[Driver-Operations.technical\|Driver-Operations]] |
| `DeliveryManPrice` | child | covered-by | Delivery | Delivery Man Operations | folded into [[Driver-Operations.technical\|Driver-Operations]] |
| `DeliveryManReview` | child | covered-by | Delivery | Delivery Man Operations | folded into [[Driver-Operations.technical\|Driver-Operations]] |
| `DeliverymanShiftLog` | child | covered-by | Delivery | Delivery Man Operations | folded into [[Driver-Operations.technical\|Driver-Operations]] |
| `DeliveryManStates` | lookup | covered-by | Delivery | Delivery Man Operations | folded into [[Driver-Operations.technical\|Driver-Operations]] |
| `DeliverymanTransaction` | child | pair | Delivery | Delivery Man Operations | [[DeliverymanTransaction.technical\|DeliverymanTransaction]] |
| `DeliveryManWorkingHours` | legacy-poco-root | covered-by | Delivery | Delivery Man Operations | folded into [[Driver-Operations.technical\|Driver-Operations]] |
| `DeliverymanZone` | child | covered-by | Delivery | Delivery Man Operations | folded into [[Driver-Operations.technical\|Driver-Operations]] |
| `DeliveryMen` | child | pair | Delivery | Delivery Man Operations | [[DeliveryMen.technical\|DeliveryMen]] |
| `DeliveryMenAttendance` | legacy-poco-root | covered-by | Delivery | Delivery Man Operations | folded into [[Driver-Operations.technical\|Driver-Operations]] |
| `DeliveryMenLocations` | legacy-poco-root | covered-by | Delivery | Delivery Man Operations | folded into [[Driver-Operations.technical\|Driver-Operations]] |
| `DeliveryMenMoneyRequest` | legacy-poco-root | covered-by | Delivery | Delivery Man Operations | folded into [[Driver-Operations.technical\|Driver-Operations]] |
| `DeliveryMenShifts` | legacy-poco-root | covered-by | Delivery | Delivery Man Operations | folded into [[Driver-Operations.technical\|Driver-Operations]] |
| `DeliveryReason` | legacy-poco-root | covered-by | Delivery | Delivery Man Operations | folded into [[Delivery-Requests-and-Suppliers\|Delivery-Requests-and-Suppliers]] |
| `DeliverySupplier` | child | covered-by | Delivery | Delivery Man Operations | folded into [[Delivery-Requests-and-Suppliers\|Delivery-Requests-and-Suppliers]] |
| `DeliverySuppliersCities` | child | covered-by | Delivery | Delivery Man Operations | folded into [[Delivery-Requests-and-Suppliers\|Delivery-Requests-and-Suppliers]] |
| `DeliveryZone` | child | single | Delivery | Delivery Man Operations | [[DeliveryZone\|DeliveryZone]] |
| `DeliveryZoneArea` | child | covered-by | Delivery | Delivery Man Operations | folded into [[Delivery-Requests-and-Suppliers\|Delivery-Requests-and-Suppliers]] |
| `DriverDismissalLog` | child | covered-by | Delivery | Delivery Man Operations | folded into [[Driver-Operations.technical\|Driver-Operations]] |
| `EntityChangeHistory` | legacy-poco-root | covered-by | Admin | Admin Back-Office | folded into [[Configuration.technical\|Configuration]] |
| `ExclusiveOfferItem` | legacy-poco-root | covered-by | Customer Ordering | Discounts & Coupons | folded into [[Discount-Resolution.technical\|Discount-Resolution]] |
| `ExcutionHistory` | child | covered-by | Admin | Admin Back-Office | folded into [[Configuration.technical\|Configuration]] |
| `ExternalCustomer` | legacy-poco-root | covered-by | Customer Ordering | Order & Fulfilment | folded into [[Order.ExternalDelivery\|Order.ExternalDelivery]] |
| `ExternalCustomerAdress` | child | covered-by | Customer Ordering | Order & Fulfilment | folded into [[Order.ExternalDelivery\|Order.ExternalDelivery]] |
| `ExternalDeliveryRequests` | legacy-poco-root | covered-by | Customer Ordering | Order & Fulfilment | folded into [[Order.ExternalDelivery\|Order.ExternalDelivery]] |
| `FAQItem` | legacy-poco-root | covered-by | Customer Ordering | Marketing & Content | folded into [[Notification-Delivery.technical\|Notification-Delivery]] |
| `Favourites` | child | covered-by | Customer Ordering | Restaurant & Menu Discovery | folded into [[Discovery-Utilities\|Discovery-Utilities]] |
| `FawryCashCollectionTransaction` | legacy-poco-root | covered-by | Customer Ordering | Payments | folded into [[Money-Path.technical\|Money-Path]] |
| `FawryTransaction` | legacy-poco-root | covered-by | Customer Ordering | Payments | folded into [[Money-Path.technical\|Money-Path]] |
| `FoodType` | legacy-poco-root | covered-by | Customer Ordering | Restaurant & Menu Discovery | folded into [[Discovery-Utilities\|Discovery-Utilities]] |
| `FoodTypesDescription` | child | covered-by | Customer Ordering | Restaurant & Menu Discovery | folded into [[Discovery-Utilities\|Discovery-Utilities]] |
| `ImageBank` | legacy-poco-root | covered-by | Admin | Catalog & Content Administration | folded into [[Mart-and-Reference-Entities\|Mart-and-Reference-Entities]] |
| `ItemDescription` | child | covered-by | Customer Ordering | Restaurant & Menu Discovery | folded into [[Discovery-Utilities\|Discovery-Utilities]] |
| `ItemReplacementReport` | legacy-poco-root | covered-by | Customer Ordering | Order & Fulfilment | folded into [[Order-Lifecycle.technical\|Order-Lifecycle]] |
| `JournalSubuscriptions` | legacy-poco-root | covered-by | Delivery | Driver Cash & Compensation | folded into [[Driver-Cash-Cycle.technical\|Driver-Cash-Cycle]] |
| `LanGuage` | lookup | covered-by | Admin | Admin Back-Office | folded into [[Configuration.technical\|Configuration]] |
| `LoyaltyConfigAuditLog` | legacy-poco-root | covered-by | Customer Ordering | Discounts & Coupons | folded into [[Discount-Resolution.technical\|Discount-Resolution]] |
| `LoyaltyPoints` | child | single | Customer Ordering | Discounts & Coupons | [[LoyaltyPoints\|LoyaltyPoints]] |
| `LoyaltyPointsSrc` | child | covered-by | Customer Ordering | Discounts & Coupons | folded into [[Discount-Resolution.technical\|Discount-Resolution]] |
| `MainCategory` | lookup | covered-by | Customer Ordering | Restaurant & Menu Discovery | folded into [[MenuStructure\|MenuStructure]] |
| `MartMainCategory` | legacy-poco-root | covered-by | Customer Ordering | Restaurant & Menu Discovery | folded into [[Discovery-Utilities\|Discovery-Utilities]] |
| `MenuCategory` | child | covered-by | Customer Ordering | Restaurant & Menu Discovery | folded into [[Discovery-Utilities\|Discovery-Utilities]] |
| `MenuCategoryDescription` | child | covered-by | Customer Ordering | Restaurant & Menu Discovery | folded into [[Discovery-Utilities\|Discovery-Utilities]] |
| `MenuItem` | child | pair | Customer Ordering | Restaurant & Menu Discovery | [[MenuItem.technical\|MenuItem]] |
| `MenuItemOptionCategoryDescription` | child | covered-by | Customer Ordering | Restaurant & Menu Discovery | folded into [[Discovery-Utilities\|Discovery-Utilities]] |
| `MenuItemOptionGroup` | child | covered-by | Customer Ordering | Restaurant & Menu Discovery | folded into [[Discovery-Utilities\|Discovery-Utilities]] |
| `MenuItemOptionGroupDescription` | child | covered-by | Customer Ordering | Restaurant & Menu Discovery | folded into [[Discovery-Utilities\|Discovery-Utilities]] |
| `MenuItemOptionGroupItem` | child | covered-by | Customer Ordering | Restaurant & Menu Discovery | folded into [[Discovery-Utilities\|Discovery-Utilities]] |
| `MenuItemOptionGroupItemDescription` | child | covered-by | Customer Ordering | Restaurant & Menu Discovery | folded into [[Discovery-Utilities\|Discovery-Utilities]] |
| `MenuItemOptions` | child | covered-by | Customer Ordering | Restaurant & Menu Discovery | folded into [[Discovery-Utilities\|Discovery-Utilities]] |
| `MenuItemOptionsCategories` | child | covered-by | Customer Ordering | Restaurant & Menu Discovery | folded into [[Discovery-Utilities\|Discovery-Utilities]] |
| `MenuItemPrice` | child | single | Customer Ordering | Restaurant & Menu Discovery | [[MenuItemPrice.technical\|MenuItemPrice]] |
| `MenuItemPriceDescription` | child | covered-by | Customer Ordering | Restaurant & Menu Discovery | folded into [[Discovery-Utilities\|Discovery-Utilities]] |
| `MenuItemPriceSku` | child | covered-by | Customer Ordering | Restaurant & Menu Discovery | folded into [[Discovery-Utilities\|Discovery-Utilities]] |
| `MenuItemReplacement` | child | covered-by | Customer Ordering | Restaurant & Menu Discovery | folded into [[Discovery-Utilities\|Discovery-Utilities]] |
| `MerchantCapacityHours` | child | covered-by | Restaurant Portal | Merchant Account & Access | folded into [[Merchant-Menu-and-Orders.technical\|Merchant-Menu-and-Orders]] |
| `MerchantInstructionsVideos` | legacy-poco-root | covered-by | Restaurant Portal | Merchant Account & Access | folded into [[Merchant-Menu-and-Orders.technical\|Merchant-Menu-and-Orders]] |
| `MerchantKpiScoreConfiguration` | child | covered-by | Restaurant Portal | Merchant Account & Access | folded into [[Merchant-Menu-and-Orders.technical\|Merchant-Menu-and-Orders]] |
| `MerchantLoyaltyConfig` | legacy-poco-root | covered-by | Restaurant Portal | Merchant Account & Access | folded into [[Merchant-Menu-and-Orders.technical\|Merchant-Menu-and-Orders]] |
| `MerchantReceivement` | legacy-poco-root | covered-by | Restaurant Portal | Merchant Account & Access | folded into [[Merchant-Menu-and-Orders.technical\|Merchant-Menu-and-Orders]] |
| `MerchantRejectionReasons` | legacy-poco-root | covered-by | Restaurant Portal | Merchant Account & Access | folded into [[Merchant-Menu-and-Orders.technical\|Merchant-Menu-and-Orders]] |
| `MerchantStatementTransaction` | child | covered-by | Restaurant Portal | Merchant Account & Access | folded into [[Merchant-Menu-and-Orders.technical\|Merchant-Menu-and-Orders]] |
| `NonDeliveryReason` | legacy-poco-root | covered-by | Delivery | Delivery Man Operations | folded into [[Delivery-Requests-and-Suppliers\|Delivery-Requests-and-Suppliers]] |
| `Notification` | lookup | covered-by | Customer Ordering | Marketing & Content | folded into [[Notification-Delivery.technical\|Notification-Delivery]] |
| `NotificationExecutionHistory` | child | covered-by | Customer Ordering | Marketing & Content | folded into [[Notification-Delivery.technical\|Notification-Delivery]] |
| `NotificationTarget` | legacy-poco-root | covered-by | Customer Ordering | Marketing & Content | folded into [[Notification-Delivery.technical\|Notification-Delivery]] |
| `OfferItem` | child | covered-by | Customer Ordering | Discounts & Coupons | folded into [[Discount-Resolution.technical\|Discount-Resolution]] |
| `Offers` | child | pair | Customer Ordering | Discounts & Coupons | [[Offers.technical\|Offers]] |
| `OffersDescriptions` | child | covered-by | Customer Ordering | Discounts & Coupons | folded into [[Discount-Resolution.technical\|Discount-Resolution]] |
| `Order` | child | pair | Customer Ordering | Order & Fulfilment | [[Order.technical\|Order]] |
| `Order` | child | pair | Customer Ordering | Order & Fulfilment | [[Order.technical\|Order]] |
| `OrderAgentAssignment` | child | covered-by | Customer Ordering | Order & Fulfilment | folded into [[Order-Lifecycle.technical\|Order-Lifecycle]] |
| `OrderChat` | legacy-poco-root | covered-by | Customer Ordering | Order & Fulfilment | folded into [[Order-Lifecycle.technical\|Order-Lifecycle]] |
| `OrderComment` | child | covered-by | Customer Ordering | Order & Fulfilment | folded into [[Order-Lifecycle.technical\|Order-Lifecycle]] |
| `OrderComplaint` | aggregate-root | single | Customer Ordering | Order & Fulfilment | [[OrderComplaint\|OrderComplaint]] |
| `OrderComplaintReason` | child | covered-by | Customer Ordering | Order & Fulfilment | folded into [[Order-Lifecycle.technical\|Order-Lifecycle]] |
| `OrderComplaintReasonType` | child | covered-by | Customer Ordering | Order & Fulfilment | folded into [[Order-Lifecycle.technical\|Order-Lifecycle]] |
| `OrderCostHolder` | legacy-poco-root | covered-by | Customer Ordering | Order & Fulfilment | folded into [[Order-Lifecycle.technical\|Order-Lifecycle]] |
| `OrderCostHolderRestaurant` | child | covered-by | Customer Ordering | Order & Fulfilment | folded into [[Order-Lifecycle.technical\|Order-Lifecycle]] |
| `OrderCountTracking` | legacy-poco-root | covered-by | Customer Ordering | Order & Fulfilment | folded into [[Order-Lifecycle.technical\|Order-Lifecycle]] |
| `OrderDelivery` | child | pair | Customer Ordering | Order & Fulfilment | [[OrderDelivery.technical\|OrderDelivery]] |
| `OrderDetailReplacement` | child | covered-by | Customer Ordering | Order & Fulfilment | folded into [[Order-Lifecycle.technical\|Order-Lifecycle]] |
| `OrderDetails` | child | single | Customer Ordering | Order & Fulfilment | [[OrderDetails.technical\|OrderDetails]] |
| `OrderDetailsOptions` | child | covered-by | Customer Ordering | Order & Fulfilment | folded into [[Order-Lifecycle.technical\|Order-Lifecycle]] |
| `OrderPayment` | child | covered-by | Customer Ordering | Order & Fulfilment | folded into [[Order-Lifecycle.technical\|Order-Lifecycle]] |
| `OrderPaymentStates` | lookup | covered-by | Customer Ordering | Order & Fulfilment | folded into [[Order-Lifecycle.technical\|Order-Lifecycle]] |
| `OrderRejectedReason` | legacy-poco-root | covered-by | Customer Ordering | Order & Fulfilment | folded into [[Order-Lifecycle.technical\|Order-Lifecycle]] |
| `OrderRestaurantDelivery` | child | covered-by | Customer Ordering | Order & Fulfilment | folded into [[Order-Lifecycle.technical\|Order-Lifecycle]] |
| `OrderRestaurantDetails` | child | single | Customer Ordering | Order & Fulfilment | [[OrderRestaurantDetails\|OrderRestaurantDetails]] |
| `OrderStates` | lookup | covered-by | Customer Ordering | Order & Fulfilment | folded into [[Order-Lifecycle.technical\|Order-Lifecycle]] |
| `OrderStatusHistory` | child | covered-by | Customer Ordering | Order & Fulfilment | folded into [[Order-Lifecycle.technical\|Order-Lifecycle]] |
| `PaymentMethod` | legacy-poco-root | single | Customer Ordering | Payments | [[PaymentMethod\|PaymentMethod]] |
| `PaymentMethodCountries` | child | covered-by | Customer Ordering | Payments | folded into [[Money-Path.technical\|Money-Path]] |
| `PayMobTransaction` | child | covered-by | Customer Ordering | Payments | folded into [[Money-Path.technical\|Money-Path]] |
| `Permission` | lookup | pair | Identity & Access | Restaurant & Admin User Identity | [[Permission.technical\|Permission]] |
| `PrivacyPolicy` | legacy-poco-root | covered-by | Customer Ordering | Marketing & Content | folded into [[Notification-Delivery.technical\|Notification-Delivery]] |
| `PromoCodeArea` | child | covered-by | Customer Ordering | Discounts & Coupons | folded into [[Discount-Resolution.technical\|Discount-Resolution]] |
| `PromoCodeAudience` | child | covered-by | Customer Ordering | Discounts & Coupons | folded into [[Discount-Resolution.technical\|Discount-Resolution]] |
| `PromoCodeCity` | child | covered-by | Customer Ordering | Discounts & Coupons | folded into [[Discount-Resolution.technical\|Discount-Resolution]] |
| `PromoCodeCustomer` | child | covered-by | Customer Ordering | Discounts & Coupons | folded into [[Discount-Resolution.technical\|Discount-Resolution]] |
| `PromoCodes` | legacy-poco-root | pair | Customer Ordering | Discounts & Coupons | [[PromoCodes.technical\|PromoCodes]] |
| `RecommendationInteractionEvent` | legacy-poco-root | covered-by | Customer Ordering | Restaurant & Menu Discovery | folded into [[Discovery-Utilities\|Discovery-Utilities]] |
| `RefreshToken` | lookup | covered-by | Identity & Access | Authentication & Tokens | folded into [[Identity.technical\|Identity]] |
| `Restaurant` | child | pair | Customer Ordering | Restaurant & Menu Discovery | [[Restaurant.technical\|Restaurant]] |
| `Restaurant_FoodTypes` | child | covered-by | Customer Ordering | Restaurant & Menu Discovery | folded into [[Discovery-Utilities\|Discovery-Utilities]] |
| `RestaurantArea` | child | covered-by | Customer Ordering | Restaurant & Menu Discovery | folded into [[Discovery-Utilities\|Discovery-Utilities]] |
| `RestaurantDescription` | child | covered-by | Customer Ordering | Restaurant & Menu Discovery | folded into [[Discovery-Utilities\|Discovery-Utilities]] |
| `RestaurantFinalScoreRate` | lookup | covered-by | Customer Ordering | Restaurant & Menu Discovery | folded into [[Discovery-Utilities\|Discovery-Utilities]] |
| `RestaurantJournalSubuscriptions` | child | covered-by | Customer Ordering | Restaurant & Menu Discovery | folded into [[Discovery-Utilities\|Discovery-Utilities]] |
| `RestaurantPromoCode` | child | covered-by | Customer Ordering | Restaurant & Menu Discovery | folded into [[Discovery-Utilities\|Discovery-Utilities]] |
| `RestaurantReview` | child | single | Customer Ordering | Restaurant & Menu Discovery | [[RestaurantReview\|RestaurantReview]] |
| `RestaurantZone` | legacy-poco-root | covered-by | Customer Ordering | Restaurant & Menu Discovery | folded into [[Discovery-Utilities\|Discovery-Utilities]] |
| `RestaurantZoneArea` | child | covered-by | Customer Ordering | Restaurant & Menu Discovery | folded into [[Discovery-Utilities\|Discovery-Utilities]] |
| `ResturantBusyHistory` | child | covered-by | Customer Ordering | Restaurant & Menu Discovery | folded into [[Discovery-Utilities\|Discovery-Utilities]] |
| `RoboCall` | legacy-poco-root | covered-by | Delivery | Delivery Man Operations | folded into [[Delivery-Requests-and-Suppliers\|Delivery-Requests-and-Suppliers]] |
| `RoboCallOrder` | child | covered-by | Delivery | Delivery Man Operations | folded into [[Delivery-Requests-and-Suppliers\|Delivery-Requests-and-Suppliers]] |
| `RolePermission` | child | covered-by | Identity & Access | Restaurant & Admin User Identity | folded into [[Identity.technical\|Identity]] |
| `RushTimeAreaPriority` | child | covered-by | Admin | City & Geography Administration | folded into [[Area-and-Country\|Area-and-Country]] |
| `SalesDaily` | legacy-poco-root | covered-by | Admin | Order & Customer Administration | folded into [[Configuration.technical\|Configuration]] |
| `ScheduledNotification` | legacy-poco-root | covered-by | Customer Ordering | Marketing & Content | folded into [[Notification-Delivery.technical\|Notification-Delivery]] |
| `ScheduledNotificationCustomerGroupType` | child | covered-by | Customer Ordering | Marketing & Content | folded into [[Notification-Delivery.technical\|Notification-Delivery]] |
| `SearchHistory` | legacy-poco-root | covered-by | Customer Ordering | Restaurant & Menu Discovery | folded into [[Discovery-Utilities\|Discovery-Utilities]] |
| `ShiftLocation` | child | covered-by | Delivery | Delivery Man Operations | folded into [[Driver-Operations.technical\|Driver-Operations]] |
| `SliderHome` | legacy-poco-root | covered-by | Customer Ordering | Restaurant & Menu Discovery | folded into [[Discovery-Utilities\|Discovery-Utilities]] |
| `SpecialMartCategorySetting` | legacy-poco-root | covered-by | Customer Ordering | Restaurant & Menu Discovery | folded into [[Mart\|Mart]] |
| `StoreTypeCities` | child | covered-by | Customer Ordering | Restaurant & Menu Discovery | folded into [[Discovery-Utilities\|Discovery-Utilities]] |
| `StoreTypes` | child | single | Customer Ordering | Restaurant & Menu Discovery | [[StoreTypes.technical\|StoreTypes]] |
| `StoreTypesDescription` | child | covered-by | Customer Ordering | Restaurant & Menu Discovery | folded into [[Discovery-Utilities\|Discovery-Utilities]] |
| `Tag` | lookup | covered-by | Customer Ordering | Restaurant & Menu Discovery | folded into [[Discovery-Utilities\|Discovery-Utilities]] |
| `Tasks` | child | covered-by | Admin | Admin Back-Office | folded into [[Configuration.technical\|Configuration]] |
| `TaskType` | legacy-poco-root | covered-by | Admin | Admin Back-Office | folded into [[Configuration.technical\|Configuration]] |
| `TermsAndConditions` | legacy-poco-root | covered-by | Customer Ordering | Marketing & Content | folded into [[Notification-Delivery.technical\|Notification-Delivery]] |
| `TieredDiscount` | aggregate-root | pair | Customer Ordering | Tiered Discount | [[TieredDiscount.technical\|TieredDiscount]] |
| `TieredDiscountCustomer` | child | covered-by | Customer Ordering | Tiered Discount | folded into [[TieredDiscountTier\|TieredDiscountTier]] |
| `TieredDiscountRestaurant` | child | covered-by | Customer Ordering | Tiered Discount | folded into [[TieredDiscountTier\|TieredDiscountTier]] |
| `TieredDiscountSegment` | child | covered-by | Customer Ordering | Tiered Discount | folded into [[TieredDiscountTier\|TieredDiscountTier]] |
| `TieredDiscountTier` | child | single | Customer Ordering | Tiered Discount | [[TieredDiscountTier\|TieredDiscountTier]] |
| `UnbanReason` | legacy-poco-root | covered-by | Delivery | Delivery Man Operations | folded into [[Delivery-Requests-and-Suppliers\|Delivery-Requests-and-Suppliers]] |
| `UnRegesteredCustomers` | legacy-poco-root | covered-by | Identity & Access | Customer Identity | folded into [[Customer.technical\|Customer]] |
| `UnRevisedItem` | legacy-poco-root | covered-by | Customer Ordering | Order & Fulfilment | folded into [[Order-Lifecycle.technical\|Order-Lifecycle]] |
| `UserShift` | legacy-poco-root | covered-by | Identity & Access | Restaurant & Admin User Identity | folded into [[Identity.technical\|Identity]] |
| `UserShiftDetails` | child | covered-by | Identity & Access | Restaurant & Admin User Identity | folded into [[Identity.technical\|Identity]] |
| `Vouchers` | legacy-poco-root | pair | Customer Ordering | Discounts & Coupons | [[Vouchers.technical\|Vouchers]] |
| `WalletTransaction` | child | single | Customer Ordering | Payments | [[WalletTransaction\|WalletTransaction]] |
| `WalletTransactionRechargeReason` | legacy-poco-root | covered-by | Customer Ordering | Payments | folded into [[Money-Path.technical\|Money-Path]] |
| `Webhook` | legacy-poco-root | covered-by | Admin | Admin Back-Office | folded into [[Configuration.technical\|Configuration]] |
| `WebhookEvent` | lookup | covered-by | Admin | Admin Back-Office | folded into [[Configuration.technical\|Configuration]] |
| `WebhookSubscription` | child | covered-by | Admin | Admin Back-Office | folded into [[Configuration.technical\|Configuration]] |
| `WorkingDay` | child | covered-by | Admin | City & Geography Administration | folded into [[Area-and-Country\|Area-and-Country]] |
| `WorkUsDelivery` | child | covered-by | Delivery | Delivery Man Operations | folded into [[Driver-Operations.technical\|Driver-Operations]] |
| `WorkUsDeliveryHistory` | child | covered-by | Delivery | Delivery Man Operations | folded into [[Driver-Operations.technical\|Driver-Operations]] |
| `WorkUsDeliveryStatus` | legacy-poco-root | covered-by | Delivery | Delivery Man Operations | folded into [[Driver-Operations.technical\|Driver-Operations]] |
| `WorkUsRestaurant` | legacy-poco-root | covered-by | Delivery | Delivery Man Operations | folded into [[Driver-Operations.technical\|Driver-Operations]] |
| `WorkUsRestaurantComment` | child | covered-by | Delivery | Delivery Man Operations | folded into [[Driver-Operations.technical\|Driver-Operations]] |

### Excluded, with the evidence for each exclusion

| Entity | Class | Why it is not documented |
|---|---|---|
| `AdminOrderHistoryStoredProcure` | keyless-view | registered `.HasNoKey().ToView(null)` in Shared/TalabatkData/Talabatk_Context/TalabatkContext.cs:97-121 — a query shape, not a table |
| `AdminOrderList` | projection | stored-procedure / report result shape named in _inbox/pathA-A-models-batch04-final.md — no invariants |
| `AspNetRole` | identity-framework | ASP.NET Identity plumbing subclass — no business invariants (pathA-A-models-batch04-final.md "Checked and clean") |
| `AspNetRoleClaims` | identity-framework | ASP.NET Identity plumbing subclass — no business invariants (pathA-A-models-batch04-final.md "Checked and clean") |
| `AspNetUserClaim` | identity-framework | ASP.NET Identity plumbing subclass — no business invariants (pathA-A-models-batch04-final.md "Checked and clean") |
| `AspNetUserLogin` | identity-framework | ASP.NET Identity plumbing subclass — no business invariants (pathA-A-models-batch04-final.md "Checked and clean") |
| `AspNetUserRole` | identity-framework | ASP.NET Identity plumbing subclass — no business invariants (pathA-A-models-batch04-final.md "Checked and clean") |
| `AspNetUserTokens` | identity-framework | ASP.NET Identity plumbing subclass — no business invariants (pathA-A-models-batch04-final.md "Checked and clean") |
| `AvalibleAds` | keyless-view | registered `.HasNoKey().ToView(null)` in Shared/TalabatkData/Talabatk_Context/TalabatkContext.cs:97-121 — a query shape, not a table |
| `BotPerformanceReportRow` | projection | stored-procedure / report result shape named in _inbox/pathA-A-models-batch04-final.md — no invariants |
| `CartItemOptionPoco` | dto | input/output DTO under a POCOs folder — carries no invariants of its own |
| `CategoriesCountsResult` | keyless-view | registered `.HasNoKey().ToView(null)` in Shared/TalabatkData/Talabatk_Context/TalabatkContext.cs:97-121 — a query shape, not a table |
| `ChatReportRow` | projection | stored-procedure / report result shape named in _inbox/pathA-A-models-batch04-final.md — no invariants |
| `CSTAppItemsCount` | keyless-view | registered `.HasNoKey().ToView(null)` in Shared/TalabatkData/Talabatk_Context/TalabatkContext.cs:97-121 — a query shape, not a table |
| `CustomerInfoStoredProcure` | keyless-view | registered `.HasNoKey().ToView(null)` in Shared/TalabatkData/Talabatk_Context/TalabatkContext.cs:97-121 — a query shape, not a table |
| `CustomerOrdersReport` | dto | input/output DTO under a POCOs folder — carries no invariants of its own |
| `CustomerOrderWithReview` | projection | stored-procedure / report result shape named in _inbox/pathA-A-models-batch04-final.md — no invariants |
| `CustomerWalletHistory` | projection | stored-procedure / report result shape named in _inbox/pathA-A-models-batch04-final.md — no invariants |
| `DeliveryBounsTierSpec` | dto | input/output DTO under a POCOs folder — carries no invariants of its own |
| `DeliveryManLastLocationView` | projection | stored-procedure / report result shape named in _inbox/pathA-A-models-batch04-final.md — no invariants |
| `DeliveryManNotificationStatusEnum` | enum-only | file declares 1 enum(s) and no class; enum values are documented with the entity that uses them |
| `DeliveryManOrders` | projection | stored-procedure / report result shape named in _inbox/pathA-A-models-batch04-final.md — no invariants |
| `DeliveryManOrderStoredProcure` | keyless-view | registered `.HasNoKey().ToView(null)` in Shared/TalabatkData/Talabatk_Context/TalabatkContext.cs:97-121 — a query shape, not a table |
| `DeliveryManPriceData` | projection | stored-procedure / report result shape named in _inbox/pathA-A-models-batch04-final.md — no invariants |
| `DeliveryManReviewMap` | infrastructure | not an entity: it is an EF `IEntityTypeConfiguration<DeliveryManReview>` (`DeliveryManReviewMap.cs:12`, `Configure` at `:14`) misfiled in the domain-models folder instead of Shared/TalabatkData/Mapping. It was classified as a lookup because a folder-based entity scan cannot tell the difference; the interface it implements can. Confirmed the only such case — one grep for IEntityTypeConfiguration un |
| `DeliveryMenReport` | projection | stored-procedure / report result shape named in _inbox/pathA-A-models-batch04-final.md — no invariants |
| `DeliveryMenTotalReport` | projection | stored-procedure / report result shape named in _inbox/pathA-A-models-batch04-final.md — no invariants |
| `DeliveryOrderRestaurant` | projection | stored-procedure / report result shape named in _inbox/pathA-A-models-batch04-final.md — no invariants |
| `DeliveryRoundOrderList` | projection | stored-procedure / report result shape named in _inbox/pathA-A-models-batch04-final.md — no invariants |
| `DriverPerformanceReportDto` | keyless-view | registered `.HasNoKey().ToView(null)` in Shared/TalabatkData/Talabatk_Context/TalabatkContext.cs:97-121 — a query shape, not a table |
| `EntityBase` | infrastructure | base/abstract type, not a persisted entity (pathA-A-models-batch04-final.md: EntityBase has zero derived types in the live project) |
| `ErpJournalLog` | projection | stored-procedure / report result shape named in _inbox/pathA-A-models-batch04-final.md — no invariants |
| `ErpRushOrderLog` | projection | stored-procedure / report result shape named in _inbox/pathA-A-models-batch04-final.md — no invariants |
| `ExternalCustomerAdressPoco` | dto | input/output DTO under a POCOs folder — carries no invariants of its own |
| `HomeSearchDefaultRestaurantRow` | keyless-view | registered `.HasNoKey().ToView(null)` in Shared/TalabatkData/Talabatk_Context/TalabatkContext.cs:97-121 — a query shape, not a table |
| `ItemReplacementReportSpRow` | keyless-view | registered `.HasNoKey().ToView(null)` in Shared/TalabatkData/Talabatk_Context/TalabatkContext.cs:97-121 — a query shape, not a table |
| `ItemReplacementResultStatusSpRow` | keyless-view | registered `.HasNoKey().ToView(null)` in Shared/TalabatkData/Talabatk_Context/TalabatkContext.cs:97-121 — a query shape, not a table |
| `ItemReplacementTopItemSpRow` | keyless-view | registered `.HasNoKey().ToView(null)` in Shared/TalabatkData/Talabatk_Context/TalabatkContext.cs:97-121 — a query shape, not a table |
| `ItemsByCategory` | projection | stored-procedure / report result shape named in _inbox/pathA-A-models-batch04-final.md — no invariants |
| `LastTaskUserView` | projection | stored-procedure / report result shape named in _inbox/pathA-A-models-batch04-final.md — no invariants |
| `MartBrandOffers` | keyless-view | registered `.HasNoKey().ToView(null)` in Shared/TalabatkData/Talabatk_Context/TalabatkContext.cs:97-121 — a query shape, not a table |
| `MartMainCategoryDto` | keyless-view | registered `.HasNoKey().ToView(null)` in Shared/TalabatkData/Talabatk_Context/TalabatkContext.cs:97-121 — a query shape, not a table |
| `MartProductCategoryDto` | keyless-view | registered `.HasNoKey().ToView(null)` in Shared/TalabatkData/Talabatk_Context/TalabatkContext.cs:97-121 — a query shape, not a table |
| `MartSubCategoryDto` | keyless-view | registered `.HasNoKey().ToView(null)` in Shared/TalabatkData/Talabatk_Context/TalabatkContext.cs:97-121 — a query shape, not a table |
| `MerchantAcceptanceReport` | projection | stored-procedure / report result shape named in _inbox/pathA-A-models-batch04-final.md — no invariants |
| `MerchantPerformanceReport` | projection | stored-procedure / report result shape named in _inbox/pathA-A-models-batch04-final.md — no invariants |
| `MerchantRejectedReport` | keyless-view | registered `.HasNoKey().ToView(null)` in Shared/TalabatkData/Talabatk_Context/TalabatkContext.cs:97-121 — a query shape, not a table |
| `OrderDeliveryRequest` | projection | stored-procedure / report result shape named in _inbox/pathA-A-models-batch04-final.md — no invariants |
| `OrderList` | projection | stored-procedure / report result shape named in _inbox/pathA-A-models-batch04-final.md — no invariants |
| `OrderRestaurant` | projection | stored-procedure / report result shape named in _inbox/pathA-A-models-batch04-final.md — no invariants |
| `PromoCodeReportResponse` | keyless-view | registered `.HasNoKey().ToView(null)` in Shared/TalabatkData/Talabatk_Context/TalabatkContext.cs:97-121 — a query shape, not a table |
| `PromoOrdersReportResponse` | keyless-view | registered `.HasNoKey().ToView(null)` in Shared/TalabatkData/Talabatk_Context/TalabatkContext.cs:97-121 — a query shape, not a table |
| `ReadyOrder` | projection | stored-procedure / report result shape named in _inbox/pathA-A-models-batch04-final.md — no invariants |
| `ReadyToPickOrdersForDeliveryMenStoredProcure` | keyless-view | registered `.HasNoKey().ToView(null)` in Shared/TalabatkData/Talabatk_Context/TalabatkContext.cs:97-121 — a query shape, not a table |
| `RecommendationEventType` | enum-only | file declares 1 enum(s) and no class; enum values are documented with the entity that uses them |
| `Request` | projection | stored-procedure / report result shape named in _inbox/pathA-A-models-batch04-final.md — no invariants |
| `RestaurantActiveForSearch` | projection | stored-procedure / report result shape named in _inbox/pathA-A-models-batch04-final.md — no invariants |
| `RestaurantPayment` | projection | stored-procedure / report result shape named in _inbox/pathA-A-models-batch04-final.md — no invariants |
| `RestaurantPaymentBalance` | projection | stored-procedure / report result shape named in _inbox/pathA-A-models-batch04-final.md — no invariants |
| `ResturantList` | projection | stored-procedure / report result shape named in _inbox/pathA-A-models-batch04-final.md — no invariants |
| `TieredDiscountTierPoco` | dto | input/output DTO under a POCOs folder — carries no invariants of its own |
| `TieredDiscountTypeEnum` | enum-only | file declares 1 enum(s) and no class; enum values are documented with the entity that uses them |
| `UpSellingCartItems` | keyless-view | registered `.HasNoKey().ToView(null)` in Shared/TalabatkData/Talabatk_Context/TalabatkContext.cs:97-121 — a query shape, not a table |

<!-- END generated: entity registry -->
