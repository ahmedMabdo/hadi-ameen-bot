---
id: 8orders/admin/admin-back-office/apikey
note_type: single
rule_count: 6
context: Admin
feature: Admin Back-Office
entity: ApiKey
entity_type: child
sources:
  - path: Shared/TalabatkLogic/TalabatkModels/ApiKey.cs
    sha1: 1ffab2f0d746
last_updated: 2026-08-23
tags: [admin, technical, backend-domain]
---
# ApiKey

An API credential issued to a system user (`AspNetUser`) — presumably for server-to-server or
integration access. `Shared/TalabatkLogic/TalabatkModels/ApiKey.cs`.

## Business rules
- `Instance(...)` (`:25-53`) validates: `name` non-blank, a real (non-default) creation date, an
  expiration date that's both non-default and after the creation date, and a positive `userId`.
- The key itself is a 32-byte cryptographically random value, base64-encoded
  (`GenerateApiKey`, `:56-61`, `RandomNumberGenerator.GetBytes(32)`) — generated internally, never
  passed in.
- No update/revoke method exists on this class — expiration is presumably enforced by checking
  `ExpiresAt` at auth time rather than by revoking the row; not traced to a caller in this pass.

## Rule / Decision Matrix

The API key a partner uses for server-to-server calls. Short, and unusually well guarded for this codebase — four checks on the only construction path, all of them real.

| # | Rule | Where | Notes |
|---|---|---|---|
| 1 | Name must be non-empty | `Shared/TalabatkLogic/TalabatkModels/ApiKey.cs:29` | The one guard most entities here would also have |
| 2 | Creation date must be valid | `Shared/TalabatkLogic/TalabatkModels/ApiKey.cs:33` | Rejects `default(DateTime)` rather than storing year 1 |
| 3 | Expiry must be in the future | `Shared/TalabatkLogic/TalabatkModels/ApiKey.cs:37` | "Expiration must be greater than current time!" — an already-expired key cannot be created, which is rarer than it sounds |
| 4 | User id must be positive | `Shared/TalabatkLogic/TalabatkModels/ApiKey.cs:41` | So a key always belongs to somebody |
| 5 | The key value is generated, never supplied | `Shared/TalabatkLogic/TalabatkModels/ApiKey.cs:56` | `GenerateApiKey()` produces it inside the entity, so a caller cannot choose a weak one |
| 6 | `Instance` returns `Result<ApiKey>`, so failure is representable | `Shared/TalabatkLogic/TalabatkModels/ApiKey.cs:25` | Private constructor, so this is the only way in |

> **The plaintext-key exposure is not in this entity.** `ApiKey` stores the key it generated; the
> finding is that the listing endpoint returns it for every key belonging to the caller — see
> `_conflicts.md` #402 and `_idor-instances.md`. Nothing about that is visible from the entity.

## Related
- `AspNetUser` — the owning system user (not documented as its own entity in this pass; part of
  ASP.NET Identity's built-in tables).

## Open Questions
- [ ] Where/how `ExpiresAt` is actually checked (which host, which middleware) — not traced.
- [ ] Whether keys can be revoked before expiry — no method found for it here.
