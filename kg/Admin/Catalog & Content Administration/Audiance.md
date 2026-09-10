---
id: 8orders/admin/catalog-and-content-administration/audiance
note_type: single
rule_count: 10
context: Admin
feature: Catalog & Content Administration
entity: Audiance
entity_type: child
sources:
  - path: Shared/TalabatkLogic/TalabatkModels/Audiance.cs
    sha1: 77baa8f36765
last_updated: 2026-08-23
tags: [admin, marketing, technical, backend-domain]
---
# Audiance (Audience Segmentation)

A marketing audience segment — a named, filterable group of customers, used to target campaigns
(ads, announcements, tiered discounts). `Shared/TalabatkLogic/TalabatkModels/Audiance.cs`.

## Business rules
- `Create(...)` (`:25-63`) requires Arabic name, English name, `createdBy`, and an `Operator`
  (presumably the filter-combination logic — AND/OR — stored as a raw string, not a typed enum).
- `Update(...)` (`:68-105`) re-validates the **same** four fields — a positive counter-example to
  several other entities in this pass where Update skips validation Create has (`DeliveryZone`,
  `DeliverySupplier`, `City.OneRestaurantPerOrder`) — here they stay in sync.
- `ApplyAfterCustomerRegestration` (note the repo's recurring "Regestration"/"Registeration" spelling
  variant, consistent with `Customer.RegisterationDate`) — a segment can optionally auto-include
  newly registered customers going forward, not just apply to the audience computed at creation time.
- Filters (`AudianceFilter`) and explicit member customers (`AudienceCustomer`) are two independent
  mechanisms on the same segment — a segment can be filter-defined, an explicit list, or presumably
  both at once; how the two combine (if both present) isn't specified in this class.
- `FilterJson` is set independently via `SetFilter(...)` (`:64-67`), outside the main
  `Create`/`Update` pair — same "set outside the main factory" shape as `Area.UpdateBorder`.

## Key Fields
| Field | Meaning |
|-------|---------|
| `Operator` | Raw string — filter combination logic, not a typed enum in this class |
| `FilterJson` | Serialized filter definition, set separately from `Filters` (the `AudianceFilter` collection) |
| `ApplyAfterCustomerRegestration` | Whether new registrants auto-join this segment |

## Rule / Decision Matrix

A campaign audience: a named segment with an operator, a filter set, and the customers it resolved to. Eleven methods, four guards, and a deliberate split between "create/update" (validated) and everything else (not).

| # | Rule | Where | Notes |
|---|---|---|---|
| 1 | Arabic name required on create | `Shared/TalabatkLogic/TalabatkModels/Audiance.cs:37` |  |
| 2 | English name required on create | `Shared/TalabatkLogic/TalabatkModels/Audiance.cs:40` |  |
| 3 | `CreatedBy` required on create | `Shared/TalabatkLogic/TalabatkModels/Audiance.cs:43` | So every audience is attributable |
| 4 | Operator required on create | `Shared/TalabatkLogic/TalabatkModels/Audiance.cs:46` | The operator is what makes the filter set mean AND rather than OR |
| 5 | `Update` re-checks all four | `Shared/TalabatkLogic/TalabatkModels/Audiance.cs:81-90` | A properly symmetric pair — rare here |
| 6 | `UpdateNamesAndDescription` checks nothing | `Shared/TalabatkLogic/TalabatkModels/Audiance.cs:107` | A second, unguarded path to the same two name fields that `Update` guards |
| 7 | Filters are held twice: as `FilterJson` and as a `Filters` collection | `Shared/TalabatkLogic/TalabatkModels/Audiance.cs:64` | `SetFilter` writes the JSON; `AddFilter`/`RemoveFilter`/`ClearFilters` (`:115`, `:124`, `:153`) manage the rows. Nothing keeps the two in step |
| 8 | Membership is mutable in place | `Shared/TalabatkLogic/TalabatkModels/Audiance.cs:133-151` | `AddCustomer`, `RemoveCustomer`, `ClearCustomers` — no guards, so a resolved audience can be edited after a campaign has used it |
| 9 | Deletion is soft | `Shared/TalabatkLogic/TalabatkModels/Audiance.cs:159` | `SetAsDeleted` flips `IsDeleted`; campaign history survives |
| 10 | `ApplyAfterCustomerRegestration` decides whether new registrants join automatically | `Shared/TalabatkLogic/TalabatkModels/Audiance.cs:25` | Set at creation; no method changes it afterwards |

> The **operator semantics** are where 🔴 `_conflicts.md` #423 lives: a filter meaning "exactly N days"
> selects everyone within N days, so campaigns reach a wider audience than marketing intends. That is a
> property of how the filter is evaluated, not of this entity — which is why the entity looks clean and
> the campaign still misfires.

## Related
- Referenced by Tiered Discount's segment/allow-list mechanism ([[TieredDiscountTier|TieredDiscountTier]]) and Marketing & Content targeting — not cross-verified in this pass.

## Open Questions
- [ ] How `Filters` (structured) and `FilterJson` (serialized) relate — duplicate representations of
  the same thing, or is one a cache/snapshot of the other?
- [ ] How filter-based and explicit-customer-list membership combine, if both are present.
- [ ] `AudianceFilter`, `AudienceCustomer` not opened in full.
