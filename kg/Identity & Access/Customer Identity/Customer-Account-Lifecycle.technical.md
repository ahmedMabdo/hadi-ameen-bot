---
id: 8orders/identity-and-access/customer-identity/customer-account-lifecycle-technical
note_type: technical
context: Identity & Access
feature: Customer Identity
sources:
  - path: AdminUi/Controllers/CustomerController/CustomerController.cs
    sha1: 54a6cd2065b5
  - path: Shared/TalabatkApplication/Commands/AddCustomerWalletFromIRecycleRedeemsCommand/AddCustomerWalletFromIRecycleRedeemsCommand.cs
    sha1: 25ad3521aa17
  - path: Shared/TalabatkApplication/Commands/AddNewCartItemCommand/AddNewCartItemCommand_V1.cs
    sha1: 48c497cb1c32
  - path: Shared/TalabatkApplication/Commands/AddNewCompensationCommand/AddNewCompensationCommand.cs
    sha1: 004a38a778bc
  - path: Shared/TalabatkApplication/Commands/ChangeCartItemQuantityCommand/ChangeCartItemQuantityCommand.cs
    sha1: 872b006b0f20
  - path: Shared/TalabatkApplication/Commands/ClearCustomerCartCommand/ClearCustomerCartCommand.cs
    sha1: f22901f0e395
  - path: Shared/TalabatkApplication/Commands/DeleteCartItemCommand/DeleteCartItemCommand.cs
    sha1: c3951268d4b4
  - path: Shared/TalabatkApplication/Commands/DeleteCustomerCommand/DeleteCustomerCommand.cs
    sha1: 28d7576044f7
  - path: Shared/TalabatkApplication/Commands/EditCartItemCommand/EditCartItemCommand.cs
    sha1: 05f3af04a1f0
  - path: Shared/TalabatkApplication/Commands/MangeCustomerActivationFromAdminCommand/MangeCustomerActivationFromAdminCommand.cs
    sha1: 909a84d98818
  - path: Shared/TalabatkApplication/Commands/MangeCustomerBlockingForAdminCommand/MangeCustomerBlockingForAdminCommand.cs
    sha1: 17d7477125ab
  - path: Shared/TalabatkApplication/Commands/MergeGuestCartIntoCustomerCommand/MergeGuestCartIntoCustomerCommand.cs
    sha1: 08634d0387d9
  - path: Shared/TalabatkApplication/Commands/PurgeAbandonedGuestCustomersCommand/PurgeAbandonedGuestCustomersCommand.cs
    sha1: ab7070313d56
  - path: Shared/TalabatkApplication/Commands/UpdateCompensationStateCommand/UpdateCompensationStateCommand.cs
    sha1: 7dc1b3655d34
  - path: Shared/TalabatkApplication/Commands/UpdateCustomerAddressCommand/UpdateCustomerAddressCommand.cs
    sha1: 2df348aae4aa
  - path: Shared/TalabatkApplication/Commands/UpdateCustomerUnavailableItemsPreferenceCommand/UpdateCustomerUnavailableItemsPreferenceCommand.cs
    sha1: 1290d1c91af8
  - path: Shared/TalabatkApplication/DomainEventsHandlers/OrderEventsHandlers/FirstCustomerOrderReferralEventHandler.cs
    sha1: 3487bad70955
  - path: Shared/TalabatkApplication/Feature/Complaints/Commands/SaveOrderComplaintCommand.cs
    sha1: 3288dfbfcf94
  - path: Shared/TalabatkApplication/Queries/GetConfigurationQuery/GetServiceFeesConfigurationQuery.cs
    sha1: 6d3496022c94
  - path: Shared/TalabatkApplication/Queries/GetCustomerCartQuery/GetCustomerCartQuery.cs
    sha1: 1f643c779087
  - path: Shared/TalabatkApplication/Queries/GetMaxDeliveryFeesWithServicesFeesQuery/GetMaxDeliveryFeesWithServicesFeesQuery.cs
    sha1: 960c3f219372
  - path: Shared/TalabatkApplication/Queries/GetUpsellingItemsIntoCartQuery/GetUpSellingItemsIntoCart.cs
    sha1: 8c58d4cd522f
  - path: Shared/TalabatkApplication/Services/GuestCustomerResolver/IResolveGuestCustomerService.cs
    sha1: 32894f28bb55
  - path: Shared/TalabatkApplication/Services/GuestCustomerResolver/ResolveGuestCustomerService.cs
    sha1: 03427d4e316d
  - path: Shared/TalabatkData/Services/PhoneValidatorService.cs
    sha1: ebe91c58beac
  - path: Talabatk.IDS/Application/Commands/ActivateCustomerV2Command/ActivateCustomerV2Command.cs
    sha1: 0582b34dba5b
  - path: Talabatk.IDS/Application/Commands/CompleteCustomerRegistrationCommand/CompleteCustomerRegistrationCommand.cs
    sha1: 0b09426afa70
  - path: Talabatk.IDS/Application/Commands/RegisterCustomerV2Command/RegisterCustomerV2Command.cs
    sha1: f480da554257
  - path: Talabatk.IDS/Application/Commands/SendCustomerOtpCommand/SendCustomerOtpCommand.cs
    sha1: 08c25b5bfa24
  - path: Talabatk.IDS/Application/Commands/SendCustomerOtpCommand/SendOtpRequest.cs
    sha1: dcf5ae0ca3bb
  - path: Talabatk.IDS/Controllers/CustomerController.cs
    sha1: f2a016cb6aa3
  - path: Talabatk.IDS/CustomerIdentityProfileService.cs
    sha1: 50f1db0f2635
  - path: Talabatk.IDS/CustomerResourceOwnerValidator.cs
    sha1: 949797e366d7
  - path: Talabatk.IDS/OtpGrantValidator/OtpCustomerGrantValidator.cs
    sha1: 6419cf4db2c4
  - path: TalabatkAPIs/Controllers/Cart/CartController.cs
    sha1: 400452213f9f
  - path: TalabatkAPIs/Controllers/CustomerUser/CustomerUserController.cs
    sha1: fc15a3e7f335
  - path: TalabatkAPIs/Controllers/Wallet/WalletController.cs
    sha1: e76da84651f6
