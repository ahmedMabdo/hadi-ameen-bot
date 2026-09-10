---
id: 8orders/identity-and-access/customer-identity/customeraddresses
note_type: single
rule_count: 7
context: Identity & Access
feature: Customer Identity
entity: CustomerAddresses
entity_type: child
sources:
  - path: Shared/TalabatkApplication/Commands/UpdateCustomerAddressCommand/UpdateCustomerAddressCommand.cs
    sha1: 2df348aae4aa
  - path: Shared/TalabatkLogic/TalabatkModels/CustomerAddresses.cs
    sha1: 039d81d75d83
last_updated: 2026-08-23
tags: [identity-access, customer, child, technical, backend-domain]
---
> [!important] Superseded — see [[CustomerAddress.technical\|CustomerAddress (canonical)]]
> This is the original **domain-model** note for the `CustomerAddresses` POCO. A fuller entity note was
> written in Round 5 at `Identity & Access/CustomerAddress/CustomerAddress.technical.md` (48 citations,
> 8 numbered rules) before anyone checked that this file existed — my error, logged as part of #433.
> Both are kept rather than one deleted: **this file's observations about the class itself are not
> duplicated there**, and its Open Question turned out to matter. Read the canonical note for behaviour
> and findings; read this one for the POCO's own oddities below.
>
> **Its first Open Question is now answered, and the answer is a confirmed high-severity defect.** This
> note asked whether `UpateAddress`'s ability to reassign `CustomerId` is "ever actually exercised".
> It is: `UpdateCustomerAddressCommand.cs:47` looks the row up by `UserAddressId` **alone** and `:63`
> writes the caller-supplied `CustomerId` onto it — cross-account address overwrite and ownership
> transfer, logged as **#400**. The suspicion recorded here as an unknown was correct.

# CustomerAddresses

A saved delivery address belonging to a [[Customer.technical|Customer]]. The one-default-per-customer
invariant is enforced on `Customer`, not here (see `Customer.technical.md` Rule 6) — this class has no
guard of its own against multiple defaults; it's a pure record with several overlapping update paths.
`Shared/TalabatkLogic/TalabatkModels/CustomerAddresses.cs`.

## Notable oddities (not confirmed as live bugs, but worth flagging)
- **Two identical-effect default-setters:** `SetAsDefault(bool)` (`:136-139`, `void`) and
  `SetIsDefault(bool)` (`:142-146`, returns `Result.Success()`) do exactly the same assignment —
  likely incidental duplication from two different call sites being added independently.
- **`UpateAddress` (note the typo — missing "d") lets a caller reassign the address's own primary key
  and owning customer** (`:83-102`, takes `UserAddressId` and `CustomerId` as parameters and
  reassigns both) — every other update method (`UpdateAddressDetails`, `:105-126`) only touches
  content fields. Reassigning `CustomerId` through an "update" call reads as an unusual surface for a
  change request to touch carefully; not confirmed whether any caller actually changes these values
  in practice or always passes them back unchanged.
- **No validation anywhere in this class** — `Instance`, `UpateAddress`, and `UpdateAddressDetails`
  all just assign fields; contrast `Customer.AddNewAddress`'s default-clearing guard, which lives on
  the parent, not here.
- **Two different address-creation paths:** a public constructor (`:35-57`, takes an already-built
  `Geometry`) used by `Customer.AddNewAddress`/the guest-merge address copy, and the static `Instance`
  factory (`:58-80`, takes raw `latitude`/`longtitude` and builds the `Geometry` itself via
  `GeomeryFactoryCustom`) used elsewhere (not traced in this pass) — both produce the same shape, just
  via different entry points.

## Key Fields
| Field | Meaning |
|-------|---------|
| `CustomerId` | Owning customer (nullable — not confirmed why an address could exist without one) |
| `AreaId` → `TA_Area` | Geographic area — see [[Area-and-Country\|Area]] |
| `location` (`Geometry`) | Pin location |
| `IsDefault` | Default-address flag — invariant enforced on `Customer`, not here |
| `IsDelete` | Soft-delete flag, nullable |

## Rule / Decision Matrix

A saved delivery address. Seven methods, four returning `Result`, and **not one of them can fail** — the `Result` here is shape without substance, which matters because this is the entity behind the largest IDOR cluster in the register.

| # | Rule | Where | Notes |
|---|---|---|---|
| 1 | `Instance` returns `Result<CustomerAddresses>` and has no failure path | `Shared/TalabatkLogic/TalabatkModels/CustomerAddresses.cs:58` | No check on area, coordinates or description |
| 2 | `UpateAddress` (misspelt) returns `Result` and cannot fail | `Shared/TalabatkLogic/TalabatkModels/CustomerAddresses.cs:83` | The spelling matters when searching |
| 3 | `UpdateAddressDetails` is a second, differently-scoped update path | `Shared/TalabatkLogic/TalabatkModels/CustomerAddresses.cs:105` | Building, floor and apartment; also unguarded |
| 4 | Deletion is soft | `Shared/TalabatkLogic/TalabatkModels/CustomerAddresses.cs:129` | `SetIsDeleted` flips `IsDelete` (singular, misspelt) — so order history keeps its address |
| 5 | Two ways to set the default address | `Shared/TalabatkLogic/TalabatkModels/CustomerAddresses.cs:136-142` | `SetAsDefault` (`void`) and `SetIsDefault` (`Result`) — nothing enforces that only one address is default |
| 6 | The area link is what ties an address to coverage and fees | `Shared/TalabatkLogic/TalabatkModels/CustomerAddresses.cs:58` | `AreaId` plus a geographic `location`; the area decides whether anything can be delivered at all |
| 7 | No ownership check exists in the entity | `Shared/TalabatkLogic/TalabatkModels/CustomerAddresses.cs:58` | `CustomerId` is a plain property. Every guarantee that an address belongs to its caller lives in the handlers — which is why #227, #350, #366 and #400 are all about this one entity |

## Related
- [[Customer.technical|Customer]] — owns the one-default invariant (Rule 6)
- [[Area-and-Country|Area (+ Country)]]

## Open Questions
- [ ] Whether `UpateAddress`'s `CustomerId`/`UserAddressId` reassignment capability is ever actually
  exercised, or always a no-op reassignment of the same values.
- [ ] Which callers use `Instance` vs. the public constructor.
