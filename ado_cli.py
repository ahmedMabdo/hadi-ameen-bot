#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
General-purpose Azure DevOps CLI for Hadi — replaces the `@azure-devops/mcp`
MCP server entirely. Talks to the ADO REST API directly over `requests` with
the same PAT (`AZURE_DEVOPS_PAT`) `ado_client.py` already uses, so no MCP
server, OAuth flow, or connector authorization is needed.

Each subcommand maps 1:1 to one of the `mcp__azure-devops__*` tools this
project used to grant in `.claude/settings.local.json`:

  READ (always allowed):
    list-projects            core_list_projects
    list-teams               core_list_project_teams
    search                   search_workitem            (WIQL Title CONTAINS)
    get-work-item            wit_get_work_item
    get-work-items           wit_get_work_items_batch_by_ids
    get-work-item-type       wit_get_work_item_type
    wiql                     wit_query_by_wiql
    my-work-items            wit_my_work_items
    list-backlogs            wit_list_backlogs
    list-backlog-work-items  wit_list_backlog_work_items
    list-iterations          work_list_iterations
    list-team-iterations     work_list_team_iterations
    team-settings            work_get_team_settings

  WRITE (create-only, confirmed with the requester first — see CLAUDE.md):
    create-work-item         wit_create_work_item
    add-comment               wit_add_work_item_comment
    add-child                 wit_add_child_work_items

  There is intentionally NO update or delete command — those stay denied,
  exactly as they were denied for the MCP server.

Env (read from a `.env` file alongside this script if present, else the
process environment) — same variables `ado_client.py` uses:
  AZURE_DEVOPS_PAT    personal access token, scope: Work Items (Read & Write)
  ADO_ORG             org name ("hadafsolutions") OR full URL — default hadafsolutions
  ADO_PROJECT         default project — default "0_Projects_Team"

