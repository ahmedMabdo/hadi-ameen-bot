---
id: 8orders/delivery/delivery-man-operations/delivery-requests-and-suppliers
note_type: single
context: Delivery
feature: Delivery Man Operations
group: Delivery-Requests-and-Suppliers
covers: [DeliveryAsset, DeliveryAssetDeliveryMan, DeliveryBoxUnitSize, DeliveryComment, DeliveryInstruction, DeliveryInstructionDescription, DeliveryReason, DeliverySupplier, DeliverySuppliersCities, DeliveryZoneArea, NonDeliveryReason, RoboCall, RoboCallOrder, UnbanReason]
sources:
  - path: Shared/TalabatkLogic/TalabatkModels/DeliveryAsset.cs
    sha1: 8480b1654ed2
  - path: Shared/TalabatkLogic/TalabatkModels/DeliveryAssetDeliveryMan.cs
    sha1: c65f163ef81e
  - path: Shared/TalabatkLogic/TalabatkModels/DeliveryBoxUnitSize.cs
    sha1: 3b1c200be698
  - path: Shared/TalabatkLogic/TalabatkModels/DeliveryComment.cs
    sha1: 05359e0faec3
  - path: Shared/TalabatkLogic/TalabatkModels/DeliveryInstruction.cs
    sha1: 0bfd709a5cfd
  - path: Shared/TalabatkLogic/TalabatkModels/DeliveryInstructionDescription.cs
    sha1: cbd59023b430
  - path: Shared/TalabatkLogic/TalabatkModels/DeliveryReason.cs
    sha1: 1a7ce605b116
  - path: Shared/TalabatkLogic/TalabatkModels/DeliverySuppliersCities.cs
    sha1: fa61a37d9b86
  - path: Shared/TalabatkLogic/TalabatkModels/NonDeliveryReason.cs
    sha1: 9b2e11255e05
  - path: Shared/TalabatkLogic/TalabatkModels/RoboCall.cs
    sha1: ffb4771ff313
  - path: Shared/TalabatkLogic/TalabatkModels/RoboCallOrder.cs
    sha1: e3a748094e95
  - path: Shared/TalabatkLogic/TalabatkModels/UnbanReasons.cs
    sha1: dfceaffd61dc
  - path: Shared/TalabatkLogic/TalabatkModels/DeliverySupplier.cs
    sha1: 8f2012d576fb
  - path: Shared/TalabatkLogic/TalabatkModels/DeliveryZoneArea.cs
    sha1: 1a5481a9679b
  - path: Shared/TalabatkLogic/TalabatkModels/ExternalDeliveryRequests.cs
    sha1: a4270e1aed4b
last_updated: 2026-08-23
tags: [delivery, master, technical, backend-domain]
---
# ExternalDeliveryRequests, DeliveryZoneArea, DeliverySupplier

Three lighter Delivery-context entities, grouped here rather than given full separate treatment.

## ExternalDeliveryRequests
A delivery request for a merchant using the platform purely for delivery fulfillment (not routed
through the normal Order flow) — ties to `DeliveryMen.IsExternalDelivery`/`ExternalDeliveryCashLimit`
and `DeliverymanTransaction`'s external-order comment flag.
`Shared/TalabatkLogic/TalabatkModels/ExternalDeliveryRequests.cs`. No validation in `Instance` —
plain field assignment. `Cancel()` and `SetOrderId(orderId)` are the only two behaviors.

## DeliveryZoneArea
The fee/time configuration for one `Area` within a `DeliveryZone` — customer/delivery-man/external
delivery fees and an expected delivery time. `Shared/TalabatkLogic/TalabatkModels/DeliveryZoneArea.cs`.
No validation in either `Instance` or `Update` — unlike `DeliveryZone` itself (which has a
create/update asymmetry, see `_system/_conflicts.md` #13), here **neither** path validates, so
there's no asymmetry to flag, just an overall lack of guards on fee/time values (e.g. nothing stops a
negative fee).

## DeliverySupplier
A third-party delivery provider a city can contract with, with its own delivery men and cash limit.
`Shared/TalabatkLogic/TalabatkModels/DeliverySupplier.cs`.

