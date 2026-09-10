---
id: 8orders/identity-and-access/authentication-and-tokens/identity-technical
note_type: technical
rule_count: 11
context: Identity & Access
feature: Authentication & Tokens
group: Identity
covers: [Application, AspNetUser, AspNetUserAttendance, AspNetUserRestaurant, AspNetUserShift, RefreshToken, RolePermission, UserShift, UserShiftDetails]
sources:
  - path: Shared/TalabatkLogic/TalabatkModels/AspNetUserAttendance.cs
    sha1: 4236ef661ba1
  - path: Shared/TalabatkLogic/TalabatkModels/AspNetUserRestaurant.cs
    sha1: 85e99210df2c
  - path: Shared/TalabatkLogic/TalabatkModels/AspNetUserShift.cs
    sha1: 3e8a63791842
  - path: Shared/TalabatkLogic/TalabatkModels/RolePermission.cs
    sha1: 713a69361667
  - path: Shared/TalabatkLogic/TalabatkModels/UserShift.cs
    sha1: 75820933c4bd
  - path: Shared/TalabatkLogic/TalabatkModels/UserShiftDetails.cs
    sha1: 0413f00cfb72
  - path: AdminUi/appsettings.json
    sha1: 8510ab3fc024
  - path: Talabatk.IDS/Configurations/Identity.cs
    sha1: 9ac57860f5a7
  - path: Talabatk.IDS/Configurations/IdentityConfig.cs
    sha1: 7d1c5a777680
  - path: Talabatk.IDS/Talabatk.IDS.csproj
    sha1: 778fc69e5029
  - path: Talabatk.IDS/appsettings.json
    sha1: d4087410cefc
  - path: TalabatkAPIs/appsettings.json
    sha1: 13b918e5a078
  - path: TalabatkDelivery/appsettings.json
    sha1: f64d0fc469c9
  - path: TalabatkRestaurants/appsettings.json
    sha1: 26dfcca93fb6
last_updated: 2026-08-23
tags: [identity-access, authentication, technical, backend-web]
---
# Identity — Technical

> **Layer:** Backend-Web (`Talabatk.IDS` host) — this is startup/configuration wiring for
> IdentityServer4, not a domain entity/POCO; "fields" below are configuration keys, not columns.
> **Context:** Identity & Access, per `CONTEXT-MAP.md` — the token issuer every other context
> (Customer Ordering, Delivery, Restaurant Portal, Admin) trusts.
> **Source Path:** `Talabatk.IDS/Configurations/Identity.cs`,
> `Talabatk.IDS/Configurations/IdentityConfig.cs`   **Last Updated:** 2026-08-21

Bridges to `Talabatk.IDS/CONTEXT.md` (actor/state/OTP glossary — read that first for terminology)
and to [[Login-and-Activation|Login & Activation]] (the full per-actor login/activation-check
comparison, already documented in detail — not duplicated here).

## Security handling note
This subsystem's whole job is managing credentials and signing keys. Per this note's own
constraints, no secret value, password, private-key/certificate content, or token is reproduced
below — only file paths, key/field names, and line numbers.

## Business Rules

### Rule 1: The production token-signing certificate is loaded from a file with a hardcoded password
- **Plain language:** In production, the certificate that signs every access token is read from a
  local `.pfx` file, unlocked with a password that is a literal string in the source code.
- **Source:** `Identity.cs:100-101` (`Path.Combine(AppContext.BaseDirectory, "8orders.pfx")`, then
  `new X509Certificate2(filePath, "..." , X509KeyStorageFlags.MachineKeySet)` — password value not
  reproduced here). **Established, do not re-investigate:** `_conflicts.md` #331 — the `.pfx` file
  itself (`Talabatk.IDS/8orders.pfx`) is the real production signing certificate, including its
  private key, committed to git; the hardcoded password is at this same cited line. Anyone with
  repository read access could extract the key and mint valid tokens for any user across all 5
  hosts — the highest-severity finding in the whole audit.

### Rule 2: Development and production sign tokens with different, non-interchangeable key material
- **Plain language:** A developer running the app locally gets an ephemeral, auto-generated signing
  key; production always uses the committed certificate from Rule 1.
