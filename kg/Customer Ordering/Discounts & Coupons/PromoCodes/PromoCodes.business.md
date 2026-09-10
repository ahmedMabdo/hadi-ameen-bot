---
id: 8orders/customer-ordering/discounts-and-coupons/promocodes-business
note_type: business
context: Customer Ordering
feature: Discounts & Coupons
entity: PromoCodes
entity_type: legacy-poco-root
last_updated: 2026-08-23
tags: [customer-ordering, discounts-coupons, transactional, business]
---
# Promo Code

A discount code a customer types in at checkout.

## What it is
A Promo Code is a text code (like "WELCOME10") that a customer enters during checkout to get a
discount — either off their items or off delivery. Unlike a Tiered Discount, nothing about it is
automatic: the customer has to know the code and type it in.

## Business rules (plain words)
- Each code has a validity window, and can have a total redemption cap, a per-customer redemption
  cap, and a total budget the campaign shouldn't exceed — once any of those runs out, the code stops
  working.
- A code can be restricted to specific delivery areas, cities, restaurants, customers, or customer
  segments, or left open to everyone.
- A code can be limited to customers who've never had a delivered order before.
- A code discounts either the order total or just the delivery fee, as a percentage or a fixed
  amount, capped at a maximum.
- Only one of a Promo Code or a Voucher can be used per order — never both.

## Who uses it
- **Roles:** Customers enter it at checkout; managed internally (likely by Admin/ops, not confirmed
  in this pass).
- **Screens:** Checkout, promo code entry field.

## Related
- [[Vouchers.business|Voucher]] — a different, non-typed discount mechanism issued from redeeming loyalty points.
- [[Customer Ordering/Tiered Discount/_overview|Tiered Discount]] — a third, fully automatic discount mechanism.
- Technical detail: [[PromoCodes.technical|PromoCodes — technical]]