- **⚠️ Confirmed bug — `Instance` crashes on a null name instead of validating it:**
  `DeliverySupplier.cs:33-35` runs `string actualName = name.Trim();` **before** the
  `string.IsNullOrEmpty(name)` guard on the very next line — if `name` is `null`, `.Trim()` throws an
  unhandled `NullReferenceException`, so the intended `Result.Failure("Supplier name can't be
  null.")` path is unreachable for the null case (it would still work for an empty string, since
  `"".Trim()` doesn't throw).
- `Instance` (`:26-55`) otherwise validates: at least one city, at least one delivery man, and a
  non-negative cash limit.
- **`UpdateDeliverySupplier` has none of `Instance`'s validation** (`:56-65`) — no name/city/delivery-man
  checks — another instance of the create-validates/update-doesn't asymmetry seen elsewhere in this
  codebase (`DeliveryZone`, `City.OneRestaurantPerOrder`).

## Folded entities — the 12 further satellites documented here

The rest of what this group covers. Unusually for this codebase, **most of these validate** — the
"reason" entities in particular are among the most consistently guarded in the repository.

### Reasons — the well-behaved family

| Entity | What it is | Rules |
|---|---|---|
| `NonDeliveryReason` | Why an order was not delivered, and whether it bans the driver | Eight guards across four methods, and create and update agree exactly: `Instance` requires a name, a description and a creator (`Shared/TalabatkLogic/TalabatkModels/NonDeliveryReason.cs:26-32`); `Update` requires the same with a modifier (`:50-56`); `UpdateAdminStatus` (`:72`) and `UpdateDriverStatus` (`:90`) each require a modifier. `IsResultBan` is the consequential field — this is the table that decides whether a non-delivery costs a driver their account — and `IsForAdmin`/`IsForDriver` control who may select the reason |
| `UnbanReason` | Why a banned driver was reinstated | Same shape, same rigour: name, description and creator on create (`Shared/TalabatkLogic/TalabatkModels/UnbanReasons.cs:22-28`), name, description and modifier on update (`:43-49`), modifier on `UpdateActivityStatus` (`:63`). Full audit columns. Note the file is `UnbanReasons.cs` while the class is singular |
| `DeliveryReason` | A driver-facing reason, Arabic only | The counter-example in the same family: two properties, `Instance` (`Shared/TalabatkLogic/TalabatkModels/DeliveryReason.cs:15`) and a `void Update` (`:23`), **no guards and no audit columns**. `ReasonAr` is the only text field, so this reason type has no English at all |

### Driver equipment

| Entity | What it is | Rules |
|---|---|---|
| `DeliveryAsset` | A piece of equipment a driver can be issued, with a unit cost | Guards on both paths and both fields: `Instance` requires a name and a non-negative cost (`Shared/TalabatkLogic/TalabatkModels/DeliveryAsset.cs:37`, `:42`), and `UpdateItemName`/`UpdateUnitCost` repeat the same two checks (`:58`, `:69`). The three collection methods — `AddDeliveryMan` (`:76`), `RemoveDeliveryMan` (`:91`), `ClearDeliveryMen` (`:100`) — are unguarded `void`s |
| `DeliveryAssetDeliveryMan` | One asset issued to one driver, with the cost and year at issue | `Instance` only, no guards (`Shared/TalabatkLogic/TalabatkModels/DeliveryAssetDeliveryMan.cs:21`). It copies `Cost` onto the row, so a later change to the asset's unit cost does not rewrite what a driver owes — which is what makes the dismissal settlement in `DriverDismissalLog` reproducible |
| `DeliveryBoxUnitSize` | A delivery-box size and how many units it holds | Private ctor and a `void Update` (`Shared/TalabatkLogic/TalabatkModels/DeliveryBoxUnitSize.cs:22`), no guards, and **no public factory** — rows come from EF or a seed |

### Delivery instructions shown to the customer

| Entity | What it is | Rules |
|---|---|---|
| `DeliveryInstruction` | A selectable instruction ("leave at the door") with an icon | `Instance` requires a reference name, at least one description **and** an icon (`Shared/TalabatkLogic/TalabatkModels/DeliveryInstruction.cs:28-34`); `UpdateIcon` (`:49`) and `UpdateReferenceName` (`:58`) each guard their own field. One of the few entities here that requires its child collection to be non-empty at construction |
| `DeliveryInstructionDescription` | An instruction's text in one language | `Instance` validates the **language id** as well as the name (`Shared/TalabatkLogic/TalabatkModels/DeliveryInstructionDescription.cs:24`, `:27`) — the only per-language description type in the whole repository that checks the language id rather than trusting it. `UpdateName` guards too (`:40`) |

### Robocalls

| Entity | What it is | Rules |
|---|---|---|
| `RoboCall` | An automated outbound call, with timings, type, status and an optional parent call | `Instance` requires a call id, a phone number and at least one attached order (`Shared/TalabatkLogic/TalabatkModels/RoboCall.cs:57`, `:62`, `:67`) — but the phone-number guard reports **"Call Id is Required"**, so a rejection misnames the field at fault (🟡 `_conflicts.md` #634). `Update` is an unguarded `void` (`:86`). `ParentRoboCallId` makes retries a chain rather than separate rows |
| `RoboCallOrder` | Links a robocall to the order it was about | Four fields, `Instance` only (`Shared/TalabatkLogic/TalabatkModels/RoboCallOrder.cs:17`). `RoboCall.Instance` requires at least one of these, which is why the two are always created together |

### Supplier and order notes

| Entity | What it is | Rules |
|---|---|---|
| `DeliverySuppliersCities` | Which cities a delivery supplier serves | `Instance` returns `Result` but cannot fail (`Shared/TalabatkLogic/TalabatkModels/DeliverySuppliersCities.cs:19`) |
| `DeliveryComment` | A free-text note against an order from the delivery side | `Instance` only, no guards (`Shared/TalabatkLogic/TalabatkModels/DeliveryComment.cs:24`). The delivery-side twin of `OrderComment`, with the same shape and the same absence of rules |

### What the split means

This group inverts the pattern seen everywhere else. Seven of these twelve validate on both the create
and the update path, and two — `NonDeliveryReason` and `UnbanReason` — carry full audit columns and
require a named actor for every mutation, which is appropriate given that they gate whether a driver
keeps their account. The gaps are narrow and specific: `DeliveryReason` has no rules and no English text
at all while its two siblings have both, and `RoboCall`'s phone-number guard reports the wrong field.

## Related
- [[DeliveryMen.technical|DeliveryMen]] — external delivery flags, supplier assignment
- [[DeliveryZone|DeliveryZone]] — parent of `DeliveryZoneArea`
- [[Area-and-Country|Area]] — the other side of `DeliveryZoneArea`

## Open Questions
- [ ] Whether the `DeliverySupplier.Instance` null-name crash (vs. the intended validation message)
  has ever been hit in practice — not verified.
- [ ] Who calls `ExternalDeliveryRequests.Instance`/`Cancel`/`SetOrderId` — not traced.
