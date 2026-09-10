---
id: 8orders/customer-ordering/discounts-and-coupons/vouchers-business
note_type: business
context: Customer Ordering
feature: Discounts & Coupons
entity: Vouchers
entity_type: legacy-poco-root
last_updated: 2026-08-23
tags: [customer-ordering, discounts-coupons, transactional, business]
---
# Voucher

Store credit a customer earns by redeeming their loyalty points.

## What it is
A Voucher is created when a customer trades in loyalty points for a cash-value discount. Unlike a
Promo Code, there's nothing to type — the customer just picks it from a list at checkout, since it
already belongs to them and them alone. It can optionally be tied to a specific restaurant, with
that restaurant covering part of its cost.

## Business rules (plain words)
- The discount amount comes from a fixed points-to-money exchange rate at the moment of redemption.
- A voucher belongs to exactly one customer and can be used exactly once.
- It expires a set number of days after it's issued.
- If tied to a specific restaurant, it can only be used on an order from that restaurant, and only
  if the order meets a minimum amount.
- Only one of a Voucher or a Promo Code can be used per order — never both.

## Who uses it
- **Roles:** Customers, via the loyalty points redemption screen and checkout.
- **Screens:** Loyalty/points redemption screen, checkout voucher selection.

## Related
- [[PromoCodes.business|Promo Code]] — a different, typed-code discount mechanism.
- [[Customer Ordering/Tiered Discount/_overview|Tiered Discount]] — a third, fully automatic discount mechanism.
- Technical detail: [[Vouchers.technical|Vouchers — technical]]
