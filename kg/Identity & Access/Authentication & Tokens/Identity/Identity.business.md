---
id: 8orders/identity-and-access/authentication-and-tokens/identity-business
note_type: business
context: Identity & Access
feature: Authentication & Tokens
group: Identity
last_updated: 2026-08-23
tags: [identity-access, authentication, business]
---
# Identity

The one place in the whole system that checks who someone is and hands out the digital "pass"
(a token) every other app then trusts — instead of each app checking passwords itself.

## What it is
Identity is the login/authentication service (project `Talabatk.IDS`), built on an open-source
product called IdentityServer4. Every other part of 8Orders — the customer app, the delivery-man
app, the restaurant portal, and the admin back office — hands a user's login to this one service
and gets back a short-lived token instead of handling passwords directly. That token is what the
other four apps check on every request to decide "is this a real, still-valid session."

Customers, delivery men, restaurant staff and back-office admins are each a separate kind of
account under the hood, and each logs in through its own path with its own set of checks (see
[[Login-and-Activation|Login & Activation]] for the detailed comparison). Customers can also log
in with a one-time SMS code (OTP) instead of a password, and that same OTP flow can silently
register a brand-new customer the first time they use a phone number.

## Business rules (plain words)
- Different account types log in differently and are checked differently: a customer's phone
  number and password are checked against being deleted, blocked, or not-yet-activated; a delivery
  man's password is checked against being deleted; a restaurant user's password is checked against
  nothing else at all today (a gap — see [[Login-and-Activation|Login & Activation]]).
- A login attempt is capped at 5 wrong passwords before a 5-minute lockout, and a password can be
  as short as 6 characters with no requirement for a digit, a capital letter, or a symbol — this is
  the one password-strength rule for the entire platform.
- A token issued to a customer's phone lasts a few hours before the app has to come back for a new
  one; a token used for internal server-to-server calls between 8Orders' own apps lasts much
  longer.
- The cryptographic certificate that "signs" every token — the thing that lets every other app
  trust that a token really came from here — is a real production file that has been committed
  into source control, along with the password needed to unlock it, sitting directly in the code.
  This is the single most serious finding across the entire audit of this codebase: anyone who can
  read the repository could, in principle, mint a valid login for any user, on any app, without
  ever knowing a real password. See `_conflicts.md` #331.
- The underlying product this login system is built on, IdentityServer4, stopped receiving updates
  or security fixes years ago — its maker replaced it with a newer, paid product (Duende
  IdentityServer). See `_conflicts.md` #332.

## Who uses it
- **Roles:** every actor in the system, indirectly — Customer, Delivery Man, Restaurant User,
  back-office Admin. None of them interact with this service knowingly; their own app (mobile app,
  delivery app, restaurant portal, admin portal) talks to it behind the scenes to get a token.
- **Screens:** `Talabatk.IDS`'s own login/registration pages, used only by the browser-based apps
  (admin, restaurant portal); the mobile and API-only clients exchange credentials for a token
  directly and never see this service's UI.

## Related
- [[Login-and-Activation|Login & Activation]] — the detailed, per-actor-type login and
  activation-check comparison
- [[Customer.business|Customer]] / [[DeliveryMen.business|DeliveryMen]]
  — the identity records this service authenticates
- Technical detail: [[Identity.technical|Identity — technical]]
