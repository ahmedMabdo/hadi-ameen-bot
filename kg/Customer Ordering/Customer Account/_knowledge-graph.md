---
id: 8orders/customer-ordering/customer-account/knowledge-graph
note_type: knowledge-graph
context: Customer Ordering
feature: Customer Account
sources:
  - path: TalabatkAPIs/Controllers/CustomerUser/CustomerUserController.cs
    sha1: fc15a3e7f335
  - path: TalabatkAPIs/Controllers/UserPreferences/UserPreferencesController.cs
    sha1: 763614986762
last_updated: 2026-08-23
---
# Customer Account — Knowledge Graph

> **Context:** Customer Ordering
> **Source Project:** `TalabatkAPIs/Controllers/CustomerUser`, `UserPreferences`, `IRecycleRedeems`
> **Last Updated:** 2026-08-02
> **Entities Covered:** profile/address/loyalty management (light-technical, controller-level — no dedicated aggregate found for "Customer" itself in this pass) + 1 flagged bug

---

## CustomerUserController (32 routes — profile, addresses, devices, notifications, loyalty)
Not a single cohesive aggregate — a wide controller fronting many independent MediatR
commands/queries against `Customer`, `CustomerAddresses`, and `LoyaltyPoints`/`Vouchers`. Notable
groups:
- **Profile & addresses:** `GetCustomerInfo`, `UpdateCustomerInfo`, `Cards`/`DeleteCard`,
  `AddNewAddress`/`UpdateAddress`/`deleteAddress`/`deleteAllAddress`, `ChangeCustomerCity`.
