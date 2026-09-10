---
id: 8orders/customer-ordering/order-and-fulfilment/cancellation-and-refund-business
note_type: business
context: Customer Ordering
feature: Order & Fulfilment
last_updated: 2026-08-23
tags: [flow, business]
---
# Cancellation, Rejection and Refund

## What this is

This is what happens whenever an order does not run its normal course to "delivered and paid for" —
the customer changes their mind, the restaurant can't fulfil it, an item turns out to be unavailable,
support has to step in, the payment never went through, or a driver couldn't hand the order over. It
covers who can stop an order and when, what happens to money already paid, and who covers the cost.

## The steps, in plain words

1. **The customer changes their mind.** They can cancel their own order themselves, but only before a
   restaurant has accepted it. Once a restaurant confirms, only support can cancel it for them. Before
   agreeing, the system double-checks with the payment provider that the charge hasn't just cleared —
   if it has, the cancellation is refused and the payment is accepted instead.
2. **The restaurant can't fulfil it.** A restaurant can reject an order, or its own portion of a
   multi-restaurant order, while it's still awaiting confirmation. Rejecting without good cause can
   cost the restaurant a penalty, unless it holds an exemption.
3. **An item turns out to be unavailable.** The restaurant flags which items it can't provide; what
   happens next follows the customer's own standing preference — cancel the whole order, suggest
   alternatives, or drop the unavailable items and continue at a reduced total (which can trigger a
   partial refund for the difference).
4. **Support steps in.** An admin agent can reject an order almost any time before delivery — even
   after a driver is assigned or en route — a reach neither the customer nor the restaurant has on
   their own. Before overriding an order still awaiting restaurant confirmation, the system shows the
   agent what each restaurant has actually done, so nothing is overridden blind.
5. **The customer never finishes paying.** If checkout starts with an online payment that's never
   completed, the system cancels the order by itself after a configurable wait — no human involved.
6. **The driver can't deliver.** A failed hand-off is still recorded as "delivered," just flagged with
   a reason. Money already paid is **not** automatically returned — someone has to notice and manually
   raise a compensation.
7. **Getting the money back.** An online refund goes to the customer's wallet or back to their bank,
   per their saved preference and a company-wide auto-refund setting. If a bank refund fails, the
   customer is credited to their wallet instead so they're never left with nothing, and support can
   later push that credit through to the bank once resolved. Cash/wallet legs that were never charged
   are simply cancelled.
8. **Compensation, separate from cancelling.** When something went wrong but the order itself isn't
   cancelled, support can add a compensation. Small amounts (within a configured limit/percentage of
   the order) pay out automatically; larger ones need a second approver. It can go to the customer's
   wallet or as cash the driver hands over on the spot. Whoever is judged responsible — restaurant or
   driver — has it deducted from their own running account; if no one is, the company absorbs it.

## Who is involved

- **Customer** — cancels pre-confirmation; sets standing preferences for unavailable items and refund
  destination.
- **Restaurant** — rejects orders or items it can't fulfil; can be penalized for doing so without
  cause.
- **Driver** — records a failed hand-off; can be told to hand cash compensation to a customer,
  deducted from what the driver owes the company.
- **Support / admin** — broadest power to reject at any stage; approves larger compensations; can
  manually push a stalled refund through to the bank.
- **The system** — auto-cancels orders where online payment was never completed.
- **The company** — absorbs penalty/compensation costs whenever neither restaurant nor driver is
  specifically judged responsible.

## What can go wrong, in business terms

- A customer can be told a cancellation succeeded when it didn't actually save.
- A rejection reason lookup that isn't checked for existence can crash the request instead of showing
  a clean error, in two support-side spots.
- A partial rejection inside the "item unavailable" flow can silently fail to save while still
  reporting success.
- One cancellation endpoint doesn't verify the caller owns the order — in principle another customer's
  order number could be used to cancel it.
- The manual "complete a stalled bank refund" action only checks that the caller is *an* authenticated
  admin, not that they hold a refund-specific permission, unlike the sibling reject actions.
- A failed hand-off never automatically triggers a refund — a human must notice and raise one.
- If a bank reversal succeeds with the payment provider but our own save then fails, retrying could
  reverse the same charge with the provider a second time.

## What the company should know

The refund logic is genuinely careful about not double-refunding a customer and about never leaving
one with nothing if a bank refund fails — those safeguards are real and consistent across every
trigger. The gaps are narrower: two places report failure as success, one cancellation endpoint is
missing an ownership check, the manual bank-refund action is missing a fine-grained permission, and
there is no automatic safety net when a driver can't complete a hand-off. None are exotic; each is
fixable without touching the overall design.
