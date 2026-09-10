---
id: 8orders/customer-ordering/payments/paymob-technical
note_type: technical
rule_count: 14
context: Customer Ordering
feature: Payments
sources:
  - path: AdminUi/Controllers/Order/OrderController.cs
    sha1: 934f4250495d
  - path: AdminUi/appsettings.json
    sha1: 8510ab3fc024
  - path: Shared/TalabatkApplication/Commands/ChangePaymentOnlineStatusCommand/CaptureOnlinePaymentAfterPaidatBank.cs
    sha1: e3978ed3a3dc
  - path: Shared/TalabatkApplication/Commands/GenerateNewPayMobCardSessionCommand/GenerateNewPayMobCardSessionCommand.cs
    sha1: fba5bbd35aea
  - path: Shared/TalabatkApplication/Commands/PayMobCallBackCommand/PayMobCallBackCommand.cs
    sha1: 32e4413e4e02
  - path: Shared/TalabatkApplication/Commands/RefundOnlinePaymentCommand/RefundOnlinePaymentCommand.cs
    sha1: 51c136d3af61
  - path: Shared/TalabatkApplication/Commands/RegenerateURLCommand/RegenerateURLCommand.cs
    sha1: 04de9458b503
  - path: Shared/TalabatkApplication/Commands/SavePayMobCustomerCardTokenCommand/SavePayMobCustomerCardTokenCommand.cs
    sha1: bc106d32074b
  - path: Shared/TalabatkApplication/Helper/OnlinePaymentStrategies/OnlinePaymentStrategyFactory.cs
    sha1: e1939ded90ad
  - path: Shared/TalabatkApplication/Helper/OnlinePaymentStrategies/PayMobApplePaymentStrategy.cs
    sha1: 289c3e3ef34f
  - path: Shared/TalabatkApplication/Helper/OnlinePaymentStrategies/PayMobCreditCardPaymentStrategy.cs
    sha1: e8ac709b499b
  - path: Shared/TalabatkApplication/Helper/OnlinePaymentStrategies/PayMobSmartWalletPaymentStrategy.cs
    sha1: fb827192a21e
  - path: Shared/TalabatkApplication/Helper/OnlinePaymentStrategies/PaymentProcessingService.cs
    sha1: c2541744da09
  - path: Shared/TalabatkApplication/Helper/PayMobServices/PayMobServicesProvider.cs
    sha1: d79535b775e6
  - path: Shared/TalabatkApplication/Queries/GetAllPaymentMethodsQuery/GetAllPaymentMethodsQuery.cs
    sha1: c73823965a54
  - path: Shared/TalabatkApplication/Services/OnlinePaymentRefundService.cs
    sha1: 3fda660302d5
  - path: Shared/TalabatkData/Mapping/PayMobTransctionMap.cs
    sha1: 1b6010d4dd7f
  - path: Shared/TalabatkData/Migrations/20240110113745_payMobTransction.cs
    sha1: 9627b86a6820
  - path: Shared/TalabatkLogic/TalabatkModels/Order.cs
    sha1: a8504688c441
  - path: Shared/TalabatkLogic/TalabatkModels/OrderPayment.cs
    sha1: 10ce6c0d300f
  - path: Shared/TalabatkLogic/TalabatkModels/PayMobTransaction.cs
    sha1: 281f6da533b7
  - path: TalabatkAPIs/Controllers/Order/OrderController.cs
    sha1: 0cb6a66fdb8c
  - path: TalabatkAPIs/appsettings.json
    sha1: 13b918e5a078
  - path: TalabatkRestaurants/appsettings.json
    sha1: 26dfcca93fb6
last_updated: 2026-08-23
tags: [customer-ordering, payments, technical, backend-application]
---
# PayMob — Technical