- **Source:** `Identity.cs:120-123` (`if (env.IsDevelopment()) builder.AddDeveloperSigningCredential();`)
  vs. `:124-130` (`else` branch: `builder.AddSigningCredential(cert).AddValidationKey(cert)`, throws
  if `cert == null`). This dev/prod switch is itself correctly scoped per `_conflicts.md` #331 (a
  separate `tempkey.jwk` file's blast radius is limited *because* this gate is right).

### Rule 3: Every consuming application is a pre-registered, in-code OAuth/OIDC client — not data
- **Plain language:** There are 19 named "clients" (one or more per consuming app or tool), each
  with its own allowed login method, allowed scopes, and secret, all defined as C# object literals,
  not rows in a database.
- **Source:** `Talabatk.IDS/Configurations/IdentityConfig.cs:192-620` (`Clients` property). Representative shapes:
  - Resource-owner-password + client-credentials (username/password login): `mobile` (`:195-215`,
    Customer app), `RestaurantMobile` (`:331-351`), `deliverymobile` (`:413-433`, Delivery Man app)
  - Custom `otp` grant only: `OtpMobile` (`:217-237`)
  - Authorization Code (+ PKCE for one): `AdminAngularClient` (`:381-412`, AdminUi — `RequirePkce =
    true` at `:406`), `AngularClient` (`:353-380`, explicitly commented `//Restaurant Web` at
    `:352` — TalabatkRestaurants)
  - Hybrid flow + reference (opaque) access tokens: `TalabatkAdminDelivery` (`:450-486`,
    `ClientName = "Delivery Web"` at `:453`)
  - Client Credentials only (server-to-server): `TalabatkAdminApis` (`:434-449`) — the client whose
    `client_id`/`client_secret` are hardcoded and reused across hosts per `_conflicts.md` #280/#289
  - Implicit flow (3 Swagger UIs — dev/test tooling only): `:507-572`
- Every client's secret is a literal string passed through `.Sha256()` (e.g. `:198`, `:220`, `:601`)
  — values not reproduced here. **New observation from this pass, not yet logged in
  `_conflicts.md`:** the `VMSTools` client's secret literal at `Talabatk.IDS/Configurations/IdentityConfig.cs:601` is a
  high-entropy, random-looking string, unlike every other client's descriptive
  `"<ClientId>Secret"`-shaped placeholder — worth confirming separately whether it is a live
  credential needing rotation.

### Rule 4: Token lifetimes are configuration-driven and differ for server-to-server callers
- **Plain language:** How long a token lasts before the app has to ask for a new one is a config
  value, not hardcoded per client — except server-to-server calls get a longer-lived token type.
- **Source:** `appsettings.json:67-70` — `TokenLifeTime` (10800s / 3h), `TokenLifeTimeServertoServer`
  (43200s / 12h), `RefreshTokenLifeTime` (2628003s / ~30.4 days, sliding), `MaximumRefreshTokenLifeTime`
  (31536035s / ~365 days, absolute cap). Read per-client via `config.GetValue<int>(...)` — e.g.
  `Talabatk.IDS/Configurations/IdentityConfig.cs:203-205` (`mobile`, using `TokenLifeTime`) vs. `:439` (`TalabatkAdminApis`,
  using `TokenLifeTimeServertoServer` instead).

### Rule 5: Password policy is deliberately weak; lockout is short
- **Plain language:** A password can be 6 characters with no digit, uppercase letter, or symbol
  required; 5 wrong attempts locks the account for 5 minutes.
- **Source:** `Identity.cs:196-201` (`Password.RequireDigit`/`RequireLowercase`/
  `RequireNonAlphanumeric`/`RequireUppercase` all `false`, `RequiredLength = 6`,
  `RequiredUniqueChars = 0`), `:204-206` (`Lockout.DefaultLockoutTimeSpan` = 5 minutes,
  `MaxFailedAccessAttempts = 5`). Applies platform-wide to every ASP.NET Identity-backed sign-in.

### Rule 6: Password-grant and OTP-grant login enforce different status checks per client — bridged, not re-documented
- **Plain language:** Which checks (deleted/blocked/inactive) apply at login and on every later
  request depends on which app is logging in, and this has already been traced in full elsewhere.
