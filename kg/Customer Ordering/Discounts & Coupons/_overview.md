---
id: 8orders/customer-ordering/discounts-and-coupons/overview
title: Discounts & Coupons — Overview
note_type: overview
context: Customer Ordering
feature: Discounts & Coupons
audience: Business
last_updated: 2026-08-02
---
# Discounts & Coupons — Overview

## What is this? (for everyone)
8Orders has **three separate discounting mechanisms** that customers can encounter, and it's easy
to blur them together because the business (and even the codebase itself) sometimes uses "coupon"
or "voucher" loosely for all three:

| Mechanism | How a customer gets it | How it's applied |
|-----------|---------------------------|---------------------|
| **Promo Code** | Types in a known code at checkout | Manual — must be entered |
| **Voucher** | Redeems loyalty points | Picked from a list, tied to that customer only |
| **Tiered Discount** | Just qualifies by spending enough | Fully automatic, no action needed |

This document covers Promo Codes and Vouchers. Tiered Discount has its own feature note (see
[[Customer Ordering/Tiered Discount/_overview|Tiered Discount]]).

## The Feature at a Glance
| # | Step (Screen) | Who | Purpose |
|---|----------------|-----|---------|
| 1 | Checkout — code entry | Customer | Type a Promo Code |
| 2 | Loyalty/points screen | Customer | Redeem points into a Voucher |
| 3 | Checkout — voucher list | Customer | Pick an available Voucher |
| 4 | Checkout | Customer | Apply exactly one of Promo Code or Voucher (never both) |

## Business Flow (plain language)
1. A Promo Code is set up (area/city/restaurant/customer/segment targeting, a validity window, a
   usage cap, and a budget) and shared with customers through marketing.
2. Separately, a customer accumulates loyalty points and can redeem them into a Voucher — a
   one-time-use amount of store credit tied to just that customer.
3. At checkout, the customer supplies either a Promo Code or picks a Voucher — never both in the
   same order. Whichever is used gets validated (still active, not already used, order meets any
   minimum) and its discount applied.

## Key Concepts
- **Promo Code budget & usage caps** — a code campaign has a total spend ceiling and can limit how
  many times it's used overall and per customer.
- **Voucher single-use** — a voucher is spent once, by the one customer it was issued to.
- **Mutual exclusivity** — a Promo Code and a Voucher can never both apply to the same order.

## Detailed Notes
- [[_knowledge-graph|Technical Knowledge Graph]] — for developers & CR work, including the ambiguity
  this note resolves (as far as the code shows) between "Promo Code," "Voucher," and "coupon."
- [[_scenarios|Scenario Catalog]]