> **Layer:** Backend-Application (payment strategies and commands under `Shared/TalabatkApplication`)
> + Backend-Domain (`Order`, `OrderPayment`, `PayMobTransaction` in `TalabatkLogic.TalabatkModels`)
> + Backend-API (`OrderController`'s callback/status endpoints in `TalabatkAPIs`, refund endpoint in
> `AdminUi`).
> **Context:** Customer Ordering (Payments) — the online-payment leg of checkout; also reachable
> from Admin for refunds (`AdminUi/Controllers/Order/OrderController.cs:169`).
> **Source Path:** `Shared/TalabatkApplication/Helper/PayMobServices/PayMobServicesProvider.cs`;
> `Shared/TalabatkApplication/Helper/OnlinePaymentStrategies/*`;
> `Shared/TalabatkApplication/Commands/{GenerateNewPayMobCardSessionCommand,PayMobCallBackCommand,RegenerateURLCommand,SavePayMobCustomerCardTokenCommand,RefundOnlinePaymentCommand,CallIntentionAPIForApplePayCommand}/*`;
> `Shared/TalabatkLogic/TalabatkModels/PayMobTransaction.cs`.
> **Last Updated:** 2026-08-21

## Business Rules

### Rule 1: Payment-method routing picks one of four strategies, three of them PayMob
- **Plain language:** Whether an order's online amount goes to PayMob at all — and if so, to the
  card, wallet, or Apple Pay flow — is decided once per payment request, before any provider call
  is made. Below a configured minimum, or with no online component at all, no strategy runs.
- **Source:** `PaymentProcessingService.ProcessPayment` (`PaymentProcessingService.cs:29-39`)
  returns an empty `OnlinePaymentSessionResult` with no provider call if there is no `Online`
  `OrderPayment` (`:29-33`) or its amount is below `configuration.MinimumOnlinePaymentAmount`
  (`:36-39`). Otherwise `OnlinePaymentStrategyFactory.GetPaymentStrategy`
  (`OnlinePaymentStrategyFactory.cs:30-50`) picks: the non-PayMob `CibPaymentStrategy` when
  `!paymentRequest.UsePayMob || !config.GetValue<bool>("ApplyPayMob")` (`:32-36`); else
  `PayMobApplePaymentStrategy` if `paymentRequest.ApplePay` (`:39-41`); else
  `PayMobSmartWalletPaymentStrategy` if `paymentRequest.PayWithPayMobWallet` (`:44-46`); else
  `PayMobCreditCardPaymentStrategy` (`:49`). Feature-flag keys (names only — booleans, not
  secrets): `PayMob:*` block, `ApplyPayMob` (`TalabatkAPIs/appsettings.json:112`),
  `ApplyPayMobWallet` (`TalabatkAPIs/appsettings.json:88`) — present as separate copies in
  `AdminUi/appsettings.json:76`+ and `TalabatkRestaurants/appsettings.json:50`+; not reconciled for
  drift across hosts in this pass.

### Rule 2: Only the card/wallet strategies register a PayMob order id on the order — Apple Pay doesn't
- **Plain language:** After a session is created, the order is normally updated with the id PayMob
  assigned it. Apple Pay's own provider call never returns that id, so an Apple Pay order is left
  without one — it relies on its own `IsApplePay` flag instead.
- **Source:** `PaymentProcessingService.ProcessPayment` calls the chosen strategy (`:53-55`), then
  `if (sessionResult.PayMobOrderId.HasValue) order.RegisterPayMobOrderId(...)` (`:62-66`).
  `PayMobCreditCardPaymentStrategy.ProcessPayment` (`PayMobCreditCardPaymentStrategy.cs:20-33`) and
  `PayMobSmartWalletPaymentStrategy.ProcessPayment` (`PayMobSmartWalletPaymentStrategy.cs:19-32`)
  both populate `PayMobOrderId` on the result from `GetPayMobPaymentUrl`/`InizializeWalletPayment`.
  `PayMobApplePaymentStrategy.ProcessPayment` (`PayMobApplePaymentStrategy.cs:19-32`) only
  populates `PublicKey`/`ClientSecret` from `ApplePayCreateIntention` — never `PayMobOrderId` — so
  `RegisterPayMobOrderId` is never invoked for a fresh Apple Pay session. `IsApplePay` is set once,
  at order creation (`Order.cs:2097`, inside `CreateOrderFromCustomerCart`), and is the only durable
  signal that the order is an Apple Pay order until/unless a card or wallet id is later registered.

