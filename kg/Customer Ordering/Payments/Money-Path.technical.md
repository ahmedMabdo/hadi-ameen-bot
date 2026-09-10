---
id: 8orders/customer-ordering/payments/money-path-technical
note_type: technical
context: Customer Ordering
feature: Payments
group: Money-Path
covers: [AccountingEntry, FawryCashCollectionTransaction, FawryTransaction, PayMobTransaction, PaymentMethodCountries, WalletTransactionRechargeReason]
sources:
  - path: AdminUi/Controllers/MerchantController/MerchantController.cs
    sha1: bd49e82a3347
  - path: AdminUi/Controllers/Order/OrderController.cs
    sha1: 934f4250495d
  - path: AdminUi/Helper/ERPIntegration/CashControllApiServices/CashControllApiServices.cs
    sha1: a6668ea790a5
  - path: AdminUi/Helper/ERPIntegration/GlApiServices/GlApiService.OnlinePaymentsReceivement.cs
    sha1: d2e33cfd4b3c
  - path: AdminUi/Helper/ERPIntegration/GlApiServices/GlApiService.RestaurantsAccrualsJournal.cs
    sha1: dceea39c50b9
  - path: AdminUi/Helper/ERPIntegration/GlApiServices/GlApiService.SendManualMerchantsTranasctionsJournals.cs
    sha1: 8f6d8dc01f82
  - path: AdminUi/Helper/ERPIntegration/GlApiServices/GlApiService.cs
    sha1: cf3d51af02ae
  - path: Shared/TalabatkApplication/Commands/AddMerchantTransactionCommand/AddMerchantTransactionCommand.cs
    sha1: b3bf9a51e2c9
  - path: Shared/TalabatkApplication/Commands/DeleteRestaurantCommand/DeleteRestaurantCommand.cs
    sha1: ecbfccf96502
  - path: Shared/TalabatkApplication/Commands/PayMobCallBackCommand/PayMobCallBackCommand.cs
    sha1: 32e4413e4e02
  - path: Shared/TalabatkApplication/DomainEventsHandlers/OrderEventsHandlers/MerchantCollectMoneyEventHandler.cs
    sha1: 1e28ab836489
  - path: Shared/TalabatkApplication/DomainEventsHandlers/OrderEventsHandlers/OrderDeliveredEventHandler.cs
    sha1: 57f2b31cd7dd
  - path: Shared/TalabatkLogic/DomainServices/CompanyProfitCalculator.cs
    sha1: 276f2456c72b
  - path: Shared/TalabatkLogic/Enum/PaymentMethods.cs
    sha1: 720541e222b5
  - path: Shared/TalabatkLogic/TalabatkModels/DeliverymanTransaction.cs
    sha1: ad9f630f0b02
  - path: Shared/TalabatkLogic/TalabatkModels/MerchantStatementTransaction.cs
    sha1: 950a66f2f1c5
  - path: Shared/TalabatkLogic/TalabatkModels/Order.cs
    sha1: a8504688c441
  - path: Shared/TalabatkLogic/TalabatkModels/OrderDelivery.cs
    sha1: f86d116d0efc
  - path: Shared/TalabatkLogic/TalabatkModels/OrderDetails.cs
    sha1: 188c9874b4a5
  - path: Shared/TalabatkLogic/TalabatkModels/OrderRestaurantDetails.cs
    sha1: 8ca4ea189b1e
last_updated: 2026-08-23
tags: [flow, technical]
---
# The Money Path: Customer Payment → Order Split → Merchant Statement → GL → Payout

