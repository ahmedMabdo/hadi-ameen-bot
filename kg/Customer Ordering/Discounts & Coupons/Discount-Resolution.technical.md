---
id: 8orders/customer-ordering/discounts-and-coupons/discount-resolution-technical
note_type: technical
context: Customer Ordering
feature: Discounts & Coupons
group: Discount-Resolution
covers: [ExclusiveOfferItem, LoyaltyConfigAuditLog, LoyaltyPointsSrc, OfferItem, OffersDescriptions, PromoCodeArea, PromoCodeAudience, PromoCodeCity, PromoCodeCustomer]
sources:
  - path: Shared/TalabatkApplication/Commands/CreateOrderFromCartCommand/CreateOrderFromCartCommand.cs
    sha1: 26e07e2fc0b4
  - path: Shared/TalabatkLogic/TalabatkModels/Order.cs
    sha1: a8504688c441
  - path: Shared/TalabatkLogic/TalabatkModels/OrderRestaurantDetails.cs
    sha1: 8ca4ea189b1e
  - path: Shared/TalabatkLogic/TalabatkModels/PromoCodes.cs
    sha1: f8280d78440d
last_updated: 2026-08-23
tags: [flow, technical]
---
# Discount Resolution — Technical

> Bridges rather than restates the four mechanisms' own rules: [[PromoCodes.technical|PromoCodes]],
> [[Vouchers.technical|Vouchers]],
> [[TieredDiscount.technical|TieredDiscount]],
> [[Offers.technical|Offers]] (menu-item offers).
> Checkout's broader validation gauntlet (address, area coverage, price re-validation) is documented in
> [[CustomerCart.technical|CustomerCart]] Rule 9 — this note covers only
> steps 9 and 11 of that gauntlet in depth (the promo/voucher gate and `Order.CreateOrderFromCustomerCart`'s
> internal discount pipeline). Who ultimately pays for each discount (the merchant-statement/ERP side of the
> split) is documented in [[Money-Path.technical|Money-Path]] step 4 and step 7b — this note
> covers only where each contribution percentage is *set*, not where it lands on the ledger.

## Trigger

Two distinct trigger points feed the same calculation pipeline:

1. **Checkout** — `CartController.CheckOut_V1` → `CreateOrderFromCartCommand.Handle`, which reads the
   customer's cart, resolves whichever discounts apply, and calls the static factory
   `Order.CreateOrderFromCustomerCart(...)` (`Shared/TalabatkApplication/Commands/CreateOrderFromCartCommand/CreateOrderFromCartCommand.cs:427`),
   which itself calls `CalculateOrderTotalFromCart` (`Shared/TalabatkLogic/TalabatkModels/Order.cs:2125`).
2. **Order edit** (adding/removing items on an existing pending order) — a separate instance-method path
   calls `CalculateOrderTotal` (`Order.cs:4825`), a near-duplicate that runs the same three-stage discount
   pipeline (offers → tiered → voucher/promo) but skips the final `CompanyProfitCalculator.CalculateProfit`
   call (`Order.cs:5127`) — which caller(s) invoke this edit path is not traced in this pass.

Two of the four mechanisms are **selected before checkout even begins**, at add-to-cart time, and are only
*re-validated and calculated* at checkout; the other two are **selected at the checkout request itself**:

- **Offers** (menu-item level) — a cart item carries `CartItem.OfferItemId`/`OfferId` from the moment it's
  added, because the customer added a specific discounted item. Bridge to
  [[Offers.technical|Offers]] for how an offer becomes attached to
  an item; not re-derived here.
- **Tiered Discount** — `CartItem.TieredDiscountId` is set per restaurant before checkout, and carried
  through Guest→real-account cart merges via `CustomerCart.LockedTieredDiscountId`. Bridge to
  [[TieredDiscount.technical|TieredDiscount]] Rule 11 and
  [[CustomerCart.technical|CustomerCart]] Rule 8 for the selection/carry-over
  mechanics; not re-derived here.