last_updated: 2026-08-23
tags: [flow, technical]
---
# Customer Account Lifecycle — Technical

End-to-end trace of a customer identity from first anonymous cart touch through registration,
guest-merge, everyday self-service, and deactivation/deletion. Bridges to
[[Customer.technical|Customer]], [[CustomerAddress.technical|CustomerAddress]],
[[Identity.technical|Identity]], [[Permission.technical|Permission]] and
[[Login-and-Activation|Login & Activation]] rather than restating them — only the pieces of those
notes load-bearing for *this* flow are repeated here.

## Trigger
No single trigger — this is a multi-entry lifecycle:
- Any unauthenticated cart-touching request (first app use) — spawns a provisional guest identity.
- `POST api/Customer/SendOTP` — requests a verification code, for either registration or login.
- `POST connect/token` (`grant_type=otp`), `POST api/Customer/CompleteRegistration`, or
  `POST api/Customer/RegisterV2` — the three converging paths that turn a phone number into a live
  session.
- `POST AdminUi .../MangeCustomerActivation` / `.../MangeCustomerBlocking` — staff-initiated.
- `POST api/CustomerUser/DeleteCustomer` — customer-initiated.
- A recurring Hangfire job — abandoned-guest cleanup (schedule/registration site not traced in this
  pass).

## Step-by-step

### 1. Pre-registration token (not fully traced)
Cart endpoints require `[Authorize(JwtBearer)]` at the controller level (e.g.
`TalabatkAPIs/Controllers/Cart/CartController.cs:31`), yet the resolved customer id defaults to `0`
whenever the JWT carries no `customerId` claim
(`TalabatkAPIs/Helper/Middlewares/SessionInfoHandlerMiddleware.cs:26,48`). So guest usage runs on a
bearer token that authenticates the *app*, not a customer — which OAuth grant/client issues that
token is not traced in this pass.

### 2. Guest browsing → provisional Customer creation
Trigger: the first cart-touching request with resolved customer id `0` plus a client-supplied
`guestDeviceId`. Called identically from `AddNewCartItemCommand_V1.cs:67`,
`ChangeCartItemQuantityCommand.cs:52`, `ClearCustomerCartCommand.cs:33`, `DeleteCartItemCommand.cs:39`,
`EditCartItemCommand.cs:78`, `GetCustomerCartQuery.cs:52`, `GetServiceFeesConfigurationQuery.cs:43`,
`GetMaxDeliveryFeesWithServicesFeesQuery.cs:57`, `GetUpSellingItemsIntoCart.cs:41`,
`UpdateCustomerUnavailableItemsPreferenceCommand.cs:39` (all `Shared/TalabatkApplication/...`) into
`IResolveGuestCustomerService.ResolveAsync` (`Shared/TalabatkApplication/Services/GuestCustomerResolver/IResolveGuestCustomerService.cs:12`).

