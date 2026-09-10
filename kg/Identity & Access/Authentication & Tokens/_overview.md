---
id: 8orders/identity-and-access/authentication-and-tokens/overview
title: Authentication & Tokens — Overview
note_type: overview
context: Identity & Access
feature: Authentication & Tokens
audience: Business
last_updated: 2026-08-23
tags: [identity-and-access, authentication-and-tokens, business]
---
# Authentication & Tokens — Overview

## What is this? (for everyone)

The front door. **Every** person who uses 8Orders signs in here — customers on the app, delivery
drivers, restaurant staff on the portal, and the 8Orders back-office team. There is one sign-in page,
and everything else in the system trusts what it says.

When someone signs in successfully, this service hands their app a **pass**. The app shows that pass on
every later request, and each part of 8Orders checks it before answering. That is why this feature
matters out of proportion to its size: it is small, but it is the only thing between the outside world
and every screen in the business.

Signing in also does two less obvious jobs. It decides **which app you are allowed to use** — a
restaurant manager cannot sign in to the admin back-office even with correct credentials — and it
records a **clock-in**, so signing in doubles as attendance for back-office staff.

## The Feature at a Glance

| # | Step (Screen) | Who | Purpose |
|---|---|---|---|
| 1 | Login page | Everyone | Enter username and password |
| 2 | Wrong-app notice | Restaurant staff on the old portal | Told the portal has moved |
| 3 | Access denied | Restaurant staff on the admin app | Refused — wrong app for the role |
| 4 | Signed in | Everyone | The app receives its pass |
| 5 | Clock-in | Back-office staff | Attendance recorded on sign-in |
| 6 | Logout | Everyone | Ends the session |
| 7 | External sign-in | Everyone (where configured) | Sign in through another provider |

## Business Flow (plain language)

1. A person opens their app. The app sends them to the single 8Orders sign-in page.
2. They enter their username and password.
3. Before the password is checked, the system checks whether this *kind* of user may use this
   *particular* app, and refuses with an explanation if not.
4. If the password is right, a session starts, an attendance record is written, and the app is handed
   its pass.
5. The app carries that pass everywhere. Each service checks it independently — using its **own private
   copy** of the checking rules.
6. Logging out ends the session here. Passes already handed out stay valid until they expire.

## What a business reader must know

**There is no limit on password guessing.** The system is *configured* to lock an account after five
wrong passwords for five minutes — and the sign-in page explicitly switches that off. So someone can try
passwords against any account, as fast as they like, indefinitely: a customer account, a driver account,
a restaurant manager account, or an 8Orders administrator account.

The password rules make that materially worse. They are set as low as they go: six characters, with no
requirement for a digit, a capital letter, a small letter or a symbol, and no requirement that the
characters differ. A six-character password of one repeated letter is acceptable for an administrator.

The two together mean the front door has a weak lock and no limit on how many keys may be tried. To be
precise about the risk: this is not a hole someone walks through without a password — it is the absence
of the thing that stops them trying every password.

**Second: the security log can say the opposite of what happened.** A successful sign-in that arrives
with an unexpected return address is written into the audit log as an invalid-credentials failure. So a
genuine sign-in can appear as a failed one. Anyone investigating suspicious activity, or any alert that
counts failed logins, is reading a number that includes events which were not failures.

**Third, a structural point worth knowing before any security work is scoped:** the pass is issued in
one place but **checked in four separate copies** of the same code, one per service. A change to the
rules — how long a pass lasts, who issued it, who may accept it — has to be made four times, and if one
copy is missed, that service quietly keeps the old rules.

Register rows: #612 (no lockout, weak password policy), #613 (false audit record), and integration
row 3 (the four duplicated validators).

## Key Concepts

- **The pass (token)** — proof of identity handed to an app at sign-in and shown on every request.
- **Session vs. pass** — logging out ends the session here; passes already issued keep working until
  they expire.
- **Client** — a specific app (customer app, driver app, merchant portal, admin SPA). Sign-in checks
  which client you are using, not only who you are.
- **Account lockout** — temporarily refusing sign-in after repeated wrong passwords. Configured here,
  and not applied.
- **External provider** — signing in through another service instead of a username and password.

## Detailed Notes

- [[Identity & Access/Authentication & Tokens/_knowledge-graph|Technical Knowledge Graph]] — the
  sign-in path line by line, the client and role gates, and the token-validation duplication.
- [[Identity & Access/Authentication & Tokens/_scenarios|Scenario Catalog]] — what happens if…
- [[Login-and-Activation|Login & Activation]] — the login and activation entities.
- [[Identity.business|Identity]] — the user record in plain language.
