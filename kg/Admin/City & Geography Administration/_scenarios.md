---
id: 8orders/admin/city-and-geography-administration/scenarios
title: City & Geography Administration — Scenario Catalog
note_type: scenarios
context: Admin
feature: City & Geography Administration
audience: Business · QA · Developer
last_updated: 2026-08-23
sources:
  - path: Shared/TalabatkLogic/TalabatkModels/CityRushTimeConfiguration.cs
    sha1: f757c5b8a06e
  - path: Shared/TalabatkLogic/TalabatkModels/City.cs
    sha1: dcb1e22e8f7e
  - path: Shared/TalabatkApplication/TimeOutRequestsCashing/RushModeEndCheckerService.cs
    sha1: b488a3b4bc81
  - path: Shared/TalabatkApplication/DomainEventsHandlers/OrderEventsHandlers/MangeRushTimeEvnetHandler.cs
    sha1: 2189e4952b51
tags: [admin, city-and-geography-administration, scenarios]
---
# City & Geography Administration — Scenario Catalog

> The rush-mode rows are the ones with operational consequence; the geography rows are ordinary CRUD
> whose interest is what depends on them.

## Happy path

| # | Precondition | Action | Expected outcome | Rule / source |
|---|---|---|---|---|
| H1 | New market | create country → city → areas | Geography hierarchy in place | `AdminUi/Controllers/Country/CountryController.cs`, `AdminUi/Controllers/Area/AreaController.cs` |
| H2 | City exists, weights sum to 1 | create the city | Accepted | `Shared/TalabatkLogic/TalabatkModels/City.cs:126-129` |
| H3 | Zones needed | create delivery and restaurant zones | Drivers assignable; stores matched to addresses | `AdminUi/Controllers/DelivaryZoneController/DeliveryZoneController.cs`, `AdminUi/Controllers/RestaurantZoneController/RestaurantZoneController.cs` |
| H4 | Valid thresholds, at least one area priority | create rush configuration | Accepted, starting **out** of rush mode | `Shared/TalabatkLogic/TalabatkModels/CityRushTimeConfiguration.cs:67-89` |
| H5 | Late deliveries exceed the busy threshold | evaluation runs | City enters rush mode; an end-check job is scheduled after the configured interval | `_integrations.md` row 23 |
| H6 | Count has fallen below reopen-below | end-check job runs | Rush mode disabled; transition logged | `Shared/TalabatkLogic/TalabatkModels/CityRushTimeConfiguration.cs:51`, `:109` |
| H7 | Operator wants it ended early, count already low | force-end | Accepted | `Shared/TalabatkLogic/TalabatkModels/CityRushTimeConfiguration.cs:99-109` |
| H8 | Customers ask for an unserved city | suggestion recorded | Demand captured | `AdminUi/Controllers/CitySuggestionsController/CitySuggestionsController.cs` |

## Partial / incremental

| # | Precondition | Action | Expected outcome | Rule / source |
|---|---|---|---|---|
| P1 | Count still above threshold when the check runs | end-check job | **Re-schedules itself** — the chain continues until the count falls | `_integrations.md` row 23 |
| P2 | Host restarted | boot job seeds the timeout counter per city | Rush decisions depend on this having run | `_integrations.md` row 24 |
| P3 | City already in rush mode | edit the thresholds | **Accepted without validation** — both guards are conditioned on `!RushMode` | 🔴 `Shared/TalabatkLogic/TalabatkModels/CityRushTimeConfiguration.cs:121-130` |
| P4 | Working days change | update the city | Feeds the daily pickup-tag sequence | `Shared/TalabatkLogic/TalabatkModels/CityDailyPickupTagCounter.cs` |

## Negative / guard