- `ResolveGuestCustomerService.ResolveAsync` (`ResolveGuestCustomerService.cs:32-97`): an already
  non-zero customer id short-circuits (`:36-39`); otherwise a `guestDeviceId` is required (`:41-45`).
- Existing guest for that device (`:47-80`): reused, self-healing a missing/incomplete default
  address via `EnsureDefaultAddressAsync` (`:237-324`).
- No existing guest, location supplied: `CreateGuestAsync` (`:138-230`) runs one DB transaction that
  inserts `Customer.Guest(deviceId, currentCity:1, now)` plus a default `CustomerAddresses` row
  resolved by a point-in-polygon lookup against `Area.AreaBorder` (`:339-360`) — both commit or
  neither does.
- Concurrency: `DeviceId` carries a filtered unique index `WHERE IsGuest=1`
  (bridge [[Customer.technical|Customer]] Rule 3); a lost insert race re-queries for the
  winner instead of failing (`:117-131`, `:205-229`).
- Design rationale: `TalabatkAPIs/docs/adr/0001-guest-mode-provisional-customer.md` — chose this
  backend-owned "Approach B" specifically so a price-tier discount stays locked to one cart across
  the guest→login transition; a client-only local cart had no durable anchor for that lock.
- **#341 bites here:** guest creation is keyed solely on a client-supplied `guestDeviceId` with no
  per-device/per-IP limit, despite the ADR's explicit "Consequences" section mandating one. The only
  bound is the 24h purge (step 7).
- Identity at this point: `IsGuest=true`, `Active=false`, no phone, notifications disabled (bridge
  Customer Rule 1). The guest carries the app-level bearer token from step 1 plus its own
  client-generated `DeviceId` — enough to browse, build a multi-restaurant cart, set a delivery pin,
  and lock a tiered discount, but not enough for any authenticated-only screen.

### 3. OTP request
`POST api/Customer/SendOTP`, `[AllowAnonymous]`
(`Talabatk.IDS/Controllers/CustomerController.cs:166-186`) → `SendCustomerOtpCommand.Handle`
(`Talabatk.IDS/Application/Commands/SendCustomerOtpCommand/SendCustomerOtpCommand.cs:44-94`).

- Branches on the `OtpLoginOrRegister` feature flag (`:47`): legacy mode rejects any unregistered
  number outright (`:61-69`, OTP is login-only); unified mode instead validates the phone/country
  code (`:53-59`) and lets an unregistered number through, since the same code doubles as a
  registration OTP.
- Either mode rejects a soft-deleted account (`:73-80`).
- On acceptance: `BackgroundJob.Enqueue<SendOtpDeliveryJob>` (`:82-83`) — the actual SMS/WhatsApp send
  is not traced in this pass.
- **#429 bites here:** `SendOtpRequest.CountryCode` defaults to `""`
  (`Talabatk.IDS/Application/Commands/SendCustomerOtpCommand/SendOtpRequest.cs:8`); in unified mode
  it reaches `PhoneValidatorService.Validate` (`SendCustomerOtpCommand.cs:55`) whose
  `int.Parse(countryDialCode.Replace("+",""))` (`Shared/TalabatkData/Services/PhoneValidatorService.cs:14`)
  throws `FormatException` unguarded — an unhandled 500 on a public, pre-auth endpoint for any
  request that simply omits the field.
- Context for why this step matters at all: **#407** (confirmed, now fixed) previously let any
  authenticated admin-portal user read a customer's *live* OTP value back out through an unrelated
  admin query — cited here only to establish that OTP is a genuine authentication factor, not a
  delivery-status notification; not re-investigated.

### 4. OTP verification — three converging entry points
**4a. Direct grant** — `POST connect/token`, `grant_type=otp` →
`OtpCustomerGrantValidator.ValidateAsync`
(`Talabatk.IDS/OtpGrantValidator/OtpCustomerGrantValidator.cs:46-145`):
- Unknown phone (`:64-98`): peeks the OTP (`consume:false`, `:79`) so a wrong/expired code still just
  says "invalid," but a *correct* code on an unknown number returns a custom `registration_required`
  error code (`:93-96`) — OTP stays unconsumed, handed to step 5.
