---
id: 8orders/customer-ordering/marketing-and-content/notification-delivery-technical
note_type: technical
context: Customer Ordering
feature: Marketing & Content
group: Notification-Delivery
covers: [AboutApp, AdCard, AdReservation, Ads, Announcement, AnnouncementDescription, AudianceFilter, AudienceCustomer, AudienceCustomerAds, FAQItem, Notification, NotificationExecutionHistory, NotificationTarget, PrivacyPolicy, ScheduledNotification, ScheduledNotificationCustomerGroupType, TermsAndConditions]
sources:
  - path: Shared/TalabatkLogic/TalabatkModels/AboutApp.cs
    sha1: c925be4c24e1
  - path: Shared/TalabatkLogic/TalabatkModels/AdCard.cs
    sha1: 0bf3093e4f06
  - path: Shared/TalabatkLogic/TalabatkModels/AdReservation.cs
    sha1: 9fe7f4a14a4d
  - path: Shared/TalabatkLogic/TalabatkModels/Ads.cs
    sha1: f6b239bd29b2
  - path: Shared/TalabatkLogic/TalabatkModels/Announcement.cs
    sha1: c75d676577ae
  - path: Shared/TalabatkLogic/TalabatkModels/AnnouncementDescription.cs
    sha1: a06d422e7dc6
  - path: Shared/TalabatkLogic/TalabatkModels/AudianceFilter.cs
    sha1: 029e560c780a
  - path: Shared/TalabatkLogic/TalabatkModels/AudienceCustomer.cs
    sha1: 5f7da15eed72
  - path: Shared/TalabatkLogic/TalabatkModels/AudienceCustomerAds.cs
    sha1: e382437dd65c
  - path: Shared/TalabatkLogic/TalabatkModels/FAQItem.cs
    sha1: 9e7f44e319ca
  - path: Shared/TalabatkLogic/TalabatkModels/NotificationExecutionHistory.cs
    sha1: d60e5324a6d1
  - path: Shared/TalabatkLogic/TalabatkModels/NotificationTargets.cs
    sha1: ba66a3c92a6d
  - path: Shared/TalabatkLogic/TalabatkModels/PrivacyPolicy.cs
    sha1: 04df7b38ac26
  - path: Shared/TalabatkLogic/TalabatkModels/ScheduledNotificationCustomerGroupType.cs
    sha1: e847b4edf3a1
  - path: Shared/TalabatkLogic/TalabatkModels/TermsAndConditions.cs
    sha1: fa25038be7f3
  - path: AdminUi/Startup.cs
    sha1: 9b3cc183bae1
  - path: Shared/SharedWeb/Helpers/Extenstions/DataBaseServices.cs
    sha1: 101669d0a0d9
  - path: Shared/TalabatkLogic/TalabatkModels/Customer.cs
    sha1: 312359030eb8
last_updated: 2026-08-23
tags: [flow, technical]
---
# Notification and Campaign Delivery — Technical

> **Provenance note.** Written by the orchestrator after two agent attempts at this note stalled. It is
> therefore **narrower than the other flow notes**: roughly 8 source files were traced rather than ~15,
> and the Open Questions section is correspondingly longer. Findings referenced by number were
> established elsewhere and are cited, not re-derived. Stated plainly so nobody reads this note as
> being as thorough as its siblings.

## Trigger

Two independent entry points.

**Transactional** — a domain event or command writes a notification row, then hands off to
`SendNotificationJob`. Registered as a recurring Hangfire job on a very short cycle: the cron comes
from configuration key `SendNotificationJob:CronExpression`, held in a variable named
`CronExpressionEvery30Sec` (`AdminUi/Startup.cs:452`), so the queue is drained roughly every 30 seconds
rather than pushed synchronously.

**Campaign** — `SendScheduledNotificationJob`, registered as `"SendScheduledNotification"`
(`AdminUi/Startup.cs:456`). It evaluates which scheduled notifications are due on this run.

## Step-by-step

1. **A notification row is written.** Created by the originating command or event handler with both
   Arabic and English title/body. Written to the **chat database**, not the main one — see *Data
   written* below.

2. **The job picks it up.** `SendNotificationJob.SendNotificationForNotificationId(int)` (`:98`) is the
   single-notification entry; `SendNotificationForNotificationIdAndVoucher(...)` (`:138`) is the
   variant that carries a voucher payload.

