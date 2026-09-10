---
id: 8orders/customer-ordering/marketing-and-content/scenarios
title: Marketing & Content — Scenario Catalog
note_type: scenarios
context: Customer Ordering
feature: Marketing & Content
audience: Business · QA · Developer
last_updated: 2026-08-23
sources:
  - path: TalabatkAPIs/Controllers/Ads/AdsController.cs
    sha1: 78498e08ab55
  - path: TalabatkAPIs/Controllers/Announcement/AnnouncementController.cs
    sha1: 666fa6fdebd4
  - path: TalabatkAPIs/Controllers/CustomerAds/CustomerAdsController.cs
    sha1: 1fbb1a466491
  - path: TalabatkAPIs/Controllers/FAQ/FaqController.cs
    sha1: c5df7635da25
  - path: TalabatkAPIs/Controllers/PrivacyPolicy/PrivacyPolicyController.cs
    sha1: 8cc6e9ce5ccc
  - path: TalabatkAPIs/Controllers/TermsAndConditions/TermsAndConditionsController.cs
    sha1: dd380da1c7db
  - path: TalabatkAPIs/Controllers/AbouApp/AboutAppController.cs
    sha1: c19a9c9ef215
  - path: Shared/TalabatkLogic/TalabatkModels/Ads.cs
    sha1: f6b239bd29b2
  - path: Shared/TalabatkLogic/TalabatkModels/Announcement.cs
    sha1: c75d676577ae
  - path: Shared/TalabatkApplication/Commands/AddAnnouncementCommand/AddAnnouncementCommand.cs
    sha1: b78f0b666edc
  - path: Shared/TalabatkApplication/Commands/EditAnnouncementCommand/EditAnnouncementCommand.cs
    sha1: 784a5b3c78ef
  - path: Shared/TalabatkApplication/Queries/GetAnnouncementQuery/GetAnnouncementQuery.cs
    sha1: cff594f70689
  - path: Shared/TalabatkApplication/Queries/GetAvalibleAdsByLocationQuery/GetAvalibleAdsByLocationQuery.cs
    sha1: d26333bb3f85
tags: [customer-ordering, marketing-and-content, scenarios]
---
# Marketing & Content — Scenario Catalog

> The customer-facing **read** side of what
> [[Admin/Catalog & Content Administration/_knowledge-graph|Catalog & Content Administration]] authors.
> All seven endpoints are GETs; nothing here writes. The behaviour worth knowing is therefore split
> between **what the read query is willing to show** and **what the authoring path was willing to save**
> — and those two disagree for announcements.

## The two near-identical entities that behave differently

`Ads` and `Announcement` model the same three fields — `HasTime`, `StartTime`, `EndTime` — with opposite
levels of rigour. This is the single most useful fact in the feature, because every announcement defect
below follows from it:

| | `Ads` | `Announcement` |
|---|---|---|
| Factory | `Instance(...)` returning `Result<Ads>` (`Shared/TalabatkLogic/TalabatkModels/Ads.cs:33`) | `AddAnnouncement(...)` returning a plain object (`Shared/TalabatkLogic/TalabatkModels/Announcement.cs:34`) |
| Time guard on create | **Yes** — "Start And End Time Should Have values" (`Shared/TalabatkLogic/TalabatkModels/Ads.cs:47`) | **None** |
| Image guard on create | **Yes** — "Both Arabic And English Images must have value" (`Shared/TalabatkLogic/TalabatkModels/Ads.cs:53`) | n/a |
| Turning the window off | `Update` **clears** both times (`Shared/TalabatkLogic/TalabatkModels/Ads.cs:86-87`) | nothing clears them on edit — 🔴 #625 |
| Deactivation | via `Update` | explicit `DeActivateAnnouncement()` (`Shared/TalabatkLogic/TalabatkModels/Announcement.cs:66`) |
| Can reach "HasTime with null times"? | **No** | **Yes**, and the row then never displays — 🔴 #625 |

The read queries make the asymmetry consequential. Both dereference `.Value` inside the `HasTime` branch
— `Shared/TalabatkApplication/Queries/GetAvalibleAdsByLocationQuery/GetAvalibleAdsByLocationQuery.cs:65-66`
for ads and `Shared/TalabatkApplication/Queries/GetAnnouncementQuery/GetAnnouncementQuery.cs:56` for
announcements. For ads that is safe **only because** `Ads.Instance` guarantees the times exist. For
announcements nothing guarantees it, so the comparison silently evaluates to unknown and the row drops
out of the result.