- Known phone, inactive (`:100-108`) or blocked (`:110-118`): rejected before the OTP is touched —
  neither attempt spends the code.
- Known phone, active, unblocked (`:120-131`): the one path that actually consumes the OTP
  (`ValidateOtpAsync(phone, otp)`, default `consume:true`). On success: triggers the guest-cart merge
  (step 6, `:135`) then issues the token (`:141-144`) **regardless of whether that merge succeeded**.

**4b. Unified registration** — `POST api/Customer/CompleteRegistration` →
`CompleteCustomerRegistrationCommand.Handle`
(`Talabatk.IDS/Application/Commands/CompleteCustomerRegistrationCommand/CompleteCustomerRegistrationCommand.cs:65-153`):
- Peeks the OTP first, non-consuming (`:73`) — a wrong code fails before any account exists
  (`:74-93`), disambiguating "wrong OTP" from "a second device already finished registering this
  phone" by checking whether the phone now has an account.
- On a valid peek, calls `RegisterCommand` (step 5) with `SendOtpAfterRegister=false` (`:97-108`).
- Then re-exchanges that same still-valid, still-unconsumed OTP for a token via its own
  `connect/token` call with `grant_type=otp` (`:122-139`) — i.e. it recurses into 4a, which is where
  the OTP is actually consumed and the guest merge actually fires.

**4c. Classic path** — `POST api/Customer/RegisterV2` directly (no OTP check inside that handler at
all, see step 5), followed later by `POST api/Customer/ActivateUserV2` →
`ActivateCustomerV2Command.Handle`
(`Talabatk.IDS/Application/Commands/ActivateCustomerV2Command/ActivateCustomerV2Command.cs:33-62`),
which independently validates the OTP (`:45-46`) and calls `user.ActivateUser()` (`:54`).

### 5. Registration — `RegisterCustomerV2Command.Handle`
`Talabatk.IDS/Application/Commands/RegisterCustomerV2Command/RegisterCustomerV2Command.cs:68-216`,
reached from both 4b and 4c.
- Validates phone format (`:70-75`), rejects an already-registered non-deleted number (`:78-81`).
- Branches on whether `GuestDeviceId` resolves to an existing guest row (`:106-123`):
  - **Promotion** (same device, bridge Customer Rule 4): `guestToPromote.PromoteFromGuest(...)`
    (`:130-137`) mutates that row in place — same primary key, cart/addresses already attached, no
    merge needed. Sets `IsGuest=false`, calls `MangeCustomerActivation(active:true)` internally.
  - **Fresh row**: `Customer.Instance(...)` (`:153-167`), then immediately
    `newUser.MangeCustomerActivation(active: true)` (`:169`) — *before* `SaveChanges` and *before*
    any OTP is checked by this handler.
- Non-Egypt country codes also insert a `BlockedUsersFromCOD` row (`:181-188`) — COD denied by
  default outside Egypt.
- `SaveChangesAsyncWithResult()` (`:194`) persists whichever branch ran.
- If `SendOtpAfterRegister` (default `true`, only actually `true` on the classic path 4c): enqueues
  the OTP-send job (`:208-212`) — meaning on the classic path the account is already
  `Active=true`/`PhoneNumberConfirmed=true` *before* its own verification code has even been sent.
- **Self-traced, not in `_conflicts.md`:** both branches activate before any OTP is verified in this
  handler. On the classic path (4c) specifically, the documented "registered creation starts
  unverified" lifecycle (bridge Customer Rule 2) does not hold in practice — the account is fully
  active by the time `ActivateUserV2` is ever called, leaving `ActivateCustomerV2Command`'s
  `ActivateUser()` (which additionally clears `IsNewCustomer`, Customer Rule 8) as its only remaining
  effect. Exposure is bounded — a login token still needs the correct OTP via the `otp` grant (4a) or
  a password nobody has set on this account yet — but the activation flag is not a "phone verified"
  signal on this path.