- **PromoCode** — a `Promo` string typed by the customer, supplied on the checkout request.
- **Voucher** — a `VoucherId` chosen by the customer from their issued vouchers, supplied on the checkout
  request.

## Step-by-step

1. **PromoCode / Voucher fetch — mutual exclusivity enforced before either is even loaded.**
   `CreateOrderFromCartCommand.cs:263` reads the `Features.VoucherCampaigne` flag
   (`isVoucherCampaigneEnabled`). Then, at `:268`: if `request.PromoCode` is non-empty, the code looks up a
   `PromoCodes` row and **never inspects `request.VoucherId` at all**, even if the client also sent one
   (`:268-289`). Only in the `else` branch (`:290-318`), when no promo string was supplied, is
   `request.VoucherId` considered. This is the first of two independent enforcements of "only one of these
   two" — see step 6 for the second, defensive one inside the domain layer.
   - **Promo lookup itself forks on the same feature flag**: with the flag on, the query filters only by
     trimmed code text (`:271-276`); with it off, it additionally filters by `IsShourtCutApp` and requires
     a `PromoCodeCities` row matching the checkout's `cityId` (`:279-286`) — i.e. the **city eligibility
     gate is only enforced at the fetch level when the feature flag is off**. Observed in this pass, not a
     registered `_conflicts.md` finding.
   - **Voucher checks at fetch time** (`:292-318`): must exist and belong to `request.CustomerId` (else
     "Voucher is not valid", `:296-301`), must not be `IsUsed` (else "Voucher is used before", `:305-307`),
     and if merchant-scoped (`voucher.MerchantId.HasValue`), that restaurant must be present in the cart
     (`:310-316`).

2. **PromoCode usage-history lookup.** `promoCodeCalculationForOrderBulider.GetPromoCodeResultForCalculation`
   (`:322`) resolves `isCustomerHasAnyDeliveredOrder`, the customer's prior usage count for this code, and
   the code's total usage count — these three feed the `NewCustomerOnly` and per-customer-cap gates inside
   `PromoCodes.ValidatePromoCode` (`Shared/TalabatkLogic/TalabatkModels/PromoCodes.cs:459-518`), not
   re-derived here (see [[PromoCodes.technical|PromoCodes]] Rule 3).

3. **Offer items and active-offer restaurant set gathered.** `offerItemIdsInCart`/`offerIdsInCart` are
   pulled from the cart's items (`CreateOrderFromCartCommand.cs:349-358`), used to fetch the full
   `OfferItem` rows (`:360-366`). Separately, `restaurantIdsWithActiveOffers` queries every restaurant in
   the cart with an `Offers` row active **right now** — active flag, weekday, and date range, but **not**
   the time-of-day window (`:408-416`) — this is the same "weekday but not time-of-day" gap already
   documented as part of **#410**'s root cause (`GetAllRestaurantItemsQuery` picks an offer the same
   incomplete way when it decides whether to show a discount on the menu).

4. **Tiered discounts per restaurant gathered.** `tieredDiscountIds` are read off cart items
   (`:371-375`), and the matching `TieredDiscounts` rows are fetched **with an `IsActive` +
   `StartDate`/`EndDate` re-check right here** (`:379-390`) — i.e. even though the discount was locked in
   at add-to-cart time, a discount that expired or was deactivated between add-to-cart and checkout is
   silently dropped from `tieredDiscountsByRestaurant` rather than surfaced as an error to the customer.

5. **Mart stock check** (unrelated to discounts, listed for pipeline completeness) —
   `CheckMartQuantity(customerCart, ...)` (`:420`), a hard failure if it fails.

