---
id: 8orders/restaurant-portal/menu-and-order-management/merchant-menu-and-orders-business
note_type: business
context: Restaurant Portal
feature: Menu & Order Management
group: Merchant-Menu-and-Orders
last_updated: 2026-08-23
tags: [flow, business]
---
# Merchant Menu and Order Management

## What this process is
This is the restaurant's (or store's) day-to-day operation of the platform: setting up when they're
open, keeping the menu and stock accurate, and handling orders from the moment a customer pays through
to handing the food to a driver. It runs in a dedicated web portal that restaurant and store staff log
into separately from the customer app.

## The steps, in plain words

1. **Staff sign in** to the merchant portal with their own account, which is tied to one or more
   restaurants/stores.

2. **Set hours and pauses.** Staff can mark the restaurant "busy" for a period — either right now or a
   window scheduled to start later — which is meant to stop new orders from coming in during that
   window, and can end a busy period early.

3. **Build and maintain the menu.** Categories, items, prices, and option groups (like "choose your
   size" or "add extra toppings") are created and edited directly in the portal. Individual items can
   be turned on/off, and for grocery/store-type accounts, stock levels are tracked per item.

4. **Bulk changes via Excel**, for anyone with a lot of items to update at once: one spreadsheet format
   for menu categories/items/prices, one for option groups, and one for store item price/availability/
   stock updates. The store-item version previews the file first — showing which rows are ready,
   missing information, or duplicates — before anything is actually saved.

5. **A new order shows up automatically.** When a customer finishes paying, the order appears on the
   restaurant's screen in real time, without needing to refresh — the system pushes it directly.

6. **Staff respond to the order**: accept it as-is, reject the whole thing, or reject/flag individual
   items as unavailable (in which case the customer can be offered a substitute, depending on their
   preference settings). Accepting includes giving an estimated cooking time.

7. **Mark it ready for pickup** once the food is prepared. At that point the kitchen's part of the job
   is done — a driver takes over for pickup and delivery, which is a separate part of the platform not
   covered by this note.

8. **Check performance.** Staff can see a daily summary of their orders and, through separate reporting
   screens, more detailed performance, financial, and rejected-order reports.

## Who's involved at each step
Restaurant/store staff (front-of-house or kitchen operators using the portal) at every step above; the
customer indirectly, whose order and payment trigger step 5 and whose preferences shape what happens on
a rejected item in step 6; drivers who take over after step 7; and platform admins, who can also end a
restaurant's busy period on the restaurant's behalf.

## What can go wrong, in business terms
- **A "closed for later" period can go into effect too early.** If staff schedule a busy window to
  start in the future, the system currently treats it as busy starting immediately — turning away
  orders before the intended start time (`_system/_conflicts.md` #409).

- **Some portal actions don't check which restaurant the logged-in user actually belongs to.** A number
  of order actions and the merchant performance dashboard accept a restaurant ID directly from the
  request rather than strictly from the signed-in account's own restaurant — in principle letting a
  logged-in user at one restaurant view or act on another restaurant's orders or performance figures
  (`_system/_conflicts.md` #404, full detail in the IDOR register).

- **A failed save can be reported as if it worked.** Two spots in the busy-period feature notify staff's
  devices about a busy period before actually confirming the change was saved — so if the save quietly
  fails, staff are told about a state change that never took effect. This is the same category of bug
  as a separately-confirmed one elsewhere in the platform where a failed action is reported as a
  success (`_system/_conflicts.md` #396 family).

- **Store stock isn't always double-checked at the final moment.** When a customer's cart includes items
  from more than one restaurant or store, the last-moment stock recheck before payment is skipped
  entirely for those orders — and the system still reports the check as passed. A merchant can
  therefore receive a paid order for something they're actually out of, discovered only after the fact
  (`_system/_conflicts.md` #451).

- **One of the order-notification channels has no login check at all.** Separate from the normal
  customer-driven flow, the internal channel that pushes "new order" / "order rejected" / "order
  delayed" events to the restaurant's screen doesn't require anyone to be logged in to trigger it — so,
  in principle, someone who finds that address could push a fake event to a restaurant's live order
  screen. This is a known, already-documented gap in the portal's notification relay.

## What the company should know
The order-acceptance and ready-for-pickup steps themselves are solid — they correctly check order state
before acting and correctly report failure when a save fails. The risk in this flow concentrates in
three places: the restaurant-ownership checks that are inconsistently applied across near-identical
actions (menu-category creation and merchant dashboards, not just orders), the busy-period feature's
timing and success-reporting bugs, and the multi-restaurant cart's skipped stock recheck — all three are
already tracked findings rather than new discoveries, but this note is the first place they're shown
sitting on the actual step of the merchant's day where they bite.
