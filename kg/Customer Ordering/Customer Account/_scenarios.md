---
id: 8orders/customer-ordering/customer-account/scenarios
title: Customer Account — Scenario Catalog
note_type: scenarios
context: Customer Ordering
feature: Customer Account
audience: Business · QA · Developer
last_updated: 2026-08-24
sources:
  - path: TalabatkAPIs/Controllers/CustomerUser/CustomerUserController.cs
    sha1: fc15a3e7f335
  - path: TalabatkAPIs/Controllers/UserPreferences/UserPreferencesController.cs
    sha1: 763614986762
  - path: Shared/TalabatkApplication/Commands/DeleteCustomerAddressCommand/DeleteCustomerAddressCommand.cs
    sha1: d415010a9143
  - path: Shared/TalabatkApplication/Commands/MangeCustomerUnRegestirationCommand/MangeCustomerUnRegestirationCommand.cs
    sha1: 6d1400a86225
tags: [customer-ordering, customer-account, scenarios]
---
# Customer Account — Scenario Catalog

> Thirty-four endpoints on two controllers: profile, addresses, saved cards, devices, notification
> preferences, loyalty and account closure. Twenty-eight of them are role-gated to `Customer`; the six
> that are not are where this feature's findings live, and the exceptions are not the ones you would
> guess.

## The six actions without a role gate

| Action | Anchor | Why it matters |
|---|---|---|
| `UpdateUnavailableItemsPreference` | `TalabatkAPIs/Controllers/CustomerUser/CustomerUserController.cs:145` | Guest-capable by design — the preference survives the guest→account cart merge |
| `deleteAddress` | `TalabatkAPIs/Controllers/CustomerUser/CustomerUserController.cs:287` | 🔴 **#227** — a `[HttpGet]` that deletes **any** customer's address by id |
| `deleteAllAddress` | `TalabatkAPIs/Controllers/CustomerUser/CustomerUserController.cs:306` | Scoped correctly to the session's customer, unlike the line above it |
| `GetCustomerVouchers_V1` | `TalabatkAPIs/Controllers/CustomerUser/CustomerUserController.cs:569` | The V1 twin is role-gated; this one is not |
| `GetCustomerTieredDiscount` | `TalabatkAPIs/Controllers/CustomerUser/CustomerUserController.cs:586` | Accepts a `guestDeviceId`, so guest-capable by design |
| `ManageCustomerUnRegestiration` | `TalabatkAPIs/Controllers/CustomerUser/CustomerUserController.cs:840` | 🔓 `[AllowAnonymous]` — deliberately, since it runs before registration |

## Happy path

| # | Precondition | Action | Expected outcome | Rule / source |
|---|---|---|---|---|
| H1 | Signed-in customer | `GET api/CustomerUser/GetCustomerInfo` | Their profile | `TalabatkAPIs/Controllers/CustomerUser/CustomerUserController.cs:74` |
| H2 | Profile edited | `POST api/CustomerUser/UpdateCustomerInfo` | Name, phone and details updated | `TalabatkAPIs/Controllers/CustomerUser/CustomerUserController.cs:457` |
| H3 | New delivery address | `POST api/CustomerUser/AddNewAddress` | Saved and selectable at checkout | `TalabatkAPIs/Controllers/CustomerUser/CustomerUserController.cs:209` |
| H4 | Address changed | `POST api/CustomerUser/UpdateAddress` | Updated | `TalabatkAPIs/Controllers/CustomerUser/CustomerUserController.cs:250` |
| H5 | Customer moves city | `POST api/CustomerUser/ChangeCustomerCity` | City switched, which re-scopes stores and fees | `TalabatkAPIs/Controllers/CustomerUser/CustomerUserController.cs:328` |
| H6 | City not served | `POST api/CustomerUser/CustomerSuggestionCity` | Suggestion recorded for the back office | `TalabatkAPIs/Controllers/CustomerUser/CustomerUserController.cs:352` |
| H7 | App installed on a new phone | `POST api/CustomerUser/AddDeviceIds` | Device registered for push | `TalabatkAPIs/Controllers/CustomerUser/CustomerUserController.cs:376` |
| H8 | Customer changes language | `POST api/CustomerUser/ChangePreferredLanguage` | All later content served in it | `TalabatkAPIs/Controllers/CustomerUser/CustomerUserController.cs:430` |
| H9 | Customer has enough points | `POST api/CustomerUser/RedeemPoints` | A voucher is created — this, not the campaign, is what mints one | `TalabatkAPIs/Controllers/CustomerUser/CustomerUserController.cs:625` |
| H10 | Points redeemed at a merchant | `POST api/CustomerUser/RedeemPointsWithMerchant` | Merchant-scoped voucher | `TalabatkAPIs/Controllers/CustomerUser/CustomerUserController.cs:648` |
| H11 | Customer checks their balance | `GET api/CustomerUser/GetCustomerLoyaltyPoints` | Current points | `TalabatkAPIs/Controllers/CustomerUser/CustomerUserController.cs:514` |
| H12 | Customer opens notifications | `GET api/CustomerUser/Notifications` | Their inbox | `TalabatkAPIs/Controllers/CustomerUser/CustomerUserController.cs:487` |
| H13 | Saved card no longer wanted | `POST api/CustomerUser/DeleteCard` | Removed | `TalabatkAPIs/Controllers/CustomerUser/CustomerUserController.cs:121` |
| H14 | External recycling partner has a phone number | `AddCustomerWallet` | Wallet credited; hidden from the generated client by `[OpenApiIgnore]` | `TalabatkAPIs/Controllers/IRecycleRedeems/IRecycleRedeemsController.cs` |

