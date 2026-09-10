# 8Orders KG — Coverage Manifest (summary)

> Machine-generated. **Do not hand-edit.** Regenerate with
> `node docs/knowledge-graph/_system/verify-coverage.js --generate`,
> verify with `node docs/knowledge-graph/_system/verify-coverage.js`.
>
> Row-level data lives in `_coverage-manifest.tsv` (one line per file). This file is the
> summary. The verifier is the authority — if it exits non-zero, this summary is stale.

**Attested commit:** `7b9a6962b09a8900b3704d62ecb5fc40c8331650`

**Total tracked in-scope files:** 15116
**In coverage scope (read + swept):** 7550
**Deliberately excluded:** 7566

## By status

| status | files |
|---|---|
| `excluded:agent-tooling` | 15 |
| `excluded:binary-asset` | 134 |
| `excluded:build-output` | 65 |
| `excluded:build-tooling` | 3 |
| `excluded:documentation` | 15 |
| `excluded:editor-settings` | 4 |
| `excluded:ide-personal-settings` | 2 |
| `excluded:ide-tool-artifact` | 4 |
| `excluded:ide-tooling` | 34 |
| `excluded:legacy-project-user-instruction` | 5301 |
| `excluded:lockfile` | 4 |
| `excluded:nswag-generated-client` | 10 |
| `excluded:out-of-scope-user-instruction` | 15 |
| `excluded:planning-notes-not-source` | 10 |
| `excluded:repo-template` | 1 |
| `excluded:runtime-generated-keyring` | 1 |
| `excluded:scratch-output` | 2 |
| `excluded:source-map` | 64 |
| `excluded:spreadsheet-test-data` | 1 |
| `excluded:styling-no-business-rules` | 443 |
| `excluded:test-project-user-instruction` | 71 |
| `excluded:this-knowledge-graph` | 1056 |
| `excluded:tooling-dotfile` | 12 |
| `excluded:vendor-library` | 298 |
| `excluded:windows-shortcut-junk` | 1 |
| `read` | 5617 |
| `swept` | 1933 |

## By phase (covered files only)

| phase | files |
|---|---|
| 1-1 | 951 |
| 1-2 | 1 |
| 1-3 | 238 |
| 1-4 | 927 |
| 2-1 | 676 |
| 2-2 | 1096 |
| 2-3 | 109 |
| 2-4 | 131 |
| 2-5 | 38 |
| 2-x | 754 |
| 3-1 | 271 |
| 3-1/3-2 | 993 |
| 3-2 | 127 |
| 3-3 | 2 |
| 4-1 | 38 |
| 5-1 | 40 |
| 5-2 | 4 |
| 5-3 | 8 |
| 5-4 | 7 |
| 5-5 | 12 |
| 6-1 | 7 |
| 6-2 | 3 |
| 6-3 | 16 |
| 7-1 | 12 |
| 8-1 | 25 |
| 9-1 | 293 |
| 9-2 | 60 |
| 9-3 | 15 |
| 9-4 | 14 |
| 9-5 | 18 |
| 9-6 | 549 |
| 9-7 | 40 |
| 9-9 | 61 |
| P10 | 14 |

## By extension

| ext | files |
|---|---|
| `cs` | 6630 |
| `js` | 2215 |
| `css` | 1237 |
| `md` | 1220 |
| `ts` | 995 |
| `html` | 838 |
| `png` | 485 |
| `json` | 336 |
| `cshtml` | 198 |
| `map` | 147 |
| `scss` | 128 |
| `less` | 94 |
| `resx` | 40 |
| `vsrepx` | 38 |
| `svg` | 38 |
| `txt` | 30 |
| `tmpl` | 30 |
| `(noext)` | 29 |
| `pubxml` | 26 |
| `xsc` | 24 |
| `xsd` | 24 |
| `xss` | 24 |
| `jpg` | 20 |
| `yml` | 18 |
| `ttf` | 16 |
| `ico` | 16 |
| `csproj` | 15 |
| `gitignore` | 14 |
| `woff` | 14 |
| `mdc` | 13 |
| `xml` | 11 |
| `woff2` | 11 |
| `bak` | 10 |
| `config` | 10 |
| `sln` | 9 |
| `jshintrc` | 9 |
| `eot` | 8 |
| `sql` | 7 |
| `tsv` | 6 |
| `editorconfig` | 5 |
| `gitattributes` | 5 |
| `gif` | 4 |
| `dll` | 4 |
| `py` | 3 |
| `ps1` | 3 |
| `mp3` | 3 |
| `bowerrc` | 3 |
| `npmignore` | 3 |
| `browserslistrc` | 2 |
| `gitkeep` | 2 |
| `wav` | 2 |
| `jwk` | 2 |
| `otf` | 2 |
| `zip` | 2 |
| `psd` | 2 |
| `lock` | 2 |
| `gzip` | 2 |
| `nvmrc` | 2 |
| `bithoundrc` | 2 |
| `jsbeautifyrc` | 2 |
| `jslintrc` | 2 |
| `nuspec` | 2 |
| `sh` | 2 |
| `markdown` | 2 |
| `docx` | 2 |
| `pdf` | 1 |
| `lnk` | 1 |
| `webp` | 1 |
| `yaml` | 1 |
| `cer` | 1 |
| `pfx` | 1 |
| `asax` | 1 |
| `licx` | 1 |
| `htm` | 1 |
| `jscsrc` | 1 |
| `csslintrc` | 1 |
| `dist_jshintrc` | 1 |
| `versions` | 1 |
| `swf` | 1 |
| `csv` | 1 |
| `bat` | 1 |

## How this prevents a fourth false completion

Every prior round asserted completeness in prose and could not detect its own staleness.
This manifest is derived from `git ls-files`, so a rebase, merge, or new commit that adds
a file makes the verifier fail and name that file. Coverage is therefore a property that
is re-provable at any commit, not a claim frozen at the moment someone wrote it down.