### 6. Guest→registered merge (Rule 5 — only when logging into a *pre-existing different* account)
Triggered identically from `OtpCustomerGrantValidator.TryMergeGuestCartAsync`
(`OtpCustomerGrantValidator.cs:147-198`) and from the password-grant path
(`Talabatk.IDS/CustomerResourceOwnerValidator.cs:159-192`, same "CART-MERGE-TRACE (password)"
shape) → `MergeGuestCartIntoCustomerCommand.Handle`
(`Shared/TalabatkApplication/Commands/MergeGuestCartIntoCustomerCommand/MergeGuestCartIntoCustomerCommand.cs:50-399`):
- **Preference carried over first** (`:72-76`, `:409-445`) — only if the guest's
  `UnavailableItemsPreference` is non-default, since every guest starts at `SuggestAlternatives` and
  an unconditional copy would clobber a returning customer's real setting.
- **Cart — guest replaces, not merges** (`:104-162`): the real customer's existing cart is cleared in
  place (`ClearCustomerCart`/`ClearLockedDiscount`) and discarded, not combined. Guest items are
  re-added one by one via `CustomerCart.AddItem` after re-resolving each item's live
  Restaurant/MenuItem/Price/Offer graph (`:180-281`) — deliberately skipping the normal add-to-cart
  validation gauntlet (stock, hours, offer validity), since this is a data move, not a fresh add;
  those checks still run for real at checkout. The guest's locked tiered discount carries over too
  (`:283-290`).
- **Address — also replaces, as new rows** (`:292-371`): guest addresses are copied as brand-new rows
  owned by the real customer (not renamed); an existing default on the real customer is cleared first
  if the guest had one (`:309-328`, preserving the one-default invariant), then the guest's own rows
  are deleted.
- Guest cart and guest `Customer` row are deleted at the end (`:373-379`) inside the same
  `SaveChangesAsyncWithResult()` (`:385`) as everything above — one atomic save.
- **Not carried over, traced in this pass:** wallet balance and loyalty points. Neither
  `WalletTransaction` nor `LoyaltyPoints` is referenced anywhere in this handler — either table, if a
  guest row somehow held one, would simply be deleted with the guest `Customer` row with no transfer.
  Not confirmed to occur in practice (see Open Questions).
- **Self-traced, not in `_conflicts.md`:** merge failure is not fatal to login. Both call sites
  (`OtpCustomerGrantValidator.cs:186-191` and the password-grant equivalent) only log
  `mergeResult.IsFailure` — the token is issued unconditionally afterward (`:141`). A customer whose
  guest cart/address fails to merge (e.g. a restaurant/menu item vanished between guest session and
  login, per the `Result.Failure` returns at `:193-229`) still logs in successfully, silently losing
  that in-progress guest cart with no client-visible error.

### 7. Abandoned-guest purge
Recurring Hangfire job (registration/schedule not located in this pass) →
`PurgeAbandonedGuestCustomersCommand.Handle`
(`Shared/TalabatkApplication/Commands/PurgeAbandonedGuestCustomersCommand/PurgeAbandonedGuestCustomersCommand.cs:28-67`).
Selects every `IsGuest` row with `RegisterationDate <= now-24h` (`:30-38`, matches the ADR's mandated
window) and deletes its cart, addresses, and the row itself in one save (`:45-66`) — the only
after-the-fact bound on #341.

### 8. Wallet — no self-service top-up exists
`TalabatkAPIs/Controllers/Wallet/WalletController.cs` exposes only `GetBalance` (`:28-54`) and
`GetMyWelletTransaction` (`:60-87`), both reads, both `[Authorize(Roles="Customer")]`. Every
`WalletTransaction.Instance(...)` write site traced in this pass credits the wallet as a *side
effect* of something else, never a direct customer action: online-payment refunds
(`OnlinePaymentRefundService.cs:277,389`), order-level refunds/adjustments (`Order.cs:1937,1982,3036,
3813,3828,3847,4787`), PayMob callback refunds (`PayMobCallBackCommand.cs:247,291`),
delivery/complaint compensation (`AddNewCompensationCommand.cs:154`,
`UpdateCompensationStateCommand.cs:103`, `SaveOrderComplaintCommand.cs:546`), first-order referral
bonus (`FirstCustomerOrderReferralEventHandler.cs:91`), and third-party point redemption
(`AddCustomerWalletFromIRecycleRedeemsCommand.cs:50`). Bridge
[[WalletTransaction|WalletTransaction]] for the ledger row itself.

