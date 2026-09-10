---
id: 8orders/admin/admin-back-office/overview
title: Admin Back-Office — Overview
note_type: overview
context: Admin
feature: Admin Back-Office
audience: Business
last_updated: 2026-08-23
tags: [admin, admin-back-office, business]
---
# Admin Back-Office — Overview

## What is this? (for everyone)

The control room. Who at 8Orders may do what, the system-wide settings that change how the whole
platform behaves, the dashboards management looks at, and the report engine everything else prints
through.

Three jobs sit here, and they are the reason this feature matters more than its size suggests:

**Permissions.** Every other Admin screen asks this feature whether the person in front of it is
allowed. Roles are defined here, permissions are attached to roles, and users are put into roles.

**Configuration.** Not one settings page but eight or nine — delivery, accounting, loyalty points,
reviews, tips, robo-calls, operations, merchant loyalty. These are the numbers and switches the rest of
the platform reads at runtime. A change here changes behaviour for customers, drivers and restaurants
without any software being deployed.

**Reporting.** A commercial report engine renders the statements, sales reports and driver reports that
the rest of the business runs on.

## The Feature at a Glance

| # | Step (Screen) | Who | Purpose |
|---|---|---|---|
| 1 | Roles | Admin | Define roles and what each may do |
| 2 | User permissions | Admin | See what a given user is allowed |
| 3 | Delivery settings | Operations | Fees, timings, assignment behaviour |
| 4 | Accounting settings | Finance | How money is recorded |
| 5 | Loyalty settings | Marketing | Points earning and redemption |
| 6 | Tips, reviews, robo-call, operations settings | Various | Platform-wide behaviour |
| 7 | Merchant loyalty participation | Marketing | Which merchants take part, and in what order they appear |
| 8 | Loyalty audit log | Finance, audit | Who changed loyalty settings and when |
| 9 | Dashboards | Management | Live operational figures |
| 10 | Reports | Everyone | The printed and exported outputs |

## Business Flow (plain language)

1. An 8Orders employee signs in through the central sign-in service.
2. When they open an Admin screen, the system checks whether their role carries the permission that
   screen requires.
3. Operations, finance and marketing staff adjust settings; the rest of the platform picks the new
   values up without a release.
4. Changes to loyalty settings are written to an audit log, so a question about "who changed the
   earning rate" has an answer.
5. Management reads dashboards; everyone prints reports through the shared report engine.

## What a business reader must know

This feature has the **weakest access control in the system**, and because it is the feature that
*grants* access, that matters more here than anywhere else. Four separate problems, all recorded:

1. **Role management itself is not protected.** Any signed-in portal user can create roles, rewrite
   what a role is allowed to do, and delete roles. That is a direct path from "any account" to "full
   administrator".
2. **Anyone can read any user's permission list without signing in at all.** One endpoint is
   deliberately open, and when the caller is not signed in it falls back to using the user number they
   supplied — which is exactly the case where it should refuse.
3. **Most Admin screens have no permission requirement at all.** Only about a third of the Admin
   controllers carry a permission marker; the rest are protected only by "you are signed in as
   someone".
4. **When the permission check is applied and the marker is missing, the request fails as a server
   error rather than a refusal.** So a misconfigured screen looks like a crash, not a denied action,
   and never appears in any access-denied metric.

Two further mechanical problems in the same permission check are worth knowing before anyone tries to
fix the above: it identifies the screen by **matching text against class names** (and 8Orders has
near-identical names such as store-type and store-types), and where a screen has two versions of the
same action — one to show a form, one to save it — it may read the permission from the **wrong one**,
so a save can inherit the laxer rule of the form that preceded it.

Register rows: #447 (role management unprotected), #405 (anonymous permission enumeration), #617 (denial
returns a server error), #618 (name-matching and overload risk), plus #571/#580 on the unguarded report
engine and #456 on the front-end route guard.

## Key Concepts

- **Role** — a named set of permissions. Users belong to roles.
- **Permission** — the right to use a particular screen or action.
- **Configuration group** — one of the platform-wide settings pages (delivery, accounting, loyalty…).
- **Audit log** — a record of who changed loyalty configuration and when. Only loyalty has one.
- **Report engine** — the third-party component that renders reports and exports.

## Detailed Notes

- [[Admin/Admin Back-Office/_knowledge-graph|Technical Knowledge Graph]] — the controller inventory and
  the permission mechanism in detail.
- [[Admin/Admin Back-Office/_scenarios|Scenario Catalog]] — what happens if…
- [[Permission.business|Permission]] · [[Configuration.business|Configuration]] · [[ApiKey|API Key]]
