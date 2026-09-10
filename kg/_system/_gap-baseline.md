---
id: 8orders/system/gap-baseline
title: Gap baseline — the first computed answer to "how much is left"
note_type: system
last_updated: 2026-08-23
tags: [system, baseline, machine-generated]
---

# Gap baseline

> **Machine-generated. Do not hand-edit.** Regenerate with
> `node docs/knowledge-graph/_system/verify-notes.js --all`.
>
> This file is the answer three weeks of rounds could not produce: a *computed* count of what the
> knowledge graph is still missing. Every phase after Phase 0 is sized from these numbers, not from
> an estimate. When every count below reaches zero the graph is finished, and the same command
> re-proves it at any later commit.

```
commit           : 2f6a58575544df48814efff7a5a2ab19f5e633c0

entities: candidates in code            : 304
entities: classified rows               : 305
entities: to document                   : 243  (own note 38 · folded into a canonical note 205)
entities: excluded, with stated reason   : 62

depth:    rules-extracted notes          : 0
depth:    stub notes                     : 0
depth:    entities with no note at all    : 56  <- these FAIL

features: entry points in code           : 198
features: mapped                         : 198
features: total                          : 31  (complete 5 · incomplete 26)

notes:    in vault                       : 146
notes:    frontmatter problems           : 398
notes:    stale citations                : 0
notes:    unstamped citations            : 0
notes:    broken wikilinks               : 4

register: rows                           : 640
register: rows linking no note           : 447
flows:    integrations wired in code     : 7
flows:    unregistered / untraced        : 4 / 0
```

## Failure classes at baseline

```
KNOWLEDGE GAPS - 1260 problem(s) in 11 class(es):
  REGISTER-UNLINKED          447
  FRONTMATTER-INVALID        381
  COVERS-MISMATCH            205
  FEATURE-INCOMPLETE         93
  NOTE-ABSENT                56
  ENTITY-AT-FEATURE-DEPTH    29
  NOTE-AT-CONTEXT-DEPTH      23
  FRONTMATTER-MISSING        17
  WIKILINK-BROKEN            4
  INTEGRATION-UNREGISTERED   4
  CONTEXT-MISSING            1
```
