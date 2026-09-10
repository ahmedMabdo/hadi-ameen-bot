---
id: 8orders/admin/delivery-administration/deliveryannouncement-and-notification
note_type: single
context: Admin
feature: Delivery Administration
sources:
  - path: Shared/TalabatkLogic/DeliveryAnnouncementAggregate/DeliveryAnnouncement.cs
    sha1: a76bd37f02b4
  - path: Shared/TalabatkLogic/DeliveryManNotificationAggregate/DeliveryManNotification.cs
    sha1: 869546a4890e
last_updated: 2026-08-23
tags: [admin, delivery, transactional, technical, backend-domain]
---
# DeliveryAnnouncement & DeliveryManNotification

Two mature, proper DDD aggregates (private constructor, validated `Create`/`Update`, `Result`
returns) — confirming the earlier claim that these two match Tiered Discount's rigor.
`Shared/TalabatkLogic/DeliveryAnnouncementAggregate/DeliveryAnnouncement.cs`,
`Shared/TalabatkLogic/DeliveryManNotificationAggregate/DeliveryManNotification.cs`.

## DeliveryAnnouncement
A city-scoped announcement/notice shown to delivery men, with two mutually-exclusive modes.

- **Two modes selected by `IsAnnouncement`:** if `true`, title/description are cleared and an image
  is **required** (`SetImageUrl`, `Shared/TalabatkLogic/DeliveryAnnouncementAggregate/DeliveryAnnouncement.cs:123-132`, fails without one); if `false`, title/description in
  both languages are required and the image is force-cleared. Not a bug — a deliberate "pure image
  banner" vs. "titled text notice" split, enforced by `Validate` (`Shared/TalabatkLogic/DeliveryAnnouncementAggregate/DeliveryAnnouncement.cs:134-178`) and `SetImageUrl` acting
  in concert.
- **Overlap detection is caller-computed, not internal:** `Create`/`Update` both take a
  `hasOverlappingAnnouncement` bool parameter and simply fail if it's `true` (`Shared/TalabatkLogic/DeliveryAnnouncementAggregate/DeliveryAnnouncement.cs:173-174`) — the actual
  date/city overlap query happens upstream (Application layer, not traced), not on this aggregate.
- `EndDate` must be strictly after `StartDate` (`Shared/TalabatkLogic/DeliveryAnnouncementAggregate/DeliveryAnnouncement.cs:170-171`).

## DeliveryManNotification
A broadcast notification to a set of delivery men, scoped to a city (required) and optionally a
zone, optionally scheduled.

- **Locked once sent:** `Update` (`Shared/TalabatkLogic/DeliveryManNotificationAggregate/DeliveryManNotification.cs:91-145`) immediately fails if `Status != Pending` (`Shared/TalabatkLogic/DeliveryManNotificationAggregate/DeliveryManNotification.cs:104-105`) —
  a sent notification can never be edited.
- **Scheduled notifications must be dated in the future:** `Validate` (`Shared/TalabatkLogic/DeliveryManNotificationAggregate/DeliveryManNotification.cs:175-203`) requires
  `scheduledDate.Value > dateTimeNow` when `isScheduled` is true.
- **⚠️ Worth flagging — `Update`'s `isScheduled` parameter is accepted but unused for its own field:**
  `IsScheduled` is actually set from `scheduledDate.HasValue` (`Shared/TalabatkLogic/DeliveryManNotificationAggregate/DeliveryManNotification.cs:128`), not from the `isScheduled`
  argument itself, in both `Create` (`Shared/TalabatkLogic/DeliveryManNotificationAggregate/DeliveryManNotification.cs:76`) and `Update` (`Shared/TalabatkLogic/DeliveryManNotificationAggregate/DeliveryManNotification.cs:128`) — meaning the explicit `isScheduled`
  flag passed in only participates in *validation* (Rule above), while the *stored* flag is always
  derived from whether a date was given. Not confirmed whether callers ever pass a value for
  `isScheduled` that disagrees with `scheduledDate.HasValue` — if they do, the validation and the
  stored state could tell different stories.
- **Send-time recipient filtering, not creation-time:** `MarkAsSent(deliveryMenInShift, ...)`
  (`Shared/TalabatkLogic/DeliveryManNotificationAggregate/DeliveryManNotification.cs:148-172`) only marks the notification-detail rows **actually delivered** to whichever delivery
  men from the original list are in `deliveryMenInShift` at send time — a delivery man on the original
  list who isn't in shift when the job actually runs is simply not marked sent (their detail row
  presumably stays pending, though no failure is raised for them individually).
- `GetJobId()` (`Shared/TalabatkLogic/DeliveryManNotificationAggregate/DeliveryManNotification.cs:205`) — a deterministic Hangfire job id (`"DeliveryManNotification_{id}"`), implying
  scheduled notifications are dispatched via a matching Hangfire job (not traced further in this pass).

## Related
- [[DeliveryMan-Attendance|DeliveryMan Attendance & Shifts]] — `MarkAsSent`'s shift-filtering
- [[City.technical|City]]

## Open Questions
- [ ] Whether `isScheduled` vs. `scheduledDate.HasValue` (the flagged point above) ever actually
  disagree in practice.
- [ ] Who computes `hasOverlappingAnnouncement` and the Hangfire job that dispatches scheduled
  `DeliveryManNotification`s — neither traced in this pass.
