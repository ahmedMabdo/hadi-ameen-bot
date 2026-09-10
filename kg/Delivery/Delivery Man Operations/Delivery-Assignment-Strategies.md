---
id: 8orders/delivery/delivery-man-operations/delivery-assignment-strategies
note_type: single
context: Delivery
feature: Delivery Man Operations
group: Delivery-Assignment-Strategies
covers: [AutoAssignRequest, AvilableDeliveryMan]
sources:
  - path: Shared/TalabatkLogic/TalabatkModels/AutoAssignRequest.cs
    sha1: 9126e401d976
  - path: Shared/TalabatkLogic/TalabatkModels/AvilableDeliveryMan.cs
    sha1: 2f8fe2ca9db9
last_updated: 2026-08-23
tags: [delivery, transactional, technical, backend-domain]
---
# Delivery Assignment Strategies & Profit Calculation

Covers `Shared/TalabatkLogic/CreateOrderDeliveryRequestStrategies/`,
`Shared/TalabatkLogic/DeliveryRequestAssignementStratgies/`, and the profit-calculation
`DomainServices` — the machinery deciding how a multi-restaurant order gets split across delivery
men, and how much each earns.

## The two strategy families
Two distinct decision points, each a classic Strategy pattern with a factory:

1. **Creating delivery requests** (`CreateOrderDeliveryRequestStrategies/`, `IOrderDeliveryStrategy`) —
   how a new order gets carved into one or more `OrderDelivery` requests in the first place.
   `DistributedOrderDeliveryStrategy` (read in full, `:15-58`) — for a multi-restaurant order,
   creates one `OrderDelivery` request per requested delivery man, each pre-assigned exactly one of
   the requested restaurants, with an initial company/delivery-man profit split from
   `DeliverymenProfitCalculator.GetInitialCompanyAndDeliveryManProfitForOrderDelivery`. Siblings
   `ParentOrderDeliveryStrategy`, `PrimmaryOrderDeliveryStrategy`, `SupporterOrderDeliveryStrategy`,
   `NotSupporterNorPrimmaryOrderDeliveryStrategy` were not opened in full in this pass (same naming
   pattern as the assignment strategies below — presumably each handles one role's request-creation
   variant).
2. **Assigning a confirmed delivery man to a request** (`DeliveryRequestAssignementStratgies/`,
   `IDeliveryAssignmentStrategy`) — picked by `DeliveryAssignementStrategyFactory.GetStrategy(orderDelivery)`
   (`:12-30`) based on `DeliveryManParentId`/`IsSupporter`/`IsPrimary`:
   - No parent → `ParentDeliveryManAssignementStrategy` (the order's original/owning delivery man)
   - Has parent + `IsSupporter` → `SupporterDeliveryManAssignementStrategy`
   - Has parent + `IsPrimary` → `PrimmaryDeliveryAssignementStrategy`
   - Has parent, neither flag → `NotSupportNotPrimmaryDeliveryAssignementStrategy`
   - **`PrimmaryDeliveryAssignementStrategy`** (read in full, `:11-57`) — assigns the delivery man,
     then removes the just-assigned request's restaurants from every **other** delivery under the
     same parent (the parent itself, and any of its other supporters) — coordinating a split order so
     the same restaurant isn't double-handled by two delivery men working the same parent order.

## Profit calculation (`DomainServices/`)
- **`DeliverymenProfitCalculator.GetInitialCompanyAndDeliveryManProfitForOrderDelivery`** (`:14-26`) —
  for an external delivery order, splits `DeliveryFees` by `externalDeliveryProfitPercentage`
  (company share) with the remainder to the delivery man; for a normal order, the **entire**
  delivery fee initially goes to the delivery man (company profit starts at `0`).
- **`DeliverymenProfitCalculator.Calculate`** (`:28-107`) — the full per-delivery profit
  recalculation, run per `New`-status `OrderDelivery`:
  - No-ops entirely for external delivery orders (`:30-34`).
  - Tips are split evenly across however many simultaneous deliveries exist for the order
    (`order.Tips / orderDeliveries.Count`).
  - `ExtraRestaurantDeliveryFees` only applies **if there's exactly one delivery** for the order
    (`:46`) — a multi-way split order doesn't get the extra fee at all, not divided among them.
  - Picks the **best-paying zone** among the restaurants covered by this delivery
    (`OrderByDescending(x => x.DeliveryManProfit).FirstOrDefault()`, `:66-68`) — not the delivery's
    own assigned restaurant necessarily, but whichever zone-profit figure is highest among the
    candidates.
  - **Address-changed recompute** (`:73-76`, `:85-95`) preserves the delivery man's already-earned
    profit component from before the address change and layers the new zone's profit on top, rather
    than recomputing from scratch — a deliberate "don't retroactively shrink what they'd already
    earned" design.
  - An optional `IDeliveryManPricingCalculator` plugin can adjust the zone profit by a percentage
    (`:79-103`) — dynamic/demand-based pricing, injected rather than hardcoded; also writes the
    adjustment back onto the order itself (`order.SetDeliveryManPricing`).
- **`CompanyProfitCalculator.CalculateProfit`** (`:9-20`) — much simpler: sums `OrderDetails.ProfitValue`
  per restaurant into that restaurant's `OrderRestaurantDetails.UpdateProfit`. The company-side
  counterpart to the delivery-man profit math above.

## Folded entities — the 2 satellites documented here

| Entity | What it is | Rules |
|---|---|---|
| `AutoAssignRequest` | One offer of an order to one driver, with a status and an expiry | `Instance` (`Shared/TalabatkLogic/TalabatkModels/AutoAssignRequest.cs:16`), `SetExpiration` (`:27`), `MarkAsAccepted` (`:32`) and `MarkAsRejected` (`:38`) — four state transitions, **no guards on any of them**, so a request can be accepted after it was rejected or after it expired. Whether `Status` reaching `Timeout` reliably triggers a reassignment is the open question behind 🔴 `_conflicts.md` #3; the entity itself imposes no ordering, so the guarantee has to come from the scheduler |
| `AvilableDeliveryMan` | A read-only projection of drivers currently available | Eight lines, one property — `DeliveryManId` with a **private setter and no factory** (`Shared/TalabatkLogic/TalabatkModels/AvilableDeliveryMan.cs:7`), so nothing in C# can populate it. It is a mapped `DbSet` (`Shared/TalabatkApplication/ITalabatkContext.cs:204`) with its own EF configuration, i.e. a query-result type rather than a domain entity. Worth knowing for two reasons: the assignment strategies read it as their candidate pool, and the class and its mapping spell "available" **differently** — `AvilableDeliveryMan` versus `AvalibleDeliveryManMaping` — so a grep for either name finds only half the pair |

## Related
- [[OrderDelivery.technical|OrderDelivery]] — the entity these strategies create/mutate
- [[DeliveryMen.technical|DeliveryMen]]

## Open Questions
- [ ] The four sibling strategies in each family not opened in full (`Parent`/`Supporter`/
  `NotSupportNotPrimmary` variants on both sides) — the one read in full per family is representative
  but not necessarily identical in shape to its siblings.
- [ ] `IDeliveryManPricingCalculator`'s concrete implementation(s) not located in this pass.
- [ ] `UpdateHoldedOrderJob` (`Shared/TalabatkLogic/HangfireJobs/`) — a Hangfire job payload
  (`OrderId` + `confirmDate`) implying a "held order" auto-confirm mechanism; its handler/scheduler
  wasn't traced.
