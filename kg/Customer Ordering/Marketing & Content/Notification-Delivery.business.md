---
id: 8orders/customer-ordering/marketing-and-content/notification-delivery-business
note_type: business
context: Customer Ordering
feature: Marketing & Content
group: Notification-Delivery
last_updated: 2026-08-23
tags: [flow, business]
---
# Notification and Campaign Delivery

## What this is

Every message the platform pushes to a phone — "your order is on the way", "your wallet was topped
up", a marketing campaign, a price-drop alert — travels one of two routes. Knowing which route a
message took is the difference between "the customer didn't get it" being a delivery problem and it
being a targeting problem.

**Transactional** messages are a consequence of something happening: an order changes state, money
moves, an item comes back in stock. The system reacts and sends.

**Campaign** messages are composed by a person in the admin portal, aimed at a group of customers
defined by rules ("registered but never ordered", "no order in 30 days"), and sent once or on a
repeating schedule.

## The steps, in plain terms

**Transactional:**
1. Something happens to an order, a wallet, or an item.
2. A notification record is written, holding the Arabic and English text.
3. The system looks up which phones that customer has registered — Android and iOS are tracked
   separately, each as a single text field holding all of that customer's device tokens.
4. The message is handed to Google Firebase, which delivers to the phones.
5. The customer sees a push, and the same message appears in their in-app notification list.

**Campaign:**
1. An admin writes the message in both languages and picks who should receive it, using filters.
2. The audience is built — either live, as the campaign sends, or overnight by a scheduled job.
3. The campaign is sent once, or repeats weekly, monthly or yearly.
4. Each recipient gets a per-person record so the platform knows who was reached.

## What can go wrong here — and several things currently do

This flow has more confirmed defects than any other in the graph, and they compound: a campaign can be
**mis-scheduled**, **mis-targeted**, **sent to nobody**, or **sent in the wrong language** — each by a
different bug, none of which reports an error.

- **Monthly campaigns fire every second month, yearly ones every third year.** The code uses the
  recurrence *type* as if it were a count of periods, and the values happen to be 1, 2 and 3. Weekly
  is correct by coincidence, which is why the feature looks like it works.
- **A campaign targeted by area or by merchant reaches nobody.** One of the three audience engines has
  no rule for those two filter types and quietly answers "no match" for every customer, which empties
  the whole audience.
- **"Exactly N days" silently means "N days or more".** One comparison operator in the filter builder
  was copy-pasted from another, so a precise cohort becomes a much larger one — an admin targeting a
  narrow group reaches far more people than intended.
- **The overnight audience and the live audience disagree.** Two of the three engines drop a condition
  the third applies, and the one that drops it is the one the nightly job uses.
- **English-speaking customers get English in the Arabic slot.** The fallback text is filled with the
  wrong language for one of the two groups.
- **Removing one device unregisters all of them.** A customer or driver who signs out on one phone
  silently stops receiving notifications everywhere. This is the most likely explanation for any
  "notifications just stopped working" report.
- **A customer can be told something happened that then didn't.** In at least one path the push is
  sent, and a second database is written, before the change that prompted it is confirmed saved. A
  push cannot be recalled.

## Who is involved

- **Admin / marketing** compose campaigns, define audiences, and set schedules.
- **Customers** receive both kinds; their device registrations decide whether anything arrives.
- **Delivery men and merchants** receive their own operational notifications through related paths.

## Worth knowing about the data

Notification records do **not** live in the main platform database — they are written to a separate
database used for chat and notifications. Audience and customer data live in the main one. Because the
two are separate, a write to one can succeed while the other fails, and nothing ties them together.
That is the mechanism behind the "told something that didn't happen" case above.

## Related
- [[Notification-Delivery.technical|Notification Delivery — Technical]]
- [[Support-and-Chat.business|Support and Chat]] — shares the separate chat database
- [[Customer-Account-Lifecycle.business|Customer Account Lifecycle]] — where device registration happens
