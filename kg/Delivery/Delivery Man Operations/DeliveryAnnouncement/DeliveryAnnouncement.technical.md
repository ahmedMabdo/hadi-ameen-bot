---
id: 8orders/delivery/delivery-man-operations/deliveryannouncement-technical
title: DeliveryAnnouncement — Technical
note_type: technical
context: Delivery
feature: Delivery Man Operations
entity: DeliveryAnnouncement
entity_type: aggregate-root
side: backend-domain
rule_count: 8
last_updated: 2026-08-23
sources:
  - path: Shared/TalabatkLogic/DeliveryAnnouncementAggregate/DeliveryAnnouncement.cs
    sha1: a76bd37f02b4
tags: [delivery, delivery-man-operations, transactional, technical, backend-domain]
---
# DeliveryAnnouncement — Technical

> **Layer:** Domain — **Aggregate Root** (one of only 4 real DDD aggregates in the codebase)
> **Context:** Delivery (consumption) / Admin (management)   **Feature:** Delivery Man Operations
> **Source Path:** `Shared/TalabatkLogic/DeliveryAnnouncementAggregate/DeliveryAnnouncement.cs`
> **Last Updated:** 2026-08-23

A city-scoped, date-bounded message shown to delivery men — either a **titled announcement with text**
in both languages, or an **image-only banner**. One `IsAnnouncement` flag switches between those two
shapes and changes which fields are required, which is the single most important thing to understand
before touching it.

Until this note, this aggregate had **no documentation at all** despite being one of four genuine DDD
aggregates in the system: private constructor, static `Create` factory returning `Result<T>`, private
setters throughout, and all mutation through behaviour methods.

## The `IsAnnouncement` inversion — read this first

The flag's name is the opposite of what the code does with it:

| `IsAnnouncement` | Titles and descriptions | Image | What the driver sees |
|---|---|---|---|
| `false` | **Required** — all four language fields validated | forced to `string.Empty` | A titled text announcement |
| `true` | **Not required, and actively blanked** to `string.Empty` | **Required** | An image-only banner |

So `IsAnnouncement = true` means "this is an *image* banner, not a text announcement". The blanking is
unconditional: passing titles alongside `IsAnnouncement = true` silently discards them
(`DeliveryAnnouncement.cs:63-66` in `Create`, `:109-112` in `Update`). A caller that sets the flag and
supplies text will see its text vanish with no error.

## Business Rules

### Rule 1: A city is mandatory
- **Plain language:** An announcement always belongs to exactly one city; there is no global announcement.
- **Trigger:** `Create` and `Update`, via `Validate`.
- **Violation result:** `Result.Failure("City is required")`
- **Source:** `DeliveryAnnouncement.cs:145-146`
- **Note:** the parameter is a `Maybe<City>`, so absence is modelled explicitly rather than as a null id.

### Rule 2: Text announcements require all four language fields
- **Plain language:** A text announcement must have an Arabic title, an English title, an Arabic
  description and an English description — no partial bilingual content.
- **Trigger:** `Create`/`Update` when `IsAnnouncement` is `false`.
- **Violation result:** `Result.Failure("Arabic title is required")` / `"English title is required"` /
  `"Arabic description is required"` / `"English description is required"`
- **Source:** `DeliveryAnnouncement.cs:157-167`; the guard block is entered at `:150`
- **Note:** each field is `Trim()`-ed before the check (`:152-155`), so whitespace-only text is rejected.

### Rule 3: The end date must be strictly after the start date
- **Plain language:** An announcement cannot end when or before it starts — a zero-length window is rejected.
- **Trigger:** `Create` and `Update`.
- **Violation result:** `Result.Failure("End date must be greater than start date")`
- **Source:** `DeliveryAnnouncement.cs:170-171`
- **Note:** `<=`, so equal dates fail. There is **no** guard against a start date in the past — unlike
  `TieredDiscount`, which rejects one (`TieredDiscount.cs:233`). A back-dated announcement is legal here.

### Rule 4: One announcement per city per overlapping period
- **Plain language:** Two announcements for the same city cannot cover overlapping dates.
- **Trigger:** `Create` and `Update`.
- **Violation result:** `Result.Failure<DeliveryAnnouncement>("There is already an announcement for this city in the same date period.")`
- **Source:** `DeliveryAnnouncement.cs:173-174`
- **Note:** the aggregate does **not** compute the overlap. It receives a pre-computed
  `hasOverlappingAnnouncement` boolean from the caller (`:41`, `:90`), so the invariant is only as good
  as the query the application layer runs. That is a real seam: the rule lives here, the evidence for it
  lives in the handler.

### Rule 5: An image is required for an image banner
- **Plain language:** If it is an image banner, it must have an image.
- **Trigger:** `SetImageUrl`.
- **Violation result:** `Result.Failure("Image is required when IsAnnouncement is true")`
- **Source:** `DeliveryAnnouncement.cs:125-126`
- **Note:** `SetImageUrl` is a **separate call** from `Create`. So an image banner can be persisted with
  no image if the caller creates it and never calls `SetImageUrl` — the invariant is enforced per method,
  not at the aggregate boundary.

### Rule 6: A text announcement's image is discarded
- **Plain language:** Setting an image on a text announcement silently clears it rather than failing.
- **Trigger:** `SetImageUrl` when `IsAnnouncement` is `false`.
- **Violation result:** none — `ImageUrl` becomes `string.Empty` (`:129`).
- **Source:** `DeliveryAnnouncement.cs:129`

