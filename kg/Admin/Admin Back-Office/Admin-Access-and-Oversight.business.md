---
id: 8orders/admin/admin-back-office/admin-access-and-oversight-business
note_type: business
context: Admin
feature: Admin Back-Office
last_updated: 2026-08-23
tags: [flow, business]
---
# Admin Back-Office — Access and Oversight

## What this process is
How a staff member gets a back-office login, what that account is then allowed to do (a role, built
from a list of named permissions), the checks meant to enforce that everywhere the account
goes — the admin website, the API behind it, the reports menu — and whether the company keeps a
record of what was actually done. It also covers the screens that change behaviour for every
customer and order at once: feature switches, accounting configuration, and per-city rules.

## The steps, in plain words

1. **Creating a staff account.** Someone with access to the "Users" admin page enters a new
   colleague's email, phone and password, picks their role, and optionally flips a "Full Control"
   switch reserved for senior admins — it turns off every other permission check for that account.
2. **Defining what a role can do.** A separate "Roles & Permissions" screen lets someone build or
   edit a role by picking from the master list of named permissions, one per admin feature.
3. **Every screen and API call is supposed to check the role.** The admin website hides buttons the
   user's role doesn't cover; the server behind it is supposed to independently reject any request
   for a permission the role lacks. The website hiding a button is a convenience, not the lock.
4. **Reports and dashboards.** A large reports menu (merchant payouts, driver performance,
   complaints, loyalty points) and an embedded dashboard tool summarize the business, gated the same
   way as any other admin feature — in principle.
5. **System-wide settings.** Feature switches, accounting ledger mappings, delivery and loyalty
   economics, and per-city rules all live in the same back office. One save here affects every
   order, everywhere — the highest blast-radius screens in the product.
6. **The paper trail.** Every step above is supposed to leave a record — who created which account,
   who changed which role, who edited which setting — so the company can answer "who did this."

## Who is involved
Any existing back-office user who can reach the "Users" page creates accounts and assigns their
first role. Any existing back-office user who can reach "Roles & Permissions" decides what every
role — including their own — is allowed to do. Engineering decides, screen by screen, whether a
given button or API action gets checked at all; there is no company-wide "closed by default" rule.
Nobody currently reviews the paper trail, because it isn't actually being kept (see below).

## What can go wrong, in business terms

- **The single worst finding this round: any staff login can turn itself into a full
  administrator.** The screen that defines *roles* — deciding what every other account may
  do — has no permission check beyond "are you logged in." The lowest-privileged account in the
  company can use it to grant itself every permission, or hand another account Full Control, and
  from then on it behaves like a legitimate top-tier admin in every later check.
- **The full permission map can be read with no login at all**, by guessing an internal account ID —
  turning the escalation above into a planned attack: scout first, then sign in and climb.
- **New accounts can be created with Full Control on by a fairly junior admin.** Creating a user only
  checks whether the creator can reach the "Users" page — not whether they're senior enough to hand
  out unrestricted access.
- **A handful of admin screens look protected and aren't**, due to a coding mistake unrelated to the
  business rules — they carry what reads as a security lock that silently does nothing.
- **The reports menu has a shortcut-matching flaw**: holding permission for one report can
  accidentally unlock a different report whose name happens to be contained inside the first one's.
- **There is no "closed by default" safety net.** A screen a developer forgot to lock is open to the
  whole internet, not restricted to staff — already true of a dozen-plus screens, including ones
  touching customer complaints, mass push notifications, and a live third-party API key handed to
  any logged-in staff member regardless of role.
- **The paper trail does not work.** The mechanism meant to record "who changed what" has never
  written a single row, for any save, in the life of this feature. Combined with the self-escalation
  above, an account that promotes itself to administrator leaves no trace of having done so.
- **Most system-wide settings accept nonsense.** Of roughly seven settings groups, only delivery
  timing actually rejects bad numbers; accounting mappings, loyalty economics and operational
  thresholds accept negatives or zero with nothing stopping the save.

## What the company should know
Two already-identified gaps — the ungated role-management screen and the anonymous permission
lookup — combine into a complete, two-step path from "any valid login" to "full administrator," and
it leaves no trace, because the audit log that should catch it has never recorded anything. This is
the top-priority fix from this review. Everything else here (silently-inert locks, the reports
shortcut bug, the missing default-deny rule, unvalidated settings) erodes trust in the back office
even before that headline issue is counted — and none of it is currently visible after the fact,
because there is nothing to look at.
