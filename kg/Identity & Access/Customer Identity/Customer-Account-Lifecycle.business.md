---
id: 8orders/identity-and-access/customer-identity/customer-account-lifecycle-business
note_type: business
context: Identity & Access
feature: Customer Identity
last_updated: 2026-08-23
tags: [flow, business]
---
# Customer Account Lifecycle

## What this process is
The journey of a single customer identity from the moment someone opens the app for the first
time — before they've given us a phone number — through registration, everyday account use, and
eventually deactivation or deletion. The company's central design choice here is that **browsing
is never truly anonymous**: the moment someone touches a cart, we quietly create a real, provisional
customer record for them (a "Guest"), tied to their device, so that whatever they build — a cart,
a delivery address, a discount they qualified for — has somewhere durable to live before they ever
register. Registration then either upgrades that same record in place, or, if they turn out to
already have an account, merges the guest's in-progress work onto it.

## The steps, in plain words

1. **Guest browsing.** The first time someone adds something to a cart without being logged in, we
   create a Guest account behind the scenes, identified only by their device, with a default
   delivery address guessed from their map pin. They can browse, order, and pick delivery details
   with no phone number at all.
2. **Requesting a verification code (OTP).** Whether someone is about to register for the first
   time or log into an existing account, the flow starts the same way: enter a phone number,
   receive a text with a code.
3. **Verifying the code and registering.** Entering the correct code either creates a brand-new
   account or, if the phone was already registered, logs the person into that existing account.
   If the phone had never been used before, a new customer record is created; if it's the same
   device that was already browsing as a Guest, that Guest record is simply upgraded in place —
   nothing is lost.
4. **The guest-to-registered merge.** This is the moment that matters most, and it only happens
   when the phone number turns out to belong to a *different*, already-existing account (not the
   device's own Guest record). In that case, the policy is "the guest wins": whatever cart, chosen
   delivery address, and discount the person had just built as a guest **replaces** whatever was
   already sitting on their real account, rather than combining with it. Their wallet balance and
   any loyalty points are not part of this move — a guest session essentially never has either, so
   this is mostly theoretical, but it means neither is designed to be preserved if it ever did.
5. **Everyday account use.** Once registered, a customer manages their own profile and saved
   addresses, sees their loyalty points and wallet balance, and places orders. There is currently no
   way for a customer to add their own money into their wallet — the wallet is only ever credited by
   the company itself, as a refund, a compensation payout, a referral bonus, or a redemption from a
   partner loyalty program.
6. **Admin intervention.** Support staff can activate, deactivate, or block a customer's account,
   with a required reason when blocking. Blocking takes effect immediately, cutting the customer off
   on their very next request, not just their next login.
7. **Leaving.** A customer can delete their own account at any time. This doesn't erase their data —
   it's marked deleted and their phone number is freed up so it could be used to register again
   later. Abandoned Guest sessions that nobody ever came back to are automatically cleaned up after
   24 hours if they were never turned into a real account.

## Who is involved
The customer, at every step. Support/admin staff for activation, blocking, and any staff-assisted
address correction. Nobody else is involved in day-to-day account maintenance — this is designed to
be almost entirely self-service.

## What can go wrong, in business terms
- **Unlimited "free" accounts.** Because guest accounts are created just by browsing, and there is
  no limit on how many a single source can create, this is an open door for abuse (fake accounts,
  inventory/discount probing) that was flagged as a requirement when the guest feature was designed
  but was never actually built. The only safety net is that abandoned ones get swept away after a
  day.
- **A blank phone-country field crashes the "send me a code" screen** instead of showing a normal
  "please enter your number" message — an unhelpful dead end for anyone whose app sends an
  incomplete request.
- **An old vulnerability (since fixed)** briefly let any staff member with basic portal access read
  a customer's live verification code and use it to sign in as that customer. It's resolved, but
  it's the reason this whole verification step is treated as a real security boundary, not a minor
  detail.
- **Editing an address can silently steal it.** A flaw in the "edit my address" feature lets someone
  who knows or guesses another customer's saved-address reference both wreck that customer's saved
  address and claim it for their own account.
- **Deleting your account doesn't immediately log you out.** Because of how the deletion flag is
  checked, someone who deletes their account can, in principle, keep using the app with their
  existing session for a while afterward.
- **A guest's cart can quietly vanish at login.** If merging a guest's in-progress cart onto an
  existing account fails partway (for example, an item the guest picked is no longer available by
  the time they log in), the login itself still succeeds — the customer is simply signed in with
  their old cart, or no cart, and no error explaining why the guest cart didn't come along.

## What the company should know
The guest-first design is deliberate and serves a real product need (keeping discounts locked to a
cart across login), but it was shipped without the abuse-prevention control that was called for at
design time. The account-verification code is a genuine security credential, not a formality, and
should be treated with the same care as a password anywhere it appears in logs, admin screens, or
support tooling. Account deletion and the guest-merge step both currently favor "don't lose data
silently" less than they should — deletion doesn't clean up related records, and a failed merge
doesn't tell anyone it failed.