## Happy path

| # | Precondition | Action | Expected outcome | Rule / source |
|---|---|---|---|---|
| H1 | Ads configured, in window, customer inside a covered area | `GET api/Ads/Get` | Eligible ads for the store type and location | `TalabatkAPIs/Controllers/Ads/AdsController.cs:34` |
| H2 | Same, newer client | `GET api/Ads/GetV1` | Same data, V1 shape — and gated by the `Advertisements` feature flag | `TalabatkAPIs/Controllers/Ads/AdsController.cs:55-60` |
| H3 | Active announcement for the customer's area, today is a display day, now is inside the hour window | `GET api/Announcement/GetAnnouncement` | The announcement | `TalabatkAPIs/Controllers/Announcement/AnnouncementController.cs:30-34` |
| H4 | Same, newer client | `GET api/Announcement/GetAnnouncementV1` | Same query, V1 shape | `TalabatkAPIs/Controllers/Announcement/AnnouncementController.cs:51-56` |
| H5 | Customer in a targeted audience | `GET api/CustomerAds/Avalible` | The customer's targeted ads | `TalabatkAPIs/Controllers/CustomerAds/CustomerAdsController.cs:30-37` |
| H6 | Same, newer client | `GET api/CustomerAds/AvalibleV1` | Same query, V1 shape | `TalabatkAPIs/Controllers/CustomerAds/CustomerAdsController.cs:59-66` |
| H7 | Customer opens help | `GET api/faq/getAllFqaItems` | FAQ items | `TalabatkAPIs/Controllers/FAQ/FaqController.cs:28-32` |
| H8 | Customer opens the privacy policy in their language | `GET api/GetPrivacyPolicy?langId=` | The text for that language | `TalabatkAPIs/Controllers/PrivacyPolicy/PrivacyPolicyController.cs:25-30` |
| H9 | Customer opens terms | `GET api/GetTermsAndConditions?langId=` | The text for that language | `TalabatkAPIs/Controllers/TermsAndConditions/TermsAndConditionsController.cs:24-29` |
| H10 | Customer opens "about" | `GET api/AboutApp/Info` | Store-type, item and customer counts | `TalabatkAPIs/Controllers/AbouApp/AboutAppController.cs:26-32` |

## Partial / incremental

| # | Precondition | Action | Expected outcome | Rule / source |
|---|---|---|---|---|
| P1 | Ad created with `hasTime` true | read ads | Shown only inside its hour window; both times are guaranteed present by the factory, which is what makes the read query's `HasTime` branch safe to dereference | `Shared/TalabatkLogic/TalabatkModels/Ads.cs:44-48`, `Shared/TalabatkApplication/Queries/GetAvalibleAdsByLocationQuery/GetAvalibleAdsByLocationQuery.cs:65-66` |
| P2 | Ad's hour window later turned off | `Update` | Both times **cleared**, so the ad becomes always-eligible | `Shared/TalabatkLogic/TalabatkModels/Ads.cs:78-88` |
| P3 | Announcement's hour window turned off **on create** | add handler | Times nulled by the handler — the one place the invariant is enforced | `Shared/TalabatkApplication/Commands/AddAnnouncementCommand/AddAnnouncementCommand.cs:131-135` |
| P4 | Announcement's hour window turned off **on edit** | edit handler | Flag changes, times **kept** — no layer clears them | 🔴 #625 · `Shared/TalabatkApplication/Commands/EditAnnouncementCommand/EditAnnouncementCommand.cs:117-121` |
| P5 | Announcement has `DisplayDays` | read announcements | Restricted to the listed weekdays; empty or null means every day | `Shared/TalabatkApplication/Queries/GetAnnouncementQuery/GetAnnouncementQuery.cs:53` |
| P6 | Announcement has no dates at all | read announcements | Eligible on every date — the date filter only applies when **both** dates are present | `Shared/TalabatkApplication/Queries/GetAnnouncementQuery/GetAnnouncementQuery.cs:49-51` |
| P7 | Announcement targets a specific area | read announcements | Matches that area **or** the area-less broadcast rows | `Shared/TalabatkApplication/Queries/GetAnnouncementQuery/GetAnnouncementQuery.cs:47` |
| P8 | Two client versions in the field | each calls its variant | Three endpoint pairs serve two shapes of the same query | `TalabatkAPIs/Controllers/Ads/AdsController.cs`, `TalabatkAPIs/Controllers/CustomerAds/CustomerAdsController.cs`, `TalabatkAPIs/Controllers/Announcement/AnnouncementController.cs` |