### Rule 7: `Update` re-runs every creation invariant
- **Plain language:** Editing is validated as strictly as creating.
- **Trigger:** `Update`.
- **Violation result:** the failure from `Validate` is returned unchanged (`:105-106`).
- **Source:** `DeliveryAnnouncement.cs:92-106`
- **Note:** `Update` **cannot change the city's own identity check** result — it re-validates, but
  `Serial` and `CreationDate`/`CreatedBy` are immutable after creation, which is correct.

### Rule 8: Audit fields are set by the aggregate, from caller-supplied time
- **Plain language:** Who created/updated it and when are always recorded.
- **Trigger:** `Create` sets `CreationDate`, `CreatedBy`, `UpdatedDate`, `UpdatedBy` all from the same
  values (`:71-74`); `Update` sets only the updated pair (`:117-118`).
- **Source:** `DeliveryAnnouncement.cs:71-74`, `:117-118`
- **Note:** the clock is injected (`dateTimeNow`, `updatedDate`) rather than read from `DateTime.Now`
  inside the aggregate — good for testability, and it means the caller decides "now".

## Rule / Decision Matrix

| # | Trigger (when) | Condition / guard | Outcome | Source |
|---|---|---|---|---|
| 1 | Create / Update | `maybeCity.HasNoValue` | rejected — "City is required" | `DeliveryAnnouncement.cs:145` |
| 2 | Create / Update, text mode | any of the 4 language fields blank after trim | rejected, field-specific message | `:157-167` |
| 3 | Create / Update | `endDate <= startDate` | rejected — "End date must be greater than start date" | `:170` |
| 4 | Create / Update | `hasOverlappingAnnouncement` true | rejected — overlap for this city | `:173` |
| 5 | SetImageUrl, banner mode | image null/whitespace | rejected — "Image is required when IsAnnouncement is true" | `:125` |
| 6 | SetImageUrl, text mode | — | image silently set to empty | `:129` |
| 7 | Create / Update, banner mode | — | titles and descriptions silently blanked | `:63-66`, `:109-112` |
| 8 | Create | — | serial, city, dates, audit fields set; `Result.Success` | `:59-77` |

## Key Fields

| Field | Meaning | Constraints |
|---|---|---|
| `DeliveryAnnouncementId` | Identity | private setter |
| `Serial` | Caller-supplied ordering/reference number | no guard — uniqueness is not enforced here |
| `AnnouncementTitleByArabic` / `ByEnglish` | Title per language | required in text mode, blanked in banner mode |
| `DescriptionByArabic` / `ByEnglish` | Body per language | same |
| `StartDate` / `EndDate` | Display window | `EndDate > StartDate`; past start dates allowed |
| `CityId` | Owning city | taken from `maybeCity.Value.CityId`, never from a raw id |
| `IsAnnouncement` | **Image-banner mode** when `true` | drives which fields are required |
| `ImageUrl` | Banner image | required in banner mode, forced empty in text mode |
| `CreationDate` / `CreatedBy` | Audit — creation | set once |
| `UpdatedDate` / `UpdatedBy` | Audit — last change | set on create and on every update |

## Status / State

No status field. Whether an announcement is *live* is derived from `StartDate`/`EndDate` against the
current time, by whoever queries it — the aggregate has no `IsActive` and no activation method, so
there is nothing to keep in step. That is a deliberate simplification worth knowing: you cannot
"deactivate" an announcement, only edit its dates or delete the row.

## Dependencies & Integrations

| Depends on / integrates | Side/Context | Via | Notes |
|---|---|---|---|
| [[City.technical\|City]] | Backend-Domain | `Maybe<City>` passed into `Create`/`Update` | The city object, not an id — so the caller must have loaded it |
| Overlap query | Backend-Application | `hasOverlappingAnnouncement` boolean | Rule 4's evidence is computed outside the aggregate |
| Admin management UI | Admin | `AdminUi/Controllers/DeliveryAnnouncementController/` | Where announcements are authored — see [[Admin/Delivery Administration/_knowledge-graph\|Delivery Administration]] |
| Driver app | Delivery | read on the driver's home screen | Consumption side |

## Change Surface

| Signal | Value | Notes |
|---|---|---|
| Direct dependents (Ring 1) | Admin authoring controller, driver-facing read query | |
| Sides touched | 3/5 | Domain · Application · API host (Admin) |
| Cross-context integrations | 1 | Admin authors, Delivery consumes |
| Domain events involved | 0 | This aggregate raises none |
| Hub? | no | |

## Related

- Business view: [[DeliveryAnnouncement.business|DeliveryAnnouncement]]
- [[DeliveryManNotification.technical|DeliveryManNotification]] — the *push* sibling: targeted,
  scheduled and delivered, where this one is passively displayed
- Also part of: [[Admin/Delivery Administration/_knowledge-graph|Delivery Administration]]

## Open Questions

- [ ] Who computes `hasOverlappingAnnouncement`, and does that query use the same city scope and
      inclusive/exclusive date semantics as Rule 3? A mismatch there would let overlaps through.
- [ ] Is `Serial` meant to be unique per city? Nothing enforces it.
- [ ] Can an image banner be created without ever calling `SetImageUrl` (Rule 5's seam)? If the handler
      does not call it, the invariant never runs.
- [ ] Are past-dated announcements intentional (Rule 3 has no past-date guard, unlike `TieredDiscount`)?
- [ ] Is there a delete path, given there is no deactivation?