## Partial / incremental

| # | Precondition | Action | Expected outcome | Rule / source |
|---|---|---|---|---|
| P1 | Guest, pre-registration | `POST api/CustomerUser/ManageCustomerUnRegestiration` | Anonymous branch: the device is tracked as an unregistered install | `Shared/TalabatkApplication/Commands/MangeCustomerUnRegestirationCommand/MangeCustomerUnRegestirationCommand.cs:67-86` |
| P2 | Same device, now registered | the same endpoint with a token | Authenticated branch: the device id is written onto the customer and the unregistered row removed | `Shared/TalabatkApplication/Commands/MangeCustomerUnRegestirationCommand/MangeCustomerUnRegestirationCommand.cs:41-63` |
| P3 | Customer sets a refund preference | `POST api/CustomerUser/UpdateRefundPreference` | Wallet or original payment method on later refunds | `TalabatkAPIs/Controllers/CustomerUser/CustomerUserController.cs:191` |
| P4 | Item unavailable at fulfilment | `UpdateUnavailableItemsPreference` | Substitute, remove or cancel — set before checkout, and carried through the guest-cart merge | `TalabatkAPIs/Controllers/CustomerUser/CustomerUserController.cs:145` |
| P5 | Two app versions live | `GetCustomerVouchers` / `_V1` | Both served; only the non-V1 is role-gated | `TalabatkAPIs/Controllers/CustomerUser/CustomerUserController.cs:553`, `:569` |
| P6 | Guest with a locked tiered discount | `GET api/CustomerUser/GetCustomerTieredDiscount?guestDeviceId=` | The discount held against their cart | `TalabatkAPIs/Controllers/CustomerUser/CustomerUserController.cs:586` |

## Negative / guard

| # | Precondition | Action | Expected outcome (rejection) | Rule / source |
|---|---|---|---|---|
| N1 | No token | any endpoint except `ManageCustomerUnRegestiration` | 401 — class-level JWT | `TalabatkAPIs/Controllers/CustomerUser/CustomerUserController.cs:50` |
| N2 | Token without the `Customer` role | 28 of the 34 actions | 403 | `TalabatkAPIs/Controllers/CustomerUser/CustomerUserController.cs:74` |
| N3 | `"UserPreferences"` flag **on** | `GET GetUserPreferences` | **Still an empty list** — a hardcoded `false` field short-circuits the flag, so the endpoint can never return anything | 🔴 `TalabatkAPIs/Controllers/UserPreferences/UserPreferencesController.cs:40` |
| N4 | Not enough points | `RedeemPoints` | Rejected before a voucher is minted | `TalabatkAPIs/Controllers/CustomerUser/CustomerUserController.cs:625` |
| N5 | Another customer's address id | `GET api/CustomerUser/deleteAddress?adressId=N` | **Accepted** — soft-deleted, no ownership check anywhere in the path | 🔴 `Shared/TalabatkApplication/Commands/DeleteCustomerAddressCommand/DeleteCustomerAddressCommand.cs:27` |

## Returns / cancellation / reversal

