---
id: 8orders/admin/city-and-geography-administration/citybreakconfiguration
note_type: single
context: Admin
feature: City & Geography Administration
entity: CityBreakConfiguration
entity_type: legacy-poco-root
rule_count: 22
sources:
  - path: Shared/TalabatkLogic/TalabatkModels/CityBreakConfiguration.cs
    sha1: d77e533a294d
  - path: Shared/TalabatkApplication/Commands/AddCityBreakConfigurationCommand/AddCityBreakConfigurationCommand.cs
    sha1: c0f180f86d46
  - path: Shared/TalabatkApplication/Commands/UpdateCityBreakConfigurationCommand/UpdateCityBreakConfigurationCommand.cs
    sha1: b72bdc3bb6d0
  - path: Shared/TalabatkApplication/Commands/StartBreakCommand/StartBreakCommand.cs
    sha1: 42a1533c29ef
  - path: Shared/TalabatkApplication/Queries/GetBreakOptionsQuery/GetBreakOptionsQuery.cs
    sha1: c193be80cc33
  - path: Shared/TalabatkData/Mapping/CityBreakConfigurationMap.cs
    sha1: 0b2ae15f3be5
  - path: AdminUi/Controllers/CityBreakConfigurationController/CityBreakConfigurationController.cs
    sha1: 8cfe7d7fc51e
last_updated: 2026-08-23
tags: [admin, delivery, technical, backend-domain]
---
# CityBreakConfiguration

One row per city that decides **which break durations a delivery man may choose**, **how long before a
break ends they are warned**, and **what share of a shift's drivers may be away at once**. It is read on
every break request and on every load of the driver's break screen.

The entity itself is nearly empty — a private constructor, five fields, one factory, one setter and one
parser (`Shared/TalabatkLogic/TalabatkModels/CityBreakConfiguration.cs`). Every rule that governs it lives
somewhere else: the two commands validate, the EF map defaults, and the two consumers decide what a
missing row means. That split is the point of this note, because the interesting behaviour is in the
seams — particularly what happens when no row exists.

## Rule / Decision Matrix

| # | Rule | Where it is enforced | Notes |
|---|---|---|---|
| 1 | `Instance` assigns every field with no validation | `Shared/TalabatkLogic/TalabatkModels/CityBreakConfiguration.cs:23-38` | The entity cannot refuse anything; guards are in the commands |
| 2 | Optional parameter defaults: notify 5 minutes before end, cap 80% | `Shared/TalabatkLogic/TalabatkModels/CityBreakConfiguration.cs:27-28` | Same two values as the DB defaults (rule 15) |
| 3 | `Update` changes only durations, notification minutes and cap | `Shared/TalabatkLogic/TalabatkModels/CityBreakConfiguration.cs:53-58` | So `CityId` and `BreakType` are **write-once** — see 🟡 #630 |
| 4 | `GetAvailableDurations()` returns an empty list for a null or blank string | `Shared/TalabatkLogic/TalabatkModels/CityBreakConfiguration.cs:42-45` | The one defensive line in the entity |
| 5 | Otherwise `AvailableDurationsMinutes` is split on `,`, empty entries dropped, and each `int.Parse`d | `Shared/TalabatkLogic/TalabatkModels/CityBreakConfiguration.cs:47-50` | **Unguarded** — a non-numeric entry throws out of the entity |
| 6 | `CityId` must be greater than zero | `Shared/TalabatkApplication/Commands/AddCityBreakConfigurationCommand/AddCityBreakConfigurationCommand.cs:62-65` | Add only; update identifies the row by `Id` |
| 7 | At least one duration must be supplied | Add `:67-70`, Update `Shared/TalabatkApplication/Commands/UpdateCityBreakConfigurationCommand/UpdateCityBreakConfigurationCommand.cs:55-58` | Both paths agree |
| 8 | Every duration must be greater than zero | Add `:72-75`, Update `:60-63` | Both paths agree |
| 9 | `NotificationMinutesBeforeEnd` may not be negative | Add `:77-80`, Update `:65-68` | No upper bound — a value larger than the break length is accepted |
| 10 | `RestBreakMaxPercentage` must be 0–100 | Add `:82-85`, Update `:70-73` | **0 is accepted and means the opposite of what it reads like** — 🔴 #629 |
| 11 | The city must exist | Add `Shared/TalabatkApplication/Commands/AddCityBreakConfigurationCommand/AddCityBreakConfigurationCommand.cs:90-98` | Add only |
| 12 | One configuration per city, regardless of break type | Add `:100-111` (friendly message) **and** `Shared/TalabatkData/Mapping/CityBreakConfigurationMap.cs:25` (unique index) | Two layers; the index is the real guarantee, so a concurrent second insert fails as a DB error rather than the friendly message |
| 13 | Update requires the row to exist by `Id` | `Shared/TalabatkApplication/Commands/UpdateCityBreakConfigurationCommand/UpdateCityBreakConfigurationCommand.cs:80-87` | |
| 14 | Durations are persisted as a comma-joined string built from validated ints | Add `:115`, Update `:89` | This is what keeps rule 5 from throwing today — the guard is in the caller, not the entity |
| 15 | Column is required, `nvarchar(500)`; DB defaults 5 and 80 | `Shared/TalabatkData/Mapping/CityBreakConfigurationMap.cs:15-17` | 500 chars is ~125 durations |
| 16 | Deleting a city cascades to its configuration | `Shared/TalabatkData/Mapping/CityBreakConfigurationMap.cs:19-22` | |
| 17 | Reads select on `CityId` **only** — `BreakType` is never a predicate | `Shared/TalabatkApplication/Commands/StartBreakCommand/StartBreakCommand.cs:175-176`, `Shared/TalabatkApplication/Queries/GetBreakOptionsQuery/GetBreakOptionsQuery.cs:121-122` | 🟡 #630 |
| 18 | No row → durations `{15, 30, 45, 60}` and notify 5 | `Shared/TalabatkApplication/Commands/StartBreakCommand/StartBreakCommand.cs:184-185`, `Shared/TalabatkApplication/Queries/GetBreakOptionsQuery/GetBreakOptionsQuery.cs:140-141` | Duplicated verbatim in both consumers, and consistent — a warning is logged either way |
| 19 | No row → rest-break cap 0, which the guard treats as **unlimited** | `Shared/TalabatkApplication/Commands/StartBreakCommand/StartBreakCommand.cs:216-221` | 🔴 #629 — missing configuration is the most permissive state |
| 20 | The selected duration must be one of the available ones, except for `Accident` | `Shared/TalabatkApplication/Commands/StartBreakCommand/StartBreakCommand.cs:196-212` | The rejection message lists the valid durations, in the driver's language |
| 21 | A break is refused when offline-or-on-break drivers reach the cap | `Shared/TalabatkApplication/Commands/StartBreakCommand/StartBreakCommand.cs:234-241` | Counts `!Active` **or** an open break log across the whole shift; the message is Arabic-only while its two siblings in the same file are localised |
| 22 | `Accident` breaks get no durations and no notification time | `Shared/TalabatkApplication/Queries/GetBreakOptionsQuery/GetBreakOptionsQuery.cs:108-118` | Consistent with rule 20's exemption |

