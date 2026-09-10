---
id: 8orders/customer-ordering/order-and-fulfilment/orderdetails-technical
note_type: technical
rule_count: 5
context: Customer Ordering
feature: Order & Fulfilment
entity: OrderDetails
entity_type: child
sources:
  - path: Shared/TalabatkLogic/TalabatkModels/OrderDetails.cs
    sha1: 188c9874b4a5
last_updated: 2026-08-23
tags: [customer-ordering, order-fulfilment, transactional, technical, backend-domain]
---
# OrderDetails — Technical

> **Layer:** Backend-Domain — legacy entity, richer than anemic (private setters, several calc
> methods), no private constructor.
> **Context:** Customer Ordering — a line item within `Order` (already partially documented; this
> extends coverage to the line-item level rather than duplicating).
> **Source Path:** `Shared/TalabatkLogic/TalabatkModels/OrderDetails.cs`   **Last Updated:** 2026-08-03

## Business Rules

### Rule 1: The same "price + options, discount, total" math is computed independently in three places
- **Plain language:** There are three separate code paths that each compute a line item's price,
  offer discount, and total after discount — from the catalog at order-creation time, from a cart at
  checkout time, and again on update — and they don't share one calculation method.
- **`CalcItemPrice`/`DetailCalcTotals`** (`Shared/TalabatkLogic/TalabatkModels/OrderDetails.cs:489-524`, `Shared/TalabatkLogic/TalabatkModels/OrderDetails.cs:545-552`) — used by `Instance` (catalog-sourced
  creation, via `CalcDetail` at `Shared/TalabatkLogic/TalabatkModels/OrderDetails.cs:465-488`) and by `Update` (`Shared/TalabatkLogic/TalabatkModels/OrderDetails.cs:265-306`, calls `DetailCalcTotals`
  directly). Offer discount: `Quantity * (IsPercentage ? round(Discount * priceWithOpt / 100, 2) :
  Discount)`. Total: `max(0, Quantity * PriceWithOption - OfferDiscount)`.
- **`CreateDetailsFromCartItems`** (`Shared/TalabatkLogic/TalabatkModels/OrderDetails.cs:210-263`) — building order details from an already-priced
  `CartItem` — computes `TotalAfterDiscountAndTax` **inline**, a third independent expression
  (`Shared/TalabatkLogic/TalabatkModels/OrderDetails.cs:254-255`) rather than calling `DetailCalcTotals()`, though it lands on the same formula shape
  (`max(0, Quantity * PriceWithOption - OfferDiscount)`).
- Three independent implementations of essentially the same total-after-discount formula is a more
  pronounced instance of the repo's established "same rule, multiple implementations" pattern
  (`_conflicts.md` #8, #10, #18, #22, #23) — worth flagging as the most-duplicated single formula
  found in this pass so far.

### Rule 2: Tax formula matches CartItem's, confirmed consistent (not a conflict)
- **Source:** `SetTaxUsingStoredValues` (`Shared/TalabatkLogic/TalabatkModels/OrderDetails.cs:451-464`) — `itemTaxValue = PriceAfterDiscount -
  PriceAfterDiscount / (1 + RestaurantTaxValue/100)` — the same VAT-style inclusive-rate formula
  already documented on `CartItem.SetTax` (Cart & Checkout). Cross-checked and found consistent, not
  duplicated-and-diverging — noted here so a future reader doesn't need to re-derive it.

### Rule 3: Extra-offer-item bilingual fields fall back to each other when one language is blank
- **Source:** `Instance` (`Shared/TalabatkLogic/TalabatkModels/OrderDetails.cs:152-153`) —
  `ExtraOfferItemEn = extraofferitemEN.Trim() == "" ? extraofferitemAr : extraofferitemEN` and the
  mirror for `ExtraOfferItemAR`. If the English text is missing, the English field ends up holding
  Arabic text (and vice versa) rather than staying blank — presumably intentional ("show something
  rather than nothing"), but worth flagging since it means these fields can't be assumed to actually
  be in their named language.

### Rule 4: Three distinct rejection paths with different field footprints
- **Source:** `RejectOrderByAvailability` (`Shared/TalabatkLogic/TalabatkModels/OrderDetails.cs:363-372` — sets `Rejected` + `IsAvailable=false`),
  `RejectSomeItemsOrderByAvailability` (`Shared/TalabatkLogic/TalabatkModels/OrderDetails.cs:373-382` — sets `NotAvilableItems` + `IsAvailable=false`,
  not `Rejected`), `RejectedByAnotherReasons` (`Shared/TalabatkLogic/TalabatkModels/OrderDetails.cs:405-410` — sets only `Rejected`, leaves `IsAvailable`
  untouched). Three genuinely different rejection scenarios (whole item unavailable, partial
  items unavailable, rejected for an unrelated reason) rather than one rule implemented three times —
  noted for completeness, not flagged as a conflict.

### Rule 5: Cooking time can only be set once (idempotent against re-assignment)
- **Source:** `SetDetailCookingTime` (`Shared/TalabatkLogic/TalabatkModels/OrderDetails.cs:417-424`) — only assigns if
  `!CookingTime.HasValue || CookingTime.Value == 0`.

## Key Fields
| Field | Meaning |
|-------|---------|
| `OfferDiscount` / `OrderLevelDiscount` | Two independent discount tracks — item-level offer vs. order-wide discount, both feed `RecalculateTaxAndProfit` (`Shared/TalabatkLogic/TalabatkModels/OrderDetails.cs:578-584`) |
| `ProfitPercentage`/`ProfitValue` | Internal margin, mirrors `CartItem`'s category-vs-restaurant profit source logic (`ApplyProfit`, `Shared/TalabatkLogic/TalabatkModels/OrderDetails.cs:525-544`) |
| `Replacements` (`OrderDetailReplacement`) | Item-replacement history — not opened in this pass |
| `IsReplacement` / `HasAlternatives` | Flags for the item-replacement flow, ties to `docs/items-replacement.md` (bridged in Ops & Infra) |

## Related
- [[Order.technical|Order]] — owning aggregate
- [[CartItem|CartItem]] — Rule 2's shared tax formula, and the source for `CreateDetailsFromCartItems`

## Open Questions
- [ ] Whether the three independent total-calculation implementations (Rule 1) have ever drifted
  against each other in practice.
- [ ] `OrderDetailReplacement`, `OrderRejectedReason` not opened in full.
