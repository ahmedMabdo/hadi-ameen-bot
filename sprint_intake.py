#!/usr/bin/env python3
"""
sprint_intake.py - DM ceremony intake at sprint rollover (module C10).

Detects a new sprint (from the ADO snapshot) and asks Asser (DM) for the
CHANGING ceremony times (planning / refinement / review / retro / demo), using
last sprint's answers as defaults. Answers are saved to sprint_ceremonies.json,
which sprints_sync.py merges into knowledge/sprints.md.

Discord send/receive is owned by discord_bot (it holds the client). This module
is pure logic; wire from the bot / a daily routine:

    from sprint_intake import check_rollover, compose_dm, save_answers, mark_seen
    new, name = check_rollover()
    if new:
        await dm_asser(compose_dm(name))     # then mark_seen(name) after sending
    # when Asser replies in DM with the times:
    save_answers(name, parsed_dict)          # parsed_dict: {"planning": "...", ...}
"""
import os
import json
import datetime

import ado_snapshot as snap

STATE = os.environ.get(
    "ADO_INTAKE_STATE",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "sprint_intake_state.json"))
CEREMONIES = os.environ.get(
    "ADO_CEREMONIES_JSON",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "sprint_ceremonies.json"))
CEREMONY_KEYS = ["planning", "refinement", "review", "retro", "demo"]


def _load(path, default):
    if os.path.exists(path):
        try:
            return json.load(open(path, encoding="utf-8"))
        except Exception:
            return default
    return default


def check_rollover():
    con = snap._db()
    snap._init(con)
    try:
        m = snap._meta(con)
    finally:
        con.close()
    name = m.get("sprint_name")
    if not name:
        return False, None
    st = _load(STATE, {})
    return (st.get("last_sprint") != name), name


def mark_seen(name):
    json.dump({"last_sprint": name, "seen_at": datetime.datetime.utcnow().isoformat()},
              open(STATE, "w", encoding="utf-8"))


def compose_dm(name):
    cer = _load(CEREMONIES, {})
    last = {}
    for k in sorted(cer.keys()):
        if k != name:
            last = cer[k]
    lines = [f"يا باشمهندس آسر، بدأنا سبرنت جديد ({name}). 🎯",
             "محتاج مواعيد الإيفنتات المتغيّرة (في رد واحد):"]
    for k in CEREMONY_KEYS:
        d = f"  (المرة اللي فاتت: {last[k]})" if last.get(k) else ""
        lines.append(f"- {k}{d}")
    lines.append("لو زيها زي المرة اللي فاتت، اكتب: زي ما هي.")
    return "\n".join(lines)


def save_answers(name, answers):
    cer = _load(CEREMONIES, {})
    cer[name] = {k: answers.get(k, "") for k in CEREMONY_KEYS if answers.get(k)}
    json.dump(cer, open(CEREMONIES, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    mark_seen(name)
    return cer[name]


if __name__ == "__main__":
    new, name = check_rollover()
    print("new sprint:", new, name)
    if new and name:
        print(compose_dm(name))