### Rule 3: Registering a PayMob order id always clears the Apple Pay flag
- **Plain language:** Once an order gets a real PayMob order id from the card or wallet flow, it
  stops being treated as an Apple Pay order, regardless of how it started.
- **Source:** `Order.RegisterPayMobOrderId` (`Order.cs:1097-1107`) unconditionally sets
  `this.IsApplePay = false` (`:1100`) as a side effect of setting `PayMobRegisteredOrderId`.

### Rule 4: Confirmed bug — Apple Pay's session-regeneration exemption is dereferenced unguarded
- **Plain language:** Established finding — **`_conflicts.md` #355**. Regenerating a PayMob session
  (`GenerateNewPayMobSessionCommand`, defined in `GenerateNewPayMobCardSessionCommand.cs`) validates
  via `ValidateIfOrderCanGenerateNewSession`, whose gate at `:225` is
  `if (!order.PayMobRegisteredOrderId.HasValue && !order.IsApplePay) return Failure(...)` — an Apple
  Pay order passes precisely when its id is null (deliberate, since Rule 2 means it usually is).
  But `Handle` (`:41-215`) never checks `IsApplePay` itself, and when `OrderCardTransctions.Any()`
  is true it dereferences `order.PayMobRegisteredOrderId.Value` at `:184` unconditionally — an Apple
  Pay order that already has a non-wallet PayMob transaction row throws an unhandled
  `NullReferenceException` instead of a controlled error. The validator call site is `:54`; a
  sibling unguarded `OrderCardTransctions.FirstOrDefault().PayMobOrderId` sits at `:152`.
