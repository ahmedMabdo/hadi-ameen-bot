---
id: 8orders/admin/admin-back-office/knowledge-graph
note_type: knowledge-graph
context: Admin
feature: Admin Back-Office
sources:
  - path: AdminUi/ClientApp/src/app/announcement/create-announcement/create-announcement.component.ts
    sha1: 7d9e4ca1919d
  - path: AdminUi/Controllers/NotificationsController/NotificationsController.cs
    sha1: 842bbcbc70c9
  - path: AdminUi/Controllers/Order/OrderController.cs
    sha1: 934f4250495d
  - path: AdminUi/Controllers/RestaurantController/RestaurantController.cs
    sha1: f2ffa50b40de
  - path: Shared/TalabatkApplication/Commands/AddScheduledNotificationCommand/AddScheduledNotificationCommand.cs
    sha1: aaea42a1b782
  - path: Shared/TalabatkApplication/Commands/AddSliderHomeCommand/AddSliderHomeCommand.cs
    sha1: 9c61c6b7b978
  - path: Shared/TalabatkApplication/Commands/AddSliderHomeCommand/AddSliderHomeCommandValidator.cs
    sha1: 724b9626c030
  - path: Shared/TalabatkApplication/Commands/EditAdCommand/EditAdCommand.cs
    sha1: 862f1a63e44d
  - path: Shared/TalabatkApplication/Commands/EditRestaurantCommand/EditRestaurantCommand.cs
    sha1: 6e197e03cafe
  - path: Shared/TalabatkApplication/Commands/EditeSliderHomeCommand/EditSliderHomeCommand.cs
    sha1: 485b446cf5b9
  - path: Shared/TalabatkApplication/Commands/MerchantsVideosCommands/AddMerchantVideoCommand.cs
    sha1: bd5da593e698
  - path: Shared/TalabatkApplication/Commands/MerchantsVideosCommands/DeleteMerchantVedioCommand.cs
    sha1: 3f04b5f16ddb
  - path: Shared/TalabatkApplication/Commands/ReserveAdCommand/ReserveAdCommand.cs
    sha1: 1e872a5e9227
  - path: Shared/TalabatkApplication/Commands/SaveAppDesignImagesCommand/SaveAppDesignImagesCommand.cs
    sha1: 4f5d27829ced
  - path: Shared/TalabatkApplication/Commands/SaveEditAreaCommand/SaveEditAreaCommand.cs
    sha1: 29f1e15c161c
  - path: Shared/TalabatkApplication/Commands/SaveEditCityCommand/SaveEditCityCommand.cs
    sha1: 51c821495960
  - path: Shared/TalabatkApplication/Commands/SaveEditFoodTypeCommand/SaveEditFoodTypeCommand.cs
    sha1: 3906bc95fdc5
  - path: Shared/TalabatkLogic/TalabatkModels/MerchantInstructionsVideos.cs
    sha1: 32885a9f87e2
last_updated: 2026-08-23
---
# Admin Back-Office — Knowledge Graph

> **Context:** Admin (`AdminUi`)
> **Last Updated:** 2026-08-03

## Controller Inventory (~85 controllers — largest of the four hosts)
The overwhelming majority are thin write-side/management wrappers around entities already documented
from the shared-layer side in this pass — confirming AdminUi's role as the back-office for nearly
everything: `CityController`/`CityRushTimeConfigurationController`/`CityBreakConfigurationController`
→ [[City.technical|City]] family; `CountryController` → [[Area-and-Country|Country]];
`CompensationController` → [[Compensation|Compensation]];
`DeliveryAnnouncementController`/`DeliveryManNotificationController` →
[[DeliveryAnnouncement-and-Notification|DeliveryAnnouncement & Notification]];
`DeliverySupplierController` → [[Delivery-Requests-and-Suppliers|DeliverySupplier]];
`FAQItemsController` → bridged Support & Chat FAQ; `JournalSubscriptionController` →
[[Mart-and-Reference-Entities|JournalSubuscriptions]]; `MartCategoryController`/
`SpecialMartCategoryController` → [[Mart-and-Reference-Entities|MartMainCategory]];
`PaymentMethodController` → [[PaymentMethod|PaymentMethod]]; `PromoCodeController`/
`VoucherController` → already-documented Discounts & Coupons; `RestaurantZoneController`/
`DeliveryZoneController` → [[DeliveryZone|DeliveryZone]]; `StoreTypeController`/
`StoreTypesController` → [[StoreTypes.technical|StoreTypes]]; `TieredDiscountController`
→ already-documented Tiered Discount; `AudianceController` → [[Audiance|Audiance]];
`ConfigurationController` → [[Configuration.technical|Configuration]];
`DeliveryBounsController` → [[DeliveryBouns.technical|DeliveryBouns]];
`RoboCallController` → [[Merchant-Accounting-and-Order-Cost|RoboCall]];
`ComplaintsController` → [[OrderComplaint|OrderComplaint]];
`CustomerAdminChatController`/`DeliveryManChatController`/`ChatHistoryController`/`ChatDashboardController`/
`ChatReportsController`/`ChatRateController`/`ChatSettingsController` → bridged chat system.