## Negative / guard

| # | Precondition | Action | Expected outcome (rejection) | Rule / source |
|---|---|---|---|---|
| N1 | No token | any endpoint **except** the ads ones | 401 — the other six controllers require the JWT bearer scheme | `TalabatkAPIs/Controllers/FAQ/FaqController.cs:16`, `TalabatkAPIs/Controllers/Announcement/AnnouncementController.cs:14` |
| N1b | **No token** | `GET api/Ads/Get` or `GET api/Ads/GetV1` | **Accepted** — `AdsController`'s `[Authorize]` is commented out, so the whole controller is anonymous | 🔴 `_conflicts.md` #443 · `TalabatkAPIs/Controllers/Ads/AdsController.cs:15` |
| N2 | Token without the `Customer` role | `GET api/CustomerAds/Avalible` | 403 — the only role-gated action in this feature | `TalabatkAPIs/Controllers/CustomerAds/CustomerAdsController.cs:32` |
| N3 | Ad created with `hasTime` true and a missing time | (Admin authoring) | **Rejected** — "Start And End Time Should Have values" | `Shared/TalabatkLogic/TalabatkModels/Ads.cs:44-48` |
| N4 | Ad created with only one language's image | (Admin authoring) | **Rejected** — both images required | `Shared/TalabatkLogic/TalabatkModels/Ads.cs:50-54` |
| N5 | Announcement created with `HasTime` and unparseable times | (Admin authoring) | **Accepted** and saved active — no guard exists at any layer | 🔴 #625 · `Shared/TalabatkLogic/TalabatkModels/Announcement.cs:34` |
| N6 | Announcement created with a date range but no hour window | (Admin authoring) | **Saved, notified, then the request fails** on an empty cron expression | 🔴 #623 · `Shared/TalabatkApplication/Commands/AddAnnouncementCommand/AddAnnouncementCommand.cs:199-205` |

## Returns / cancellation / reversal

| # | Precondition | Action | Expected outcome | Rule / source |
|---|---|---|---|---|
| R1 | Announcement no longer wanted | `DeActivateAnnouncement()` | Deactivated explicitly — the cleanest off-switch in the feature | `Shared/TalabatkLogic/TalabatkModels/Announcement.cs:66-70` |
| R2 | A new announcement is created for the same areas | add handler | **Every other active announcement in those areas is deactivated first**, and that deactivation is committed before the new row exists | 🟡 #627 · `Shared/TalabatkApplication/Commands/AddAnnouncementCommand/AddAnnouncementCommand.cs:99-128` |
| R3 | A broadcast announcement is created | add handler | Every active announcement with the same `IsShortCut` flag is deactivated — platform-wide, not per area | 🟡 #627 · `Shared/TalabatkApplication/Commands/AddAnnouncementCommand/AddAnnouncementCommand.cs:113-124` |
| R4 | Ad no longer wanted | `Update` with the window changed, or deactivate in Admin | `Ads` has no dedicated deactivate method | `Shared/TalabatkLogic/TalabatkModels/Ads.cs:73` |
| R5 | Announcement edited after creation | edit handler | The new schedule is written under a **different** Hangfire id than the create path used, so the original job survives | 🔴 #624 |
| R6 | Legal text published in error | edit it in Admin | Customers see the change immediately — no versioning observed | [[Admin/Catalog & Content Administration/_knowledge-graph\|Catalog & Content Administration]] |

## Integration (cross-side / cross-context)

| # | Precondition | Action | Expected outcome | Rule / source |
|---|---|---|---|---|
| I1 | Admin authors an ad or announcement | it appears here | This feature is read-only; authoring lives in Admin | [[Admin/Catalog & Content Administration/_knowledge-graph\|Catalog & Content Administration]] |
| I2 | Announcement saved | immediate push sent, then two recurring jobs registered | Notification delivery is Hangfire + FCM, not this feature | `Shared/TalabatkApplication/Commands/AddAnnouncementCommand/AddAnnouncementCommand.cs:267-289` |
| I3 | Campaign audience defined in Admin | `CustomerAds/Avalible` | Targeting is evaluated by the audience rules — whose "exactly N days" filter is wider than stated | 🔴 `_conflicts.md` #423 |
| I4 | Ad read by location | area geometry intersected | Ads are filtered by the area polygon the coordinates fall in | `Shared/TalabatkApplication/Queries/GetAvalibleAdsByLocationQuery/GetAvalibleAdsByLocationQuery.cs:51` |
| I5 | Ad-card list read by a merchant | merchant portal | Can contain literal `null` entries — the merchant sibling omits the placeholder fallback the two customer-facing queries use | 🔴 `_conflicts.md` #437 |
| I6 | About-app counts requested | aggregate read | Store-type, item and customer counts computed for display | `Shared/TalabatkLogic/TalabatkModels/AboutApp.cs` |