| # | Precondition | Action | Expected outcome (rejection) | Rule / source |
|---|---|---|---|---|
| N1 | Busy threshold zero or negative | create rush configuration | Rejected — "busy threshold must be greater than zero" | `Shared/TalabatkLogic/TalabatkModels/CityRushTimeConfiguration.cs:67` |
| N2 | Reopen-below ≥ busy threshold | create rush configuration | Rejected — the city could never leave rush mode | `Shared/TalabatkLogic/TalabatkModels/CityRushTimeConfiguration.cs:72` |
| N3 | Checker interval zero | create rush configuration | Rejected | `Shared/TalabatkLogic/TalabatkModels/CityRushTimeConfiguration.cs:76` |
| N4 | No area priorities | create rush configuration | Rejected — "rush time area priorities can not be null or empty" | `Shared/TalabatkLogic/TalabatkModels/CityRushTimeConfiguration.cs:80` |
| N5 | Force-end while the count is still above the busy threshold | force-end | Rejected — an operator cannot override the live condition | `Shared/TalabatkLogic/TalabatkModels/CityRushTimeConfiguration.cs:106` |
| N6 | Scoring weights do not sum to 1, on **create** | create city | Rejected cleanly with a `Result` failure | `Shared/TalabatkLogic/TalabatkModels/City.cs:126-129` |
| N7 | Same, on **update** | update city | **Throws a raw exception** instead of returning a failure — same rule, two mechanisms | 🔴 `Shared/TalabatkLogic/TalabatkModels/City.cs:271-274` |

## Returns / cancellation / reversal

| # | Precondition | Action | Expected outcome | Rule / source |
|---|---|---|---|---|
| R1 | Rush mode entered in error | force-end | Only once the count has fallen (N5) | `Shared/TalabatkLogic/TalabatkModels/CityRushTimeConfiguration.cs:99-109` |
| R2 | Zone drawn wrongly | edit or delete it | Ordinary CRUD; existing assignments are not re-evaluated | `AdminUi/Controllers/DelivaryZoneController/DeliveryZoneController.cs` |
| R3 | City created in error | — | `City` is referenced by 20 model types; deletion is not a light operation | [[City.technical\|City]] |
| R4 | Break window wrong | edit it | Takes effect on the next window | `AdminUi/Controllers/CityBreakConfigurationController/CityBreakConfigurationController.cs` |

## Integration (cross-side / cross-context)

| # | Precondition | Action | Expected outcome | Rule / source |
|---|---|---|---|---|
| I1 | Late deliveries counted | shared cache read | Rush evaluation reads a counter seeded at host boot and updated in operation | `_integrations.md` rows 23–24 |
| I2 | Rush mode changes | delivery behaviour | Assignment prioritisation shifts — see [[Delivery/Delivery Man Operations/_knowledge-graph\|Delivery Man Operations]] | `_integrations.md` row 23 |
| I3 | City settings change | every context | Driver pay, scoring, cash limits and store availability all read the city | [[City.technical\|City]] |
| I4 | Working day rolls over | pickup-tag counter | Per-city, per-day sequence used on orders | [[Customer Ordering/Order & Fulfilment/_knowledge-graph\|Order & Fulfilment]] |

## Consistency scenarios

| # | Precondition | Action | Actual outcome today | Source |
|---|---|---|---|---|
| X1 | City in rush mode | set reopen-below **above** the busy threshold | **Accepted.** The city can then never satisfy its own exit condition through the normal path | 🔴 `Shared/TalabatkLogic/TalabatkModels/CityRushTimeConfiguration.cs:121-130` |
| X2 | Count never falls | end-check job | Re-schedules indefinitely; no observed retry ceiling | `_integrations.md` row 23 |
| X3 | Boot seeding skipped | rush evaluation | Reads an unseeded counter; behaviour unverified | `_integrations.md` row 24 |
| X4 | Update a city with invalid weights | update | Raw exception rather than a validation message (N7) | 🔴 `Shared/TalabatkLogic/TalabatkModels/City.cs:271-274` |

## Open Questions

- [ ] X1 is the sharpest question in this feature: is the `!RushMode` condition on the update guards
      deliberate, and what is the intended recovery if a city is left with impossible thresholds?
- [ ] Does the end-check chain have a retry ceiling or backoff?
- [ ] What is the behaviour when the boot-time counter seeding has not run?
- [ ] Should `City.UpdateCity` return a `Result` like `AddCity` rather than throwing (N7)?
- [ ] Are city suggestions reviewed on any cadence, or only stored?
