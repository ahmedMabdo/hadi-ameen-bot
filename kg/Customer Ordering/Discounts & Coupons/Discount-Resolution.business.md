---
id: 8orders/customer-ordering/discounts-and-coupons/discount-resolution-business
note_type: business
context: Customer Ordering
feature: Discounts & Coupons
group: Discount-Resolution
last_updated: 2026-08-23
tags: [flow, business]
---
# Discount Resolution — Business

## What this process is

A customer's cart can be touched by up to four different discount mechanisms at once: a manually-typed
**promo code**, a **voucher** (store credit earned by redeeming loyalty points), an automatic
**tiered discount** (spend more, save more, no code needed), and a restaurant's own **menu-item offer**
(a discounted price on specific dishes, no code needed). This process is what decides, at the moment of
checkout, which of these actually apply, in what order, and who — the restaurant or the company — ends up
paying for each one.

## Who is involved

- **The customer** — may already have a menu-item offer baked into their cart and a tiered discount
  earned by spending enough at a restaurant, and can additionally type a promo code or pick a voucher at
  checkout.
- **The restaurant** — funds a share (sometimes all, sometimes none) of each discount that touches its
  menu, per a percentage agreed when that campaign or offer was set up.
- **The company** — funds the remaining share, and owns the promo-code and tiered-discount campaign
  tools.
- **Ops/marketing** — configure eligibility (cities, customers, restaurants, minimum order size) when
  creating a promo code, voucher rate, or tiered-discount campaign.

## The steps, in plain words

1. Before checkout, the menu-item offer (if any) is already locked in from adding that item; the tiered
   discount was already attached per restaurant based on how much the customer is spending there.
2. At checkout, the customer can additionally supply a promo code or pick a voucher — never both. Typing
   a promo code makes any voucher selection ignored outright, even if one was also sent.
3. The menu-item offer is calculated and capped first: does the order meet its minimum spend, and does the
   discount exceed the cap the restaurant set? If so, it's scaled back proportionally.
4. The tiered discount is calculated second, per restaurant, at the highest spending tier the order
   qualifies for there. If the restaurant is running an item offer the customer used, and the tiered
   campaign wasn't configured to combine with item offers, the tiered discount is silently switched off
   for that restaurant.
5. The promo code or voucher is calculated last, on what's left of the order. A promo code also checks a
   list of gates: date window, usage/budget cap, area coverage, new-customer-only status, per-customer
   usage cap, restaurant requirement, and minimum order size.
6. The cost of whichever discounts applied is split between restaurant and company per that discount's
   own agreed percentage — one stream might land entirely on the company, another entirely on the
   restaurant, another split down the middle. This is what later shows up on the restaurant's statement.

## What can go wrong, in business terms

A promo code and a voucher genuinely cannot both apply to one order — that part is solid, enforced
twice over. Everything else is where the edges show:

- **Which discounts are even allowed to stack together is inconsistent.** A promo campaign's "can this
  combine with a restaurant's item offer" setting is only respected under one of two ways the system can
  compute the discount — under the other, it's silently ignored and the two stack regardless of
  configuration. The same promo code, on the same order, can also come out to a different amount
  depending on which calculation path is active, because only one of them subtracts a tiered discount
  that already applied.
- **A promo code scoped to a specific customer list or segment isn't actually locked to it at
  redemption.** The targeting is saved when the code is created, but nothing checks it when the code is
  used — anyone with the code text can redeem it, subject only to the other limits (dates, budget, area,
  restaurant). The equivalent restriction on tiered-discount campaigns does not have this gap.
- A tiered discount valid when added to the cart can quietly stop applying by checkout (expired or
  deactivated in between) — the total comes out lower than the cart showed, with nothing explaining why.
- Two already-known platform issues bite this process from the outside: which offer a restaurant is
  considered to have "active" right now can be decided arbitrarily when more than one exists (the same
  shortcut used here to decide whether an offer blocks a tiered discount or promo code from combining
  with it), and the two screens that tell a customer which vouchers they have disagree, so a customer can
  pick a voucher checkout then rejects.
- One thing that looks like a gap but is not: a guest outside a tiered discount's target audience who
  adds a qualifying item, then logs in with an account outside that audience, can still keep the
  discount. This was reviewed and deliberately accepted as a bounded cost of guest browsing — a known,
  signed-off tradeoff, not an oversight.

## What the company should know

Discount resolution is not one system deciding one number — it's four independent mechanisms, built at
different times, whose interactions were never fully reconciled. The order they apply in (offer, then
tiered discount, then promo code or voucher) is consistent, but *whether* two of them are allowed to
combine, and what base amount a discount is calculated against, depends in places on a feature flag rather
than on a single rule everyone can point to. The cost-sharing split between restaurant and company is
correctly wired per discount stream, but an unscoped voucher (one not tied to any specific merchant) is
funded entirely by the company by default — worth confirming that matches the intended loyalty-program
economics.
