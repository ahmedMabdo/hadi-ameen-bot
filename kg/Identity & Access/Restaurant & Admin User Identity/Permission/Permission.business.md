---
id: 8orders/identity-and-access/restaurant-and-admin-user-identity/permission-business
note_type: business
context: Identity & Access
feature: Restaurant & Admin User Identity
entity: Permission
entity_type: lookup
last_updated: 2026-08-23
tags: [identity-access, authorization, cross-cutting, business]
---
# Permission

The access-control system behind the Admin back office — it decides which buttons, pages and API
actions each back-office user is allowed to use, based on the role(s) they've been assigned.

## What it is
Every admin user is assigned one or more **roles** (e.g. "Support Agent", "Finance"), and every role
is assigned a set of **permissions** (e.g. "can delete a restaurant", "can approve a compensation",
"can view the merchant sales report"). When an admin opens a screen or clicks a button, the system is
supposed to check — both in the browser and on the server — whether one of that admin's roles carries
the specific permission that action requires. There are close to 200 distinct permissions defined
across the admin app, covering orders, restaurants, delivery men, customers, ads, reports, wallets,
compensations and more, and new ones are added routinely as new admin features ship.

Two admin-level "master switches" exist and quietly skip this whole check: a **Full Control** flag on
an individual user's account, and a specific built-in **Admin role** — either one grants every
permission automatically, with no per-permission lookup at all.

## Business rules (plain words)
- A permission is only enforced if the specific screen or API action was actually built to ask for
  one — there is no "deny by default." Findings this round showed **13 of 81 admin API controllers
  have no access check of any kind**, meaning some back-office endpoints are reachable without even
  logging in (`_conflicts.md` #374).
- Two things bypass every permission check entirely, everywhere: a user marked **Full Control**, and
  membership in the one built-in **Admin role**. Neither is per-feature — once either is true, every
  permission question is answered "yes" automatically.
- The permission-name list a user is checked against is stored as **data in the database**, not fixed
  in the app's code — every time a new admin feature ships, a fresh row is added to the permissions
  table by hand. This means a spelling mistake when adding a new permission can silently make that
  permission impossible to ever grant, with nothing in the build process to catch it.
- Buttons and menu items in the admin screens hide themselves when the current admin lacks a
  permission, but this is a **convenience, not a security control** — several admin screens are
  already known to expose destructive actions (deleting a merchant, rebuilding search, approving a
  submission) with **no permission check at all**, inconsistent with a matching control right next to
  them that does check (#372). The real security boundary is always the server-side check, and this
  pass found that boundary is not always present either.
- Two more confirmed, narrower defects: one part of the permission-matching logic on a report screen
  checks whether a permission name merely *contains* another name rather than matching it exactly,
  which could over-grant access to reports (#316); and the very screen used to manage roles and
  permissions is itself one of the admin routes with no permission requirement declared on it (#370),
  and its own list grid mislabels the Edit/Delete buttons' tooltips (#373).
- A newly-traced defect in this pass: the endpoint the admin app calls right after login to fetch
  "what am I allowed to do" is marked to allow anonymous callers, and when there's no logged-in
  session it will use whatever user id is passed on the request instead — in effect, an unauthenticated
  caller could ask "what can user #47 do" and get a real answer back.

## Who uses it
- **Roles:** Every back-office admin user — the permission a person holds determines which parts of
  `AdminUi` they can see and use. Managed by whoever administers roles (a "Permissions" admin screen),
  typically a senior admin or IT/ops role.
- **Screens:** `AdminUi` → Permissions section (role list, add/edit role with a permission picker) —
  this is also the screen most of this note's findings concern, since it's both the tool that
  manages permissions and one of the areas found least protected by them.
- **Everywhere else:** almost every other admin screen reads permissions indirectly, to decide what to
  show — restaurants, orders, reports, delivery, wallets, compensations, and more all gate at least
  one action behind a permission check.

## Related
- [[DeliveryMen.technical|DeliveryMen]] — a delivery-man-specific dismissal permission
  is checked the same way as general admin permissions
- [[City.technical|City]] — one of many master screens whose admin actions are
  gated (or, in some documented cases, should be but aren't) by a Permission
- Technical detail: [[Permission.technical|Permission — technical]]
