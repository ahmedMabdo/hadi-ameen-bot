---
id: 8orders/customer-ordering/marketing-and-content/knowledge-graph
title: Marketing & Content — Knowledge Graph
note_type: knowledge-graph
context: Customer Ordering
feature: Marketing & Content
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
  - path: Shared/TalabatkLogic/TalabatkModels/AboutApp.cs
    sha1: c925be4c24e1
  - path: Shared/TalabatkApplication/Commands/AddAnnouncementCommand/AddAnnouncementCommand.cs
    sha1: b78f0b666edc
  - path: Shared/TalabatkApplication/Commands/EditAnnouncementCommand/EditAnnouncementCommand.cs
    sha1: 784a5b3c78ef
  - path: Shared/TalabatkApplication/Queries/GetAnnouncementQuery/GetAnnouncementQuery.cs
    sha1: cff594f70689
  - path: Shared/TalabatkApplication/Queries/GetAvalibleAdsByLocationQuery/GetAvalibleAdsByLocationQuery.cs
    sha1: d26333bb3f85
  - path: Shared/TalabatkApplication/Queries/GetActiveAdsQuery/GetActiveAdsQuery.cs
    sha1: 8ec4395e7447
tags: [customer-ordering, marketing-and-content, technical, api-host]
---
# Marketing & Content — Knowledge Graph

> **Context:** Customer Ordering
> **Source Project:** `TalabatkAPIs` (7 controllers, all read-only)
> **Entities:** `Ads`, `Announcement`, `AboutApp` — all folded into
> [[Customer Ordering/Marketing & Content/Notification-Delivery.technical|Notification-Delivery]]
> **Register findings open here:** #443, #623, #624, #625, #626, #627, #423, #437

Everything a customer reads that is not a restaurant or an order: banners, targeted campaign ads,
app-wide announcements, FAQ, privacy policy, terms, and the about-app counters. Seven controllers, seven
GET-only surfaces, no writes — authoring lives in
[[Admin/Catalog & Content Administration/_knowledge-graph|Catalog & Content Administration]].

That makes the feature sound thin, and its previous note treated it that way. It is not. The read side is
simple; the **contract between the read side and the authoring side** is where six register findings
live, because the two sides disagree about what a valid announcement is.

## The `Ads` / `Announcement` asymmetry — the organising fact

Both entities model the same three fields. One defends them, the other does not:

| | `Ads` | `Announcement` |
|---|---|---|
| Construction | `Result<Ads> Instance(...)` — a failure is representable | `Announcement AddAnnouncement(...)` — no failure is representable |
| `hasTime` with a null time | **refused**, `Shared/TalabatkLogic/TalabatkModels/Ads.cs:44-48` | accepted, `Shared/TalabatkLogic/TalabatkModels/Announcement.cs:34` |
| Missing per-language image | **refused**, `Shared/TalabatkLogic/TalabatkModels/Ads.cs:50-54` | n/a |
| Turning the window off | `Update` nulls both times, `Shared/TalabatkLogic/TalabatkModels/Ads.cs:84-88` | nothing nulls them on the edit path — #625 |
| Deactivation | via `Update` | `DeActivateAnnouncement()`, `Shared/TalabatkLogic/TalabatkModels/Announcement.cs:66-70` |

The consequence is not stylistic. Both read queries dereference `.Value` inside the `HasTime` branch:

```
GetAvalibleAdsByLocationQuery.cs:65-66   !x.HasTime || (x.HasTime && ... x.StartTime.Value.Hour ...)
GetAnnouncementQuery.cs:55-56            !x.HasTime || (x.HasTime && x.StartTime.Value.TimeOfDay <= currentTime ...)
```

