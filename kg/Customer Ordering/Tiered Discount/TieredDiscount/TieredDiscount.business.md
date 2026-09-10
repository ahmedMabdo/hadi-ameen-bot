---
id: 8orders/customer-ordering/tiered-discount/tiereddiscount-business
note_type: business
context: Customer Ordering
feature: Tiered Discount
entity: TieredDiscount
entity_type: aggregate-root
last_updated: 2026-08-23
tags: [customer-ordering, tiered-discount, transactional, business]
---
# Tiered Discount

A "spend more, save more" discount campaign: the bigger a customer's order, the bigger the
discount they unlock, in steps.

## What it is
A Tiered Discount is a promotion that rewards a bigger basket with a bigger discount — for example
"spend 200 to get 10% off, spend 400 to get 15% off, spend 600 to get 20% off." It can apply to the
whole order or just to the delivery fee, and it can be aimed at everyone, a specific list of
customers, a customer segment, or one/several restaurants only. The cost of the discount is shared
between the restaurant and 8Order at a percentage split set when the campaign is created.

Since mid-2026 it can also be shown to guests — people browsing and building a cart before they've
logged in — so a promotion can hook a new customer before they've even created an account.

## Business rules (plain words)
- The restaurant's and 8Order's share of the discount cost must always add up to 100% — there's no
  scenario where either side pays more or less than its agreed share.
- A delivery-fee discount is always a flat amount, never a percentage — only order discounts can be
  percentage-based.
- Each tier needs a strictly higher spend threshold than the one before it, and (in practice, though
  enforced only in the admin tool that creates it) a strictly bigger reward too.
- A campaign can't start or end in the past, and you can't turn a campaign back on once its end date
  has already passed — the expiry date needs to be pushed forward first.
- Two active campaigns can't share the same name.
- At the moment a customer's cart is checked, the discount only shows up if the campaign is
  currently active, today falls inside its date window, the customer is allowed to see it (on the
  list/segment, or a guest if the campaign is marked guest-visible), and the restaurant doesn't have
  a conflicting item-level offer running (unless the campaign explicitly allows stacking with one).
- If a guest locks in a tiered discount while browsing, and then logs in, they keep that exact
  discount on their cart — it isn't re-evaluated against their now-real account's own eligibility.

## Who uses it
- **Roles:** Created and managed by internal Admin/ops staff; seen and used by Customers (including
  guests) while browsing and checking out.
- **Screens:** The Tiered Discount management screens in the Admin back-office
  (create/edit/activate/deactivate/delete a campaign); the "spend X more to unlock Y% off" progress
  banner in the customer mobile app's cart/restaurant view.

## Related
- [[TieredDiscountTier|The spending tiers]] — the actual thresholds and reward amounts within a campaign.
- Technical detail: [[TieredDiscount.technical|Tiered Discount — technical]]