## Correctness scenarios — current behaviour

| # | Precondition | Action | Actual outcome today | Finding |
|---|---|---|---|---|
| X1 | Announcement submitted with `HasTime` true and time strings `DateTime.TryParse` rejects | customer reads announcements | Saved active with null times; the query's `x.StartTime.Value.TimeOfDay` comparison is unknown, so the announcement is **never shown to anyone** and nothing reports an error | 🔴 **#625** · `Shared/TalabatkApplication/Queries/GetAnnouncementQuery/GetAnnouncementQuery.cs:56` |
| X2 | Announcement edited to untick its hour window | later read | The flag goes false, the times stay in the row — the edit handler parses `StartTime`/`EndTime` and passes them straight through, with no branch that nulls them; inert today only because the read query short-circuits | 🔴 **#625** · `Shared/TalabatkApplication/Commands/EditAnnouncementCommand/EditAnnouncementCommand.cs:117-121` |
| X3 | Announcement with a date range and no hour window | admin saves it | Announcement committed, push sent, **then a 500** — the end-job cron is the empty string it was initialised with | 🔴 **#623** · `Shared/TalabatkApplication/Commands/AddAnnouncementCommand/AddAnnouncementCommand.cs:199-205` |
| X4 | Admin retries after X3 | add handler runs again | The retry deactivates the row the first attempt created, so the outcome looks clean while a trail of deactivated rows accumulates | 🔴 **#623** + 🟡 **#627** |
| X5 | Two announcements created for the same area set | both saved | They share one Hangfire recurring-job id, so only the most recent has a live schedule | 🔴 **#624** · `Shared/TalabatkApplication/Commands/AddAnnouncementCommand/AddAnnouncementCommand.cs:276-289` |
| X6 | Broadcast announcements (no areas) | any number created | All of them collide on the id `AnnouncementNotificationStartJobForArea:` — one global slot | 🔴 **#624** |
| X7 | Announcement created for areas `3,7`, then edited | edit handler | The edit writes to a different id and a different job type, orphaning the original recurring job | 🔴 **#624** |
| X8 | The same date string submitted to create and to edit | both handlers | Parsed by different rules — `TryParseExact`/invariant on create, culture-sensitive `TryParse` on edit, which can transpose day and month | 🔴 **#626** |
| X9 | **No credential** | `GET api/Ads/Get` | Ads for any store type and coordinates, with no token | 🔴 **#443** · `TalabatkAPIs/Controllers/Ads/AdsController.cs:15` |
| X10 | Campaign targeted "exactly N days" | customer ads | Reaches customers within N days — wider than intended | 🔴 **#423** |

## Open Questions

- [x] **Do the announcement read queries filter on `HasTime` or on the times?** Both — `!x.HasTime` short-circuits, and the `HasTime` branch compares `StartTime`/`EndTime` (`Shared/TalabatkApplication/Queries/GetAnnouncementQuery/GetAnnouncementQuery.cs:55-67`). That is what makes X1 a live silent-invisibility bug and X2 a latent one.
- [ ] Which of the `V1`/non-`V1` endpoint pairs does the shipped app call? Three pairs are live and only `GetV1` carries the `Advertisements` feature flag.
- [ ] Should `Announcement` gain the guards `Ads` already has? They model the same three fields, and the entity is the only layer that could enforce it for both the add and the edit path.
- [ ] How many announcements exist today with `HasTime` true and a null `StartTime` or `EndTime`? That is the exact population of X1, and it is a one-line query.
- [ ] Is the legal text versioned anywhere, given customers are asked to accept it?
- [ ] Are the about-app counts cached, or recomputed per request on the host that serves every customer?
- [ ] Why does the query add two minutes to "now" (`Shared/TalabatkApplication/Queries/GetAnnouncementQuery/GetAnnouncementQuery.cs:41`)? It widens every window by two minutes and no comment explains it.