3. **Recipients are grouped.** The job groups by a `NotificationGroupKey` (`:26`) which carries the
   platform targeting flags — `SendToAndroid`, `SendToIOS`. Grouping exists so one Firebase call can
   serve many recipients sharing the same payload and platform.

4. **Device tokens are resolved.** Per customer, per platform:
   ```csharp
   if (!string.IsNullOrWhiteSpace(customer.AndroidDevices) && group.Key.SendToAndroid)
       tokens.AddRange(customer.AndroidDevices.Split(';'));
   if (!string.IsNullOrWhiteSpace(customer.IOSDevices) && group.Key.SendToIOS)
       tokens.AddRange(customer.IOSDevices.Split(';'));
   ```
   (`:511-514`). Both are **single delimited string columns** on `Customer` —
   `public string IOSDevices` / `public string AndroidDevices` (`Customer.cs:58-59`) — holding every
   device for that customer separated by `;`. A separate path resolves tokens the same way from a
   `DeviceToken` field (`:322`).

   **This storage choice is the root of #351.** Because all of a customer's tokens live in one string,
   removing one device is a string-manipulation problem rather than a row delete — and the code that
   does it uses a predicate that ignores its own lambda parameter, so it empties the field instead of
   removing one entry. Five occurrences across three files, covering customers, drivers and merchants.

