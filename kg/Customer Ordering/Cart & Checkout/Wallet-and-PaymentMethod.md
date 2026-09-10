---
id: 8orders/customer-ordering/cart-and-checkout/wallet-and-paymentmethod
note_type: single
rule_count: 9
context: Customer Ordering
feature: Cart & Checkout
sources:
  - path: Shared/TalabatkLogic/TalabatkModels/WalletTransaction.cs
    sha1: d49b022e33d0
  - path: Shared/TalabatkApplication/Queries/GetAllPaymentsByAddressQuery/GetAllPaymentsByAddressQuery.cs
    sha1: f556ad73bbcf
  - path: Shared/TalabatkApplication/Queries/GetCustomerWalletQuery/GetCustomerWalletBalanceQuery.cs
    sha1: bfb6e2bc5e1e
  - path: TalabatkAPIs/Controllers/PaymentMethod/PaymentMethodController.cs
    sha1: 9eadf93be946
  - path: TalabatkAPIs/Controllers/Wallet/WalletController.cs
    sha1: e76da84651f6
last_updated: 2026-08-23
tags: [customer-ordering, cart-checkout, light, backend-application]
---
# Wallet & PaymentMethod

Reclassified from "full depth" to **light** during research: from the Customer Ordering
(`TalabatkAPIs`) side, both are thin, mostly read-only lookups. The actual wallet-balance mutation
logic (crediting/debiting) is not exposed here and wasn't found in this pass — likely owned by
Admin or the payment-processing path inside `CreateOrderFromCartCommand` itself.

## Wallet (`TalabatkAPIs/Controllers/Wallet/WalletController.cs`)
Two read-only endpoints, both simple MediatR query passthroughs:
- `GetBalance` → `GetCustomerWalletBalanceQuery` — the customer's current wallet balance.
- `GetMyWelletTransaction` → `GetTransactionsByCustomerIdQuery` — transaction history.

At checkout, `CreateOrderFromCartCommand` reads the wallet balance (`FetchWalletBalanceAsync`,
run in parallel with fetching the cart and config) and accepts a `WalletAmount` as one of up to
three payment components alongside cash and online payment — see the parent
`CustomerCart.technical.md`'s checkout gauntlet. The actual debit/validation logic for that amount
lives inside `Order.CreateOrderFromCustomerCart` (Order & Fulfilment feature, not yet documented).

## PaymentMethod (`TalabatkAPIs/Controllers/PaymentMethod/PaymentMethodController.cs`)
One endpoint: `GetAllPaymentMethodsByAddress` → `GetAllPaymentsByAddressQuery` — which payment
methods are available for a given delivery address (implies some methods are geographically or
merchant-restricted; not verified further in this pass).

## Rule / Decision Matrix

The wallet balance a customer can spend, and the payment methods offered at their address. Both looked thin from the controller side; the rules are one layer down, in the query handlers — which is also where the answers to this note's two long-standing open questions turn out to be.

| # | Rule | Where | Notes |
|---|---|---|---|
| 1 | **The wallet balance is not stored anywhere** — it is computed on every read | `Shared/TalabatkApplication/Queries/GetCustomerWalletQuery/GetCustomerWalletBalanceQuery.cs:45-46` | Credits minus debits: `Where(t => !t.Withdrawal).Sum()` less `Where(t => t.Withdrawal).Sum()`. This answers the question this note carried for weeks — there is no balance column to reconcile, and no balance to corrupt; a wrong balance means a wrong transaction row |
| 2 | Direction is the `Withdrawal` flag, not the sign of the amount | `Shared/TalabatkLogic/TalabatkModels/WalletTransaction.cs:30` | So a negative amount on a withdrawal row double-negates, and nothing prevents it — see [[WalletTransaction\|WalletTransaction]] |
| 3 | A posted transaction stays editable | `Shared/TalabatkLogic/TalabatkModels/WalletTransaction.cs:58` | `UpdateWalletAmount` is an unguarded `void`, and because the balance is a live sum, editing a row silently restates the balance |
| 4 | Payment methods are filtered by the **country of the address**, not by the address itself | `Shared/TalabatkApplication/Queries/GetAllPaymentsByAddressQuery/GetAllPaymentsByAddressQuery.cs:34-40` | The address resolves to a city, the city to a country, and the country to `PaymentMethodCountries`. That is the answer to the second open question: nothing is per-address, the address is just how the country is discovered |
| 5 | `activeOnly` narrows the list to active methods | `Shared/TalabatkApplication/Queries/GetAllPaymentsByAddressQuery/GetAllPaymentsByAddressQuery.cs:43` | Defaulted true by the controller |
| 6 | Cash is excluded by name comparison, not by id | `Shared/TalabatkApplication/Queries/GetAllPaymentsByAddressQuery/GetAllPaymentsByAddressQuery.cs:52` | A `EnglishName != CashPayment` string match — so renaming the cash method in the admin screen changes which methods are offered |
| 7 | OnlineWallet is excluded by enum id | `Shared/TalabatkApplication/Queries/GetAllPaymentsByAddressQuery/GetAllPaymentsByAddressQuery.cs:55` | The same query filters one method by name and another by hard-coded enum value — the two halves of 🟡 #632 in a single method |
| 8 | The address id is taken from the request and never checked against the caller | `Shared/TalabatkApplication/Queries/GetAllPaymentsByAddressQuery/GetAllPaymentsByAddressQuery.cs:70-72` | 🔴 `_idor-instances.md` instance 27 — `CustomerId` is present on the request and never used. The leak is limited to which payment methods a country offers, which is why it is recorded as low impact rather than dropped |
| 9 | Both wallet endpoints are read-only passthroughs | `TalabatkAPIs/Controllers/Wallet/WalletController.cs:33` | `GetBalance` and `GetMyWelletTransaction` (misspelt) — no mutation is exposed on this host at all |

> **Where the balance actually moves**, since this note previously could not say: nowhere in this
> feature. Every credit and debit is a `WalletTransaction` row written by another path — order
> checkout, the PayMob refund callback, a compensation switched to wallet, or the IRecycle partner
> webhook. The wallet is a projection of that ledger, so "who changed my balance" is always answerable
> from `WalletTransaction.CreatedBy` and `Type`.

## Open Questions
- [ ] Where wallet balance is actually credited/debited was not found in this pass — needed before
  this note could honestly claim full coverage of Wallet as a concept.
- [ ] Why `GetAllPaymentMethodsByAddress` varies by address (online-payment support per
  restaurant/city? per delivery zone?) was not investigated.

## Related
- [[CustomerCart.technical|CustomerCart]] — where `WalletAmount`/`PaymentOnlineAmount`/`CashAmount` are combined at checkout.
