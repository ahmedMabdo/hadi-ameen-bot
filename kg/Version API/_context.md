---
id: 8orders/version-api/context
note_type: context
context: Version API
last_updated: 2026-08-23
tags: [context, version-api]
---
# Version API — Overview

Tells a freshly launched mobile app whether the version it is running is still allowed. The customer
and delivery-man apps call it before anything else; if the answer says the build is too old, the app
shows a forced-update screen instead of its home page. Nothing else in the business depends on it.

> No `CONTEXT.md` business glossary exists for this context yet. That is not this graph's job to
> create — recorded here as an open question rather than invented.

## Why this hub exists even though the code is out of scope

The skill lists **Version API** as one of the six bounded contexts, while the project that implements
it, `Talabatk.VersionAPI`, is marked `excluded:out-of-scope-user-instruction` in
[[_coverage-manifest|the coverage manifest]] — a standing instruction, not an oversight. Left
unresolved, that reads as a missing context in one place and an ignored project in the other.

Both are true at once, and this note is where they are reconciled:

| Question | Answer | Where it is proved |
|---|---|---|
| Is Version API a context? | Yes — it is one of the six | `CONTEXT-MAP.md`, and the skill's context list |
| Are its files audited? | No — deliberately excluded | `_coverage-manifest.md`, status `excluded:out-of-scope-user-instruction` (10 files) |
| Does it have documented features? | No, by that same instruction | `_system/_feature-map.tsv` maps its 3 controller files to `excluded:out-of-scope-user-instruction` |
| Would including it later restructure anything? | No | Add feature folders under this context and flip the map rows; nothing else moves |

`verify-notes.js` knows this: `Version API` is listed in `CONTEXTS_WITHOUT_FEATURES`, so the context
must have this hub, and is not expected to have features. The contradiction is now data, not an
argument.

## What is actually in the project

Read only from the file list and the project's own shape — **the code was not audited**, so nothing
below should be treated as a verified rule:

- `Talabatk.VersionAPI/Controllers/VersionsController.cs` — the single endpoint surface.
- `Talabatk.VersionAPI/Controllers/AppVersionDto.cs` — the response shape.
- `Talabatk.VersionAPI/Controllers/VersionReader.cs` — reads the configured version data.
- **No project references to `Shared/*` at all** — it shares no domain code, no `DbContext`, and no
  JWT validation with the other five hosts. That isolation is why excluding it costs the rest of the
  graph nothing.

## Integrates With

- **Mobile apps (not in this repo)** — the only consumers. They call this API on launch; there is no
  client code here to trace, so behaviour beyond the HTTP contract is unknown by construction.
- No inbound or outbound dependency on any other context: it appears nowhere in
  [[_integrations|the integration register]], which is consistent with having no `Shared/*`
  references.

## Open Questions

- [ ] Where does the allowed-version list actually come from — configuration, database, or a file?
      Unaudited by instruction; `VersionReader.cs` is the place to look if the instruction changes.
- [ ] Is the forced-update decision made by this API or by each app? Only the API contract is
      visible from this repo.
- [ ] No `CONTEXT.md` exists for this context.
- [ ] If the Mobile Apps repository is added as a second root later, this is the context whose
      consumers become visible for the first time — worth revisiting then.