- **Source:** `Identity.cs:67-69` wires the custom pieces in (`.AddAspNetIdentity<AspNetUser>()`,
  `.AddResourceOwnerValidator<CustomerResourceOwnerValidator>()`,
  `.AddProfileService<CustomerIdentityProfileService>()`); `:40` registers the custom `otp` extension
  grant (`AddTransient<IExtensionGrantValidator, OtpGrantValidator.OtpCustomerGrantValidator>`). The
  actual per-client rule comparison — including the confirmed `RestaurantMobile`-has-no-status-check
  gap and the `deliverymobile` `IsActiveAsync` double-bug (`_conflicts.md` #292) — lives in
  [[Login-and-Activation|Login & Activation]]; not duplicated here.

### Rule 7: Data Protection keys are per-server unless explicitly switched to a shared path — and production leaves the switch off
- **Plain language:** The encryption keys behind login cookies and anti-forgery tokens are, by
  default, stored separately on each web server; there's a config switch to share them instead, and
  production does not use it.
- **Source:** `Identity.cs:105-106` (reads `ProtectionKey:UseSharedKey` / `:SharedKeyPath`),
  `:108-118` (branch: `true` → `PersistKeysToFileSystem` at the shared path; `false`, the `else`
  taken in production, → a local `{ContentRoot}\..\keys` folder). **Established, high severity, do
  not re-investigate:** `_conflicts.md` #367 — production's `appsettings.json:194` sets
  `UseSharedKey: false`, leaving the provisioned Azure File share at `:195` unused, on a two-server
  farm — sessions/antiforgery tokens don't survive a load-balancer hop or a deploy.

### Rule 8: Four of the five host projects trust this issuer via a config-only `Authority` URL — and it is not the same string everywhere
- **Plain language:** Each of the other four apps is told where to find this login service through
  one config setting, and two different hostnames are in use for that setting across production.
- **Source:** `AdminUi/appsettings.json:27` and `TalabatkDelivery/appsettings.json:20` both set
  `Authority: "https://idsx.8orders.com"`; `TalabatkAPIs/appsettings.json:19` and
  `TalabatkRestaurants/appsettings.json:19` both set `Authority: "https://ids.8orders.hadaf.website"`
  — the same hostname `Talabatk.IDS/appsettings.json:11`'s own `"IDS"` key uses for itself. **Not
  traced in this pass** whether `idsx.8orders.com` and `ids.8orders.hadaf.website` are aliases of
  the same origin (e.g. a CNAME/reverse-proxy) or a genuine two-hostname drift — flagged as an open
  question, not assumed to be a bug. Talabatk.IDS itself is the only one of the 5 hosts that does
  not consume an external `Authority` — it validates JWTs for its own endpoints (e.g. SignalR hubs)
  using its self-referential `"IDS"` key instead (`Identity.cs:150,160`).

### Rule 9: SignalR hub connections accept the access token from a query-string parameter, scoped to `/hubs` only
- **Plain language:** Browser WebSocket connections can't set a normal `Authorization` header, so
  this service is told to also accept the token as a URL parameter — but only for hub paths.
- **Source:** `Identity.cs:177-188` (`JwtBearerEvents.OnMessageReceived` — reads `access_token` from
  `context.Request.Query`, applied only `if (path.StartsWithSegments("/hubs"))`).

### Rule 10: System roles are seeded idempotently at startup, not managed as an EF migration
- **Plain language:** A fixed list of back-office roles is created on every app startup if missing,
  rather than being part of the database migration history.
- **Source:** `Identity.cs:240-300` (`InitalizeRolesAndUsers`) — `admin`, `operation`, `restaurant`,
  `DataEntry`, `Accountants`, `RestaurantAdmin`, `Customer`, `Delivery`, each guarded by
  `if (!roleManager.RoleExistsAsync(...))`.

### Rule 11: IdentityServer4 itself is end-of-life software, on top of an already-unsupported .NET runtime
- **Plain language:** The open-source product this entire login system is built on stopped
  receiving updates years ago, and the .NET version it runs on is itself past its own support date.
- **Source:** `Talabatk.IDS/Talabatk.IDS.csproj` (`<TargetFramework>net6.0</TargetFramework>`).
  **Established, do not re-investigate:** `_conflicts.md` #332 — IdentityServer4 is EOL, superseded
  by its commercial successor Duende IdentityServer; .NET 6 reached end-of-life 2024-11-12 with no
  further security patches, and this pins the entire dependency graph (also affects DevExpress
  v21.2, EF Core 6 platform-wide, not specific to Identity).

## Key Fields
*(Identity is configuration/wiring, not a data entity — "fields" here are the configuration keys
and constants that actually govern behavior.)*

| Key / Constant | Meaning | Source |
|---|---|---|
| `8orders.pfx` + hardcoded password | Production token-signing certificate | `Identity.cs:100-101`; see #331 |
| `ProtectionKey:UseSharedKey` / `:SharedKeyPath` | Data Protection key-ring mode | `Identity.cs:105-118`; `appsettings.json:193-195`; see #367 |
| `IDS` | This host's own base URL — used for its own JwtBearer validation, not an `Authority` | `appsettings.json:11`; `Identity.cs:150,160` |
| `TokenLifeTime` / `TokenLifeTimeServertoServer` / `RefreshTokenLifeTime` / `MaximumRefreshTokenLifeTime` | Per-client token lifetimes, in seconds | `appsettings.json:67-70` |
| `FeatureManagement:DeploymentName` | Feature-flag namespace this host resolves flags under | `Startup.cs:215`; established mismatch at `_conflicts.md` #356 (`"Testing"` in production, not `"Production"`) |
| Client catalog (`ClientId` values) | 19 pre-registered OAuth/OIDC clients, one per consuming app/tool | `Talabatk.IDS/Configurations/IdentityConfig.cs:192-620` |
| `Password.*` / `Lockout.*` options | Platform-wide password strength & lockout policy | `Identity.cs:196-206` |

## Dependencies & Integrations
| Depends on / integrates | Side/Context | Via | Notes |
|---|---|---|---|
| `AspNetUser`/`AspNetRole` (back-office/admin accounts) | Backend-Domain, Identity & Access | `AddIdentity<AspNetUser, AspNetRole>()` | `Identity.cs:33-37` |
| `Customer`, `DeliveryMen` (separate identity stores) | Backend-Domain, Identity & Access | `CustomerUserManager`, `DeliveryUserManager` | Used throughout `CustomerResourceOwnerValidator.cs:31,34` and `CustomerIdentityProfileService.cs:24,27`; the DI registration site for these two managers was not traced in this pass. See [[Customer.technical|Customer]], [[DeliveryMen.technical|DeliveryMen]] |
| `TalabatkContext` (EF Core, SQL Server) | Backend-Data | `AddOperationalStore` persists IdentityServer's grants/tokens | `Identity.cs:60-66` |
| AdminUi, TalabatkAPIs, TalabatkDelivery, TalabatkRestaurants | API host (all 4 other hosts) | Each validates JWTs against this service's `Authority` | See Rule 8; cross-service token-handling bugs already logged at `_conflicts.md` #279, #280, #286, #289, #306 |
| Esquio (external feature-flag service) | Third-party HTTP, same project | `FeaturesController` (this project) | `_conflicts.md` #39 |
| `IOtpAuthService` | Backend-Application | Consumed by the custom `otp` grant validator | See [[Login-and-Activation|Login & Activation]] |
| Google OAuth (external login) | Third-party OIDC | `AddGoogle(...)`, placeholder `ClientId`/`ClientSecret` literally reading `"copy client ID from Google here"` | `Identity.cs:136-146` — not wired to a real Google app in this configuration |

## Change Surface
| Signal | Value | Notes |
|---|---|---|
| Direct dependents (Ring 1) | 4 other host projects + every mobile/API client | Every host validates tokens issued here; nothing in the platform bypasses it |
| Sides touched | 3 confirmed | Backend-Web (this host's config), Backend-Domain (Identity stores it wires up), Backend-Data (operational/grant store) |
| Cross-context integrations | High — 4 of 4 other contexts | Customer Ordering, Delivery, Restaurant Portal, Admin all authenticate through this one issuer |
| Domain events involved | 0 traced | IdentityServer4 raises its own internal pipeline events (`RaiseErrorEvents`/`RaiseInformationEvents`/etc., `Identity.cs:51-54`) — not traced further in this pass |
| Hub? | Yes — highest blast-radius component in the system | A compromise here (Rule 1 / #331) defeats every authorization check in every other context |

## Folded entities — the 6 satellites documented here

The rows that hang off `AspNetUser`: what a back-office user may do, which merchant they belong to, and
when they were on shift. **None of the six validates anything**, which for two of them is consequential.

| Entity | What it is | Rules |
|---|---|---|
| `RolePermission` | Grants one permission to one role — the row the whole back-office authorisation model rests on | Four properties, `Instance` only, **no guards** (`Shared/TalabatkLogic/TalabatkModels/RolePermission.cs:18`). This is the join that `PermissionAuthorizationHandler` consults for every `[Permission]` attribute in AdminUi, so the entity carrying the platform's authorisation model is a bare pair of ids with no invariants of its own — nothing here prevents a duplicate or an orphaned grant. Every finding in the #404 permission family concerns whether an attribute is *present*; this is the table that decides what the attribute *means* |
| `AspNetUserRestaurant` | Which merchant a back-office or portal user belongs to | Four properties, `Instance` only, no guards (`Shared/TalabatkLogic/TalabatkModels/AspNetUserRestaurant.cs:17`). This is the tenancy link — the row that should scope a merchant user to their own restaurant — and it is also where the Restaurant Portal's IDOR family bites: the queries in `_idor-instances.md` instances 9-21 take a restaurant id from the caller instead of resolving it through this table |
| `AspNetUserShift` | A named shift window for back-office staff | `Instance` returns `Result<AspNetUserShift>` and **cannot fail** (`Shared/TalabatkLogic/TalabatkModels/AspNetUserShift.cs:36`), so `FromTime` may follow `ToTime` |
| `AspNetUserAttendance` | A staff member's attendance on a date, against a shift | `Instance` only, no guards (`Shared/TalabatkLogic/TalabatkModels/AspNetUserAttendance.cs:12`). The entity behind 🔴 `_conflicts.md` #432 — attendance that reports success without recording anything |
| `UserShift` | A staff shift instance with a start and end, owning its offline periods | Private ctor, `Instance` (`Shared/TalabatkLogic/TalabatkModels/UserShift.cs:93`) and a `void UpdateShift` (`:103`), neither validating. It is a 109-line file for two methods, because most of it is the property surface |
| `UserShiftDetails` | One offline period inside a shift, with a reason | Private ctor, `Instance` (`Shared/TalabatkLogic/TalabatkModels/UserShiftDetails.cs:22`) and `SetOfflineTo` (`:26`), no guards — so an offline period can be closed before it opened, and nothing prevents two open periods at once |

### What the split means

Two of these six are load-bearing for security and neither has an invariant: `RolePermission` defines what
every `[Permission]` attribute grants, and `AspNetUserRestaurant` defines which merchant a user is. The
codebase's two largest finding families — the permission gaps (#404, #414, #446, #622) and the
Restaurant Portal tenancy IDORs (#580-#605) — are both about code failing to consult these two tables
correctly. The tables themselves enforce nothing, so every guarantee has to come from the caller.

## Related
- Business view: [[Identity.business|Identity]]
- [[Login-and-Activation|Login & Activation]] — full per-actor login/activation rule comparison (not duplicated here)
- [[Customer.technical|Customer]] · [[DeliveryMen.technical|DeliveryMen]] — the identity records this service authenticates
- [[Configuration.technical|Configuration]] — the feature-flag `DeploymentName` mismatch (#356) also touches this host
- `Talabatk.IDS/CONTEXT.md` — actor/state/OTP terminology; read that first

## Open Questions
- [ ] Whether `idsx.8orders.com` and `ids.8orders.hadaf.website` (Rule 8) are the same origin (alias/reverse-proxy) or a genuine configuration drift — not traced in this pass.
- [ ] Whether the `VMSTools` client secret (`Talabatk.IDS/Configurations/IdentityConfig.cs:601`) is a live credential requiring rotation — observed in this pass, not yet logged in `_conflicts.md`.
- [ ] What IdentityServer4 does when `IsActiveAsync` falls through with no matching client branch (`RestaurantMobile`) — version-dependent, see `_conflicts.md` #292 / [[Login-and-Activation|Login & Activation]].
- [ ] Where `CustomerUserManager`/`DeliveryUserManager` are actually registered in DI — referenced throughout but registration site not opened in this pass.
- [ ] The `notifications` and `FeatureManagement` `ApiResource`/scope consumers were not traced end-to-end in this pass.
