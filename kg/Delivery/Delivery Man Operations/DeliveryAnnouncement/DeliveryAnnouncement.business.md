---
id: 8orders/delivery/delivery-man-operations/deliveryannouncement-business
title: DeliveryAnnouncement
note_type: business
context: Delivery
feature: Delivery Man Operations
entity: DeliveryAnnouncement
entity_type: aggregate-root
last_updated: 2026-08-23
tags: [delivery, delivery-man-operations, transactional, business]
---
# Delivery Announcement

A message 8Orders shows to delivery drivers in one city, for a set period — either a written notice or
a picture.

## What it is

When 8Orders needs to tell drivers something — a new bonus scheme, a road closure, a change to how a
zone works — it publishes an announcement for a city and a date range. Drivers in that city see it in
their app while it is current; after the end date it stops appearing.

An announcement comes in two forms, and it is one or the other, never both:

- **A written notice** — a title and a body, in Arabic and English.
- **A picture** — an image banner with no text, used for campaign artwork.

## Business rules (plain words)

- Every announcement belongs to **one city**. There is no way to announce something to all drivers
  everywhere in a single record; each city needs its own.
- A written notice must be complete in **both languages** — an Arabic title, an English title, an
  Arabic body and an English body. A half-translated notice is refused, so no driver sees a blank.
- The end date must be **after** the start date. Same-day start and end is refused.
- **Only one announcement per city can cover any given stretch of time.** If one already covers those
  dates, a second is refused rather than both being shown.
- A picture announcement must actually have a picture.
- A written notice cannot carry a picture, and a picture announcement cannot carry text. If you supply
  the wrong one it is **quietly dropped, not rejected** — worth knowing, because someone filling in a
  form can lose the text they typed without being told.
- The system records who created and who last edited each announcement, and when.

## Who uses it

- **Roles:** 8Orders operations staff create and edit announcements; delivery drivers read them.
- **Screens:** the announcements page in the Admin back-office; the driver's home screen in the
  delivery app.

## Two things worth knowing before planning work here

**There is no on/off switch.** An announcement is "live" purely because today falls inside its dates.
You cannot pause one — you either change its dates or remove it. If someone asks to "disable an
announcement temporarily", that capability does not exist today.

**A start date in the past is allowed.** Nothing stops an announcement being created with dates that
have already begun. That may be intentional (publishing something that should already have been up),
but it also means a mistyped date can make an announcement appear immediately.

## Related

- [[DeliveryManNotification.business|Delivery Man Notification]] — the other way to reach drivers: a *push*
  message sent to specific drivers, optionally scheduled, that can be tracked as read. Use that when
  drivers must be actively told something; use an announcement when it is enough that they see it when
  they open the app.
- [[City.business|City]] — announcements are always scoped to one.
- Technical detail: [[DeliveryAnnouncement.technical|DeliveryAnnouncement — technical]]