## Confirmed finding
- **`RestaurantController.SaveEditRestaurant`** (`AdminUi/Controllers/RestaurantController/RestaurantController.cs:1046`)
  dispatches `EditRestaurantCommand`, which calls `Restaurant.UpdateRestaurant(...)`
  (`EditRestaurantCommand.cs:295`) — confirms that full restaurant profile editing **is** reachable
  from `AdminUi` (the route name is `SaveEditRestaurant`, not literally "UpdateRestaurant" as an
  earlier informal pass assumed — the underlying claim holds, the exact route name was off).
  `RestaurantController.cs` also has narrower, separate routes for specific slices
  (`UpdateRestaurantOffer`, `UpdateRestaurantsWorkingHours`) rather than one single edit endpoint.

## Not individually inventoried (light per this pass's time budget)
`OrderController` (AdminUi's own order-management view — distinct from `TalabatkAPIs`'
customer-facing one and `TalabatkDelivery`'s delivery-man one), `MerchantController`,
`DeliverymanWalletController`, `UserController`/`PermissionController` (back-office role/permission
management), `DynamicDashboardController`, `ElasticSerachController`, `ErpController`/
`ErpIntegrationTrackingController`, `AiThirdPartyController`, `ScheduledNotificationController`,
`WorkUsDeliveryController`/`WorkUsRestaurantController`, `AutoCompensationSettingsController`,
`WebhookController`, `InAppMessagingController`, `CustomerNotificationsController`,
`NotificationsController`, `DeliveryInstructionsController`, report/export controllers.

## Related
- [[City.technical|City]], [[Configuration.technical|Configuration]] — the two most centrally-managed config entities

## Phase 4 gap-fill (2026-08-03)
- **`OrderController`** (`AdminUi/Controllers/Order/OrderController.cs`, 1,511 lines) — Admin's own
  full order-management surface, **53 routes** route-inventoried (not handler-read in depth given
  scale): delivery-request approve/reject/assign/swap, cost-holder management (ties to
  [[OrderComplaint\|OrderComplaint]]'s `OrderCostHolder`
  link, already documented), refunds, Fawry/accounting-entry exports, order comments/timeline,
  merchant-payment batches, "round" (delivery-man rotation) management. This is the single largest
  undocumented-in-depth surface remaining — flagged for a dedicated future pass rather than rushed.
- **`MerchantController`**, **`AutoCompensationSettingsController`**, **`DeliverymanWalletController`**
  — all thin CRUD/MediatR wrappers, no embedded logic, no new findings. `AutoCompensationSettingsController`
  confirms the `AutoCompensationReason` aggregate (mentioned by an earlier, unverified pass as a
  "properly 3-level nested aggregate" — `AutoCompensationReason → Question → QuestionOption`) is real
  and reachable via `api/AutoCompensationSettings/reasons` — the aggregate itself not opened in this
  pass.

## Phase 4 gap-fill, continued (2026-08-03)
Read 7 more controllers in full — all thin, no new bugs:
- **`UserController`** — admin's own profile (`GetMyProfile`/`UpdateMyProfile`), chat-module visibility
  flags per admin user.
- **`PermissionController`** — role/permission CRUD, `AllUserPermissions` is `[AllowAnonymous]` but
  falls back to the caller's own `info.UserId` if a session exists (`:107-109`) — only truly anonymous
  if called with no session and an explicit `userId` query param; not confirmed whether that's an
  intentional public lookup or an oversight.
- **`ScheduledNotificationController`** — CRUD for `ScheduledNotification` (already noted as light).
  `AddScheduledNotificationCommand.cs` (Application layer) builds the recurrence rule
  (weekly/monthly/yearly, via `SetWeeklyRecurrence`/`setMonthlyRecurrence`/`SetYearlyRecurrence`) and
  parses `FilterText` into one or more `CustomerNotificationGroupType` targets
  (`ScheduledNotificationHelper.ExtractEnumValues`); an empty `FilterText` is rejected up front as a
  required field. Optional banner image upload via `IUploadImage`.
- **`SliderHome`** (home-screen banner/slider entity, `Shared/TalabatkLogic/TalabatkModel/SliderHome.cs`
  — no dedicated entity note yet, findings recorded here from the Application layer side).
  `AddSliderHomeCommand.cs` builds a slider with Arabic/English images, optional time window
  (`HasTime`/`StartTime`/`EndTime`), city/merchant scoping, `Screen`, and `SpecialMartCategory`.
  **Confirmed bug (save-order):** the `SliderHome` row (with its `ImageBank` records) is saved via
  `SaveChangesAsyncWithResult()` **before** the actual image bytes are uploaded
  (`AddSliderHomeCommand.cs:105-127`); if `_uploadImage.Upload(...)` fails afterward, the handler
  returns a failure but the DB row already committed — an orphaned `SliderHome`/`ImageBank` record
  referencing image files that were never actually written. **Confirmed bug (validator):**
  `AddSliderHomeCommandValidator.cs:16` checks `command.NavigationTypeId>0` twice and
  `!string.IsNullOrEmpty(command.NavigationTypeName)` twice (copy-paste duplication) instead of also
  checking `NavigationType`/`NavigationName` — those two fields are never actually validated.
- **`Ads`** (home-screen ad entity, no dedicated entity note yet). **⚠️ Confirmed bug,
  `EditAdCommand`:** the two image-upload calls at the end of the handler are never `await`ed —
  `var uplaodArabicImageResult = UpladAdImage(...)` and the English equivalent are fire-and-forget
  `Task<bool>` calls whose result is assigned to a variable but never awaited or checked. The method
  returns `Result.Success()` immediately, before the uploads even run to completion — worse than the
  save-before-upload pattern above (#54/#57/`EditMenuCategoryCommand`), since here there's no
  guarantee the upload happens at all before the request completes, and any exception inside
  `UpladAdImage` is unobserved.
  **Source:** `EditAdCommand.cs:89-92`.
- **`ReserveAdCommand` (now opened, Phase 8) — 3 confirmed bugs:** reserves an ad card for a
  restaurant over a date range. **(1)** Both `DateTime.TryParseExact` calls for `StartDate`/`EndDate`
  ignore their `bool` return — a malformed date silently becomes `DateTime.MinValue`, and the very
  next line's `end.AddDays(-1)` then throws `ArgumentOutOfRangeException` when `EndDate` fails to
  parse. **(2)** `CreateImageInstance`'s format-validation branch calls
  `Result.Failure<ImageBank>(...)` but never `return`s it (missing `return` keyword) — the check is
  dead code, so invalid image formats are silently accepted. **(3)** the reservation row is saved
  before the Arabic/English images are uploaded, and both upload results are awaited but never
  checked — a further instance of the save-before-upload pattern, compounded by ignored upload
  results. **Source:** `ReserveAdCommand.cs:50-51` (bug 1), `:136-139` (bug 2), `:119-128` (bug 3).
- **Same `SliderHome`, sibling `EditSliderHomeCommand` (8th instance of the save-before-upload
  pattern, plus its own extra gap):** saves at `:89` before uploading at `:95-110` (same shape as
  #54/#57/#75/#77), **and** the upload results (`saveImage`/`saveImageEN`) are computed but never
  checked — unlike the sibling `AddSliderHomeCommand`, which does check them — before unconditionally
  returning `Result.Success("Saved")` at `:113`.
  **Source:** `EditSliderHomeCommand.cs:89-113`.
- **`MerchantInstructionsVideos`** (singleton config row — a single set of 4 instructional video links
  shown to merchants, `Shared/TalabatkLogic/TalabatkModels/MerchantInstructionsVideos.cs`) —
  **confirmed bug (copy-paste argument swap) in `AddMerchantVideoCommand`:** on first-ever save (no
  existing row), `MerchantInstructionsVideos.Instance(...)` is called with
  `request.StoresAppVideoArabic` in the `storesWebVideoArabic` slot *and* the `storesAppVideoArabic`
  slot — `request.StoresWebVideoArabic` is never passed in at all, so the admin-entered "Web Video
  Arabic" link is silently discarded and replaced with the "App Video Arabic" link the first time this
  is configured. The sibling `Update(...)` call (used once a row already exists) passes all 4 fields
  correctly, so the bug only bites on initial creation.
  **Source:** `AddMerchantVideoCommand.cs:37-38` (bug), contrast `:44` (`Update`, correct) and
  `MerchantInstructionsVideos.cs:19-24` (`Instance`'s real parameter order).
  Sibling `DeleteMerchantVedioCommand.cs` is an empty stub class (not even an `IRequest`) — delete was
  never actually implemented, not reachable, not a runtime bug.
- **`SaveEditAreaCommand`/`SaveEditCityCommand`/`SaveEditFoodTypeCommand` (now opened, Phase 8) —
  confirmed bugs, shared across all 3:** each does
  `command.Descriptions.FirstOrDefault(x => x.LanguageId == (int)Language.Arabic).XxxName` with no
  null-check on the `FirstOrDefault` result — a caller that omits the Arabic description throws.
  `SaveEditAreaCommand`/`SaveEditCityCommand` wrap the whole handler in a try/catch, so this
  degrades to a confusing raw-exception `Result.Failure` rather than a crash; `SaveEditFoodTypeCommand`
  has **no** wrapping try/catch, so there it's genuinely unhandled.
  **Additionally, 2 more confirmed instances of the save-before-upload pattern** (see `SliderHome`
  above, `_conflicts.md` #54): `SaveAppDesignImagesCommand` saves the splash-screen metadata before
  uploading the actual image, with the upload's `bool` result awaited but never checked;
  `SaveEditCityCommand` does the identical thing for the city image. `SaveEditFoodTypeCommand` also
  saves before uploading its image/icon, but at least checks both upload results before returning.
  **Source:** `SaveEditAreaCommand.cs:88-89`, `SaveEditCityCommand.cs:167` (Arabic-description bug),
  `:219-232` (save-before-upload); `SaveEditFoodTypeCommand.cs:82` (Arabic-description bug);
  `SaveAppDesignImagesCommand.cs:61-82` (save-before-upload).
- **`WebhookController`** — webhook CRUD **and** `ApiKey` creation/deletion co-located in the same
  controller (`AddApiKey`/`DeleteApiKey`/`GetAllApikeys` alongside `AddWebhook`/etc.) — an odd
  co-location (ApiKey isn't conceptually a webhook) but not a bug.
- **`DynamicDashboardController`** — a DevExpress `DashboardController` base-class passthrough, zero
  custom code.
- **`ErpController`** — accounting/ERP integration (GL accounts, treasuries, banks, merchant/delivery-man
  cash payments with PDF invoice generation) — thin wrapper delegating to `IGlApiServices`/
  `ICashControllApiServices`, no embedded business rules.
- **`AiThirdPartyController`** — a previously-undocumented integration: an API-key-authenticated
  webhook (`ReviewCommentCallBack`) letting an external AI service publish/unpublish a
  [[RestaurantReview\|RestaurantReview]] comment,
  attributed to `"System"`. Confirms AI-assisted review moderation exists in this codebase.

## RestaurantController (AdminUi's own, 1,424 lines, 47 routes) — route-inventoried
The true home of full restaurant management: profile edit (`SaveEditRestaurant`, already confirmed),
menu/offer management (`AddNewOffer`/`DeleteOffer`/`UpdateRestaurantOffer`/`ExclusiveOffers` — ties to
already-documented [[Offers.technical\|Offers]]),
brand/mart-category assignment, capacity hours (ties to already-documented `MerchantCapacityHours`),
profit application (`ApplyProfit`), and — confirmed — **`PublishrestaurantReview`/`UnPublishrestaurantReview`
dispatch the exact same `PublishRestaurantReviewCommand`/`UnPublishRestaurantReviewCommand` as
`AiThirdPartyController`'s AI-driven callback** — human admin action and AI-driven callback are two
entry points into the same moderation commands, both ultimately calling
[[RestaurantReview\|RestaurantReview]]'s
`SetReviewAsPublished`/`SetReviewAsUnPublished` (already documented). Not read handler-by-handler
beyond these confirmations.

## Open Questions
- [ ] `OrderController`'s 53 routes and most of `RestaurantController`'s 47 routes need handler-level
  depth in a future pass — this pass confirmed route lists and ties to already-documented entities,
  not full citations for every route.
- [ ] Whether `PermissionController.AllUserPermissions`'s anonymous-with-session-fallback behavior is
  intentional.
- [ ] `ReportsController` (1,335 lines) remains unopened — the next-highest-value target in this host.

## CustomerController + ConfigurationController (Phase 4b, 2026-08-03)
- **`CustomerController`** (~30 routes) — Admin's customer-management surface. Confirmed
  `MangeCustomerActivation` route → `MangeCustomerActivationFromAdminCommand` →
  [[Customer.technical\|Customer.MangeCustomerActivation]] — this
  **resolves** that entity's previously-open question about the two activation paths (see
  `Customer.technical.md` Rule 8, now marked resolved). Also confirmed `ManageCustomerCOD`/
  `LiftTheBanFromCustomer`/`GetBannedCustomers` as the admin-facing management surface for
  [[BlockedUsersFromCOD\|BlockedUsersFromCOD]].
- **`ConfigurationController`** — confirms the controller-level split matches the entity-level
  finding exactly: `GetDeliveryConfiguration`/`UpdateDeliveryConfigurationCommand` (validated, per
  `Configuration.technical.md` Rule 1) is a separate endpoint from `GetOperationConfiguration`/
  `GetAccountingConfiguration` (unvalidated) — no additional controller-level validation compensates
  for the entity-level gap. No new bug, but confirms `_conflicts.md` #17 is real end-to-end, not just
  a theoretical entity-level concern.
- [ ] `AutoCompensationReason`'s own aggregate file (3-level nested, per an earlier unverified claim)
  not opened — confirm the nesting and its business rules directly rather than trusting the informal
  description.
- [x] ~~The remaining ~80 Admin controllers were not individually re-verified~~ — **Resolved
  2026-08-03: all 84 controllers in `AdminUi/Controllers/` have now been literally read.** See the
  Phase 4 completion section below for the remaining 69 (including `ReportsController`, 1,335 lines).
- [ ] `AdminUi`'s own copy of `IdentityProvider.cs` (the 4th of the repo-wide duplicated JWT
  validators) — path not re-confirmed in this pass, carried over from `_system/_conflicts.md` #3.
- [ ] The cross-context notification receiver (`OperationHub`/`AdminHub`) mentioned in
  `references/repo-map.md` as `api/IdentityListener/*` was not found under that exact name in this
  pass — either it's named differently now or lives in a file this pass didn't check; flagged for
  correction rather than left silently asserted.

## Phase 4 complete (2026-08-03) — all 84 AdminUi controllers now literally read

### 🔴 Confirmed, high severity: `NotificationsController` stacks `[Authorize]` with `[AllowAnonymous]` — the latter wins, so the whole controller is silently unauthenticated
- **Source:** `Controllers/NotificationsController/NotificationsController.cs:14-20` — both
  `[Authorize]` and `[AllowAnonymous]` are present on the class. ASP.NET Core's documented behavior is
  that `[AllowAnonymous]` always overrides any `[Authorize]` in the same scope, regardless of order —
  so despite the `[Authorize]` attribute being visibly present (and looking like protection to anyone
  reading the class header), **every route on this controller is actually open to unauthenticated
  callers**: `NewOrderReceived`, `OrderExpedited`, `NewTimeOutRequest`, `AutoBusyResturants`,
  `ReassignOrderToAdmin`, `TakeOrderAndAssigendToAnother`, `UpdateNewAdminOrderStatus`,
  `NewRequestReceived`, `OrderReassigned`, `DeliveryActivationChange` — all SignalR-broadcast triggers
  to the admin operation dashboard (route `api/RestaurantNotification`, a confusingly-reused name
  distinct from the Restaurant Portal controller of the same route in `_conflicts.md` #41).
- **Worse than a simple missing-`[Authorize]` gap** (like #41): here the code actively signals "this is
  protected" while it isn't, which is a more dangerous false sense of security for anyone reviewing
  authorization by grepping for `[Authorize]`.

### 🔴 Confirmed: two more fully-anonymous controllers with real write/financial operations
- **`JournalSubscriptionController`** (`Controllers/JournalSubscriptionController/`) — `[AllowAnonymous]`
  at the controller level, covering full CRUD (`CreateJournalSub`/`Update`/`Delete`/`Serach`/`Details`/
  `SubAccountId`) on **accounting journal subscriptions** — a financial/accounting entity — with zero
  authentication required for any operation, including deletion.
- **`DeliveryMenController.DailyRefundableDeposit`** (top-level, `Controllers/DeliveryMenController.cs:198`)
  — `[AllowAnonymous]` on a POST that triggers `DailyInsuranceDeductionCommand`, a financial
  insurance-deposit deduction job across delivery men, with no auth check.
- **`ElasticSerachController`** (`Controllers/ElasticSerach/`) — `[AllowAnonymous]` at the controller
  level, exposing `CreateIndecies` (Elasticsearch index (re)creation) with no auth. **The auth gap is
  moot for this specific route: the command it dispatches, `CreateElasticSerachIndiciesCommand`, has
  its entire handler body commented out** (`IndexAllRestaurant`/`IndexAllItems` calls both disabled)
  and unconditionally `return Result.Success()` — the anonymous-access route triggers a no-op that
  reports success. Second confirmed instance this pass of a fully-commented-out handler that still
  reports success (see `_conflicts.md` #64, `ChangeCustomerCartAddressCommand`) — worth treating as a
  pattern to search for elsewhere, not two isolated one-offs.
- Combined with the already-documented `RestaurantNotificationController` gap (#41) and the
  `CityRushTimeConfigurationController.CheckRedisValues` anonymous diagnostic endpoint, this makes
  **5 distinct unauthenticated-write findings** across the two hosts audited so far in Phase 3/4 —
  worth a dedicated security pass rather than treating each as isolated.

### Confirmed: `WalletTransactionRechargeReasonController.GetById` silently ignores its own route parameter
- **Source:** `AdminUi/Controllers/WalletTransactionRechargeReasonController/WalletTransactionRechargeReasonController.cs:46-60` — the route is
  `[HttpGet("{id}")]` but the action method `GetById()` takes **no `id` parameter at all** — the bound
  route value is discarded, and `GetWalletTransactionRechargeReasonByIdQuery()` is sent with its `Id`
  at its default/unset value regardless of what `{id}` was requested in the URL. Every call to this
  endpoint (`GET /api/WalletTransactionRechargeReason/{anyId}`) returns the same result.

### Confirmed: 5th instance of the `features`/`GetFeatureFlagQuery` duplicate controller pattern
- `Controllers/FeatureMangamentController/FeatureMangamentController.cs` in **AdminUi** is byte-for-byte
  the same thin `features?featureName=X` → `GetFeatureFlagQuery` pattern already found in `Talabatk.IDS`,
  `TalabatkRestaurants`, and `TalabatkDelivery` — now confirmed copy-pasted across **4 of the 4 hosts** —
  see `_system/_conflicts.md` #39 (updated).

### Confirmed: `ReportsController` (1,335 lines, ~25 report routes) fully read
Admin's central reporting surface — merchant financial reports (`MerchantDailyReport`,
`MerchantTotalReportForAdmin`), delivery/driver performance, complaints, Fawry transactions, loyalty
points, wallet history, item-turnover/replacement analytics. Two notable internals:
- **`MerchantDailyReport`** inlines a large hand-written LINQ projection computing gross/discount/VAT/
  net figures directly in the controller (`:186-421`), while the near-identical
  **`MerchantTotalReportForAdmin`** (`:422-501`) delegates the same conceptual computation to a context
  extension method (`context.GetMerchantTotalReportAsync`) that additionally breaks out
  Offer/Tiered/Voucher contribution sub-totals the inline version doesn't compute at all — **the same
  "merchant financial totals" calculation exists in two different forms with different field
  coverage**, consistent with the repo-wide "same rule computed more than once" pattern already tracked
  (`_conflicts.md` #8/#10/#18/#22/#23/#25).
- All other routes are thin MediatR wrappers with the actual business logic in query handlers not
  opened in this pass (consistent with this pass's controller-only depth budget).

### Remaining 68 controllers (all thin, no other new bugs found)
`AdController` (**its Application-layer handler has a confirmed bug — see below, not actually
bug-free**), `AdCardsController`, `AnnouncementController`, `BrandController`, `CityController`,
`CityRushTimeConfigurationController`, `CitySuggestionsController`, `CompensationController`,
`ContactUsController`, `CookingTimeCategoryController`, `CountryController`,
`CustomReportDesignerController` (DevExpress passthrough), `DeliveryAnnouncementController`,
`DeliveryManNotificationController`, `DeliverySupplierController`, `FAQItemsController`,
`FeaturesManagementController`, `FoodTypeController`, `FoodTypesController`,
`JournalSubscriptionController` (see anonymous-access finding above), `LangaugeController`,
`MartCategoryController`, `NonDeliveryReasonsController`, `PaymentMethodController`,
`PrivacyPoliciesController`, `PromoCodeController`, `ReportController` (top-level, DevExpress
passthrough), `RestaurantBusyController`, `RestaurantReport/ReportListController`,
`RestaurantZoneController`, `StoreTypeController`, `StoreTypesController` (Application-layer handler
behind these, `AddstoreTypeCommand`, has the same save-before-upload ordering bug as `SliderHome`
below — see Phase 8 finding), `TawkToController` (admin
chat-notification relay — routes tawk.to webhook events to online operation-role users via
`OperationHub`, with an offline-fallback broadcast to all operation users if the target is offline or
has no active connection), `TermsAndConditionsController`, `UnbanReasonsController`,
`UserShiftController` (Application-layer `AddUserShiftCommand` has no null-check on the looked-up
`User` before calling `UpdateAvilabilaty` — an invalid `UserId` throws `NullReferenceException`
instead of a graceful failure, see `_conflicts.md`), `VoucherController`,
`WalletTransactionRechargeReasonController` (see bug
above), `WorkUsDeliveryController`, `ChatSettingsController`, `CityBreakConfigurationController`,
`DeliveryBounsController`, `RejectedReasonController`, `Slider` (home-screen slider CRUD, unusually
named class with no `Controller` suffix — **its Application-layer handler has 2 confirmed bugs, see
`SliderHome` finding below, not actually bug-free**), `ChatDashboardController`, `ChatRateController`,
`FeatureMangamentController` (see duplicate finding above), `AreaController`,
`CustomerNotificationsController`, `DeliveryZoneController`, `HealthController`,
`DeliveryInstructionsController`, `InAppMessagingController`, `AudianceController` (customer-segment
targeting with a DevExtreme dynamic filter-field builder and background-job-triggered rebuild on
create/update), `ChatReportsController`, `ComplaintsController` (only Admin controller with no
`[Authorize]` attribute at all, and no `[AllowAnonymous]` either — relies entirely on any global auth
filter configured at the app level; not confirmed whether one exists), `ItemController`,
`RoboCallController` (webhook receiver for outbound robo-call results, logs and dispatches to a
command, no auth attribute — likely relies on the calling service's own security, not confirmed),
`WorkUsRestaurantController`, `CustomerAdminChatController`, `DeliveryManChatController` (both mirror
the delivery-side chat pattern already documented, with `[AllowAnonymous]` on their
`NotifyAdminNewMessage`/`NotifyChatEnded`/`NotifyNewChat`/`NotifyChatUnassigned` internal-relay
endpoints — plausibly server-to-server calls from a background service rather than a public gap, not
confirmed), `ChatHistoryController`, `ErpIntegrationTrackingController`, `DeliveryMenController`
(top-level, ~20 routes — delivery-man lookups, delivery-asset CRUD; see `[AllowAnonymous]` finding
above), `SpecialMartCategoryController`.

**Phase 4 is now complete: all 84 controllers in `AdminUi/Controllers/` have been read.**

## Phase 5 — Frontend targeted conflict pass (2026-08-03)
Per the plan's explicit scope (974 `.ts` files across two Angular apps is not read exhaustively —
only the areas already flagged as having a real backend rule to compare against). Read the `.ts`
component logic (not templates/styles/specs) for: Tiered Discount forms (already covered by
`_conflicts.md` #1, re-confirmed unchanged), City/Configuration forms, delivery-zone forms, and
announcement forms.

### 🔴 Confirmed bug: `CreateAnnouncementComponent` self-assigns `isShortCut`, so it's never actually set from the form
- **Source:** `AdminUi/ClientApp/src/app/announcement/create-announcement/create-announcement.component.ts:181`:
  ```
  command.isShortCut = command.isShortCut;
  ```
  A freshly-constructed `command` has `isShortCut` at its default (`undefined`) at this point in the
  method — assigning the field to itself is a no-op, so whatever the admin picks in the "8Orders vs.
  ShortCut" target-app selector never reaches `isShortCut` on the outgoing `AddAnnouncementCommand`
  (only the separate `applicationName` string field is set correctly, a few lines above). Same
  self-assignment shape as the already-documented backend bug in `OfferItem.UpdateOfeerItem`
  (`_conflicts.md` #21) — this is the first confirmed instance of that pattern on the frontend side.
- Not confirmed whether `isShortCut` is actually read by the backend `AddAnnouncementCommand` handler
  (not opened in this pass) or is dead/redundant given `applicationName` already carries the same
  distinction — but as written, the assignment itself is definitely a no-op.

### Confirmed: Configuration forms mirror the backend's validation asymmetry end-to-end (extends `_conflicts.md` #17)
- **`DeliveryConfigurationComponent`** — every numeric field has `Validators.required` plus a
  `Validators.min(0)` (and `externalDeliveryProfitPrecentage` additionally has `Validators.max(100)`)
  — matches the backend's one validated path, `UpdateDeliveryConfigurationCommand`
  (`Configuration.technical.md` Rule 1).
- **`OperationConfigurationComponent`** — every field has `Validators.required` but **not one** has a
  `min`/`max`/range validator, even for fields that are obviously non-negative-only in intent
  (`compensationPercentage`, `compensationLimit`, `deliveryManArrivalDistance`,
  `customerDeliveryNotifyDistance`, `customerDeliveryNotifyTime`,
  `restaurantAutoConfirmTimeInSeconds`) — an admin can type a negative value into any of these and
  both the Angular form and the backend (`UpdateOperationConfiguration`, unvalidated per `_conflicts.md`
  #17) will accept it.
- **`AccountingConfigurationComponent`** — every one of its ~22 account-ID/tolerance fields is a bare
  `FormControl(0)` with **zero validators of any kind**, not even `required` — the least-guarded form
  found in this pass, matching the backend's `UpdateAccountingConfiguration` (also unvalidated per
  `_conflicts.md` #17).
- **Why this matters beyond the already-known entity-level gap:** it confirms the gap isn't
  compensated for anywhere in the stack — not at the Angular form layer, not at the controller layer
  (confirmed earlier in Phase 4), not at the domain layer. Only `DeliveryConfiguration`'s three layers
  all agree; the other three configuration categories have no guard rail at any layer.

### Confirmed: delivery-zone frontend papers over (but doesn't fix) the backend's create/update asymmetry
- `_conflicts.md` #13 documents that backend `AddDeliveryZone` (create) has zero validation while
  `UpdateDeliveryZone` requires non-blank English/Arabic names. Both
  `AddDeliveryZoneComponent` and `EditDeliveryZoneComponent`'s Angular forms independently apply
  `Validators.required` to `arcName`/`engName`/`cityID` — so through the normal admin UI, a
  zone can't actually be created blank, masking the backend gap for UI-originated calls. A direct API
  call bypassing the Angular form would still hit the unguarded `AddDeliveryZone` path exactly as
  documented in #13.

### Confirmed: menu-item-price forms (Restaurant Portal) mirror the backend's reversed create/update validation asymmetry (extends `_conflicts.md` #24)
- `_conflicts.md` #24 documents that backend `MenuItemPrice.Instance` (create) has zero validation
  while `Update` rejects a blank reference name — the reverse of the usual "create validates, update
  doesn't" shape found elsewhere.
- **`AddItemPriceComponent`** (`TalabatkRestaurants/ClientApp/src/app/categories/add-item-price/add-item-price.component.ts:77-87`)
  — its reactive form has **no control at all** for `referencePriceName`; `buildMenuPriceDTO` (`:182`)
  reads `formValues.referencePriceName` from a field the form never registers, so it's always
  `undefined` on create regardless of user input.
- **`EditItemPriceComponent`** (`TalabatkRestaurants/ClientApp/src/app/categories/edit-item-price/edit-item-price.component.ts:239-242`) — has
  `ItemPeiceReferenceNameControl` with `Validators.required`, enforced on every edit.
- Confirms the exact same reversed asymmetry end-to-end: creation has no meaningful reference-name
  validation (frontend doesn't even collect it), while editing requires it — matching `_conflicts.md`
  #24's backend-only finding now confirmed at the Angular layer too.

### Delivery-Announcement form (`AddDeliveryAnnouncementComponent`) — no mismatch found
Conditional-validator logic (image required only when `isAnnouncement` is true, title/description
required only when it's false) is internally consistent and has no obvious backend-mismatch
counterpart checked in this pass — flagged as clean, not exhaustively cross-checked against the
`AddDeliveryAnnouncementCommand` handler.

**Phase 5 scope note (per the plan):** this was a targeted pass over the 4 named areas, not exhaustive
coverage of the two Angular apps' 974 `.ts` files. No claim is made about the remaining frontend code.
