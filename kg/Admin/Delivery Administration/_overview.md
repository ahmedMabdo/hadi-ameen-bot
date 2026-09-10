---
id: 8orders/admin/delivery-administration/overview
title: Delivery Administration — Overview
note_type: overview
context: Admin
feature: Delivery Administration
audience: Business
last_updated: 2026-08-23
tags: [admin, delivery-administration, business]
---
# Delivery Administration — Overview

## What is this? (for everyone)

Everything 8Orders does *to and for* delivery drivers, from the back office. The drivers' own app is a
separate part of the system; this is the side operations staff use.

It covers four kinds of work:

**People.** Driver records, the suppliers who employ them, the equipment they hold, applications from
people who want to drive, and their shifts.

**Money.** Bonus schemes (by city and by shift), compensation for deliveries that went wrong, wallet
adjustments, and the daily deduction for driver insurance.

**Messages.** Two ways of reaching drivers — a city-wide announcement that appears in the app for a
date range, and a targeted notification pushed to their phones, optionally scheduled, with a record of
who received it.

**Rules.** The lists the driver app shows: reasons a delivery could not be completed, reasons a driver
was unbanned, standing delivery instructions.

## The Feature at a Glance

| # | Step (Screen) | Who | Purpose |
|---|---|---|---|
| 1 | Driver applications | Operations | Review people who want to drive |
| 2 | Driver records | Operations | Maintain details, look up by city or order |
| 3 | Suppliers | Operations | The companies that employ drivers |
| 4 | Assets | Operations | Bags, phones and other equipment held by a driver |
| 5 | Shifts | Operations | Who works when |
| 6 | Bonuses | Operations, finance | Bonus schemes per city and shift |
| 7 | Compensation | Operations, finance | Pay a driver for a delivery that went wrong |
| 8 | Wallet | Finance | Adjust a driver's balance directly |
| 9 | Announcements | Operations | A dated notice for all drivers in a city |
| 10 | Notifications | Operations | A push to specific drivers, now or scheduled |
| 11 | Reason lists | Operations | What the driver app offers when something goes wrong |

## Business Flow (plain language)

1. Someone applies to drive; operations review and create the driver record, attached to a supplier.
2. Equipment is issued and recorded against them.
3. They are put on shifts, and the reason lists their app shows are maintained here.
4. Bonus schemes are configured; compensation is raised case by case and moved through its states from
   this screen.
5. When drivers need to be told something, operations either publish a dated announcement for a city or
   send a targeted notification.
6. Every working day, an insurance deduction runs across drivers.

## What a business reader must know

**The screens that move money have the weakest protection in this feature.** Adjusting a driver's
wallet — a direct financial change — requires only that you are signed in as somebody. There is no
check of which role you hold. Reading driver transactions is the same. Both are recorded findings.

By contrast, the two newest screens in this feature — announcements and notifications — check a
specific permission on **every** action. So the correct pattern is present and in use a few files away
from the incorrect one. That contrast is the single most useful thing to know if anyone asks how much
work it would be to fix the wallet screens: the mechanism exists and is already wired.

**The daily insurance deduction can be triggered by anyone, without signing in**, and it has no
protection against running twice. This was previously recorded against the wrong service — both the
identity service and the admin service contain a file with the same name, and the referenced line
number happened to exist in both. It has been verified and re-attributed.

**Two things worth knowing about driver messages**, both from reading the underlying rules:

- A notification is marked "sent" once the send runs, but only drivers **who were on shift at that
  moment** are recorded as having received it. Reports that count sent notifications as drivers reached
  will overstate the number, sometimes to zero-vs-everyone.
- An announcement has no on/off switch. It is live purely because today falls inside its dates, so
  "pause this announcement" is not something the system can currently do.

Register rows: #375 (anonymous financial batch), #568 and #569 (wallet screens without a permission
check), plus the Admin-wide mechanism problems #617 and #618.

## Key Concepts

- **Supplier** — the company that employs a driver; 8Orders does not always employ them directly.
- **Asset** — equipment issued to a driver and tracked against them.
- **Bonus scheme** — extra earnings, configured per city and shift.
- **Compensation** — a payment for a delivery that went wrong, moved through states by staff.
- **Announcement vs. notification** — passive and dated, versus pushed and tracked.
- **Reason list** — the choices the driver app offers when a delivery fails.

## Detailed Notes

- [[Admin/Delivery Administration/_knowledge-graph|Technical Knowledge Graph]] — the authorisation
  split, the endpoint areas, and the three state machines.
- [[Admin/Delivery Administration/_scenarios|Scenario Catalog]] — what happens if…
- [[DeliveryAnnouncement.business|Delivery Announcement]] ·
  [[DeliveryManNotification.business|Delivery Man Notification]]
- [[Delivery/Driver Cash & Compensation/_overview|Driver Cash & Compensation]] — the driver-facing half
  of the money.
