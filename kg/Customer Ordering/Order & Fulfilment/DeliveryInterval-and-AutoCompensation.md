---
id: 8orders/customer-ordering/order-and-fulfilment/deliveryinterval-and-autocompensation
note_type: single
context: Customer Ordering
feature: Order & Fulfilment
sources:
  - path: Shared/TalabatkLogic/TalabatkModels/Order.cs
    sha1: a8504688c441
  - path: TalabatkAPIs/Controllers/AutoCompensation/AutoCompensationRulesController.cs
    sha1: e577966ea9ce
  - path: TalabatkAPIs/Controllers/Deliveryintevral/DeliveryIntervalController.cs
    sha1: bc6bfacf4138
last_updated: 2026-08-23
tags: [customer-ordering, order-fulfilment, light, backend-application]
---
# Delivery Interval & Auto-Compensation

## Delivery Interval (`TalabatkAPIs/Controllers/Deliveryintevral/DeliveryIntervalController.cs`)
**Finding, not a full feature write-up:** this controller has **zero action methods** — just a
constructor injecting `IMediator` and a `TimeZoneHelper` that's never used. Either scheduled-delivery
interval selection isn't actually exposed through this controller (dead/in-progress code), or it's
exposed elsewhere under a different route not found in this pass. `GetIntervalQuery` exists in
`Shared/TalabatkApplication/Queries/GetIntervalQuery/` (referenced by this controller's `using`) but
nothing in this controller calls it. Worth confirming with the team before assuming this is simply
unfinished — flagged in `Order.technical.md`'s Open Questions too.

## Auto-Compensation (`TalabatkAPIs/Controllers/AutoCompensation/AutoCompensationRulesController.cs`)
One read-only endpoint: `GetActiveRules` (`api/auto-compensation/active-rules`) →
`GetActiveAutoCompensationRulesQuery`. Returns the currently active auto-compensation rules
(presumably rules for automatically compensating a customer when something goes wrong with their
order — late delivery, unavailable items, etc.) so the mobile app can display them. The rules
themselves are configured elsewhere (likely Admin, not verified in this pass); the actual
compensation-application logic likely lives inside `Order.cs`'s `AddNewCompensation` method
(`Order.cs:1480`, not documented in this pass — see `Order.technical.md`'s scope note).

## Open Questions
- [ ] Confirm whether `DeliveryIntervalController` being action-less is intentional/in-progress or
  a bug.
- [ ] Where Auto-Compensation rules are configured (which host) wasn't verified.
- [ ] `Order.AddNewCompensation` itself wasn't documented — likely belongs with a future
  Admin/Delivery pass on `Order`'s compensation slice.

## Related
- [[Order.technical|Order]] — where compensation is actually applied (not covered in this pass).