> Bridges rather than restates: [[Merchant-Accounting-and-Order-Cost|Merchant Accounting
> and Order Cost]] (entity-level notes on `MerchantStatementTransaction`/`OrderCostHolder`),
> [[PayMob.technical|PayMob]] (online-payment capture mechanics),
> [[Fawry.technical|Fawry]] (driver→platform cash remittance rail — **not** a
> customer checkout method, see that note's Correction section),
> [[Order.technical|Order]],
> [[OrderRestaurantDetails|OrderRestaurantDetails]],
> [[OrderDetails.technical|OrderDetails]],
> [[Restaurant.technical|Restaurant]],
> [[DeliverymanTransaction.technical|DeliverymanTransaction]],
> [[Compensation|Compensation]].
> Delivery-fee *calculation* itself (how `DeliveryFees`/`DeliveryManProfit`/`CompanyProfit` on
> `OrderDelivery` are derived) is a separate, undocumented flow — not traced in this pass.

## Trigger

There is no single trigger; this is a pipeline with six independent entry points, each firing at a
different point in the order's life:

1. Checkout — customer selects a payment method, `Order`/`OrderPayments` created (cash/wallet path
   settles synchronously; online path is pending until the gateway calls back).
2. Online-payment gateway callback — `PayMobCallBackCommand` (anonymous webhook,
   `Shared/TalabatkApplication/Commands/PayMobCallBackCommand/PayMobCallBackCommand.cs:51`).
3. Driver marks restaurant pickup — `OrderRestaurantDetails.ChangeRestaurantOrderStatusToPickedUp`
   (`Shared/TalabatkLogic/TalabatkModels/OrderRestaurantDetails.cs:279`), COR restaurants only.
4. Driver marks order delivered — `OrderDeliveredEvent` → `OrderDeliveredEventHandler.Handle`
   (`Shared/TalabatkApplication/DomainEventsHandlers/OrderEventsHandlers/OrderDeliveredEventHandler.cs:47`).
5. Admin manually posts the day's accounting entries — `OrderController.AccFlexAccountingEntries`
   (`AdminUi/Controllers/Order/OrderController.cs:797-805`) → `GlApiService.SendDailyJournals`
   (`AdminUi/Helper/ERPIntegration/GlApiServices/GlApiService.cs:94`). This is a manual, admin-clicked
   action gated by `[Permission(Permissions.Sales.SalesDaily)]` (`AdminUi/Controllers/Order/OrderController.cs:801`) — **not** an
   automated nightly job in any code path traced in this pass.
6. Admin records a merchant payout/adjustment, or a cashier receives cash back from a merchant —
   `MerchantController.AddTransaction` (`AdminUi/Controllers/MerchantController/MerchantController.cs:43`)
   or `CashControllApiServices.CashReceiptPost`
   (`AdminUi/Helper/ERPIntegration/CashControllApiServices/CashControllApiServices.cs:88`).

## Step-by-step

1. **Payment method chosen at checkout.** `PaymentMethods` enum: Cash, Wallet, Online, Orange,
   OnlineWallet (`Shared/TalabatkLogic/Enum/PaymentMethods.cs:5-16`). `OrderPayments` row(s) created
   per method. Exact checkout command that creates `OrderPayments` was not opened in this pass —
   not traced in this pass; bridge to [[Order.technical|Order]].
2. **Online capture confirmed asynchronously.** `PayMobCallBackCommand.Handle`
   (`PayMobCallBackCommand.cs:51`) loads the order, verifies HMAC via
   `payMobProviderServices.VerifyHmacForPayment` (`:78-83`); on HMAC failure falls through to a live
   PayMob inquiry rather than rejecting outright (`:87-99`, deliberate — see in-file comment on the
   prior Apple Pay HMAC bypass). On success, `order.ChangeOnlinePaymentStatusForPayMob` (`:220-224`)
   marks the `OrderPayments` row Captured. Gateway-side mechanics (session creation, signature
   verification detail) are documented in [[PayMob.technical|PayMob]] — not
   restated here.
3. **Per-line-item commission computed at pricing time.**
   `OrderDetails.ApplyProfit` (`Shared/TalabatkLogic/TalabatkModels/OrderDetails.cs:525-544`): sets
   `ProfitPercentage` from `item.TA_MenuCategory.Profit` (category override) or `restaurant.Profit`
   (`:530-536`), then
   `ProfitValue = (TotalAfterDiscountAndTax - CategoryTaxValue) * (ProfitPercentage / 100)` (`:539`) —
   this is the 8orders commission on that line. `RestaurantShare()` (`:559-564`) returns
   `TotalAfterDiscountAndTax - ProfitValue`, i.e. what the restaurant keeps on that line before any
   order-level discount split. Recomputed on edit via `RecalculateTaxAndProfit` (`:578-584`).
4. **Order-level discount-contribution split.**
   `OrderRestaurantDetails.CompanyContributionValue` (`Shared/TalabatkLogic/TalabatkModels/OrderRestaurantDetails.cs:63-87`,
   computed property) apportions each of voucher/offer/tiered discounts between 8orders and the
   restaurant based on a per-stream `*ContributionPercentage` (0 → restaurant absorbs it all; 100 →
   8orders absorbs it all; in between → split). This value feeds both the merchant-ledger credit in
   step 6a and the pickup-time cash amount in step 5.
5. **[COR restaurants, cash-only orders] Driver pays merchant directly at pickup.**
   `ChangeRestaurantOrderStatusToPickedUp` (`OrderRestaurantDetails.cs:279-296`) calls
   `Order.GetMerchantPaymentAmount` (`Shared/TalabatkLogic/TalabatkModels/Order.cs:573-610`), which
   returns nonzero only if `orderRestaurant.CashOnReceived` is true (`:581-584`) **and** the order has
   no captured online leg and no wallet leg — `isOnlyCash` (`:586-603`). Amount =
   `PricewithOptionAndQuantity - TieredDiscountAmount - TotalVoucherDiscountValue` (`:609`). If > 0:
   `TotalAmountReceivedFromDelivery` is set to
   `TotalBeforeDiscount - TotalDiscountsContributionValue - CompanyContributionValue`
   (`OrderRestaurantDetails.cs:292`), `DeliverymanTransaction.AddMerchantCashPaymentTransaction` is
   called (driver ledger, `Merchant_Paid`, **credit** —
   `Shared/TalabatkLogic/TalabatkModels/DeliverymanTransaction.cs:174-197`), and
   `AddMerchantStatementCollectionEvent` fires `MerchantCollectMoneyEvent` (`:322-326`). The driver is
   fronting this cash from their own float.
6. **`MerchantCollectMoneyEvent` handled → restaurant ledger debited.**
   `MerchantCollectMoneyEventHandler.Handle`
   (`Shared/TalabatkApplication/DomainEventsHandlers/OrderEventsHandlers/MerchantCollectMoneyEventHandler.cs:24-42`)
   calls `MerchantStatementTransaction.AddMerchantCollectionTransaction` — `Merchant_Collection`,
   **debit** (`IsCredit = false`), amount `PricewithOptionAndQuantity - TieredDiscountAmount -
   TotalVoucherDiscountValue`, guarded on `restaurant.Cor && order.PricewithOptionAndQuantity > 0`
   (`Shared/TalabatkLogic/TalabatkModels/MerchantStatementTransaction.cs:141-163`). This offsets the
   restaurant's statement by the cash they already physically hold, so step 8 below doesn't double-pay
   it.
7. **Order delivered → `OrderDeliveredEventHandler.Handle`**
   (`OrderDeliveredEventHandler.cs:47-60`) does two independent things:
   - **7a. Driver ledger** (`HandleSingleDelivery`/`HandleMultiDelivery`, `:107`/`:211`) →
     `DeliverymanTransaction.AddCashOrderTransaction` (`DeliverymanTransaction.cs:87-166`): posts
     `Order_Collection` (**debit**, `orderDelivery.TotalCollectedFromCustomer` — cash the driver now
     holds and owes back, `:117-127`) and `Delivery_Profit` (**credit**,
     `orderDelivery.DeliveryManProfit` — the driver's own delivery-fee cut, `:149-159`), each guarded
     against duplicate posting (`hasAlreadyCollectionTransction`/`hasAlreadyProfitTransction`,
     checked at `OrderDeliveredEventHandler.cs:134-140`). Driver's post-transaction balance is
     recomputed as `Sum(IsCredit ? -Amount : Amount)` (`:178-182`), driving
     `UpdateRequiredPaymentAndExceededCashLimit` (`:185`).
   - **7b. Merchant ledger** (`AddMerchantStatmentTransactions`, `:64-102`): skipped entirely for
     external-delivery orders (`:71-74`). `CompanyProfitCalculator.CalculateProfit`
     (`Shared/TalabatkLogic/DomainServices/CompanyProfitCalculator.cs:9-20`) sums each restaurant's
     line-level `ProfitValue`s into `OrderRestaurantDetails.ProfitValue` (`:14-18`). Then, per
     restaurant on the order, five `MerchantStatementTransaction` rows are posted **in this literal
     order** (`OrderDeliveredEventHandler.cs:92-97`):
     1. `AddCashOrOnlineOrderTransaction` — `Order`, **credit**, `TotalBeforeDiscount -
        CompanyContributionValue` (`MerchantStatementTransaction.cs:82-100`).
     2. `Add8OrderProfitTransaction` — `Eight_Order`, **debit**, `order.ProfitValue`
        (`:166-186`) — the aggregated commission from step 3.
     3. `AddOnlinePaymentContributionTransaction` — `CON`, **debit**, `order.OnlineContributionValue`,
        no-op if null (`:188-210`) — the restaurant's share of the online-payment-gateway cost.
     4. `AddMerchantContributionTransaction` — `Merchant_CON`, **debit**, sum of
        `TieredDiscountContributionValue + OfferContributionValue + VoucherContributionValue`,
        no-op if all three are default (`:235-257`) — the restaurant's own share of the discounts.
     5. `AddCompanyContributionTransaction` — `_8Orders_CON`, **credit**, `CompanyContributionValue`,
        no-op if default (`:212-233`) — 8orders reimbursing the restaurant for the discount share
        8orders itself absorbed.
     Each call's `Result` is not checked for failure in the handler (`:91-96`) before
     `SaveChangesAsyncWithResult` (`:98`) — a failed `Instance` validation (e.g. amount ≤ 0) is silently
     dropped rather than surfaced. `IsTransactionCredit` switch: `MerchantStatementTransaction.cs:295-311`.
8. **Periodic ERP posting (admin-triggered).** `GlApiService.SendDailyJournals`
   (`AdminUi/Helper/ERPIntegration/GlApiServices/GlApiService.cs:94-160`) runs a fixed, sequential (not parallel — see the commented-out
   `Task.WhenAll` list at `:127-142` and the live sequential loop at `:157-160`) list of ~16 journal
   postings per business date, including (not exhaustive — full journal set not traced in this pass):
   - `SendRestaurantsAccrualsJournal`
     (`AdminUi/Helper/ERPIntegration/GlApiServices/GlApiService.RestaurantsAccrualsJournal.cs:16-198`):
     per restaurant, credits `restaurantAccount.LiabilitiesAccountId` with
     `TotalBeforeDiscount - ProfitValue` summed across the day's orders (`:26-28`), debits
     `accflexConfig.RestaurantOperationExpensesAccountId` for the aggregate (`:71-90`), and — gated on
     `totalRestaurantBenefits > 0` (`:51`) — adds separate online-contribution and discount-contribution
     lines. **#418(b)**: when that day's benefit for a restaurant is zero or negative, the online
     contribution for that restaurant is silently never posted by this or any other journal.
   - `SendManualMerchantsTransactionsJournals`
     (`AdminUi/Helper/ERPIntegration/GlApiServices/GlApiService.SendManualMerchantsTranasctionsJournals.cs:16-108`):
     posts the accumulated manual `MerchantStatementTransaction` rows (`Add`/`Deduction`/
     `Merchant_Payment` from step 9 below) grouped by restaurant, resolving the target account as
     `restaurantAccounts.FirstOrDefault(r => r.RestaurantId == g.Key)?.LiabilitiesAccountId ?? 0`
     (`:47`). **#418(a)**: a restaurant with no configured liabilities account is posted to
     `AccountId = 0` instead of being rejected — contrast the sibling journal above, which uses
     `.Value` on the same nullable field and throws instead.
   - `CreateOnlinePaymentReceivement`
     (`AdminUi/Helper/ERPIntegration/GlApiServices/GlApiService.OnlinePaymentsReceivement.cs:20-70`):
     books the day's total captured online amount plus wallet-refund amount as a cash receipt into the
     PayMob treasury account (`accflexConfig.PaymobSafeId`) against `CashCustomerAccountId`/
     `CustomerWalletAccountId` — this is where the online payment actually becomes "money the company
     has," on the books, separately from the per-order `MerchantStatementTransaction` credit in step 7b.
   - Also present in the same sequential run: Income Journal, Delivery Men Cash/Accruals Journals,
     Wallet And PromoCode Journal, Manual Deliverymen Transactions Journal, Compensations Journal,
     Fawry Transactions Journal, Refunded Online Payment, Rejected Orders Penality Journal, Restaurant
     Subscriptions (Ads) Journal, Delivery Men Insurance/Asset Deduction Journals, Delivery Shift Bonus
     Journal (`AdminUi/Helper/ERPIntegration/GlApiServices/GlApiService.cs:144-160` for the full ordered list) — none of these opened in this pass.
9. **Merchant payout or cash-back, recorded manually.** Two paths write directly into
   `MerchantStatementTransaction` outside the order lifecycle, both eventually swept into step 8's
   `SendManualMerchantsTransactionsJournals`:
   - **Payout/adjustment**: `AddMerchantTransactionCommand.Handle`
     (`Shared/TalabatkApplication/Commands/AddMerchantTransactionCommand/AddMerchantTransactionCommand.cs:35-58`)
     takes `MerchantId`, `Amount`, `TransactionType` (e.g. `Merchant_Payment`, **debit** — money
     actually paid out to the restaurant, typically by bank transfer executed outside this system) and
     `AccountId` straight from the admin's request body, via `MerchantController.AddTransaction`
     (`AdminUi/Controllers/MerchantController/MerchantController.cs:43-49`), gated only by the
     controller's class-level `[Authorize]` (`:16`) — no `[Permission]` attribute on this specific
     action was found in this pass.
   - **Cash received back from a merchant**: `CashControllApiServices.CashReceiptPost`
     (`AdminUi/Helper/ERPIntegration/CashControllApiServices/CashControllApiServices.cs:88-101`) →
     `_cashReceiptValidator.Validate` → `HandleMerchantReceivement` (`:275-291`) creates a
     `MerchantReceivement` row, then (not shown in the excerpt read this pass, but named identically to
     the deliveryman path) `MerchantStatementTransaction.AddMerchantReceivementTransaction` —
     `Merchant_Receivement`, **credit** (`MerchantStatementTransaction.cs:279-293`) — nets the
     restaurant's outstanding debt (e.g. from step 5's cash-on-pickup model) back toward zero.
     **#417**: `ValidateMerchantReceivement`'s signature takes only `int? restaurantAccountId` and
     never receives the posted amount, so no bounds check on `TotalCashRecieved` is possible on this
     path, unlike the sibling deliveryman cash-receipt path which is tolerance-checked.

## Data written

In trigger order for a typical cash-on-pickup COR restaurant, cash-paid order, fully delivered:

1. `OrderPayments` (checkout) — payment method + amount.
2. `OrderDetails.ProfitValue`/`ProfitPercentage` (pricing time) — per-line commission.
3. `DeliverymanTransaction` row, type `Merchant_Paid`, credit (pickup, COR only) —
   `DeliverymanTransaction.cs:174-197`.
4. `MerchantStatementTransaction` row, type `Merchant_Collection`, debit (pickup, COR only) —
   `MerchantStatementTransaction.cs:141-163`.
5. `OrderRestaurantDetails.ProfitValue` (delivery) — aggregated line commission,
   `CompanyProfitCalculator.cs:9-20`.
6. `DeliverymanTransaction` rows ×2, types `Order_Collection` (debit) and `Delivery_Profit` (credit)
   (delivery) — `DeliverymanTransaction.cs:87-166`.
7. `MerchantStatementTransaction` rows ×up to 5, types `Order` (credit), `Eight_Order` (debit), `CON`
   (debit, conditional), `Merchant_CON` (debit, conditional), `_8Orders_CON` (credit, conditional)
   (delivery) — `MerchantStatementTransaction.cs:82-257`.
8. `DeliveryMen.RequiredPayment`/`ExceededCashLimit` (delivery, recalculated from driver balance) —
   `OrderDeliveredEventHandler.cs:185-198`.
9. AccFlex ERP journal entries (admin-triggered, periodic) — restaurant liability account, expense
   account, online-payment treasury account, and whichever placeholder/actual account
   `SendManualMerchantsTransactionsJournals` resolves — `GlApiService.RestaurantsAccrualsJournal.cs`,
   `GlApiService.SendManualMerchantsTranasctionsJournals.cs`.
10. `MerchantStatementTransaction` row, type `Merchant_Payment` (debit) or `Merchant_Receivement`
    (credit) (admin-triggered, any time) — `AddMerchantTransactionCommand.cs:39-46`,
    `MerchantStatementTransaction.cs:279-293`.
11. `MerchantReceivement` row (admin-triggered cash-back only) —
    `CashControllApiServices.cs:275-283`.

## External calls

- PayMob: inbound HMAC-signed webhook (`PayMobCallBackCommand`); outbound authenticate + transaction
  inquiry when HMAC fails (`PayMobCallBackCommand.cs:90-96`). Gateway-side detail in
  [[PayMob.technical|PayMob]].
- AccFlex ERP `GLApiBaseUrl` — journal posting (`GlApiService.PostJournal`, called from every
  `Send*Journal` method in step 8).
- AccFlex ERP `CashControlApiBaseUrl` — treasury/cash-receipt posting
  (`CashControllApiServices.cs:62-64`, `:110+`), used both for the online-payment treasury receipt
  (step 8) and for merchant/deliveryman cash receipts (step 9).

## Failure modes

- **#418(a) — GL entries posted to `AccountId = 0`.** A restaurant with no configured
  `LiabilitiesAccountId` gets its manual-transaction journal silently booked to account 0 instead of
  rejected (`GlApiService.SendManualMerchantsTranasctionsJournals.cs:47`), while the sibling accruals
  journal throws on the same missing value (`GlApiService.RestaurantsAccrualsJournal.cs:56`, `.Value`
  on a nullable). Bites at step 8.
- **#418(b) — online contribution silently dropped.** When a restaurant's same-day `salesOrders`
  benefit is ≤ 0, `RestaurantsAccrualsJournal`'s online-contribution line for that restaurant is never
  posted by this or any other traced journal (`GlApiService.RestaurantsAccrualsJournal.cs:42-62`).
  Bites at step 8.
- **#417 — merchant cash receipts unvalidated.** `ValidateMerchantReceivement` cannot check the
  received amount against anything because its signature never receives it
  (`CashControllApiServices.cs`, validator referenced at step 9); the sibling deliveryman cash-receipt
  path is tolerance-checked. Bites at step 9.
- **#340 — write-once ledgers are cascade-deletable.** `Restaurant → MerchantStatementTransaction` is
  configured `Cascade`, and `DeleteRestaurantCommand.cs:63` is a real, reachable hard-delete of
  `Restaurant` that would take the restaurant's entire statement history with it — the exact ledger
  this flow spends its whole length building up. Bites at any point after step 7, for the lifetime of
  the restaurant record.
- **Unchecked `Result` failures in the per-order merchant posting loop.** None of the five
  `MerchantStatementTransaction.Add*` calls in `OrderDeliveredEventHandler.AddMerchantStatmentTransactions`
  (`:91-96`) have their `Result.IsFailure` checked before `SaveChangesAsyncWithResult` — if `Instance`'s
  validation rejects one (e.g. `amount <= 0`, `MerchantStatementTransaction.cs:44`), that leg of the
  restaurant's statement is silently missing for that order, with no error surfaced anywhere in this
  handler. Not a registered `_conflicts.md` finding — observed in this pass, not independently verified
  against a live failure case.
- **`MerchantController.AddTransaction` has no route-level `[Permission]` attribute** — only the
  controller's class-level `[Authorize]` (`MerchantController.cs:16`), so any authenticated admin
  session, not just one with an accounting-specific permission, can post an arbitrary
  `MerchantStatementTransaction` (including `Merchant_Payment`) for any restaurant. Not a registered
  finding — observed in this pass, not cross-checked against the permission scheme used elsewhere in
  Admin.

## Entities documented by this note

The five entities below have no separate note: they are the payment rails and the reference rows the
money path runs on, and splitting them out would scatter one flow across five files. Every field list
is from the class itself, so a CR touching any of them starts here.

| Entity | Type | Source | Key fields | Behaviour it owns |
|---|---|---|---|---|
| `FawryTransaction` | legacy POCO root, `Result` guards | `Shared/TalabatkLogic/TalabatkModels/FawryTransaction.cs` | `FawryTransactionId`, `DeliveryManId`, `FawryProfileId`, `MerchantRefNumber`, `FawryRefNumber`, `FawryStatus` (`FawryPaymentStatus`), `Amount`, `CreateDate`, `CaptureDate?`, `PaymentMethod` (`FawryMethod`), `Expiration`, `Signature`, `StatusCode` | One driver→platform cash remittance attempt. `Instance(...)` creates it, `UpdateTransaction`/`UpdateStatus` move it through the gateway's states, `SetSalesDaily` ties it to the day's takings. **This is a driver remittance rail, not a customer checkout method** — see the Correction section in [[Fawry.technical\|Fawry]] |
| `FawryCashCollectionTransaction` | legacy POCO root, `Result` guards | `Shared/TalabatkLogic/TalabatkModels/FawryCashCollectionTransaction.cs` | `Id`, `DeliveryManId`, `FawryProfileId`, `IsRetry`, `Amount` (string), `PaymentId`, `TransactionId`, `CustomerReferenceNo`, `PaymentDate`, `DeliveryMethod` | The cash-collection side of the same rail: what Fawry reports as actually collected from a driver. `IsRetry` marks a re-attempt, so a driver's balance must not be credited twice for one collection. Note `Amount` is a **string** here and a `decimal` on `FawryTransaction` — a conversion boundary worth checking in any reconciliation change |
| `PayMobTransaction` | child of `OrderPayments`, `Instance` factory | `Shared/TalabatkLogic/TalabatkModels/PayMobTransaction.cs` | `PayMobTransactionId`, `OrderPaymentId`, `TransactionId`, `Pending`, `Success`, `RedirectUrl`, `AmountCents`, `PayMobOrderId`, `UnixTimeStampExpiration`, `ExpirationDate`, `IsWallet`, `CustomerCardId?`, `WalletMobileNumber` | The customer's online card/wallet payment attempt. Richest behaviour of the five: `UpdatePayMobStandrdTransction`, `CaptureTransction`, `ChangeStatusOfTransction`, `SetTransctionId`, `InitiationFailure`, `MarkFailed` — i.e. the full attempt lifecycle including two distinct failure paths (failed to start vs. failed after starting). `AmountCents` means every comparison against an order total needs a ×100 conversion |
| `PaymentMethodCountries` | child (join), `Instance` factory | `Shared/TalabatkLogic/TalabatkModels/PaymentMethodCountries.cs` | `PaymentMethodId`, `CountryId` + both navigations | Which payment methods exist in which country. This is why `GetAllPaymentMethodsByAddress` takes an address rather than returning a global list — the answer is per-country |
| `WalletTransactionRechargeReason` | legacy POCO root, `Instance` factory | `Shared/TalabatkLogic/TalabatkModels/WalletTransactionRechargeReason.cs` | `Id`, `ReasonAr`, `ReasonEn`, `IsDeleted` | The reason list an admin must pick from when crediting a customer wallet by hand. `IsDeleted` is a soft delete, so historic wallet entries keep a readable reason after the reason is retired. Administered from [[Admin/Order & Customer Administration/_knowledge-graph\|Order & Customer Administration]] |
| `AccountingEntry` | legacy POCO root, **no guards at all** | `Shared/TalabatkLogic/AccountingEntry.cs` (note: the domain-layer **root**, not `TalabatkModels/`) | `AccountingEntryId`, `AccFlexAccountEntryId`, `SalesDailyId?`, `Serial`, `JournalTimeStamp` (**string**), `AccountingEntryTypeId`, `AccountingEntryTypeIdName` | The 8Orders→AccFlex General Ledger back-reference: one row per journal 8Orders has posted, holding the id AccFlex assigned it. Mapped to `TA_AccountingEntry` with `HasKey(AccountingEntryId)` (`Shared/TalabatkData/Mapping/AccountingEntryMap.cs:16`, `:17`). `Instance(...)` (`Shared/TalabatkLogic/AccountingEntry.cs:13`) assigns five fields and **validates none of them** — no `Result`, no null checks, and it does not set `SalesDailyId`, which the caller must assign afterwards. `JournalTimeStamp` is a `string`, so the posting time is unordered and unparsed at the database. **Two independent producers write this table**: the Fawry receivement journal (type `AccountingEntriesTypes.FawryReceivement`, see [[Fawry.technical\|Fawry]] Rule 7) and the ad-reservation handlers (`Shared/TalabatkApplication/DomainEventsHandlers/AdsEventsHandlers/AdReservationMadeEventHandler.cs`, `AdReservationDeletedEventHandler.cs`) — so a reconciliation that assumes payments are the only source will under-count. See `_conflicts.md` #645 |

## Open Questions

- The checkout-time creation of `OrderPayments` (which command, which validation) was not traced in
  this pass — bridge to [[Order.technical|Order]] if it covers this; if
  not, it remains a gap.
- Delivery-fee calculation itself — how `DeliveryFees`, `DeliveryManProfit`, and `CompanyProfit` on
  `OrderDelivery` are derived (`Shared/TalabatkLogic/TalabatkModels/OrderDelivery.cs:72-101`) — is
  explicitly out of scope for this flow and not traced here.
- Whether `SendDailyJournals` is ever invoked by an automated job in addition to the manual
  `AccFlexAccountingEntries` endpoint was not confirmed — only the manual admin trigger was found in
  this pass.
- The full ~16-item journal list in `AdminUi/Helper/ERPIntegration/GlApiServices/GlApiService.cs:144-160` was not exhaustively opened; only
  `SendRestaurantsAccrualsJournal`, `SendManualMerchantsTransactionsJournals`, and
  `CreateOnlinePaymentReceivement` were read. `SendIncomeJournal`, `SendDeliveryMenCashJournal`,
  `SendDeliveryMenAccrualsJournal`, `SendWalletAndPromoCodeJournal`, `SendCompensationsJournal`,
  `CreateFawryTransctionsJournal`, `CreateRefundedOnlinePayment`, `SendRejectedOrdersPenalityJournals`,
  `SendRestaruantSubscriptionsJournlas`, and the delivery-men insurance/asset/bonus journals are
  not traced in this pass.
- `HandleMerchantReceivement`'s call into `MerchantStatementTransaction.AddMerchantReceivementTransaction`
  was inferred from the method's naming symmetry with the deliveryman path and from
  `MerchantStatementTransaction.cs:279-293`'s existence, not from reading the exact call site inside
  `HandleMerchantReceivement` past line 291 — not fully confirmed in this pass.
- Whether a `MerchantReceivement`/`Merchant_Receivement` transaction is itself later included in
  `SendManualMerchantsTransactionsJournals`'s `_manualMerchantsTransactions` collection, or posted to
  the ERP by some other path entirely, was not traced.
- The exact ordering guarantee (or lack of one) between step 5 (pickup cash payment) and step 7
  (delivery-time statement lines) when a single order has multiple restaurants with mixed COR/non-COR
  configuration was not traced.