### 9. Profile and address self-service
Handled in full on the bridged entity notes. **#400 bites specifically here:**
`UpdateCustomerAddressCommand.cs:47` looks an address up by id alone (no ownership check) and writes
the caller's own `CustomerId` onto whatever row it finds (`:63`) — supplying another customer's
address id both destroys their address and re-homes it onto the caller's account. The broader IDOR
cluster on address handlers (#227, #366, #365, #350) is documented in full on
[[CustomerAddress.technical|CustomerAddress]] Rule 4 — cited, not restated.

### 10. Admin-driven activation / blocking
`AdminUi/Controllers/CustomerController/CustomerController.cs:216-232` (`MangeCustomerActivation`)
and `:279-295` (`MangeCustomerBlocking`), both gated by the single coarse-grained
`[Permission(Permissions.Customers.Customer)]` attribute (bridge
[[Permission.technical|Permission]] Rule 1 for the enforcement mechanism) — the same
permission covers activation, blocking, profile edits, and address edits on this screen, with no
finer split.
- `MangeCustomerActivationFromAdminCommand.Handle`
  (`Shared/TalabatkApplication/Commands/MangeCustomerActivationFromAdminCommand/MangeCustomerActivationFromAdminCommand.cs:26-44`)
  → `customer.MangeCustomerActivation(request.Active)` — does not touch `IsNewCustomer` (bridge
  Customer Rule 8, by design).
- `MangeCustomerBlockingForAdminCommand.Handle`
  (`Shared/TalabatkApplication/Commands/MangeCustomerBlockingForAdminCommand/MangeCustomerBlockingForAdminCommand.cs:28-51`)
  requires a non-blank `BlockReason` when blocking (`:35-38`), then `MangeCustomerBlocking(...)` +
  `SetBlockingReason(...)`.
- Effect on a live session: login-time `ValidateAsync` checks `IsBlocked` for the `mobile` client
  (bridge [[Login-and-Activation|Login & Activation]]), and the per-request `IsActiveAsync` mobile
  branch also re-checks it (`Talabatk.IDS/CustomerIdentityProfileService.cs:239-251`) — blocking cuts
  off a live token on the very next request, not just the next login. That same branch checks only
  `IsBlocked` and `!PhoneNumberConfirmed` — `Active` is not one of its conditions, so a bare
  `MangeCustomerActivation(false)` against an otherwise `PhoneNumberConfirmed` account is not
  confirmed to revoke an already-issued token (see Open Questions).

### 11. Self-service deletion
`POST api/CustomerUser/DeleteCustomer`, `[Authorize(Roles="Customer")]`, no id parameter — always the
caller's own account (`sessionInfo.CusomerId`,
`TalabatkAPIs/Controllers/CustomerUser/CustomerUserController.cs:811-823`) →
`DeleteCustomerCommand.Handle`
(`Shared/TalabatkApplication/Commands/DeleteCustomerCommand/DeleteCustomerCommand.cs:28-51`) →
`customer.DeleteAccount(index)` (bridge Customer Rule 7): sets `Deleted=true`, suffixes
`PhoneNumber`/`UserName`/`NormalizedUserName` with `_Delete{index}`. Neither `Active` nor
`PhoneNumberConfirmed` is touched.
- **Self-traced, not in `_conflicts.md`:** `IsActiveAsync`'s `mobile`/`TalabatkExternalTool` branch
  (`CustomerIdentityProfileService.cs:229-251`) checks only `IsBlocked` and `!PhoneNumberConfirmed` —
  never `Deleted` — unlike the login-time `ValidateAsync` check, which does (bridge
  [[Login-and-Activation|Login & Activation]]'s comparison table: "Deleted, PhoneNumberConfirmed &&
  Active, IsBlocked"). Since deletion leaves `PhoneNumberConfirmed=true`, an already-issued token
  stays fully valid on every request until it naturally expires (`TokenLifeTime`, 3h — bridge
  [[Identity.technical|Identity]] Rule 4) or is refreshed — deleting your own account does
  not revoke your current session.
- Cart, addresses, wallet transactions, and loyalty points are left untouched — nothing here
  parallels step 7's cleanup. They persist under the now-suffixed row indefinitely.

## Data written
In rough chronological order across this flow:
1. `TA_Customer` — insert (guest, step 2; new registration, step 5); update in place (guest
   promotion, step 5; activation/blocking, step 10; deletion, step 11).
2. `TA_CustomerAddresses` — insert (guest default address, step 2); self-heal update (step 2);
   insert-copy + delete (guest-merge, step 6); delete (purge, step 7); update (self/admin edit,
   step 9).
3. `TA_CustomerCart` / cart-item tables — cleared and re-populated on merge (step 6, existing rows
   discarded, guest rows re-created via `AddItem`); deleted on purge (step 7). Initial cart-row
   creation on first add-to-cart is not opened in this pass beyond the merge-time
   `CustomerCart.InizaializeCart` call (`MergeGuestCartIntoCustomerCommand.cs:138-142`).
4. `TA_BlockedUsersFromCOD` — insert on non-Egypt registration (step 5).
5. `WalletTransaction` / `LoyaltyPoints` — not written by any step in this flow itself; both are
   written only by the side-effect flows listed in step 8 and by order/loyalty flows out of scope
   here.

## External calls
- Hangfire background job `SendOtpDeliveryJob.SendOtpDelivery` (steps 3 and 5's classic path) — the
  actual SMS/WhatsApp delivery is not opened in this pass.
- Self-referential HTTP call: `CompleteCustomerRegistrationCommand` POSTs to its own `connect/token`
  endpoint (`:122-139`, step 4b) via `IHttpClientFactory`, base address from the `"IDS"` config key.
- `IOtpAuthService.ValidateOtpAsync` (peek/consume) — backing OTP cache/store internals (rate
  limiting, expiry, attempt counting) not opened in this pass; bridged from
  [[Login-and-Activation|Login & Activation]]'s own open question.
- `IFeatureManager.IsFeatureEnabledAsync(Features.OtpLoginOrRegister)` — feature-flag backend, not
  re-opened here (see [[Identity.technical|Identity]] for the flag-system inventory).
- Point-in-polygon `Area` lookup (`ResolveGuestCustomerService.cs:339-360`) — in-process DB query
  against master-data `Area`/`AreaBorder`, not a network call.

## Failure modes
| # | Step | What happens | Status |
|---|------|--------------|--------|
| #341 | 2 | Unbounded guest rows minted via varying `guestDeviceId`; ADR-mandated rate limit never built | 🟡 Established — cite only |
| #429 | 3 | Empty/malformed `CountryCode` crashes `SendOTP` with an unhandled 500, pre-auth | 🔴 Established — cite only |
| #407 | 3-4 | (Now fixed) any portal user could read a customer's live OTP and take over the account | 🔴 Established, **resolved** — context only |
| #400 | 9 | Unscoped address lookup lets a caller overwrite and re-home another customer's address | 🔴 Established — cite only |
| — | 5 | Both registration branches activate before any OTP check in that handler — classic path's `ActivateUserV2` is non-authoritative for phone verification | Self-traced this pass |
| — | 6 | Merge failure is logged only, never blocking — login proceeds, guest cart/address silently lost | Self-traced this pass |
| — | 6 | Wallet/loyalty rows aren't copied by the merge; would be deleted with the guest row if they existed | Self-traced, unconfirmed in practice |
| — | 10 | `IsActiveAsync`'s mobile branch never checks `Active` — a bare deactivation may not revoke a live token | Self-traced, unconfirmed |
| — | 11 | Same branch never checks `Deleted` either — self-deleted account's token survives until natural expiry (~3h) or refresh | Self-traced this pass |
| — | 11 | No cascade cleanup of cart/addresses/wallet/loyalty on deletion (contrast step 7's guest purge) | Self-traced this pass |

## Open Questions
- Which OAuth grant/client actually issues the pre-registration "guest" bearer token (step 1) — not
  traced in this pass.
- Where `PurgeAbandonedGuestCustomersCommand`'s recurring-job registration/cron schedule lives — not
  located in this pass.
- `IOtpAuthService`'s own internals (rate limiting, expiry window, attempt counting) — not opened,
  same gap already flagged on [[Login-and-Activation|Login & Activation]].
- Whether a guest customer can legitimately accumulate a `WalletTransaction` or `LoyaltyPoints` row
  before merge/purge, making step 6's uncovered case a live rather than theoretical gap — not
  confirmed either way.
- Whether admin's `MangeCustomerActivation(false)` is ever exercised against an account whose
  `PhoneNumberConfirmed` is still `true`, and if so, whether the live token genuinely survives it as
  step 10 suggests — not traced/confirmed exploited.
- Whether the classic `RegisterV2` → `ActivateUserV2` path (4c) is still reachable from any live
  client, or is dead code superseded entirely by the unified OTP flow (4a/4b) — not confirmed either
  way.
- Delivery-channel specifics of `SendOtpDeliveryJob` (SMS vs WhatsApp routing/provider) — not opened
  in this pass.