- **Source:** `GenerateNewPayMobCardSessionCommand.cs:54,152,184,225` (confirmed by direct read in
  this pass — line numbers match the conflict entry exactly, no drift since #355 was logged).

### Rule 5: Resuming an already-initialized session reuses a still-valid redirect URL; the same command has known bugs
- **Plain language:** Established finding — **`_conflicts.md` #95**. If the customer's existing
  PayMob redirect link hasn't expired, `RegenerateURLCommand` just hands it back; otherwise it asks
  PayMob for a fresh payment key and rebuilds the iframe URL. Two confirmed bugs sit in the same
  handler: the lookups for the order's online payment and its latest PayMob transaction are both
  unguarded `FirstOrDefault()`s that throw if either is missing, and the final save's result is
  captured but never checked before unconditionally reporting success.
- **Source:** `RegenerateURLCommand.cs:126` (`orderOnlinePaymet` unguarded), `:130`
  (`oldPayMobTransaction` unguarded), `:134-137` (reuse-if-not-expired branch), `:181-182` (rebuilt
  iframe URL, `PayMob:IFrameId` config, name only), `:187-189` (save result captured, never checked,
  `Success = true` returned regardless).

### Rule 6: The callback's HMAC authenticity check is real for card/wallet — and is skipped entirely for Apple Pay
- **Plain language:** This is the most important technical finding in this note, and was not
  previously logged in `_conflicts.md`. PayMob's webhook callback normally has its signature
  verified before the app trusts it. For a callback whose `source_data.sub_type` is `APPLE_PAY`,
  that verification — and the fallback re-check described in Rule 7 — is skipped outright,
  regardless of whether the computed HMAC actually matches. An Apple Pay callback with a wrong,
  missing, or forged HMAC is processed exactly like a verified one: it can capture, fail, or refund
  an order's online payment with no authenticity check at all.
- **Source:** `PayMobCallBackCommand.cs:77-84` — `compareHMacResult` is computed at `:78-80` via
  `payMobProviderServices.VerifyHmacForPayment(...)`; `isApplePay` is derived at `:82` from
  `request.CallBackData["source_data.sub_type"] == "APPLE_PAY"` (case-insensitive); the gate at
  `:84` is `if (!compareHMacResult && !isApplePay)` — when `isApplePay` is true, this whole block
  is bypassed unconditionally, whatever `compareHMacResult` was. The HMAC computation itself —
  `HMACSHA512` over the callback's field values concatenated in PayMob's fixed documented order,
  keyed with `PayMob:HMacSecret` (name only, not reproduced) — lives in
  `PayMobServicesProvider.VerifyHmacForPayment` (`PayMobServicesProvider.cs:626-673`, hash/compare
  at `:667-672`).

### Rule 7: On a non-Apple-Pay HMAC mismatch, the app falls back to asking PayMob directly before failing
- **Plain language:** For card/wallet callbacks only, a bad signature isn't immediately fatal — the
  app independently asks PayMob to confirm the transaction's real status before giving up.
- **Source:** `PayMobCallBackCommand.cs:86-100` — `payMobProviderServices.InquireTransactionByOrderDetails(authToken, payMobOrderToCheck, order.PayMobRegisteredOrderId.Value)`
  (`:89-91`); only if that inquiry also fails or reports non-success does the handler return
  `Result.Failure("HMac Verification Failed")` (`:96-100`). Note: `order.PayMobRegisteredOrderId.Value`
  is dereferenced here without a `HasValue` check (`:91`) — the same unguarded-nullable shape as
  Rule 4/#355's family, though this branch is only reached for non-Apple-Pay orders, which Rule 2
  says should always have the id set; not separately numbered as its own confirmed bug in this pass.

### Rule 8: Refund vs. void handling on the callback avoids double-crediting the customer's wallet
- **Plain language:** A "money came back" callback can mean either a genuine refund or a fee-free
  void, and the same callback can arrive more than once (e.g. echoing an admin-initiated refund).
  The handler checks multiple "already settled" markers before ever touching the wallet again.
- **Source:** `PayMobCallBackCommand.cs:113-120` (`isRefunded`/`isVoided` combined into
  `isReversed`); `:147-213` (rejected-order-and-paid branch: refund-failed comment at `:151-158` if
  not reversed, else checks `onlineRefundAlreadyProcessed`, `onlinePaymentAlreadyRefunded`,
  `order.IsOrderRefundedAfterReject`, `order.ExecutedRefundDestination == RefundExecutionDestination.Bank`
  at `:177-206` before choosing `ProcessFullRefundAsync` or `CompleteDirectBankRefundAsync`);
  `ProcessFullRefundAsync` (`:258-314`) re-checks `onlineRefundAlreadyProcessed` itself (`:262-270`)
  and bumps `order.SetVersion()` (`:309`) specifically so a concurrent admin refund conflicts on
  save rather than double-deducting the wallet.

### Rule 9: A card successfully tokenized during a PayMob payment is saved for reuse
- **Plain language:** When PayMob's callback reports a new saved-card token rather than a payment
  result, the app stores that card against the customer for future card payments.
- **Source:** `OrderController.cs:637-661` (`CallBack` action) — `callBackType.type == "TOKEN"`
  branch (`:643`) dispatches `SavePayMobCustomerCardTokenCommand` with the card id/token/masked
  PAN/subtype (`:646-654`). The handler (`SavePayMobCustomerCardTokenCommand.cs:30-70`) looks up
  the order by `PayMobOrderId` to find the owning customer (`:32-39`), then calls
  `customer.AddNewCard(...)` (`:50-55`) and checks the save result before returning
  (`:63-68` — this handler, unlike the ones in Rules 5/11, does check its save result).

### Rule 10: Admin-initiated refunds reverse the transaction directly with PayMob
- **Plain language:** A customer cannot request a PayMob refund themselves through this flow —
  refunding is a back-office action that calls PayMob's reversal API and only updates the order
  once PayMob confirms.
- **Source:** `AdminUi/Controllers/Order/OrderController.cs:169` (`Refund(RefundOnlinePaymentCommand ...)`)
  → `RefundOnlinePaymentCommand.cs:33-51` (`Handle`, loads the order with its `PayMobTransactions`
  and delegates to `IOnlinePaymentRefundService.TryConvertWalletRefundToBankAsync`) →
  `OnlinePaymentRefundService.cs:179` (`ReverseTransactionAsync(transactionIdResult.Value, onlineAmount)`,
  a second call site at `:372`) — on `refundResponse.success` the payment is marked refunded and the
  save result **is** checked (`:196-199`), unlike several of the callback/session paths above.

### Rule 11: Several PayMob save paths discard the save result and report success regardless (established finding family #72/#259)
- **Plain language:** Established finding — a repeat pattern already logged system-wide. In the
  webhook handler and the session-generation command specifically, a failed database save after a
  PayMob state change is not detected — the caller is still told the operation succeeded.
- **Source (current line numbers, confirmed by direct read; some have shifted a few lines from
  #72's original citation, presumably from later edits/rebases — same shape, re-cited here):**
  `PayMobCallBackCommand.cs:136,155,229,256,311,330` (six unchecked `SaveChangesAsyncWithResult`
  calls); `GenerateNewPayMobCardSessionCommand.cs:110,134` (plain `SaveChangesAsync`, no result
  captured at all) and `:192,212` (`SaveChangesAsyncWithResult`, result discarded);
  `PaymentProcessingService.cs:68` (established separately as **#259** — the session URL/PublicKey
  is already returned to the caller regardless of whether `RegisterPayMobOrderId`/`SetPaymentIndicator`
  actually persisted).

### Rule 12: The PayMob-wallet payment-methods lookup can throw if enum id 5 is ever renumbered (established finding #137)
- **Plain language:** Established finding. Whether PayMob's wallet appears in the payment-methods
  list depends on an in-memory lookup by a hardcoded id, dereferenced without a null-check.
- **Source:** `GetAllPaymentMethodsQuery.cs:71-72` — `typeof(PaymentMethods).List().FirstOrDefault(x => x.Id == 5)` then immediate `.Name`/`.Id` access, gated behind `query.UsePayMob && applyPayMobWallet`.

### Rule 13: The callback endpoint is intentionally anonymous; a separate status-check endpoint is anonymous too but doesn't trust the caller (established findings #374/#376)
- **Plain language:** Established findings. PayMob's webhook has to be reachable without
  authentication, since PayMob itself calls it. A different, unrelated endpoint that also lacks
  authentication was checked and found not to trust its caller's claimed payment status — it
  re-derives the truth from PayMob directly.
- **Source:** `TalabatkAPIs/Controllers/Order/OrderController.cs:631-637`
  (`[AllowAnonymous] PayMobProcessCallBack`, the real webhook — `#374` lists this as one of the
  intentionally-anonymous exceptions to the system's missing default-deny posture); a separate
  no-op `GET PaymentOnline/complete` action, also literally named `PayMobCallBack`, exists at
  `:460-471` and just returns `Ok()` — likely a browser redirect landing page, not further traced
  in this pass. `OrderController.cs:402-408` (`[AllowAnonymous] ChangePaymentOnlineStatus`) forwards
  to `CaptureOnlinePaymentAfterPaidatBank.cs:60-145`, whose PayMob branch calls
  `payMobProviderServices.InquireTransactionByOrderDetails(...)` at `:132` and derives `isPaid` from
  PayMob's answer, not the caller's `onlinePaymentStatusId` — `#376`'s conclusion that this is a
  resource-amplification/order-id-oracle issue rather than a payment bypass.

### Rule 14: PayMob's credentials are committed to `appsettings.json` in plaintext across hosts (established finding #347)
- **Plain language:** Established finding. Key names only — no values reproduced here.
- **Source:** `TalabatkAPIs/appsettings.json:62-72` (`PayMob:ApiKey`, `:IntegrationId`,
  `:WalletIntegrationId`, `:IFrameId`, `:HMacSecret`, `:ApplePayIntegrationId`,
  `:ApplePaySecrectkey`, `:ApplePayPublicKey`, `:PaymobAcceptanceURL`); the same key names
  (populated) also appear in `AdminUi/appsettings.json:76`+ and
  `TalabatkRestaurants/appsettings.json:50`+.

## Key Fields
| Field | Meaning | Constraints |
|-------|---------|--------------|
| `Order.PayMobRegisteredOrderId` (`int?`) | PayMob's own order id, once a card/wallet session is registered | Null is expected and valid for a fresh Apple Pay order (Rule 2); dereferencing it unguarded is the root of Rule 4/#355 |
| `Order.IsApplePay` (`bool`) | Marks the order as an Apple Pay checkout | Set once at creation (`Order.cs:2097`); cleared to `false` by `RegisterPayMobOrderId` (Rule 3) |
| `OrderPayment.PayWithPayMobWallet` (`bool`) | Whether this online payment is via PayMob's wallet | Set from `RegisterPayMobOrderId`'s `usePayMobWallet` argument (`Order.cs:1104`) |
| `OrderPayment.PayMobTransactions` (`IReadOnlyList<PayMobTransaction>`) | Every PayMob session/transaction attempt against this payment | 1 `OrderPayment` : many `PayMobTransaction` (`OrderPayment.cs:26-37`) |
| `PayMobTransaction.IsWallet` | Distinguishes a wallet transaction row from a card/Apple Pay one | Read via `.Where(x => x.IsWallet)` / `.Where(x => !x.IsWallet)` in `GenerateNewPayMobCardSessionCommand.cs:80,143` |
| `PayMobTransaction.IsInitiated`, `FailureStage`, `FailureReason`, `GatewayResponseCode`, `FailedAt` | Failure tracking for session-initiation and callback-decline failures | Null on non-failed rows; string fields truncated to column length (`PayMobTransaction.cs:137-142`) before saving |
| `PayMobTransaction.PayMobOrderId`, `TransactionId`, `RedirectUrl`, `AmountCents`, `ExpirationDate` | The session/transaction identity and its redirect link | `RedirectUrl`/`ExpirationDate` drive the resume-session reuse check in Rule 5 |
| `Customer.Cards` (via `AddNewCard`) | Saved/tokenized PayMob cards | Populated only through the webhook's `TOKEN` callback (Rule 9), not traced further in this pass |

## Dependencies & Integrations
| Depends on / integrates | Side/Context | Via | Notes |
|--------------------------|---------------|-----|-------|
| PayMob (external gateway) | External payment provider | HTTP, via `PayMobServicesProvider` | One class implements both `IPayMobProviderServices` and `IPayMobApplePayIntention` (`PayMobServicesProvider.cs:21`) — auth token, payment-key, wallet-init, refund/void/reverse, and HMAC verification all live together |
| [[Order.technical\|Order]] | Backend-Domain | `PayMobRegisteredOrderId`, `IsApplePay`, `ChangeOnlinePaymentStatusForPayMob` (`Order.cs:4390-4435`), `SetOnlinePaymentFailureDetails` (`:4444-4448`) | Shared entity — this note does not re-document Order itself |
| `OrderPayment` | Backend-Domain | Parent of `PayMobTransactions`, owns `PayWithPayMobWallet` | Not yet a dedicated note |
| `Customer` | Backend-Domain | `AddNewCard` (Rule 9) | |
| `WalletTransaction` | Backend-Domain | Refund/void paths credit or debit the wallet (`PayMobCallBackCommand.cs:242-256,286-294`; `OnlinePaymentRefundService.cs`) | |
| `CibPaymentStrategy` / `ICheckoutCreateSession` | Backend-Application | Sibling non-PayMob strategy, chosen when PayMob is off (`OnlinePaymentStrategyFactory.cs:34-36`) | AdminUi's implementation of this interface is a confirmed no-op stub — **#283** |
| [[Checkout-Payment-Processing\|Checkout Payment Processing]] | Backend-Domain/Application | First session creation during checkout | Documents the `CreateOrderFromCartCommand` half that calls into this payment flow |
| Configuration (`PayMob:*`, `ApplyPayMob`, `ApplyPayMobWallet`) | Config | `appsettings.json`, per host | Credentials committed in plaintext — **#347** |

## Change Surface
| Signal | Value | Notes |
|--------|-------|-------|
| Direct dependents (Ring 1) | 6+ | `GenerateNewPayMobSessionCommand`, `RegenerateURLCommand`, `PayMobCallBackCommand`, `SavePayMobCustomerCardTokenCommand`, `RefundOnlinePaymentCommand`, `PaymentProcessingService`/`OnlinePaymentStrategyFactory` |
| Sides touched | 4/5 confirmed | Backend-Application, Backend-Domain, Backend-API, Config — Backend-Data not opened in this pass (`PayMobTransctionMap.cs` exists but wasn't read) |
| Cross-context integrations | 1 confirmed | Admin's refund action (`AdminUi/Controllers/Order/OrderController.cs:169`) reaches into Customer Ordering's payment domain |
| Domain events involved | 1 | `WantToRejectOrderAfterPaymentProcessEvent` (`Order.cs:4424-4430`), raised when a PayMob callback reports a failed payment |
| Hub? | no | An external-provider integration, not a shared master entity — but touches `Order`/`OrderPayment` on nearly every checkout and payment-status path |

## Related
- Business view: [[PayMob.business|PayMob]]
- [[Order.technical|Order]] — holds the fields and state transitions this note documents
- [[Checkout-Payment-Processing|Checkout Payment Processing]] — where a session is first created
- [[Wallet-and-PaymentMethod|Wallet & PaymentMethod]] — wallet side of refunds
- `_conflicts.md` — **#355** (Rule 4), **#95** (Rule 5), **#72**/**#259** (Rule 11), **#137** (Rule
  12), **#374**/**#376** (Rule 13), **#347** (Rule 14), **#383** (this note fills that gap)

## Open Questions
- [ ] Rule 6 (Apple Pay callback skips HMAC verification entirely) was not previously logged in
  `_conflicts.md` — worth its own numbered entry given it's a live, effectively-unauthenticated
  payment-state write path.
- [ ] `order.PayMobRegisteredOrderId.Value` dereferenced unguarded at `PayMobCallBackCommand.cs:91`
  (Rule 7) — same shape as #355's family; not separately confirmed as reachable since non-Apple-Pay
  orders should always have the id set per Rule 2.
- [ ] `PayMobTransctionMap.cs` (`Shared/TalabatkData/Mapping/`) and migration
  `20240110113745_payMobTransction.cs` weren't opened — the column-length truncation in
  `PayMobTransaction.cs:137-142` wasn't cross-checked against actual DB column sizes.
- [ ] Whether the per-host `PayMob:*` config blocks (AdminUi, TalabatkAPIs, TalabatkRestaurants) are
  kept in sync, or can silently drift — not reconciled in this pass.
- [ ] `IPayMobApplePayIntention`'s request-building internals (`BuildIntentionRequestAsync`,
  `SendIntentionRequestAsync` in `PayMobServicesProvider.cs`) weren't traced line-by-line.
- [ ] The no-op `GET PaymentOnline/complete` action at `OrderController.cs:460-471` (also named
  `PayMobCallBack`) — its actual role (redirect landing page vs. dead code) wasn't traced.
