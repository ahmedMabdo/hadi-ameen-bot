---
id: 8orders/customer-ordering/restaurant-and-menu-discovery/mart
note_type: single
context: Customer Ordering
feature: Restaurant & Menu Discovery
group: Mart
covers: [SpecialMartCategorySetting]
sources:
  - path: Shared/TalabatkLogic/TalabatkModels/SpecialMartCategorySetting.cs
    sha1: 0c94d5931ca2
last_updated: 2026-08-23
tags: [customer-ordering, restaurant-menu-discovery, light, backend-application]
---
# Mart

**Not a separate domain entity** — a Mart is a [[Restaurant.technical|Restaurant]] row
with `IsStore=true`. `MartController` (`TalabatkAPIs/Controllers/Mart/`) is a browsing/search layer
over the same `Restaurant`/`MenuItem` models plus mart-specific category/product endpoints:
`GetMartCategories(V2)`, `GetCategoryProducts`, `SearchProducts`, `MartHomeSearch`,
`GetSubCategories`, `GetExclusiveOffers(V2)`, `GetMostOrderedItems`, `GetPreviousPurchases`,
`CheckMartBusyOrNot`.

## Notable feature: item-availability notification subscriptions
`ToggleItemAvailabilityNotification` / `GetMyItemsNotificationSubscriptions` — a customer can
subscribe to be notified when an out-of-stock mart item (see `MenuItem.technical.md` Rule 3) comes
back in stock. Not investigated further in this pass (which entity/table backs the subscription,
what triggers the actual notification).

## Folded entity — `SpecialMartCategorySetting`

The one entity this note covers: the configuration behind the special mart category tiles (the
"exclusive offers" and similar rails on the mart home screen).

| Entity | What it is | Rules |
|---|---|---|
| `SpecialMartCategorySetting` | A named, logo-bearing special category of a given type | Private ctor and a properly symmetric pair: `Instance` requires the category type, the Arabic name and the English name (`Shared/TalabatkLogic/TalabatkModels/SpecialMartCategorySetting.cs:33`, `:37`, `:41`); `Update` re-checks both names (`:57`, `:61`); `UpdateLogo` requires the logo (`:73`). All three return `Result`. `GetName` (`:79`) picks the language-appropriate name, so the choice is made in the domain rather than in each caller — unusual here, and the reason the mart rails cannot show a blank label |

Note the contrast with `MenuCategory`, which this feature also reads: same conceptual role, and it guards
nothing at all (see [[Customer Ordering/Restaurant & Menu Discovery/Discovery-Utilities|Discovery
Utilities]]). `SliderHome.SpecialMartCategory` is the field that points a home-screen slider at one of
these.

## Related
- [[Restaurant.technical|Restaurant]] — `IsStore` flag
- [[MenuItem.technical|MenuItem]] — stock-driven availability (Rule 3), the mechanism this feature notifies on
