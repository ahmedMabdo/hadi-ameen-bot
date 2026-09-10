---
id: 8orders/admin/erp-and-integrations/overview
title: ERP & Integrations — Overview
note_type: overview
context: Admin
feature: ERP & Integrations
audience: Business
last_updated: 2026-08-23
tags: [admin, erp-and-integrations, business]
---
# ERP & Integrations — Overview

## What is this? (for everyone)

Everything 8Orders sends to, or receives from, systems that are not 8Orders.

The big one is **AccFlex**, the accounting system. Every day, the money 8Orders has recorded — what it
owes restaurants, what it owes drivers, cash collected, bonuses, compensation, refunds, promo codes —
is turned into accounting entries and posted to AccFlex. That is how the business's books are kept.

AccFlex is also the source of truth for **stock quantities** in the grocery-style Mart stores, so
quantities flow the other way too.

Alongside those: restaurant sign-up enquiries are pushed to **Bitrix24**, the sales CRM; restaurant and
menu data is copied into a **search index** so customers can search quickly; and there are endpoints for
outbound notifications to other systems, a third-party AI service, and the support-chat widget.

## The Feature at a Glance

| # | Step (Screen) | Who | Purpose |
|---|---|---|---|
| 1 | Accounts, treasuries, banks | Finance | Look up the accounting structure |
| 2 | Pay a merchant | Finance | Record a payment to a restaurant |
| 3 | Pay a driver | Finance | Record a payment to a driver |
| 4 | Journal subscriptions | Finance | Which kinds of accounting entries are switched on |
| 5 | Integration tracking | Finance, operations | Did last night's posting actually work? |
| 6 | Search index | Operations | Rebuild or inspect the search index |
| 7 | Webhooks | Technical | Outbound notifications to other systems |

## Business Flow (plain language)

1. Through the day, orders, deliveries, deposits and compensations are recorded inside 8Orders.
2. On a schedule, those records are grouped into accounting entries — fourteen different kinds — and
   sent to AccFlex.
3. Cash paid or received at the office goes through a separate route to the same system.
4. Mart stock quantities are kept in step with AccFlex, in both directions.
5. Restaurant sign-up enquiries go to Bitrix24, and their status is polled back so 8Orders knows how
   each lead is progressing.
6. Restaurant and menu data is indexed for search.
7. A tracking screen shows whether each of those runs succeeded — which matters, because otherwise
   nobody would know.

## What a business reader must know

**There are two separate AccFlex integrations with two confusingly similar switches.** One controls the
stock synchronisation; the other controls the accounting postings. Their names both read as "is ERP
turned on?", and turning one off does **not** turn the other off. This has been confused before,
including in this project's own planning notes, so it is stated plainly here.

**The daily accounting batch is fragile in bulk and forgiving of bad data** — which is the wrong way
round for accounting. Specifically, and all recorded as findings:

- One bad row can cause a whole day's postings to be rolled back.
- Some shared state inside the posting code is not safe when things run in parallel.
- When a restaurant has no accounting account configured, entries are posted against **account zero**
  rather than being refused — so the entry exists, in the wrong place, silently.

**The stock synchronisation has an incident history worth knowing.** It originally let orders through
when the stock check failed; that has been fixed so a failed check now blocks. The remaining gap is
different and still open: **nothing reserves stock at checkout**, so two customers can be sold the last
item. Fixing the first did not fix the second, and they are easy to confuse.

Finally, a visibility point: the tracking screen tells you whether a run *happened*, not whether
8Orders and AccFlex *agree*. Reconciliation is a separate question and, as far as the code shows, not
automated.

Register rows: #263 and #272 (stock-sync history and the reservation gap), #293–#296 (batch fragility),
#418 and #418(a) (posting to account zero).

## Key Concepts

- **Journal** — an accounting entry. Fourteen kinds are built, from restaurant accruals to refunds.
- **Treasury** — the cash-handling side of the accounting system, used for receipts and payments.
- **Journal subscription** — which journal kinds are switched on.
- **Stock synchronisation** — keeping Mart quantities in step with the warehouse system.
- **Lead** — a restaurant sign-up enquiry, tracked in the sales CRM.
- **Search index** — the fast copy of restaurant and menu data used for customer searches.

## Detailed Notes

- [[Admin/ERP & Integrations/_knowledge-graph|Technical Knowledge Graph]] — the two flags, all fourteen
  journal builders, and what each finding means for a change.
- [[Admin/ERP & Integrations/_scenarios|Scenario Catalog]] — what happens if…
- [[Money-Path.business|The Money Path]] — how money reaches the point where this feature exports it.
