---
id: 8orders/customer-ordering/payments/paymob-business
note_type: business
context: Customer Ordering
feature: Payments
last_updated: 2026-08-23
tags: [customer-ordering, payments, business]
---
# PayMob

The payment gateway behind three of the app's online payment options — paying by card, paying
through PayMob's own mobile "smart wallet," and Apple Pay — and the system that later calls
8Orders back to confirm whether a payment actually succeeded.

## What it is
When a customer doesn't pay cash, the online portion of an order can be routed through PayMob in
one of three ways: a bank card (new or previously saved), PayMob's wallet product tied to a mobile
number, or Apple Pay on supported devices. A separate, older bank gateway that is *not* PayMob also
exists side-by-side, and is used instead whenever PayMob is switched off for that request. Once a
customer finishes paying (or the payment fails, is refunded, or is voided), PayMob calls the app
back with the result — that callback, not anything the customer's device reports, is what actually
marks the order's online payment as captured, failed, or refunded.

## Business rules (plain words)
- Card, PayMob wallet, and Apple Pay are three different ways of using the same PayMob gateway; a
  fourth, non-PayMob bank-gateway path exists as an alternative and is chosen instead whenever the
  app isn't configured to use PayMob for that order, or the online amount is below the configured
  minimum for online payment at all.
- A card used successfully with PayMob can be saved and reused for a later order — PayMob tells
  8Orders about the new saved card through its own callback, and 8Orders stores it against the
  customer.
- If a customer leaves the payment page and comes back, the app tries to resume the same payment
  link instead of starting over, as long as it hasn't expired.
- Apple Pay is treated as a special case throughout this flow, because its own setup step happens
  later than the card/wallet flow's does: it's allowed to reach checkout without yet having a
  PayMob order registered, where a card or wallet payment would not be. That special-casing has a
  confirmed bug behind it — the one situation Apple Pay is deliberately allowed to reach is exactly
  the situation that crashes the "resume my payment" screen with an unhandled error instead of a
  friendly one (see the technical note, Rule 4).
- When PayMob calls back to report what happened to a payment, the app normally verifies
  cryptographically that the message genuinely came from PayMob before trusting it, and even asks
  PayMob directly to confirm if that check fails. **For Apple Pay's callback specifically, none of
  that verification happens at all** — the callback is trusted and acted on regardless. This is the
  single most important finding in this note for a payment feature; see the technical note, Rule 6.
- Refunding an online payment back to the customer is something a back-office staff member
  triggers from the admin screens — it is not something the customer initiates directly.

## Who uses it
- **Roles:** Customer (chooses card, PayMob wallet, or Apple Pay at checkout, and receives the
  redirect page or Apple Pay sheet); Admin (triggers refunds on an order).
- **Screens:** Customer checkout / online-payment step (mobile app); AdminUi's order refund action.

## Related
- [[Order.technical|Order]] — holds the PayMob order id and Apple Pay
  flag, and moves through the payment-status changes PayMob's callback drives
- [[Checkout-Payment-Processing|Checkout Payment Processing]] — where a PayMob
  payment session is first created during checkout
- [[Wallet-and-PaymentMethod|Wallet & PaymentMethod]] — the customer wallet
  that a PayMob refund can credit
- Technical detail: [[PayMob.technical|PayMob — technical]]