For ads, that is safe **because** `Instance` refuses the bad state. For announcements nothing refuses it,
so a row saved with `HasTime` true and a null time makes the comparison unknown and the announcement is
**never returned to anyone** — saved, active, invisible, with no error at any layer (#625).

## The announcement authoring path — five findings in one handler

`AddAnnouncementCommand` is the only real logic in the feature's orbit, and it is worth reading in full
before touching announcements. Its shape:

```
AddAnnouncementCommand.Handle
  ├── DisplayDays defaulted to "0,1,2,3,4,5,6" — twice, at :75-78 and again at :87-90
  ├── areas supplied?  -> DeActivateAnnouncement() on EVERY active announcement in them   (:99-111)
  ├── no areas (broadcast)? -> same for EVERY active announcement with this IsShortCut,
  │                            committed in its own SaveChanges before the new row exists  (:113-128)
  ├── !HasTime -> null both times   <-- the ONLY place this invariant is enforced          (:131-135)
  ├── dates parsed with TryParseExact("yyyy/MM/dd HH:mm:ss", InvariantCulture)             (:144-155)
  ├── times parsed with TryParse -> null on failure, and nothing objects                   (:163-171)
  ├── cron branch A: dates + times  -> start cron, end cron            (correct)           (:181-194)
  ├── cron branch B: dates, no times -> start cron, then START AGAIN   (bug #623)          (:199-205)
  ├── cron branch C: times, no dates -> start cron, end cron            (correct)          (:216-218)
  ├── AddRange + SaveChanges, then immediate push per announcement                          (:249-273)
  └── two RecurringJob.AddOrUpdate calls keyed on AreasIds              (bug #624)          (:276-289)
```

Reading it top to bottom gives all five findings:

1. **#623 — the same variable assigned twice.** In branch B, `delayStartJobTime` takes the start cron at
   `:199` and is then **reassigned the end cron** at `:203`; `delayEndJobTime` keeps the `string.Empty` it
   was given at `:80-81`. So the start job runs on the end schedule, and the end job is registered with an
   empty cron that Hangfire rejects — **after** the announcement was committed at `:250` and the push sent
   at `:267`. The identical slip is in `EditAnnouncementCommand.cs:147-153`, which is what makes it a
   pattern rather than a typo. Branch B is the ordinary case: a date range with no hour window.
2. **#624 — recurring jobs keyed on the request, not the announcement.** `:276` and `:284` build the job id
   from `request.AreasIds`. Two announcements for the same area set therefore share one slot; every
   broadcast announcement shares the slot `AnnouncementNotificationStartJobForArea:`; and the edit path
   keys on the single `request.AreaId` (`EditAnnouncementCommand.cs:208`, `:216`), so it never matches the
   comma-list id the add path wrote — the original job is orphaned rather than replaced. The two paths also
   register different job types for the same schedule.
3. **#625 — the invariant lives in the wrong layer.** `:131-135` is the only enforcement of "no `HasTime`
   means no times", so the edit path leaves stale times behind and neither path refuses `HasTime` with
   unparseable times. Putting it in the entity, as `Ads` does, would fix both directions at once.
4. **#626 — two parsers for one input.** Add uses `TryParseExact` with an explicit format and
   `InvariantCulture` (`:144-155`); edit uses bare `TryParse` (`EditAnnouncementCommand.cs:109-113`), which
   is culture-sensitive and will read `dd/MM/yyyy` as `MM/dd/yyyy` on an en-US host.
5. **#627 — creation is destructive.** `:99-128` deactivates every overlapping active announcement before
   the new one is saved, so the real rule is *one active announcement per area at a time*. Nothing tells
   the caller, and combined with #623 a retry silently replaces the row the failed attempt created.

## Endpoint index

| Endpoint | Auth | What it does | Notes |
|---|---|---|---|
| `GET api/Ads/Get` | **none** | Ads for a store type at a coordinate | 🔴 #443 — `TalabatkAPIs/Controllers/Ads/AdsController.cs:15`, the class `[Authorize]` is commented out |
| `GET api/Ads/GetV1` | **none** | Same, V1 shape | Also behind the `Advertisements` Esquio flag, `TalabatkAPIs/Controllers/Ads/AdsController.cs:56` — the only flag-gated endpoint in the feature |
| `GET api/Announcement/GetAnnouncement` | JWT bearer | Active announcement for an area | `TalabatkAPIs/Controllers/Announcement/AnnouncementController.cs:30`; area, display-day and hour-window filtering all happen in the query |
| `GET api/Announcement/GetAnnouncementV1` | JWT bearer | Same query, V1 shape | `TalabatkAPIs/Controllers/Announcement/AnnouncementController.cs:52` |
| `GET api/CustomerAds/Avalible` | JWT bearer + role `Customer` | Ads targeted at the calling customer | `TalabatkAPIs/Controllers/CustomerAds/CustomerAdsController.cs:32` — the only role check here |
| `GET api/CustomerAds/AvalibleV1` | JWT bearer + role `Customer` | Same, V1 shape | `TalabatkAPIs/Controllers/CustomerAds/CustomerAdsController.cs:61` |
| `GET api/faq/getAllFqaItems` | JWT bearer | All FAQ items | `TalabatkAPIs/Controllers/FAQ/FaqController.cs:28` |
| `GET api/GetPrivacyPolicy` | JWT bearer | Privacy policy for a language | `TalabatkAPIs/Controllers/PrivacyPolicy/PrivacyPolicyController.cs:26` |
| `GET api/GetTermsAndConditions` | JWT bearer | Terms for a language | `TalabatkAPIs/Controllers/TermsAndConditions/TermsAndConditionsController.cs:25` |
| `GET api/AboutApp/Info` | JWT bearer (on the action) | Store-type, item and customer counts | `TalabatkAPIs/Controllers/AbouApp/AboutAppController.cs:28` — gated per action, not on the class |

Every one is a GET. There is no write surface in this feature at all, which is why the interesting
behaviour is the authoring contract rather than the endpoints.

## The read queries

| Query | Filters it applies | Notes |
|---|---|---|
| `GetAvalibleAdsByLocationQuery` | area polygon intersect (`:51`), store type, then the `HasTime` hour window (`:65-95`) | The hour-window arithmetic handles windows that cross midnight by shifting the day part; it is the most intricate expression in the feature |
| `GetActiveAdsQuery` | not deleted, active, `StartDate <= now <= EndDate`, restaurant in the customer's city (`:64`) | Sorts into ad tiers and substitutes a placeholder for empty tiers (`:128-144`) — the fallback the merchant sibling omits, which is #437 |
| `GetAnnouncementQuery` | active, area match or area-less, `IsShortCut` match, date range if both dates present, display day, hour window (`:46-67`) | Adds two minutes to "now" at `:41` with no explanation, widening every window |
| `GetAvalibleCustomerAdQuery` | audience membership | Its "exactly N days" predicate is wider than stated — #423 |

## Status / State

Stateless on this side. The only state is what Admin authored, plus the Hangfire recurring jobs the
announcement handlers register — and those are the state most likely to be wrong, per #623 and #624.

## Entity Index

| Entity | Layer | Type | Responsibility |
|---|---|---|---|
| `Ads` | Domain | legacy-poco-root | Placement with an optional hour window and per-language images; the one entity here that defends its own invariants. Documented in [[Customer Ordering/Marketing & Content/Notification-Delivery.technical\|Notification-Delivery]] |
| `Announcement` | Domain | legacy-poco-root | App-wide or per-area message with dates, display days and an optional hour window; no guards. Documented in [[Customer Ordering/Marketing & Content/Notification-Delivery.technical\|Notification-Delivery]] |
| `AboutApp` | Domain | lookup | Counters only, no behaviour. Documented in [[Customer Ordering/Marketing & Content/Notification-Delivery.technical\|Notification-Delivery]] |

## Feature Flow (Business Narrative)

```
AUTHORING (Admin)                        READING (customer app)
  AddAnnouncementCommand                   GET api/Announcement/GetAnnouncement
    deactivate overlapping    #627           filter: active, area, IsShortCut,
    normalise times (add only) #625                  dates, display days, hour window
    parse dates (TryParseExact) #626          -> a row with HasTime and null times
    build cron  #623                             never matches                #625
    save + push
    register 2 recurring jobs  #624

  Ad authoring (Admin)                     GET api/Ads/Get          <- anonymous  #443
    Ads.Instance refuses bad state           filter: area polygon, store type,
                                                     hour window (safe, thanks to the guard)
                                           GET api/CustomerAds/Avalible
                                             filter: audience membership          #423
```

## Key Cross-Cutting Relationships

| From | To | Relationship | Notes |
|---|---|---|---|
| This feature | [[Admin/Catalog & Content Administration/_knowledge-graph\|Catalog & Content Administration]] | reads what it authors | The authoring side owns every write; six findings live in the contract between them |
| `AddAnnouncementCommand` | Hangfire | registers two recurring jobs per announcement | #623 (empty cron), #624 (colliding ids) |
| `AddAnnouncementCommand` | FCM | immediate push on save | `Shared/TalabatkApplication/Commands/AddAnnouncementCommand/AddAnnouncementCommand.cs:267` |
| Ads reads | [[Admin/City & Geography Administration/_knowledge-graph\|City & Geography Administration]] | area polygons and cities | Ads are filtered by the area the coordinates fall in |
| `GetActiveAdsQuery` | merchant ad cards | shares the tier-sorting logic | The merchant copy drops the placeholder fallback — #437 |
| This feature | [[Customer Ordering/Restaurant & Menu Discovery/_knowledge-graph\|Restaurant & Menu Discovery]] | ads point at menu items | `Ads.MenuItemId` is the link |
| Customer mobile app | this feature | the only consumer | Not in this repository, so which endpoint version is live is unconfirmed |

## Change Surface

| Signal | Value | Notes |
|---|---|---|
| Direct dependents (Ring 1) | the customer mobile app; Admin authoring screens | |
| Sides touched | 3/5 | API host · Application · Domain |
| Cross-context integrations | 4 | Hangfire, FCM, Admin authoring, Admin geography |
| Register findings open | 8 (#443, #623, #624, #625, #626, #627, #423, #437) | Six of them concern announcements specifically |
| Hub? | no | |
| Risk flags | one anonymous controller; an announcement authoring path that commits, notifies, then fails; a domain entity with no invariants where its twin has them |

## Open Questions

- [ ] How many rows exist today with `HasTime` true and a null `StartTime` or `EndTime`? That is the exact
      live population of #625 and a one-line query.
- [ ] How many Hangfire recurring jobs match `AnnouncementNotification*ForArea:*`, and how many correspond
      to an announcement that is still active? That measures #624.
- [ ] Should the `HasTime` invariant move into `Announcement` itself, mirroring `Ads`? It is the only fix
      that covers both the add and the edit path.
- [ ] Why does `GetAnnouncementQuery` add two minutes to "now" (`Shared/TalabatkApplication/Queries/GetAnnouncementQuery/GetAnnouncementQuery.cs:41`)?
- [ ] Which of the three `V1`/non-`V1` pairs does the shipped app call, and can the older half be retired?
- [ ] Is `AdsController` intentionally anonymous — the ads it returns are location-scoped but not
      customer-scoped — or is #443 simply an un-restored `[Authorize]`?