## What a reader needs to know

**A city with no configuration row is the most permissive state, not the most restrictive.** Durations fall
back to a fixed list, the notification falls back to 5 minutes, and the rest-break cap falls back to
*unlimited*. So a newly added city that nobody configured lets every driver on a shift go on break at
once — while a city configured through the admin screen defaults to 80%. That asymmetry is the practical
consequence of #629.

**`BreakType` looks like it partitions the configuration and does not.** The column is required and stored,
`Update` cannot change it, and nothing ever selects on it. One row governs every break type in the city
(#630).

**The only unguarded line in the entity is protected by its callers.** `GetAvailableDurations()` calls
`int.Parse` with no `TryParse` and no try/catch (rule 5). Nothing can reach it with bad data through the
API, because both commands build the string from validated integers (rule 14). But the column is free
text, so a manual database edit or a data migration would crash the break-options screen for that city.
This is the same shape as [[Customer Ordering/Marketing & Content/_knowledge-graph|#625's announcement
asymmetry]]: an invariant enforced in the caller rather than the entity, which holds only for as long as
every caller remembers.

## Positive notes

Worth recording, because much of this codebase is not like this:

- Every one of the four admin actions carries `[Permission(Permissions.General.Setting)]`
  (`AdminUi/Controllers/CityBreakConfigurationController/CityBreakConfigurationController.cs:38`, `:60`,
  `:86`, `:104`), and the class imports `Microsoft.AspNetCore.Authorization`, so its bare `[Authorize]`
  is the real one — not the inert SignalR attribute of `_conflicts.md` #446.
- The add and update validators are **identical** on all four shared checks (rules 7–10), avoiding the
  create/update asymmetry that produced #625, #626 and much of the register.
- The missing-row fallback is duplicated in two consumers but **agrees** in both (rule 18) — duplication
  without divergence, unlike the #395/#398/#406 family.
- The uniqueness rule is enforced twice, in the handler and in a unique index (rule 12).

## Related

- [[Delivery/Delivery Man Operations/_knowledge-graph|Delivery Man Operations]] — where
  breaks are actually taken; `DeliverymanBreakLog` records them.
- [[Admin/City & Geography Administration/_knowledge-graph|City & Geography Administration]] — the feature
  that owns the admin screen.
- [[City.technical|City]] — the parent; deleting one cascades here.

## Open Questions

- [x] **Where `RestBreakMaxPercentage` is enforced** — `StartBreakCommand.ValidateRestBreakPercentRuleAsync`
      (`Shared/TalabatkApplication/Commands/StartBreakCommand/StartBreakCommand.cs:214-244`), counting
      drivers on the same shift. Not in `DeliveryMen.StartBreak`, which is why the earlier pass missed it.
- [x] **Whether `AvailableDurationsMinutes` is validated as well-formed CSV** — yes, but only upstream, in
      both commands (rules 7, 8, 14). The entity itself would throw.
- [ ] Should 0 mean "no breaks allowed" rather than "no limit"? If the field is ever meant to express a
      total block, the sentinel needs to move to `null` and the column become nullable.
- [ ] Should a city without a configuration row inherit the created-row defaults (80%) instead of
      unlimited? That would make missing configuration the safe state.
- [ ] Is `BreakType` intended to become a real partition key, or should the column and the two unused
      parameters be dropped?
- [ ] `NotificationMinutesBeforeEnd` has no upper bound (rule 9) — should it be capped at the shortest
      available duration? Today it can exceed the break itself.
