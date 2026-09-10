---
id: 8orders/delivery/delivery-man-operations/deliveryzone
note_type: single
rule_count: 7
context: Delivery
feature: Delivery Man Operations
entity: DeliveryZone
entity_type: child
sources:
  - path: Shared/TalabatkLogic/TalabatkModels/DeliveryZone.cs
    sha1: 37d7f375bc8f
last_updated: 2026-08-23
tags: [delivery, master, technical, backend-domain]
---
# DeliveryZone

A geographic delivery-assignment zone within a city — the unit delivery men are assigned to (via
`DeliverymanZone`) and that auto-assignment strategies operate over.
`Shared/TalabatkLogic/TalabatkModels/DeliveryZone.cs`.

## Business rules
- **Creation has no validation; update does.** `AddDeliveryZone(...)` (`:63-77`) assigns fields with
  no checks at all. `UpdateDeliveryZone(...)` (`:35-61`) requires both the English and Arabic name to
  be non-blank, rejecting otherwise (`Result.Failure`). This asymmetry — you can create an invalid
  zone but not save an update that makes it invalid — matches a previously-flagged, now-confirmed
  finding (an earlier, informal pass noted "DeliveryZone.Create has no guards while Update does";
  this pass confirms it directly, with citations).
- **`AutoAssign` mode changes are the only field change that raises a domain event.** `UpdateDeliveryZone`
  fires `DeliveryZoneModeChangedEvent` only when `this.AutoAssign != autoAssign` (`:50-53`) — renaming
  the zone or toggling `IsShortCutApp` raises nothing. `AutoAssign` presumably gates whether the
  zone's incoming delivery requests are picked up by the automatic assignment strategies
  (`CreateOrderDeliveryRequestStrategies`/`DeliveryRequestAssignementStratgies` — not yet documented,
  part of the aggregate/strategy folder batch).
- A zone has a real geo border (`ZoneBorder`, `Polygon`), set independently via `UpdateBorder(...)`
  (`:84-87`) — same "border set outside the main update method" shape as `Area.UpdateBorder`.

## Key Fields
| Field | Meaning |
|-------|---------|
| `CityId` → `ZoneCity` | Owning city |
| `AutoAssign` | Whether this zone's delivery requests are auto-assigned |
| `TA_DeliveryZoneArea` | The `Area`s that make up this zone |
| `DeliverymenZones` (`DeliverymanZone`) | Which delivery men are assigned to this zone |

## Rule / Decision Matrix

A named delivery zone inside a city, with a geographic border and the areas it contains. The border is the operational heart of it and is the one thing nothing validates.

| # | Rule | Where | Notes |
|---|---|---|---|
| 1 | English name required | `Shared/TalabatkLogic/TalabatkModels/DeliveryZone.cs:42` | On `UpdateDeliveryZone` |
| 2 | Arabic name required | `Shared/TalabatkLogic/TalabatkModels/DeliveryZone.cs:47` | Same method |
| 3 | `AddDeliveryZone` returns `Result<DeliveryZone>` but has **no** guard | `Shared/TalabatkLogic/TalabatkModels/DeliveryZone.cs:63` | So the create path accepts blank names the update path would refuse — the asymmetry runs the opposite way from most of this codebase |
| 4 | The zone border is set without validation | `Shared/TalabatkLogic/TalabatkModels/DeliveryZone.cs:84` | `UpdateBorder` is a `void`; nothing checks the polygon is closed, non-empty or inside the city |
| 5 | Areas are added one at a time, never removed | `Shared/TalabatkLogic/TalabatkModels/DeliveryZone.cs:79` | `AddNewDeliveryZoneArea` has no counterpart, so shrinking a zone means going around the entity |
| 6 | `AutoAssign` decides whether the zone participates in automatic driver assignment | `Shared/TalabatkLogic/TalabatkModels/DeliveryZone.cs:63` | Set at creation |
| 7 | `IsShortCutApp` scopes the zone to the shortcut app | `Shared/TalabatkLogic/TalabatkModels/DeliveryZone.cs:63` |  |

## Related
- [[City.technical|City]] — owning city
- [[DeliveryMen.technical|DeliveryMen]] — assigned via `DeliverymanZone`

## Open Questions
- [ ] What exactly `AutoAssign` gates — not traced to the strategy folders in this pass.
- [ ] `DeliveryZoneArea`, `DeliverymanZone` themselves not opened in full (only referenced).
