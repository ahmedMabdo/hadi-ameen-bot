---
id: 8orders/system/fix-650-review
note_type: system
last_updated: 2026-08-24
tags: [review, security, branch]
---
# Review guide — `fix/650-user-privilege-escalation`

Everything the register marks ✅ Fixed lives on this branch, and **the branch is not merged**. Until it
lands, all 40 of these defects are live in production.

```bash
git fetch origin
git checkout fix/650-user-privilege-escalation
```

| | |
|---|---|
| Commits | 3 |
| Source files changed | 36, across 5 hosts |
| Register findings closed | 40 |
| Build | all five hosts, 0 errors |
| Tests added | 16, all passing (`UserPrivilegeGuardTests`) |
| Branched from | `KnowledgeGraph`, **not** `master` — see [Before you open the PR](#before-you-open-the-pr) |

Each finding also has its own file with a status you can edit as review proceeds:
`_issues/` — see [[_system/_issues/_index\|the issue index]].

---

## Review in this order

Not by file. By what happens if the fix is wrong.

### 1. The four that matter most

| # | Severity | What was exploitable | Where the fix is |
|---|---|---|---|
| **#650** | critical | A back-office account with only Users-page access could give itself the `admin` role and `FullControl` — and `admin` short-circuits the authorization filter entirely. One form post to unrestricted access, plus the Hangfire dashboard. | `Talabatk.IDS/Application/Security/UserPrivilegeGuard.cs` (new) |
| **#509** | critical | `POST api/DeliveryMen/ResetPassword` was `[AllowAnonymous]`, never read the `Code` its own DTO declares, and minted its own reset token. Knowing a driver's phone number was enough to take the account. | `Talabatk.IDS/Controllers/DeliveryMenController.cs` |
| **#638** | high | `GET api/Report/GetTransactions` bound its whole query from the query string, so `MerchantId` was caller-chosen — any merchant could read another's statement ledger. | `TalabatkRestaurants/Controllers/Reports/ReportController.cs` |
| **#405** | high | `AllUserPermissions` was `[AllowAnonymous]`, so an unauthenticated caller got any user's full permission list. | `AdminUi/Controllers/Permission/PermissionController.cs` |

**Read `UserPrivilegeGuard.cs` first.** It is ~110 lines, it is the only new authorization primitive, and
four commands depend on it. Everything else in this branch is an application of an existing pattern.

The invariant it enforces: *a caller may not grant a privilege it does not itself hold, and may not act
on an account more privileged than its own.* Four rules, and the last two are not optional —

- assigning `admin` requires the caller to be `admin`
- granting `FullControl` requires the caller to have `FullControl`
- **modifying** an `admin` account requires the caller to be `admin`
- **modifying** a `FullControl` account requires the caller to have `FullControl`

Without the last two, the first two are decorative: a caller who cannot promote itself could still reset
an admin's password through the same command and log in as them.

### 2. The tenant-isolation batch — `0bdb2c2aa`, 32 findings

The merchant portal repeated one mistake across roughly 45 endpoints: a caller-supplied `restaurantId`
reaching a handler unchecked, or the session value used as a *default* that any supplied parameter
overrode. Two new services carry the policy so the endpoints share one implementation:

- `TalabatkRestaurants/Helpers/Security/MerchantScope.cs` — resolves a caller-named restaurant, list or
  CSV against the session.
- `TalabatkRestaurants/Helpers/Security/MerchantOwnership.cs` — for the harder half, where the caller
  names an option group, group item, menu item, price or category and the handler applied no restaurant
  filter at all.

**The policy is not invented.** It is `CategoryController.GetCurrentRestarunt` — the one place that
already did this correctly — promoted to a service. Compare the two if you want to check that nothing
was tightened by accident.

### 3. The remaining seven — `64040cf80`

`#509`, `#573`, `#575`, `#581`, `#615`, `#643`, `#649`. Each closes a distinct hole; `#649` and `#643`
are the two that need action outside the code (below).

---

## ⚠️ Two deployment steps no gate can check

Both are marked with `⚠️ DEPLOYMENT` comments at the code. Both fail **in production, quietly**, not at
build time.

**#649 — JWT audience validation.** `Talabatk.IDS` was the only one of five bearer validators not pinning
an audience, so it accepted any token this IdentityServer ever issued, including customer and driver app
tokens. It now pins five: `TalabatkAdmin`, `notifications`, `TalabatkApis`, `TalabatkApisDelivery`,
`AngularApis`.

> **Verify that list covers every client that calls this host's bearer-protected endpoints, against the
> IdentityServer ApiResource/Scope configuration, before deploying.** A missing audience logs that
> client out. It will not fail at build.

**#643 — the Ziwo robo-call webhook.** `POST api/RoboCall/WebHook` authenticated nobody: validation was
"CallID and Result are non-empty", so with a live CallID anyone could report `Answered` and silence the
escalation ladder. It now requires the `ApiKey` header, using `ApiKeyAuthorizeAttribute` — the mechanism
this solution already uses for inbound third-party callbacks.

> **Create the ApiKey row and configure it on the Ziwo side before deploying,** or robo-call results stop
> being recorded.

---

## Where these fixes could have broken you

The honest part of the review. Each fix narrows what a caller may do, so every one has a false-positive
mode. These are the ones to smoke-test.

| Change | If I got it wrong, you will see |
|---|---|
| `MerchantScope` back-office exemption (`admin`, `DataEntry`, `Accountants`) | A back-office role that legitimately spans merchants gets `"You Do Not Have A Permission To Acess This Restaurant"` on portal reports. Check the role list against who actually uses those screens. |
| `MerchantOwnership` | One extra indexed lookup per request on menu/price/option endpoints. Functionally correct, but worth a glance under load. |
| `IUserPrivilegeGuard` fails closed on an unresolvable caller | Any **background or system** caller of the four user commands is now refused. I found no such caller — all five call sites are HTTP — but a scheduled job added later would be denied, by design. |
| `#615` restricted operator tooling to `Roles = "admin"` | Whoever triggered the auto-assign job or the chat migration before may not hold `admin`. Confirm who needs it. |
| `#560` cooking-time writes now need `Permissions.General.Setting` | Someone administering cooking times without that permission loses write access. Reads untouched. |
| `#567` `MartCategoryController` gained `[Authorize]` | It was **fully anonymous**. Any caller relying on that — an internal script, a mobile path — now needs a token. |
| `#605` `GetUserPermissions` returns the caller's own | A UI reading another user's permissions via this endpoint now gets the caller's. Back-office roles can still pass a `userId`. |

**No permission name was invented.** Adding a `[Permission(X)]` nobody holds is fail-closed but an
outage, so either an existing constant that obviously fits was used, or the actual vulnerability
(anonymity) was closed and the permission-level gap left to the `#615` family. Each choice is stated at
its call site.

Suggested smoke test, three accounts: a **multi-restaurant MerchantAdmin**, a **single-restaurant
merchant**, and a **back-office admin**. Walk the portal's orders, reports, menu and option screens with
each. That covers the whole `0bdb2c2aa` surface.

---

## What I could not verify

Stated plainly so the review targets it:

- **No runtime or integration testing.** Five hosts compile with 0 errors and the guard has 16 unit
  tests. Compiling is not behaving.
- **The existing test suite could not help.** `TalabatkApplication.Test` has **273 pre-existing
  failures** on this branch, all from one `ArgumentNullException (path1)` in a fixture's `OneTimeSetUp`.
  Measured before and after these changes: 273 both times, passing 6 → 22. Not caused here, not fixed
  here — but it means the suite cannot tell you whether this branch regressed anything. Worth its own
  ticket.
- **`AdminUi/wwwroot/api/specification.json`** in `0bdb2c2aa` is an NSwag build artifact, regenerated by
  the build because attributes changed. Not hand-written. Safe to ignore, or drop from the PR.

---

## Before you open the PR

**This branch was cut from `KnowledgeGraph`, not from `master`.** So `master...fix/650` is ~452 files —
the entire knowledge graph plus these 36 code files. A PR straight to `master` merges both, and nobody
reviews 452 files properly.

Two workable orders:

1. **Merge `KnowledgeGraph` first**, then PR this branch on top — its diff becomes the clean 36 files.
2. **Cherry-pick the 3 commits onto a fresh branch off `master`** — gives you a 36-file security PR now,
   with the graph landing separately. Better if these fixes are urgent, and `#509` and `#650` argue that
   they are.

Either way, merging this branch invalidates citations in the graph, because it edits files the notes
cite. That is not a reason to delay — it is bookkeeping, and it is measured rather than guessed:

```bash
node docs/knowledge-graph/_system/merge-reverify.js fix/650-user-privilege-escalation
```

At the time of writing: **30 cited files, 103 note↔file pairs** to re-verify. The number is not recorded
anywhere as a fact, because the branch keeps moving. `_system/REBASE-PLAYBOOK.md` has the procedure, and
the graph's own gates enforce it — `CITATION-STALE` will refuse to go green until the work is done.

One last thing: the commit hashes in this file and in `_conflicts.md` are reachable only from this
branch. A squash-merge replaces them with one new hash and every reference dies. `#651` records that, and
is why the register's status cells point at the finding rather than leaning on the hash.