| # | Precondition | Action | Expected outcome | Rule / source |
|---|---|---|---|---|
| R1 | Address no longer needed | `deleteAddress` | Soft-deleted via `SetIsDeleted(true)`, so history survives | `Shared/TalabatkApplication/Commands/DeleteCustomerAddressCommand/DeleteCustomerAddressCommand.cs:33` |
| R2 | Customer wants a clean slate | `deleteAllAddress` | All of **their own** addresses removed — this one passes the session's customer id | `TalabatkAPIs/Controllers/CustomerUser/CustomerUserController.cs:306` |
| R3 | Notification read | `MarkNotifcationAsRead`, `DeleteNotification`, `DeleteAllNotifications` | Marked or removed | `TalabatkAPIs/Controllers/CustomerUser/CustomerUserController.cs:709`, `:761`, `:734` |
| R4 | Device replaced | `RemoveDeviceIds` | Deregistered — but the handler removes **every** device, not the named one | 🔴 `Customer.technical` Rule 14 · `TalabatkAPIs/Controllers/CustomerUser/CustomerUserController.cs:402` |
| R5 | Customer leaves | `POST api/CustomerUser/DeleteCustomer` | Account closed | `TalabatkAPIs/Controllers/CustomerUser/CustomerUserController.cs:817` |
| R6 | Voucher minted in error | — | No customer-facing reversal; loyalty points are already spent | `TalabatkAPIs/Controllers/CustomerUser/CustomerUserController.cs:625` |

## Integration (cross-side / cross-context)

| # | Precondition | Action | Expected outcome | Rule / source |
|---|---|---|---|---|
| I1 | Address added or changed | checkout reads it | Delivery fee and area coverage follow from the address | [[Customer Ordering/Cart & Checkout/_knowledge-graph\|Cart & Checkout]] |
| I2 | Points redeemed | a voucher appears | Redemption is the only voucher source | [[Customer Ordering/Discounts & Coupons/_knowledge-graph\|Discounts & Coupons]] |
| I3 | Device registered | FCM push | The token list is what notifications target | `_integrations.md` row 22 |
| I4 | Wallet credited by the partner | balance changes | A server-to-server call keyed on phone number, hidden from the API docs | `TalabatkAPIs/Controllers/IRecycleRedeems/IRecycleRedeemsController.cs` |
| I5 | City suggested | Admin listing | Appears with the customer's name and phone — and the permission guarding that screen is commented out | 🔴 `_conflicts.md` #414 |
| I6 | Guest registers on the same device | the guest row is promoted in place | Cart, addresses and locked discount survive | [[Identity & Access/Customer Identity/Customer/Customer.technical\|Customer]] Rule 4 |

## Correctness and exposure scenarios — current behaviour

| # | Precondition | Action | Actual outcome today | Finding |
|---|---|---|---|---|
| X1 | Any authenticated token, any role | `GET api/CustomerUser/deleteAddress?adressId=N` | Another customer's address is soft-deleted. It is a **GET**, so a link, prefetch or crawler can trigger it, and the id lands in logs and browser history | 🔴 **#227** |
| X2 | Customer removes one device | `RemoveDeviceIds` | **Every** device is removed, so push stops on phones the customer still uses | 🔴 `Customer.technical` Rule 14 |
| X3 | Feature flag turned on to launch preferences | `GetUserPreferences` | Nothing changes — the endpoint returns an empty list unconditionally | 🔴 `TalabatkAPIs/Controllers/UserPreferences/UserPreferencesController.cs:40` |
| X4 | Any signed-in back-office user | the city-suggestions screen | Every customer's name and phone, because `[Permission("SuggestionCity")]` is commented out | 🔴 **#414** |
| X5 | Someone knows a guest device id | `GetCustomerTieredDiscount?guestDeviceId=` | That guest's locked discount is readable; the device id is the whole credential | ⚠️ **#341** |
| X6 | Unauthenticated caller | `ManageCustomerUnRegestiration` with an arbitrary device id | The unregistered-device row for that id can be removed | ⚠️ `Shared/TalabatkApplication/Commands/MangeCustomerUnRegestirationCommand/MangeCustomerUnRegestirationCommand.cs:74-83` |

## Open Questions

- [ ] `deleteAddress` is a GET that deletes and takes no customer id, while `deleteAllAddress` two lines
      below passes one. Was the first an oversight, or is something upstream meant to scope it?
- [ ] Is `GetUserPreferences`' hardcoded `false` an unfinished rollout? The flag exists, the screen
      presumably exists, and the endpoint can never answer.
- [ ] Why is `GetCustomerVouchers_V1` the only voucher read without a role gate?
- [ ] Does `RemoveDeviceIds` wiping every device (X2) explain any "notifications stopped working"
      reports? The fix is one `Where` clause.