Every command accepts `--project` to override the default project, and
write commands accept `--dry-run` to preview without creating anything.
Failures print a clear "ERROR: ..." message and exit non-zero instead of
raising a bare traceback, so Hadi can read what went wrong and relay it.
"""
import argparse
import json
import sys
from urllib.parse import quote

import requests

import ado_client
import cr_media
from ado_client import ADO_ORG_BASE, ADO_PROJECT, ADO_API_VERSION, ADO_CUSTOMER, ADO_APPLICATION

DEFAULT_FIELDS = ("System.Id,System.Title,System.State,System.WorkItemType,"
                  "System.AreaPath,System.Tags,System.ChangedDate,System.AssignedTo")

ISSUES_TABLE_FIELDS = (
    "System.Id,System.Title,System.State,System.WorkItemType,"
    "System.AssignedTo,System.CreatedDate,"
    "Microsoft.VSTS.Common.Severity,Microsoft.VSTS.Common.Priority"
)


def _call(method, url, headers, **kwargs):
    r = requests.request(method, url, headers=headers, timeout=30, **kwargs)
    if r.status_code == 401:
        sys.exit("ERROR: ADO auth failed (401) — check AZURE_DEVOPS_PAT")
    if r.status_code == 403:
        sys.exit(f"ERROR: ADO denied access (403) to {url}")
    if r.status_code == 404:
        sys.exit(f"ERROR: not found (404): {url}")
    if r.status_code >= 400:
        sys.exit(f"ERROR: ADO request failed — HTTP {r.status_code}: {r.text[:400]}")
    return r


def _headers(patch=False):
    h = ado_client._auth_headers()
    if patch:
        h["Content-Type"] = "application/json-patch+json"
    return h


def _project_base(project):
    return f"{ADO_ORG_BASE}/{quote(project)}/_apis"


def _team_base(project, team):
    return f"{ADO_ORG_BASE}/{quote(project)}/{quote(team)}/_apis"


def _print_json(data):
    print(json.dumps(data, ensure_ascii=False, indent=2))


def _list_work_item_types(project):
    r = _call("GET", f"{_project_base(project)}/wit/workitemtypes?api-version={ADO_API_VERSION}",
               _headers())
    return [t["name"] for t in r.json().get("value", [])]


def _fetch_fields(ids, project, fields):
    if not ids:
        return []
    url = (f"{_project_base(project)}/wit/workitems"
           f"?ids={','.join(str(i) for i in ids)}&fields={fields}&api-version={ADO_API_VERSION}")
    r = _call("GET", url, _headers())
    rows = []
    for item in r.json().get("value", []):
        f = item.get("fields", {})
        rows.append({
            "id": item.get("id"),
            "title": f.get("System.Title"),
            "state": f.get("System.State"),
            "type": f.get("System.WorkItemType"),
            "area_path": f.get("System.AreaPath"),
            "tags": f.get("System.Tags"),
            "changed_date": f.get("System.ChangedDate"),
            "assigned_to": (f.get("System.AssignedTo") or {}).get("displayName")
                            if isinstance(f.get("System.AssignedTo"), dict) else f.get("System.AssignedTo"),
            "url": f"{ADO_ORG_BASE}/{quote(project)}/_workitems/edit/{item.get('id')}",
        })
    return rows


def _fetch_issues_fields(ids, project):
    """جلب حقول issues-table: ID, Title, State, Type, Owner, Severity, Priority, CreatedDate."""
    if not ids:
        return []
    # batch بـ 200 كحد أقصى لـ ADO
    rows = []
    for i in range(0, len(ids), 200):
        chunk = ids[i:i+200]
        url = (f"{_project_base(project)}/wit/workitems"
               f"?ids={','.join(str(x) for x in chunk)}"
               f"&fields={ISSUES_TABLE_FIELDS}&api-version={ADO_API_VERSION}")
        r = _call("GET", url, _headers())
        for item in r.json().get("value", []):
            f = item.get("fields", {})
            assigned = f.get("System.AssignedTo")
            owner = (assigned.get("displayName") if isinstance(assigned, dict) else assigned) or "—"
            # Severity بيرجع "1 - Critical" أو "2 - High" إلخ — نقصّر للرقم + الكلمة
            sev_raw = f.get("Microsoft.VSTS.Common.Severity") or "—"
            pri_raw = f.get("Microsoft.VSTS.Common.Priority")
            pri = str(pri_raw) if pri_raw is not None else "—"
            created = (f.get("System.CreatedDate") or "")[:10]  # YYYY-MM-DD
            rows.append({
                "id": item.get("id"),
                "title": f.get("System.Title") or "",
                "state": f.get("System.State") or "—",
                "type": f.get("System.WorkItemType") or "—",
                "owner": owner,
                "severity": sev_raw,
                "priority": pri,
                "created": created,
                "url": f"{ADO_ORG_BASE}/{quote(project)}/_workitems/edit/{item.get('id')}",
            })
    return rows


def _print_issues_table(rows, limit):
    """يطبع جدول نصي Discord-friendly داخل code block."""
    if not rows:
        print("مفيش إيشوز بالحالات المطلوبة.")
        return
    rows = rows[:limit]
    # عناوين الأعمدة
    COL = {
        "id":       ("ID",       6),
        "state":    ("الحالة",   12),
        "severity": ("Severity", 14),
        "priority": ("P",        3),
        "owner":    ("المسؤول",  22),
        "created":  ("Created",  10),
        "title":    ("العنوان",  48),
    }
    header = "  ".join(h.ljust(w) for _, (h, w) in COL.items())
    sep    = "  ".join("-" * w      for _, (_, w) in COL.items())
    lines  = ["```", header, sep]
    for r in rows:
        row = "  ".join([
            str(r["id"]).ljust(COL["id"][1]),
            r["state"][:COL["state"][1]].ljust(COL["state"][1]),
            r["severity"][:COL["severity"][1]].ljust(COL["severity"][1]),
            r["priority"][:COL["priority"][1]].ljust(COL["priority"][1]),
            r["owner"][:COL["owner"][1]].ljust(COL["owner"][1]),
            r["created"].ljust(COL["created"][1]),
            r["title"][:COL["title"][1]],
        ])
        lines.append(row)
    lines.append("```")
    lines.append(f"الإجمالي: {len(rows)} إيشو")
    print("\n".join(lines))


def _run_wiql(query, project, top):
    url = f"{_project_base(project)}/wit/wiql?api-version={ADO_API_VERSION}&$top={top}"
    r = _call("POST", url, {**_headers(), "Content-Type": "application/json"}, json={"query": query})
    ids = [item["id"] for item in r.json().get("workItems", [])]
    return _fetch_fields(ids, project, DEFAULT_FIELDS)


def _wiql_escape(term):
    return term.replace("'", "''")


# --------------------------------------------------------------------------
# read commands
# --------------------------------------------------------------------------

def cmd_list_projects(args):
    url = f"{ADO_ORG_BASE}/_apis/projects?api-version={ADO_API_VERSION}&$top={args.top}"
    r = _call("GET", url, _headers())
    _print_json([{"id": p["id"], "name": p["name"], "state": p.get("state")}
                 for p in r.json().get("value", [])])


def cmd_list_teams(args):
    url = f"{ADO_ORG_BASE}/_apis/projects/{quote(args.project)}/teams?api-version={ADO_API_VERSION}"
    r = _call("GET", url, _headers())
    _print_json([{"id": t["id"], "name": t["name"]} for t in r.json().get("value", [])])


def cmd_search(args):
    # كل قيمة نصية بتتهرّب — مش terms بس. أي ' في اسم مشروع/مسار كان بيكسر
    # الاستعلام بصمت ويرجّع نتيجة فاضية بدل خطأ.
    conditions = " OR ".join(f"[System.Title] CONTAINS '{_wiql_escape(t)}'" for t in args.terms)
    query = ("SELECT [System.Id] FROM WorkItems "
             f"WHERE [System.TeamProject] = '{_wiql_escape(args.project)}' AND ({conditions})")
    if args.area_path:
        query += f" AND [System.AreaPath] = '{_wiql_escape(args.area_path)}'"
    if args.type:
        query += f" AND [System.WorkItemType] = '{_wiql_escape(args.type)}'"
    query += " ORDER BY [System.ChangedDate] DESC"
    _print_json(_run_wiql(query, args.project, args.top))


def cmd_get_work_item(args):
    fields = args.fields or DEFAULT_FIELDS
    url = f"{_project_base(args.project)}/wit/workitems/{args.id}?fields={fields}&api-version={ADO_API_VERSION}"
    r = _call("GET", url, _headers())
    _print_json(_fetch_fields([r.json()["id"]], args.project, fields))


def cmd_get_work_items(args):
    ids = [i.strip() for i in args.ids.split(",") if i.strip()]
    _print_json(_fetch_fields(ids, args.project, args.fields or DEFAULT_FIELDS))


def cmd_get_work_item_type(args):
    url = f"{_project_base(args.project)}/wit/workitemtypes/{quote(args.type)}?api-version={ADO_API_VERSION}"
    r = _call("GET", url, _headers())
    wt = r.json()
    _print_json({
        "name": wt.get("name"),
        "description": wt.get("description"),
        "states": [s.get("name") for s in wt.get("states", [])],
        "fields": [f.get("referenceName") for f in wt.get("fieldInstances", [])],
    })


def cmd_wiql(args):
    _print_json(_run_wiql(args.query, args.project, args.top))


def cmd_my_work_items(args):
    query = ("SELECT [System.Id] FROM WorkItems "
             f"WHERE [System.TeamProject] = '{_wiql_escape(args.project)}' AND [System.AssignedTo] = @Me "
             "ORDER BY [System.ChangedDate] DESC")
    _print_json(_run_wiql(query, args.project, args.top))


def cmd_list_backlogs(args):
    url = f"{_team_base(args.project, args.team)}/work/backlogs?api-version={ADO_API_VERSION}"
    r = _call("GET", url, _headers())
    _print_json([{"id": b["id"], "name": b.get("name")} for b in r.json().get("value", [])])


def cmd_list_backlog_work_items(args):
    url = (f"{_team_base(args.project, args.team)}/work/backlogs/{quote(args.backlog_id)}/workItems"
           f"?api-version={ADO_API_VERSION}")
    r = _call("GET", url, _headers())
    ids = [row["target"]["id"] for row in r.json().get("workItems", []) if row.get("target")]
    _print_json(_fetch_fields(ids, args.project, DEFAULT_FIELDS))


def _flatten_iterations(node):
    attrs = node.get("attributes") or {}
    rows = [{
        "name": node.get("name"),
        "path": node.get("path"),
        "start_date": attrs.get("startDate"),
        "finish_date": attrs.get("finishDate"),
    }]
    for child in node.get("children") or []:
        rows.extend(_flatten_iterations(child))
    return rows


def cmd_list_iterations(args):
    url = (f"{_project_base(args.project)}/wit/classificationnodes/Iterations"
           f"?$depth={args.depth}&api-version={ADO_API_VERSION}")
    r = _call("GET", url, _headers())
    _print_json(_flatten_iterations(r.json()))


def cmd_list_team_iterations(args):
    url = f"{_team_base(args.project, args.team)}/work/teamsettings/iterations?api-version={ADO_API_VERSION}"
    if args.timeframe:
        url += f"&$timeframe={args.timeframe}"
    r = _call("GET", url, _headers())
    _print_json([{
        "id": it.get("id"), "name": it.get("name"), "path": it.get("path"),
        "start_date": (it.get("attributes") or {}).get("startDate"),
        "finish_date": (it.get("attributes") or {}).get("finishDate"),
    } for it in r.json().get("value", [])])


def cmd_team_settings(args):
    url = f"{_team_base(args.project, args.team)}/work/teamsettings?api-version={ADO_API_VERSION}"
    r = _call("GET", url, _headers())
    _print_json(r.json())


# --------------------------------------------------------------------------
# write commands (create-only — no update/delete exists in this script)
# --------------------------------------------------------------------------

def _build_create_ops(args):
    ops = [
        {"op": "add", "path": "/fields/System.Title", "value": args.title},
        {"op": "add", "path": "/fields/System.AreaPath", "value": args.area_path},
        {"op": "add", "path": "/fields/myagile.Customer", "value": ADO_CUSTOMER},
        {"op": "add", "path": "/fields/System.State", "value": args.state},
    ]
    # نقطة 4 (F13): Custom.Application صالح لنوع Issue بس — متحقق من تعريف الأنواع
    # في ADO الحي (مش موجود على Change Request وممنوع على Customer Issue).
    import ado_fields
    if args.type in ado_fields.APPLICATION_VALID_TYPES:
        ops.insert(3, {"op": "add", "path": "/fields/Custom.Application", "value": ADO_APPLICATION})
    if args.description:
        ops.append({"op": "add", "path": "/fields/System.Description", "value": args.description})
    if getattr(args, "assigned_to", None):
        ops.append({"op": "add", "path": "/fields/System.AssignedTo", "value": args.assigned_to})
    if args.tags:
        ops.append({"op": "add", "path": "/fields/System.Tags", "value": args.tags})
    for extra in args.field or []:
        if "=" not in extra:
            sys.exit(f"ERROR: --field expects path=value, got: {extra}")
        path, value = extra.split("=", 1)
        ops.append({"op": "add", "path": f"/fields/{path}", "value": value})
    _provided = {op["path"].split("/fields/", 1)[-1] for op in ops if "/fields/" in op.get("path", "")}
    # F12: استنتاج منصة/تصنيف الـ CR من العنوان+الوصف بدل defaults عمياء
    _context = f"{args.title or ''} {args.description or ''}"
    ops += cr_media.required_field_ops(args.type, _provided, context_text=_context)
    return ops


def _create(args, ops, label):
    if args.dry_run:
        print(f"DRY-RUN would create {args.type} in project '{args.project}': "
              f"{json.dumps(ops, ensure_ascii=False)}")
        return
    url = f"{_project_base(args.project)}/wit/workitems/${quote(args.type)}?api-version={ADO_API_VERSION}"
    r = requests.post(url, headers=_headers(patch=True), json=ops, timeout=30)
    if r.status_code not in (200, 201):
        msg = r.text[:400]
        if "work item type" in msg.lower() or r.status_code == 404:
            try:
                types = _list_work_item_types(args.project)
                msg += f"\nValid work item types in this project: {', '.join(types)}"
            except Exception:
                pass
        sys.exit(f"FAILED to create {label}: HTTP {r.status_code} {msg}")
    wi = r.json()
    url = wi.get("_links", {}).get("html", {}).get("href", "")
    print(f"CREATED #{wi['id']} -> {url}")
    return wi


def _auto_parent_ops(args):
    """يرجّع op ربط بالـ Feature الأب لو لقى وحدة مناسبة، وإلا [].

    القاعدة (قرار آسر 2026-07-25): لقى Feature → يربطها. مالقاش → يرفع من غير
    parent. مفيش سؤال ومفيش تعطيل — ربط غلط أسوأ من مفيش ربط.
    أي عطل في الوحدة دي مايوقفش الرفع أبدًا.
    """
    if getattr(args, "no_auto_parent", False):
        return []
    try:
        import ado_features
        text = " ".join(filter(None, [getattr(args, "title", ""),
                                      getattr(args, "description", "")]))
        hit = ado_features.best(text)
    except Exception as error:
        print(f"AUTO-PARENT skipped ({type(error).__name__}: {error})", file=sys.stderr)
        return []
    if not hit:
        print("AUTO-PARENT: مفيش Feature مناسبة — بيترفع من غير parent")
        return []
    print(f"AUTO-PARENT: #{hit['id']} {hit['title']} "
          f"(درجة {hit['score']}) ← {hit['epic']}")
    return [{
        "op": "add", "path": "/relations/-",
        "value": {"rel": "System.LinkTypes.Hierarchy-Reverse",
                  "url": f"{_project_base(args.project)}/wit/workItems/{hit['id']}"},
    }]


def cmd_create_work_item(args):
    wi = _create(args, _build_create_ops(args) + _auto_parent_ops(args), args.type)
    if wi:
        _ch = cr_media.resolve_channel_id(getattr(args, "channel", None))
        cr_media.maybe_attach_media(args, wi, _ch, _headers())


def cmd_add_comment(args):
    if args.dry_run:
        print(f"DRY-RUN would comment on #{args.id}: {args.text}")
        return
    url = (f"{_project_base(args.project)}/wit/workItems/{args.id}/comments"
           f"?api-version=7.1-preview.4")
    r = requests.post(url, headers={**_headers(), "Content-Type": "application/json"},
                       json={"text": args.text}, timeout=30)
    if r.status_code not in (200, 201):
        sys.exit(f"FAILED to add comment: HTTP {r.status_code} {r.text[:400]}")
    print(f"COMMENT ADDED to #{args.id}")


def cmd_add_child(args):
    ops = _build_create_ops(args)
    ops.append({
        "op": "add", "path": "/relations/-",
        "value": {"rel": "System.LinkTypes.Hierarchy-Reverse",
                  "url": f"{_project_base(args.project)}/wit/workItems/{args.parent}"},
    })
    if args.dry_run:
        print(f"DRY-RUN would create child {args.type} of #{args.parent}: "
              f"{json.dumps(ops, ensure_ascii=False)}")
        return
    url = f"{_project_base(args.project)}/wit/workitems/${quote(args.type)}?api-version={ADO_API_VERSION}"
    r = requests.post(url, headers=_headers(patch=True), json=ops, timeout=30)
    if r.status_code not in (200, 201):
        sys.exit(f"FAILED to create child work item: HTTP {r.status_code} {r.text[:400]}")
    wi = r.json()
    html_url = wi.get("_links", {}).get("html", {}).get("href", "")
    print(f"CREATED CHILD #{wi['id']} of #{args.parent} -> {html_url}")
    # F7: إرفاق ميديا الرسالة (--source-msg/--attach-url) زي cmd_create_work_item
    # بالظبط — قبل كده الفلاجز كانت بتتقبل وتتبلع في صمت على مسار السابورت الإلزامي،
    # فسكرين شوت العميل كان بيضيع من التذكرة من غير أي خطأ.
    _ch = cr_media.resolve_channel_id(getattr(args, "channel", None))
    cr_media.maybe_attach_media(args, wi, _ch, _headers())


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def cmd_issues_table(args):
    """جدول الإيشوز المفتوحة — New/Reviewed/Active مرتبة بالـ Created Date (طلب غادة).

    الحقول: ID · العنوان · الحالة · Severity · Priority · المسؤول · تاريخ الإنشاء.
    بيبعت كـ code block واحدة تقدر تنسخها على Discord.

    مثال:
        ado_cli.py issues-table
        ado_cli.py issues-table --states "New,Active" --top 50
        ado_cli.py issues-table --area-path "Support"
    """
    project = args.project
    states = [s.strip() for s in (args.states or "New,Reviewed,Active").split(",") if s.strip()]
    state_conds = " OR ".join(f"[System.State] = '{_wiql_escape(s)}'" for s in states)

    query = (
        "SELECT [System.Id] FROM WorkItems "
        f"WHERE [System.TeamProject] = '{_wiql_escape(project)}' "
        f"AND [System.WorkItemType] IN ('Issue', 'Customer Issue') "
        f"AND ({state_conds})"
    )
    if args.area_path:
        query += f" AND [System.AreaPath] UNDER '{_wiql_escape(args.area_path)}'"
    query += " ORDER BY [System.CreatedDate] ASC"

    url = f"{_project_base(project)}/wit/wiql?api-version={ADO_API_VERSION}&$top={args.top}"
    r = _call("POST", url, {**_headers(), "Content-Type": "application/json"}, json={"query": query})
    ids = [item["id"] for item in r.json().get("workItems", [])]

    if not ids:
        print(f"مفيش إيشوز مفتوحة بالحالات: {', '.join(states)}")
        return

    rows = _fetch_issues_fields(ids, project)

    if args.json:
        _print_json(rows)
    else:
        _print_issues_table(rows, args.top)


def cmd_attach_media(args):
    """Attach Discord media / URLs to an EXISTING work item.

    Additive only (AttachedFile relations + a discussion note for oversized
    files via cr_media) — no field updates, consistent with the create-only
    write policy of this CLI."""
    if not (args.source_msg or args.attach_url):
        sys.exit("ERROR: pass --source-msg and/or --attach-url")
    if args.dry_run:
        print(f"DRY-RUN would attach media to #{args.id} "
              f"(source_msg={args.source_msg}, urls={len(args.attach_url)})")
        return
    args.no_media = False
    channel = cr_media.resolve_channel_id(getattr(args, "channel", None) or "po")
    cr_media.maybe_attach_media(args, {"id": args.id}, channel, _headers())
    print(f"ATTACH-MEDIA DONE for #{args.id}")



def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    p.add_argument("--project", default=ADO_PROJECT, help=f"ADO project (default {ADO_PROJECT})")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("list-projects", help="list all projects in the org")
    s.add_argument("--top", type=int, default=100)
    s.set_defaults(func=cmd_list_projects)

    s = sub.add_parser("list-teams", help="list teams in the project")
    s.set_defaults(func=cmd_list_teams)

    s = sub.add_parser("search", help="find work items by title keyword(s)")
    s.add_argument("terms", nargs="+")
    s.add_argument("--area-path")
    s.add_argument("--type")
    s.add_argument("--top", type=int, default=20)
    s.set_defaults(func=cmd_search)

    s = sub.add_parser("get-work-item", help="get one work item by id")
    s.add_argument("id")
    s.add_argument("--fields")
    s.set_defaults(func=cmd_get_work_item)

    s = sub.add_parser("get-work-items", help="get several work items by id (comma-separated)")
    s.add_argument("ids", help="comma-separated ids")
    s.add_argument("--fields")
    s.set_defaults(func=cmd_get_work_items)

    s = sub.add_parser("get-work-item-type", help="get a work item type's definition")
    s.add_argument("type")
    s.set_defaults(func=cmd_get_work_item_type)

    s = sub.add_parser("wiql", help="run a raw WIQL query")
    s.add_argument("query")
    s.add_argument("--top", type=int, default=50)
    s.set_defaults(func=cmd_wiql)

    s = sub.add_parser("my-work-items", help="work items assigned to the PAT's identity")
    s.add_argument("--top", type=int, default=50)
    s.set_defaults(func=cmd_my_work_items)

    s = sub.add_parser("list-backlogs", help="list backlog levels for a team")
    s.add_argument("--team", required=True)
    s.set_defaults(func=cmd_list_backlogs)

    s = sub.add_parser("list-backlog-work-items", help="list work items on a team's backlog")
    s.add_argument("--team", required=True)
    s.add_argument("--backlog-id", required=True)
    s.set_defaults(func=cmd_list_backlog_work_items)

    s = sub.add_parser("list-iterations", help="project iteration tree (dates included)")
    s.add_argument("--depth", type=int, default=2)
    s.set_defaults(func=cmd_list_iterations)

    s = sub.add_parser("list-team-iterations", help="a team's assigned iterations")
    s.add_argument("--team", required=True)
    s.add_argument("--timeframe", choices=["current"], default=None)
    s.set_defaults(func=cmd_list_team_iterations)

    s = sub.add_parser("team-settings", help="a team's sprint/board settings")
    s.add_argument("--team", required=True)
    s.set_defaults(func=cmd_team_settings)

    s = sub.add_parser("issues-table",
                       help="جدول الإيشوز المفتوحة: ID/Title/State/Sev/Pri/Owner مرتبة بالـ Created Date")
    s.add_argument("--states", default="New,Reviewed,Active",
                   help='الحالات مفصولة بفاصلة (default: "New,Reviewed,Active")')
    s.add_argument("--area-path", help="فلتر على Area Path (UNDER)")
    s.add_argument("--top", type=int, default=200, help="حد أقصى للنتائج (default 200)")
    s.add_argument("--json", action="store_true", help="طباعة JSON بدل الجدول النصي")
    s.set_defaults(func=cmd_issues_table)

    def add_create_args(sp):
        sp.add_argument("--type", required=True, help='work item type, e.g. "Change Request" / "Issue"')
        sp.add_argument("--title", required=True)
        sp.add_argument("--area-path", required=True, help=r'e.g. "0_Projects_Team\Change Requests"')
        sp.add_argument("--description", help="HTML description")
        sp.add_argument("--tags", help="semicolon-separated tags")
        sp.add_argument("--state", default="New")
        sp.add_argument("--assigned-to", dest="assigned_to",
                         help='اسم المسؤول كما يظهر في ADO (displayName) أو email — مثال: "Mostafa Saad"')
        sp.add_argument("--field", action="append",
                         help="extra field as path=value, repeatable, e.g. --field Microsoft.VSTS.Common.Priority=1")
        sp.add_argument("--source-msg", help="Discord message id to auto-attach its image/video")
        sp.add_argument("--channel", help="Discord channel for --source-msg: po/mars/support or raw id")
        sp.add_argument("--attach-url", action="append", default=[], help="image/video URL(s) to attach (repeatable)")
        sp.add_argument("--no-media", action="store_true", help="skip attaching media")
        sp.add_argument("--no-auto-parent", action="store_true",
                         help="don't auto-link a parent Feature from the 8Orders tree")
        sp.add_argument("--dry-run", action="store_true")

    s = sub.add_parser("create-work-item", help="create a work item")
    add_create_args(s)
    s.set_defaults(func=cmd_create_work_item)

    s = sub.add_parser("attach-media",
                       help="attach Discord media to an EXISTING work item (additive only)")
    s.add_argument("id")
    s.add_argument("--source-msg", help="Discord message id whose image/video to attach")
    s.add_argument("--channel", help="channel of --source-msg: po/mars/issues/support or raw id (default po)")
    s.add_argument("--attach-url", action="append", default=[], help="media URL(s) to attach (repeatable)")
    s.add_argument("--dry-run", action="store_true")
    s.set_defaults(func=cmd_attach_media)


    s = sub.add_parser("add-comment", help="add a comment to a work item")
    s.add_argument("id")
    s.add_argument("text")
    s.add_argument("--dry-run", action="store_true")
    s.set_defaults(func=cmd_add_comment)

    s = sub.add_parser("add-child", help="create a work item as a child of an existing one")
    s.add_argument("--parent", required=True)
    add_create_args(s)
    s.set_defaults(func=cmd_add_child)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