- **Preferences:** `UpdateUnavailableItemsPreference` (the same preference carried over during
  guest-cart merge — see `CustomerCart.technical.md`'s guest-merge rules),
  `RefundPreference`/`UpdateRefundPreference`, `ChangePreferredLanguage`.
- **Devices & notifications:** `AddDeviceIds`/`RemoveDeviceIds` (push-notification registration),
  `Notifications`/`MarkNotifcationAsRead`/`DeleteNotification`/`DeleteAllNotifications`/`NotificationSetting`.
- **Loyalty (the real source of Vouchers):** `GetCustomerLoyaltyPoints`, `GetLoyaltyPointsHistory`,
  `GetRedeemingConfirmationMessage`, **`RedeemPoints` → `RedeemingLoyaltyPointsCommand`**,
  **`RedeemPointsWithMerchant` → `RedeemingLoyalityPointsWithMerchantCommand`**,
  `GetLoyaltyParticipatingMerchants`, `RecordLoyaltyMerchantImpressions`. This — not
  `IRecycleRedeems` — is what creates a [[Vouchers.technical|Voucher]]
  (corrects a guess made earlier in this knowledge graph, in that entity's own Open Questions).
- **Account lifecycle:** `DeleteCustomer`, `ManageCustomerUnRegestiration`.

The generated endpoint index below anchors all 34 actions to a line and records each one's gate, and
the [[Customer Ordering/Customer Account/_scenarios|scenario catalog]] covers them behaviourally in 43
rows — including the six actions that carry no role gate and why each is or is not deliberate. For the
rules inside a specific handler, the entity notes are the place: [[Customer.technical|Customer]],
[[CustomerAddresses|CustomerAddresses]], [[LoyaltyPoints|LoyaltyPoints]] and
[[WalletTransaction|WalletTransaction]] each carry their own rule matrix.

**Re-verified 2026-08-03** against the live route list — the grouping above holds; three routes not
previously named: `GetRefundPreference` (pairs with `UpdateRefundPreference`),
`GetCustomerVouchers`/`GetCustomerVouchers_V1` (versioned pair, same pattern seen elsewhere in this
codebase — not confirmed which the current app build calls), `GetCustomerTieredDiscount` (the
customer-facing read side of [[TieredDiscount.technical|TieredDiscount]],
accepts an optional `guestDeviceId` — ties to the guest-mode eligibility question already open on
that entity's note).

## UserPreferencesController

> ⚠️ **CONFIRMED BUG — the User Preferences feature always returns empty**
> `GetUserPreferences` (`UserPreferencesController.cs`) checks
> `if (!isFeatureEnabled || !isUserPreferencesFeatureEnabled) return Ok(new List<GetUserPreferencesDto>())`.
> `isUserPreferencesFeatureEnabled` is a **private field hardcoded to `false`** and never
> reassigned anywhere in the class. This means the endpoint returns an empty list **unconditionally**,
> regardless of what the `"UserPreferences"` feature flag (`_featureManager`) says — the flag check
> is dead code, short-circuited by the always-false local field. This looks like an incomplete
> feature rollout (a flag added, its actual gate accidentally left at the default) rather than
> deliberate behavior. High confidence, directly evidenced — worth a quick fix or confirmation with
> whoever owns this feature.

## IRecycleRedeemsController
A **separate, unrelated** integration: `AddCustomerWallet` lets an external partner ("I Recycle" —
presumably a recycling-rewards program) credit a customer's wallet directly by phone number
(`AddCustomerWalletFromIRecycleRedeemsCommand`). Marked `[NSwag.Annotations.OpenApiIgnore]` (hidden
from the generated API client/docs) and takes a phone number rather than using the session's
customer id — consistent with being a server-to-server webhook from the partner, not a call the
mobile app itself makes. Not part of the loyalty-points/Voucher system despite the superficial
similarity ("redeem" in both names).

<!-- BEGIN generated: endpoint index (insert-endpoints.js) -->

## Endpoint index — generated from the controllers

> Generated by `_system/insert-endpoints.js` from `_feature-map.tsv`; do not edit between the
> sentinels. Every row is anchored to a line, so `verify-citations.js` checks all of it and a
> controller that moves is caught on the next run. "Action gate" lists only attributes on the action
> itself — the class gate above each table still applies unless an action opts out of it.

**2 controller(s), 34 action(s)** — 1 carry `[AllowAnonymous]`; 6 have no action-level gate and rely entirely on the class attribute.

#### `TalabatkAPIs/Controllers/CustomerUser/CustomerUserController.cs`

Class gate: JWT bearer — `TalabatkAPIs/Controllers/CustomerUser/CustomerUserController.cs:50`

| Route | Verb | Action gate | Anchor |
|---|---|---|---|
| `api/CustomerUser/GetCustomerInfo` | GET | role `Customer` | `TalabatkAPIs/Controllers/CustomerUser/CustomerUserController.cs:74` |
| `api/CustomerUser/Cards` | GET | role `Customer` | `TalabatkAPIs/Controllers/CustomerUser/CustomerUserController.cs:99` |
| `api/CustomerUser/DeleteCard` | POST | role `Customer` | `TalabatkAPIs/Controllers/CustomerUser/CustomerUserController.cs:121` |
| `api/CustomerUser/UpdateUnavailableItemsPreference` | POST | — | `TalabatkAPIs/Controllers/CustomerUser/CustomerUserController.cs:145` |
| `api/CustomerUser/RefundPreference` | GET | role `Customer` | `TalabatkAPIs/Controllers/CustomerUser/CustomerUserController.cs:170` |
| `api/CustomerUser/UpdateRefundPreference` | POST | role `Customer` | `TalabatkAPIs/Controllers/CustomerUser/CustomerUserController.cs:191` |
| `api/CustomerUser/AddNewAddress` | POST | role `Customer` | `TalabatkAPIs/Controllers/CustomerUser/CustomerUserController.cs:209` |
| `api/CustomerUser/UpdateAddress` | POST | role `Customer` | `TalabatkAPIs/Controllers/CustomerUser/CustomerUserController.cs:250` |
| `api/CustomerUser/deleteAddress` | GET | — | `TalabatkAPIs/Controllers/CustomerUser/CustomerUserController.cs:287` |
| `api/CustomerUser/deleteAllAddress` | GET | — | `TalabatkAPIs/Controllers/CustomerUser/CustomerUserController.cs:306` |
| `api/CustomerUser/ChangeCustomerCity` | POST | role `Customer` | `TalabatkAPIs/Controllers/CustomerUser/CustomerUserController.cs:328` |
| `api/CustomerUser/CustomerSuggestionCity` | POST | role `Customer` | `TalabatkAPIs/Controllers/CustomerUser/CustomerUserController.cs:352` |
| `api/CustomerUser/AddDeviceIds` | POST | role `Customer` | `TalabatkAPIs/Controllers/CustomerUser/CustomerUserController.cs:376` |
| `api/CustomerUser/RemoveDeviceIds` | POST | role `Customer` | `TalabatkAPIs/Controllers/CustomerUser/CustomerUserController.cs:402` |
| `api/CustomerUser/ChangePreferredLanguage` | POST | role `Customer` | `TalabatkAPIs/Controllers/CustomerUser/CustomerUserController.cs:430` |
| `api/CustomerUser/UpdateCustomerInfo` | POST | role `Customer` | `TalabatkAPIs/Controllers/CustomerUser/CustomerUserController.cs:457` |
| `api/CustomerUser/Notifications` | GET | role `Customer` | `TalabatkAPIs/Controllers/CustomerUser/CustomerUserController.cs:487` |
| `api/CustomerUser/GetCustomerLoyaltyPoints` | GET | role `Customer` | `TalabatkAPIs/Controllers/CustomerUser/CustomerUserController.cs:514` |
| `api/CustomerUser/GetRedeemingConfirmationMessage` | GET | role `Customer` | `TalabatkAPIs/Controllers/CustomerUser/CustomerUserController.cs:530` |
| `api/CustomerUser/GetCustomerVouchers` | GET | role `Customer` | `TalabatkAPIs/Controllers/CustomerUser/CustomerUserController.cs:553` |
| `api/CustomerUser/GetCustomerVouchers_V1` | GET | — | `TalabatkAPIs/Controllers/CustomerUser/CustomerUserController.cs:569` |
| `api/CustomerUser/GetCustomerTieredDiscount` | GET | — | `TalabatkAPIs/Controllers/CustomerUser/CustomerUserController.cs:586` |
| `api/CustomerUser/GetLoyaltyPointsHistory` | GET | role `Customer` | `TalabatkAPIs/Controllers/CustomerUser/CustomerUserController.cs:609` |
| `api/CustomerUser/RedeemPoints` | POST | role `Customer` | `TalabatkAPIs/Controllers/CustomerUser/CustomerUserController.cs:625` |
| `api/CustomerUser/RedeemPointsWithMerchant` | POST | role `Customer` | `TalabatkAPIs/Controllers/CustomerUser/CustomerUserController.cs:648` |
| `api/CustomerUser/GetLoyaltyParticipatingMerchants` | GET | role `Customer` | `TalabatkAPIs/Controllers/CustomerUser/CustomerUserController.cs:672` |
| `api/CustomerUser/RecordLoyaltyMerchantImpressions` | POST | role `Customer` | `TalabatkAPIs/Controllers/CustomerUser/CustomerUserController.cs:692` |
| `api/CustomerUser/MarkNotifcationAsRead` | POST | role `Customer` | `TalabatkAPIs/Controllers/CustomerUser/CustomerUserController.cs:709` |
| `api/CustomerUser/DeleteAllNotifications` | POST | role `Customer` | `TalabatkAPIs/Controllers/CustomerUser/CustomerUserController.cs:734` |
| `api/CustomerUser/DeleteNotification` | POST | role `Customer` | `TalabatkAPIs/Controllers/CustomerUser/CustomerUserController.cs:761` |
| `api/CustomerUser/NotificationSetting` | POST | role `Customer` | `TalabatkAPIs/Controllers/CustomerUser/CustomerUserController.cs:788` |
| `api/CustomerUser/DeleteCustomer` | POST | role `Customer` | `TalabatkAPIs/Controllers/CustomerUser/CustomerUserController.cs:817` |
| `api/CustomerUser/ManageCustomerUnRegestiration` | POST | 🔓 **AllowAnonymous** | `TalabatkAPIs/Controllers/CustomerUser/CustomerUserController.cs:840` |

#### `TalabatkAPIs/Controllers/UserPreferences/UserPreferencesController.cs`

Class gate: JWT bearer — `TalabatkAPIs/Controllers/UserPreferences/UserPreferencesController.cs:19`

| Route | Verb | Action gate | Anchor |
|---|---|---|---|
| `GetUserPreferences` | GET | — | `TalabatkAPIs/Controllers/UserPreferences/UserPreferencesController.cs:40` |

<!-- END generated: endpoint index -->

## Open Questions
- [ ] The 32 `CustomerUserController` routes were mapped, not individually audited — a future CR
  touching profile/address/notification/loyalty logic should read the specific handler.
- [ ] Confirm the User Preferences bug with the team before fixing — worth checking git history /
  recent commits on `UserPreferencesController.cs` for context on whether this is a known
  in-progress rollout.
- [ ] What `IRecycleRedeems` authenticates as (which JWT, whose service account) wasn't
  investigated.