5. **Firebase delivery.** Tokens are handed to the Firebase Admin SDK. Credentials come from the
   committed `FireBaseConfigurations.json` service-account files — five of them, all in git history and
   part of the Appendix A rotation set (**#331**).

6. **Language selection.** Each notification carries a primary and a secondary (fallback) text pair.
   **#424**: for the English-preferring group the English text is passed into *both* slots, so the
   Arabic fallback column holds English. The Arabic branch, twenty lines away, fills them correctly.

7. **Persistence of send state.** `await _chatContext.SaveChangesAsync();` at `:128`, `:175`, `:219`,
   `:248` — four separate saves on the chat context, none of whose results are inspected. Members of
   the family tracked at **#72**.

### Campaign path — additional steps

8. **Audience construction.** Three implementations exist and they disagree — **#425**. The nightly
   `BuildingAudianceCustomerJob` uses `AudienceFilterService` / `AudienceSnapshotFilterService`; the
   real-time path uses `AudienceFilterEvaluator .ts`… note the **trailing space in that filename**, one
   of the pathological names catalogued in **#334**. The evaluator has no case for `Area` or `Merchant`
   filter types and returns `false`, which — because filters are AND-combined — empties the entire
   audience.

9. **Filter operator translation.** **#423**: in `ExpressionBuilder`'s business-override branch the
   `"="` case emits `Expression.GreaterThanOrEqual` — a verbatim copy of the `"<"` case four lines
   above. The surrounding operators are deliberately inverted (these fields express "days ago"), which
   is precisely what camouflages it.

10. **Recurrence evaluation.** **#422**: `SendScheduledNotificationJob` divides elapsed months and
    years by `(int)notification.RecurrenceType`, but that enum is a discriminator —
    `Weekly = 1, Monthly = 2, Yearly = 3` — with no interval field anywhere. Monthly therefore fires on
    alternate months, Yearly every third year, and Weekly is correct only because it divides by 1.

## Data written

In order, and across **two databases**:

| Store | What | Note |
|---|---|---|
| Chat DB (`IChatContext` → `ChatConnectionString`, SQL Server) | `CustomerNotification`, `CustomerNotificationCustomersData` | Separate SQL database from the platform's main one — confirmed at `Shared/SharedWeb/Helpers/Extenstions/DataBaseServices.cs:36` |
| Main DB (`ITalabatkContext`) | `Customer.IOSDevices` / `AndroidDevices`, audience membership, scheduled-notification definitions | |
| Firebase (external) | The push itself | Irreversible once dispatched |

**The two-database split is the mechanism behind #387 and #431.** They share no transaction, so:
- **#387** — a wallet notification is committed to the chat DB *and* a push dispatched, both before the
  wallet's own save is checked. On failure the customer has been told their balance changed and it has
  not.
- **#431** — a recipient row is added to `chatContext` and then `talabatkContext` is saved. The row is
  never persisted, and because the wrong context's save succeeds trivially, the guard passes and the
  push still goes out.

## External calls

- **Firebase Cloud Messaging** — the push itself. Credentials per #331.
- No retry or dead-letter handling was traced for a Firebase rejection. See Open Questions.

## Failure modes

| # | Effect |
|---|---|
| **#422** | Monthly campaigns fire bimonthly, yearly ones triennially. Silent |
| **#425** | Area- and merchant-targeted campaigns reach **nobody**; batch and real-time audiences disagree |
| **#423** | `=` behaves as `≥`, so a targeted cohort silently becomes a much larger one |
| **#424** | Arabic fallback column holds English text for English-preferring customers |
| **#351** | Removing one device unregisters **all** of that user's devices — the likeliest cause of any "notifications stopped working" report |
| **#387** | Push sent and chat DB committed before the authoritative save; a false financial notification survives a rolled-back transaction |
| **#431** | Recipient row silently never written; push still sent |
| **#72** | Four unchecked `SaveChangesAsync()` calls on the chat context in this job alone |
| **#331** | Five Firebase service-account private keys committed to git |

## Folded entities — the 17 satellites documented here

Everything the campaign and content side stores. `Ads` and `Announcement` are covered in depth in
[[Customer Ordering/Marketing & Content/_knowledge-graph|the feature's knowledge graph]], because their
asymmetry is the organising fact of the whole feature (🔴 #625); the rest are here.

### Merchant ad cards — the most rigorously validated entities in the feature

| Entity | What it is | Rules |
|---|---|---|
| `AdCard` | A purchasable ad slot: weekly price, four benefit lines, duration limits, a bulk discount and a tier badge | Nine guards, and they are real business rules rather than null checks: price cannot be negative (`Shared/TalabatkLogic/TalabatkModels/AdCard.cs:89`), **all four** benefit lines are mandatory (`:94`, `:99`, `:104`, `:109`), the minimum duration must be at least one week (`:115`), the maximum cannot be negative (`:120`), the discount must be 0–100 (`:125`), and the discount-week count must fall inside the min/max range (`:134`). `Update` reuses the same validator, so create and update cannot drift |
| `AdReservation` | A merchant's booking of a card for a date range | Equally strict, and the guards encode the commercial rules: restaurant and card must exist (`Shared/TalabatkLogic/TalabatkModels/AdReservation.cs:48`, `:53`), the start must precede the end (`:58`), the period must be **a whole number of weeks** (`:66`), an update **cannot change the duration while the ad is running** (`:127`), and the total booked period cannot exceed the card's maximum (`:168`). `ChangeActiveStatus` (`:174`) and `MarkAsDeleted` (`:178`) are the unguarded pair. Its merchant-facing list is the one that can return literal `null` entries — 🔴 `_conflicts.md` #437 — and its `Reserve` endpoint takes the restaurant id from the request body — 🔴 #603 |

These two are worth knowing about because they are the counter-example to this feature's reputation: the
money-bearing part of Marketing & Content validates properly, and the content-bearing part does not.

### Audiences — campaign targeting

| Entity | What it is | Rules |
|---|---|---|
| `AudianceFilter` | One criterion in an audience definition: a type, an operator and a value | `Create` rejects an empty filter value (`Shared/TalabatkLogic/TalabatkModels/AudianceFilter.cs:18`) and an invalid operator (`:21`). The **operator semantics are where #423 lives**: a filter meaning "exactly N days" selects everyone within N days, so campaigns reach a wider audience than marketing intends. Note the spelling, which is the real one |
| `AudienceCustomer` | One customer's membership of an audience, registered or not | `Create` (`Shared/TalabatkLogic/TalabatkModels/AudienceCustomer.cs:20`), `Activate` (`:29`) and `Deactivate` (`:33`) — no guards. Carries **both** `CustomerId` and `UnregisteredCustomerId` plus an `IsRegesteredCustomer` discriminator, so one table holds both kinds of person and nothing enforces that exactly one id is set |
| `AudienceCustomerAds` | Links an audience to a customer-ad campaign | Four fields, `Instance` only (`Shared/TalabatkLogic/TalabatkModels/AudienceCustomerAds.cs:16`) |

### Scheduled campaigns

| Entity | What it is | Rules |
|---|---|---|
| `NotificationTarget` | One target of a scheduled campaign — a type and a value | Private ctor, `Instance` only, no guards (`Shared/TalabatkLogic/TalabatkModels/NotificationTargets.cs:21`). Note the file is `NotificationTargets.cs` while the class is singular |
| `ScheduledNotificationCustomerGroupType` | Which customer group a scheduled campaign targets | Private ctor, `Instance` only, no guards (`Shared/TalabatkLogic/TalabatkModels/ScheduledNotificationCustomerGroupType.cs:20`) |
| `NotificationExecutionHistory` | One run of a scheduled campaign: when, whether it succeeded, how many were sent, and the error if not | Private ctor, `Instance` only (`Shared/TalabatkLogic/TalabatkModels/NotificationExecutionHistory.cs:28`). This is the table that would answer "did last night's campaign actually go out", and it records `IsSuccess`, `SentCount` and `ErrorMessage` — so the data needed to measure 🔴 #422's interval bug already exists |

### Content

| Entity | What it is | Rules |
|---|---|---|
| `FAQItem` | One question-and-answer pair, in both languages, with a display order | The most thorough content entity: `Instance` requires the Arabic question and answer, the **English** question and answer, and a creator (`Shared/TalabatkLogic/TalabatkModels/FAQItem.cs:27-39`); `Update` requires the same five with a modifier (`:59-71`); `UpdateOrder` requires a modifier (`:86`). All three return `Result`, and create and update agree exactly. The only entity in this group that requires both languages |
| `PrivacyPolicy` | The privacy-policy text for one language | `Instance` requires non-empty text and a valid language id (`Shared/TalabatkLogic/TalabatkModels/PrivacyPolicy.cs:26`, `:29`); `Update` requires non-empty text (`:43`). Tracks `CreatedBy`/`ModifiedBy` |
| `TermsAndConditions` | The terms text for one language | **The same kind of document, held to a lower standard.** `Instance` returns a bare object with **no guard at all** (`Shared/TalabatkLogic/TalabatkModels/TermsAndConditions.cs:32`), while `Update` does check ("Text Can't be Empty", `:23`). So empty terms can be created but not saved by an edit. No `CreatedBy`/`ModifiedBy` either — and the language column is misspelt `LangaugeId`. Both documents are ones customers are asked to accept, and only one of them can be audited |
| `AnnouncementDescription` | An announcement's message in one language | `AddDescription` assigns, no guard (`Shared/TalabatkLogic/TalabatkModels/AnnouncementDescription.cs:17`) — consistent with its unguarded parent (🔴 #625) |
| `AboutApp` | The three counters shown on the about screen | Three properties, **no methods** (`Shared/TalabatkLogic/TalabatkModels/AboutApp.cs`) |

### What the split means

The feature divides on whether money is involved. `AdCard` and `AdReservation` — the merchant-paid
surface — carry eighteen guards between them, including genuine commercial invariants like "a booking
must be a whole number of weeks" and "you cannot change the duration of a running ad". Everything the
customer reads for free is weaker, and `Announcement` (🔴 #625) is weakest. The clearest single
comparison is inside one pair: `PrivacyPolicy` validates on create and tracks who changed it;
`TermsAndConditions`, its twin, does neither.

## Open Questions

- [ ] Should `TermsAndConditions` match `PrivacyPolicy` — guard on create, and record who changed it?
      Customers are asked to accept both.
- [ ] `AudienceCustomer` can carry both a customer id and an unregistered-customer id. Is exactly one
      enforced anywhere, and what happens to a campaign row with both or neither?
- [ ] `NotificationExecutionHistory` already records `IsSuccess` and `SentCount` per run. Has anyone
      queried it against the intervals #422 produces?
- [ ] `AdCard` requires all four benefit lines. Is that a marketing rule or an artefact of the four
      fixed columns?
- Whether a Firebase rejection (invalid or expired token) is retried, logged, or leads to token
  cleanup. **Not traced in this pass** — and it matters, because #351 means the token field is likely
  to be empty rather than stale.
- The originating commands and event handlers that create notification rows were not enumerated; only
  the send-side job was traced.
- `SendNotificationForNotificationIdAndVoucher`'s divergence from the plain variant — not traced.
- Whether the in-app notification list reads the primary or secondary text field, which determines
  whether #424 is user-visible or only latent in storage.
- The force-update mechanism for the six mobile apps (`version-update.yml`) was in scope for this note
  and **was not reached**.
- Device-token registration (`AddCustomerDevicesCommand`) was not read; only the removal defect (#351)
  is established, from prior work.

## Related
- [[Notification-Delivery.business|Notification Delivery — Business]]
- [[Support-and-Chat.technical|Support and Chat]] — same separate chat database
- [[Customer-Account-Lifecycle.technical|Customer Account Lifecycle]]
- [[Admin-Access-and-Oversight.technical|Admin Access and Oversight]] — who may compose campaigns