6. **`Order.CreateOrderFromCustomerCart` builds the `Order` and its `OrderDetails` from the cart**
   (`Order.cs:2071`, `CreateDetailsFromCartItems` — per-line prices, including any baked-in `OfferDiscount`,
   are snapshotted here), sets `LockedTieredDiscountId` from the cart (`:2100`), then calls
   `CalculateOrderTotalFromCart(promoCode, voucher, tieredDiscountsByRestaurant, ...)` (`:2125`), which runs
   the three-stage discount pipeline in this literal order (comment at `Order.cs:4928`: *"Apply tiered
   discount AFTER offers and BEFORE vouchers"*):

   **6a. Offers (item-level), applied/capped first** (`CalculateOrderTotalFromCart`, `Order.cs:5076-5084`):
   - `TotalBeforeDiscount` is the raw sum of `OrderDetails.TotalPricewithOptionAndQuantity` (`:4923`) —
     price×quantity, **never itself reduced** by any discount stream; every discount stays in its own field
     and is only netted out when `Total` is computed at the end (step 6d). `OfferDiscount` per line was
     already set when the item was added to the cart.
   - `ApplyOfferMaximumDiscountCaps(offersitem)` (`:4920` → `Order.cs:2177-2310`) re-checks, per restaurant
     and per offer, the offer's `MinimumOrderTotal` (zeroes the offer's discount if unmet, `:2206-2214`)
     and its `MaximumDiscountPerOffer` cap (proportionally redistributed if exceeded, `:2253-2288`) — the
     same two guards as [[Offers.technical|Offers]] Rule 1,
     re-verified against the order's actual quantities rather than what was true at add-to-cart time.
   - `TotalOfferDiscount = OrderDetails.Sum(OfferDiscount)` (`:4924`, post-cap).
   - `ApplyOffersContribution(...)` (`:4926` → `Order.cs:5332-5356`) sets, per restaurant,
     `OrderRestaurantDetails.OfferContributionPercentage`/`Value` from `Offers.MerchantContributionPercentage`
     — **cost split**: merchant's dollar share = `resturantOfferDiscount * MerchantContributionPercentage /
     100` (`:5351`); the remainder is 8orders' share (`CompanyContributionValue`, step 6d).

   **6b. Tiered Discount, applied second, per restaurant** (`ApplyTieredDiscounts`,
   `Order.cs:4974-5154`, invoked at `:4933`):
   - `hasItemOffers && tieredDiscount.AllowWithItemOffers == false` **skips that restaurant's tiered
     discount entirely** (`:5052-5055`) — the Offers/Tiered-Discount compatibility gate, re-checked here
     defensively even though it was already checked when the discount was attached to the cart item
     ([[TieredDiscount.technical|TieredDiscount]] Dependencies row,
     `Shared/TalabatkApplication/Queries/GetCustomerTieredDiscountQuery/GetCustomerTieredDiscountQuery.cs:99-110`).
   - `TieredDiscount.CalculateDiscount(...)` (`:5087-5094`) runs per restaurant against that restaurant's
     own subtotal — the eligibility gauntlet (active, date window, customer/segment allow-list unless
     `LockedTieredDiscountId` bypasses it) lives inside that call; see
     [[TieredDiscount.technical|TieredDiscount]] Rule 11, not re-derived.
   - Delivery-type tiered discounts share **one budget across the whole order**, one delivery fee
     (`:5007-5012`, `remainingDeliveryCapacity`); order-type discounts are capped per-merchant inside
     `CalculateDiscount` itself.
   - `restaurantDetail.SetTieredDiscount(...)` (`:5121-5124`) stores the applied amount and winning tier.
     **Cost split** (`OrderRestaurantDetails.cs:398-400`, gated on `MerchantContributionPercentage > 0`):
     merchant's dollar share = `MerchantContributionPercentage / 100 * discountAmount`
     (`OrderRestaurantDetails.cs:189-193`); 8orders covers the rest via `EightOrderContribution` (the two
     percentages are validated to sum to exactly 100 at creation, see
     [[TieredDiscount.technical|TieredDiscount]] Rule 4).

   **6c. PromoCode or Voucher, applied last** (`ApplyVoucher`, `Order.cs:5358-5435`, invoked at `:4939`):
   - **Domain-layer mutual-exclusivity guard** (`:5375-5378`): `if (promoCode != null && voucher != null)
     return Result.Failure<decimal>("You can use only one voucher.")` — defensive, since step 1 already
     makes both non-null impossible through the checkout path; only bites a caller that reaches
     `ApplyVoucher` some other way (e.g. the order-edit path, if it were ever passed both).
   - **If a `Voucher`**: `ApplyLoyaltyPointsVoucher` (`:5385` → `Order.cs:5572-5619`) re-checks `ExpiryDate`
     (`:5576-5579`) and `IsUsed` (`:5581-5584`, skipped on update-in-place), then
     `voucherDiscount = Math.Min(voucher.DiscountAmount, totalorder)` (`:5586`), or if merchant-scoped,
     capped at that restaurant's own subtotal (`:5601`). **Cost split**: set only if merchant-scoped —
     `SetVoucherContribution(voucher.MerchantDiscountContribution ?? 0, voucherDiscount, false)` (`:5602`).
     **If not merchant-scoped** (`voucher.MerchantRestaurant == null`, `:5608-5612`), `SetVoucherContribution`
     is **never called** — the restaurant's `VoucherContributionPercentage` stays at its unset default,
     which per the step 6d formula means 8orders' `CompanyContributionValue` absorbs the **entire** unscoped
     voucher discount, no merchant share at all. Traced directly from the code; not previously documented.
   - **If a `PromoCode` and `isVoucherCampaigneEnabled` is off** (the older/default path, `:5397-5434`):
     eligibility total is `total = (TotalBeforeDiscount - TotalOfferDiscount) + ExtraRestaurantDeliveryFees
     + DeliveryFees` (`:5380-5381`) — **subtracts the offer discount but not the tiered discount already
     applied in step 6b**. If `total >= promoCode.MinimumAmount`, `PromoCodes.CalculatePromoCodeDiscount`
     (`PromoCodes.cs:395-456`) runs against a per-restaurant subtotal dictionary built from
     `OrderDetails.TotalPricewithOptionAndQuantity` — the **gross** price×quantity field (`:5401-5404`), so
     **neither the offer discount nor the tiered discount already applied to that restaurant is netted out
     of the promo's own discount base.** Capped at `total`, and for `ItemDiscount` type additionally at
     `TotalBeforeDiscount - TotalOfferDiscount` (`:5414-5420`), before `UsePromoCode` records it (`:5421` →
     `Order.cs:894-902`, increments `PromoCodes.BudgetSpent`/`NumberOfTimesUsed`). **This path never reads
     `PromoCodes.CombineWithOffers`** — an active item offer and this promo code always stack regardless of
     what that field says.
   - **If a `PromoCode` and `isVoucherCampaigneEnabled` is on** (`CalculateVoucherCampaigne`,
     `Order.cs:5437-5540`): this path **does** read `CombineWithOffers` — restaurants with an active item
     offer are excluded from the promo discount unless `CombineWithOffers` is true (`:5442-5448`) — and
     **does** net the already-applied tiered discount out of each restaurant's subtotal first (`:5455-5467`,
     with a carve-out at `:5458-5462` for delivery-type tiered discounts, which shouldn't reduce the item
     subtotal). **The same promo code is computed on a different, more consistent base purely depending on
     a feature flag** — the two paths disagree on whether an already-applied tiered discount reduces the
     promo's own base. Observed in this pass; same "divergent-duplicate-path" shape as the family behind
     **#398** and **#410**, but not itself a registered finding.
   - Either branch: a failed promo/voucher validation does **not** fail checkout — it's recorded as a
     system `OrderComment` (`:5425-5430`) and the order proceeds with `discount = 0` for that stream.

   **6d. Taxes, service fees, and the final total.**
   `CalculateTaxesAfterAllDiscounts(tieredDiscountsByRestaurant)` (`:4957`, body `Order.cs:5156+`, not
   traced in detail) recomputes per-line tax now that offer/tiered discounts are known. `SetOrderServiceFees`
   (`:4960`) applies city service fees. `TotalDiscount = TotalOfferDiscount + Sum(TieredDiscountAmount) +
   PromoValue + voucherValue` (`:4965`); `Total = TotalBeforeDiscount - TotalDiscount + ServicesFees +
   DeliveryFees + ExtraRestaurantDeliveryFees` (`:4967`). Each restaurant's `CompanyContributionValue`
   (`OrderRestaurantDetails.cs:63-86`) sums three independent terms — voucher, offer, tiered — each as
   *(percentage ≤ 0 → 8orders pays the full discount for that stream; percentage ≥ 100 → the restaurant
   pays all of it; in between → the split)*, where "percentage" is always the **restaurant's own**
   contribution percentage (fed straight from `MerchantContributionPercentage`/`MerchantDiscountContribution`
   into `Set*Contribution`, `OrderRestaurantDetails.cs:158-193,398-400`). The merchant's share reaches the
   statement via `AddMerchantContributionTransaction`, 8orders' via `AddCompanyContributionTransaction` —
   both documented, not re-derived, in [[Money-Path.technical|Money-Path]] step 7b.4-7b.5.

7. **Post-creation re-checks** (documented in
   [[CustomerCart.technical|CustomerCart]] Rule 9.12/9.13, bridged not
   restated): the voucher's `MinOrderAmountAtIssue` and the promo code's `MinimumAmount` are each checked a
   **second time**, against the *resulting* order/merchant subtotal, after steps 6a-6d have already run.

## Data written

In pipeline order, for a checkout that resolves a tiered discount, an item offer, and a promo code (a
voucher would replace the promo code fields below with `Vouchers.IsUsed`/`Order.VoucherId` instead):

1. `OrderDetails.OfferDiscount` (per line, capped/redistributed) — `Order.cs:2177-2310`.
2. `OrderRestaurantDetails.OfferContributionPercentage`/`OfferContributionValue` — `Order.cs:5332-5356`.
3. `OrderRestaurantDetails.TieredDiscountId`/`TieredDiscountAmount`/`TieredDiscountContributionPercentage`/
   `TieredDiscountContributionValue`, plus `TieredDiscount.NumberOfTimesUsed` (increment) — `Order.cs:5279-5311`,
   `UpdateTieredDiscountUsageCounts` (not traced in detail in this pass).
4. `Order.PromoValue`/`PromoCodeId` (or `Order.voucherValue`/`VoucherId`), and
   `OrderRestaurantDetails.VoucherContributionPercentage`/`VoucherContributionValue` (voucher path only,
   and only if merchant-scoped) — `Order.cs:894-902`, `:5602`.
5. `PromoCodes.BudgetSpent`/`NumberOfTimesUsed` (via `UseVoucher`) or `Vouchers.IsUsed` (via
   `MakeVoucherUsed`) — `PromoCodes.cs:532-542` (bridged, not restated), `Order.cs:5616`.
6. `Order.TotalBeforeDiscount`/`TotalOfferDiscount`/`TotalDiscount`/`Total`, and per-line
   `OrderDetails.ProfitValue`/tax fields via `CalculateTaxesAfterAllDiscounts` — `Order.cs:4964-4967`.
7. `OrderRestaurantDetails.CompanyContributionValue` is a **computed property, not a stored column**
   (`OrderRestaurantDetails.cs:63-86`) — it is read later by
   [[Money-Path.technical|Money-Path]] step 4/7b when posting `MerchantStatementTransaction`
   rows; nothing in this flow writes it directly.

## External calls

None. Discount resolution is entirely in-process against the request-scoped `ITalabatkContext` — no
gateway, webhook, or third-party call happens during this part of checkout (contrast
[[Money-Path.technical|Money-Path]], where the *payment* side of the same checkout does call
out to PayMob).

## Failure modes

- **#398 — PromoCode and Voucher write the same table under contradictory uniqueness rules.** Bites
  upstream, at campaign-creation time, not during resolution — but it's why step 1's promo-code lookup
  (`CreateOrderFromCartCommand.cs:275-290`) can match the wrong one of two codes each individually accepted
  through whichever creation path (`AddPromoCodeCommand`/`AddVoucherCommand`) was less strict.
- **#410 — an active offer's discount can be non-deterministically dropped**, because the query deciding
  which offer is "the" active one for a restaurant picks arbitrarily among same-weekday offers before
  checking the time window. This flow's `restaurantIdsWithActiveOffers` query inherits the same incomplete
  filter (`CreateOrderFromCartCommand.cs:408-416`), so a restaurant can be treated as "has an active offer"
  — suppressing its tiered discount via `AllowWithItemOffers` (step 6b) or excluding it from a
  `CombineWithOffers=false` promo campaign (step 6c) — purely because *some* same-weekday offer exists,
  regardless of whether it's actually valid right now. Bites at steps 3, 6b, and 6c.
- **#438 — two live endpoints disagree on which vouchers a customer has.** Upstream of this flow, but it
  means a voucher picked off the unfiltered list can still fail step 1's restaurant-in-cart check
  (`:310-316`) at checkout — reading as the platform silently rejecting a voucher it itself showed as usable.
- **Tiered discount silently dropped between cart-add and checkout.** Step 4's `IsActive`/date-window
  re-check (`CreateOrderFromCartCommand.cs:379-390`) omits an expired/deactivated discount from
  `tieredDiscountsByRestaurant` with no validation failure — the total comes out lower than the cart showed,
  with nothing explaining why. Not a registered finding — observed in this pass.
- **PromoCode discount base disagrees with itself depending on a feature flag.** Per step 6c: the
  `Features.VoucherCampaigne`-off path computes a promo's discount against the *gross* per-restaurant
  subtotal (`Order.cs:5401-5410`), while the flag-on path nets out both the offer and tiered discount first
  (`:5455-5467`) and additionally respects `CombineWithOffers`, which the flag-off path never reads. Same
  promo code, same cart, two different discount amounts and two different stacking rules purely by flag
  state. Not registered; same shape as the divergent-duplicate-path family (#398, #410, #406, #395).
- **Segment/customer allow-lists on `PromoCodes` are populated but never enforced at redemption.**
  `PromoCodeCustomers`/`PromoCodeAudiences` are created and stored
  (`PromoCodes.cs:23-24,56-57,251-252,344-345`), but neither `ValidatePromoCode` (`PromoCodes.cs:459-518`)
  nor the checkout fetch (`CreateOrderFromCartCommand.cs:275-290`, which `Include`s only
  `RestaurantPromoCodes`/`PromoCodeAreas`) ever reads them — a code scoped to a customer list or segment is
  redeemable by anyone with the text, subject only to the gates that *are* checked. Not registered;
  contrast [[TieredDiscount.technical|TieredDiscount]], whose equivalent
  allow-lists **are** enforced.
- **Unscoped `Vouchers` cost split is all-or-nothing, undocumented as such.** Per step 6c: a
  non-merchant-scoped voucher's discount is entirely absorbed by 8orders (no `SetVoucherContribution` call
  leaves the contribution percentage at its unset default). May be intended (loyalty points are an
  8orders program, not a merchant one) but stated here as a traced code fact, not confirmed against intent.
- **#341 / #342 — not a bug, an accepted tradeoff, noted because it bites in this exact flow.** ADR 0002
  (`accepted`) documents that a guest outside a `TieredDiscount`'s target segment who adds a qualifying
  item then logs in with an out-of-segment account still gets the discount, because
  `bypassCustomerEligibility` (`Order.cs:5243`, `LockedTieredDiscountId == tieredDiscount.TieredDiscountId`)
  skips the segment check inside `CalculateDiscount` for exactly this case. Deliberate, accepted design —
  logged as **#342** (bridged Round 4), not re-investigated. **#341** (guest creation has no rate limit) is
  the related, surrounding gap; it does not itself bite inside this flow.

## Folded entities — the 5 satellites documented here

| Entity | What it is | Rules |
|---|---|---|
| `LoyaltyPointsSrc` | The ledger of a loyalty-point transfer: source points, target points, how many were used, and the transaction type | One guard — the target must be greater than zero (`Shared/TalabatkLogic/TalabatkModels/LoyaltyPointsSrc.cs:29`). `SourcePointId`/`TargetPointId` plus `UsedPoints` is what makes a partial redemption traceable to the specific point batches it drew from, which is the data any dispute about a customer's balance has to be settled from. Nothing checks that `UsedPoints` is positive, or that it does not exceed the source |
| `LoyaltyConfigAuditLog` | Who changed which loyalty setting on which merchant, from what to what | Private ctor, `Create` only, no guards (`Shared/TalabatkLogic/TalabatkModels/LoyaltyConfigAuditLog.cs:21`). Field-level before/after with a `UserId` — the fourth distinct change-history mechanism in the platform, after the three in [[Admin/Admin Back-Office/Configuration/Configuration.technical\|Configuration]]. It exists because `MerchantLoyaltyConfig` itself validates nothing, so the audit trail is the only record of what a contribution percentage used to be |
| `ExclusiveOfferItem` | A menu item placed in one of the mart's exclusive-offer rails | Four real guards: the restaurant and menu item must be present (`Shared/TalabatkLogic/TalabatkModels/ExclusiveOfferItem.cs:32`, `:35`), the **section must be 1 or 2** (`:38`) and the display order cannot be negative (`:41`). The section check is the interesting one — a magic-number range validated in the domain, which means the two rails are a domain concept rather than a presentation choice. `UpdateDisplayOrder` (`:53`) is an unguarded `void`, so the non-negative rule holds only at creation |
| `OffersDescriptions` | An offer's description text in one language | `Instance` (`Shared/TalabatkLogic/TalabatkModels/OffersDescriptions.cs:20`) and a `void UpdateDescription` (`:32`), **neither validating** — so an offer can carry a blank description in one language while reading correctly in the other |
| `PromoCodeCity` | Restricts a promo code to a city | Four fields and one factory, misspelt **`Insatnce`** rather than `Instance` (`Shared/TalabatkLogic/TalabatkModels/PromoCodeCity.cs:17`). No guards. The misspelling matters practically: a search for `PromoCodeCity.Instance` finds nothing, which is how this row gets missed when tracing promo scoping |

### What the split means

The two entities that touch money — `LoyaltyPointsSrc` and, indirectly, `LoyaltyConfigAuditLog` — are the
weakest here, and the strongest is `ExclusiveOfferItem`, which controls where a tile appears on a screen.
`LoyaltyPointsSrc` can record a transfer that used more points than its source held; `ExclusiveOfferItem`
cannot be created in section 3.

## Open Questions

- [ ] Should `LoyaltyPointsSrc` guard `UsedPoints` against the source batch's remaining balance? Today
      the only check is that the target is positive.
- [ ] `PromoCodeCity.Insatnce` is misspelt. Renaming it is safe (no reflection use found) and would make
      promo-scoping searches work.
- `CalculateTaxesAfterAllDiscounts`'s internals (`Order.cs:5314` onward) — not traced in this pass.
- Which caller(s) invoke the order-edit path (`CalculateOrderTotal`, `Order.cs:4825`) vs. the checkout
  path — not traced in this pass; both run the same three-stage pipeline so are treated as one flow here.
- Whether the merchant-scoped `Voucher` restaurant match at step 1 (`:310-316`) and the independent
  re-derivation inside `ApplyLoyaltyPointsVoucher` (`Order.cs:5749-5753`) can ever disagree, e.g. if the
  cart's restaurant set changes mid-checkout — not confirmed.
- `UpdateTieredDiscountUsageCounts` (`Order.cs:5143`, referenced but not opened) — not traced in this pass.
- Whether any UI surface shows the customer *why* a promo/voucher failed (`OrderComment` at
  `Order.cs:5428-5430` reads as system-internal, not obviously customer-facing) — not traced in this pass.
- The interaction between `CalculateVoucherCampaigne`'s delivery-discount branch (`Order.cs:5658-5689`)
  and the tiered-discount delivery budget from step 6b, on a multi-restaurant order where only some
  restaurants are voucher-eligible — not stress-tested in this pass.
