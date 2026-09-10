---
id: 8orders/delivery/delivery-man-operations/deliverymannotification-business
title: DeliveryManNotification
note_type: business
context: Delivery
feature: Delivery Man Operations
entity: DeliveryManNotification
entity_type: aggregate-root
last_updated: 2026-08-23
tags: [delivery, delivery-man-operations, transactional, business]
---
# Delivery Man Notification

A message pushed to delivery drivers' phones — for a whole city or a single delivery zone, now or at a
chosen time — with a record of who received it and who read it.

## What it is

When 8Orders needs drivers to *actually be told* something, it sends a notification. Unlike an
announcement (which simply appears in the app when a driver happens to look), a notification is pushed
to the phone, and the system keeps a row per driver so it can answer "did this reach them, and did they
open it?"

A notification is written in Arabic and English, aimed at a city — optionally narrowed to one delivery
zone — and either sent immediately or scheduled for a future moment.

## Business rules (plain words)

- A notification must be complete in **both languages**: title and body, Arabic and English.
- It must name a **city**. A delivery zone is optional; leaving it out means the whole city.
- If it is scheduled, it must say **when**, and that moment must be **in the future**. You cannot
  schedule something for a time that has already passed.
- **Once sent, it cannot be edited.** There is no recall and no correction — a mistake has to be
  followed by a second notification.
- **It cannot be sent twice.** If the system retries the send (for example after a restart), the second
  attempt is refused rather than double-notifying every driver.
- **Only drivers who were on shift at the moment it fired are recorded as having received it.** This is
  the rule most worth understanding: who is *targeted* is decided when the notification is written, but
  who is *reached* is decided by who was actually working when it went out. A notification aimed at a
  city at 3am may legitimately reach very few people.
- A driver can dismiss a notification, which hides it without destroying the record, and a dismissed
  notification can no longer be marked as read.

## Who uses it

- **Roles:** 8Orders operations staff write and schedule notifications; delivery drivers receive them.
- **Screens:** the notifications page in the Admin back-office; the driver's notification list and the
  phone's push banner.

## Two things worth knowing before planning work here

**"Sent" and "received" are different facts, and reports can confuse them.** The notification itself is
marked as sent once the send has run. Each driver has a separate marker for whether it actually reached
them. Any report that counts "sent notifications" as "drivers reached" will overstate the number,
sometimes badly — if nobody was on shift, the notification still counts as sent.

**A notification that reaches nobody looks the same as one that reaches everyone.** If the list of
on-shift drivers is empty when the send fires, the notification is marked sent, no driver is marked as
having received it, and nothing records that the reach was zero.

## Related

- [[DeliveryAnnouncement.business|Delivery Announcement]] — the passive alternative: shown in the app for a
  date range, city-wide, with no per-driver tracking. Use an announcement for "should be visible", a
  notification for "must be told".
- [[DeliveryMen.business|Delivery Men]] — the recipients, and whose shift state decides reach.
- [[DeliveryZone|Delivery Zone]] — the optional narrower target.
- Technical detail: [[DeliveryManNotification.technical|DeliveryManNotification — technical]]
