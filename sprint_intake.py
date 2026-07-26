#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""sprint_intake.py — وعي هادي بإيفنتات السبرنت + سؤال آسر في الـ DM (C10 — نقطة 2).

الفكرة:
  مواعيد إيفنتات دورة مارس (Buz HL / Demos / Release Day...) مش موجودة في ADO،
  وبتتغير من سبرنت لسبرنت. الموديول ده:
    1. بيحسب **مواعيد متوقعة (defaults)** لكل إيفنت من قواعد الدورة المكتوبة في
       CLAUDE.md (أنكور البداية للإيفنتات الأولى وأنكور النهاية للريليز وما بعده).
    2. أول ما snapshot يكتشف سبرنت جديد → البوت بيبعت لآسر DM واحدة فيها كل
       الإيفنتات بمواعيدها المتوقعة، وآسر بيرد بالتصحيحات بس (أو «تمام زي ما هي»).
    3. هادي بيحفظ رد آسر بأمر `save` هنا → sprint_ceremonies.json →
       sprints_sync.py بيدمجها في knowledge/sprints.md المتولد (حل تناقض F8).
    4. لو تاريخ نهاية السبرنت اتغير في ADO وسط السبرنت → `check` بيكشفها والبوت
       بيسأل آسر يتأكد (قاعدة «متفترضش إن الجدول ثابت»).

أوامر الـ CLI (هادي بيستخدمها من المحادثة):
  python3 sprint_intake.py show                        # المؤكد + المتوقع للسبرنت الحالي
  python3 sprint_intake.py ask                         # نص رسالة الـ DM (للمعاينة)
  python3 sprint_intake.py save --sprint MS-92 --set release_day=2026-07-28 [--set ...]
  python3 sprint_intake.py confirm-defaults --sprint MS-92   # آسر قال «زي ما هي»
  python3 sprint_intake.py check                       # JSON: سبرنت جديد؟ النهاية اتغيرت؟
  python3 sprint_intake.py mark-seen --sprint MS-92    # البوت بيعلّم إنه سأل خلاص
"""
import argparse
import datetime
import json
import os
import re

import ado_snapshot as snap

STATE = os.environ.get(
    "ADO_INTAKE_STATE",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "sprint_intake_state.json"))
CEREMONIES = os.environ.get(
    "ADO_CEREMONIES_JSON",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "sprint_ceremonies.json"))

# إيفنتات دورة مارس الحقيقية (المرجع: CLAUDE.md «سيكونات السبرنت بالترتيب»)
# (key, label, week, py_weekday) — py_weekday: Mon=0..Sun=6 (أسبوع مصر يبدأ الأحد)
CEREMONY_DEFS = [
    ("buz_hl_1",          "Buz HL 1",            0, 0),  # الاتنين — الأسبوع الأول
    ("review_meeting",    "Review Meeting",      0, 2),  # الأربع — وسط الأسبوع الأول
    ("buz_hl_2",          "Buz HL 2",            1, 0),  # الاتنين — الأسبوع التاني
    ("team_hl",           "Team HL",             2, 6),  # الأحد — بداية الأسبوع التالت
    ("closing_branches",  "Closing Branches",    2, 1),  # الثلاثاء — الأسبوع التالت
    ("team_demo",         "Team Demo",           2, 2),  # الأربع — آخر الأسبوع التالت
    ("buz_demo",          "Buz Demo",            2, 3),  # الخميس — آخر الأسبوع التالت
    ("release_day",       "Release Day",        -1, 1),  # آخر ثلاثاء قبل نهاية السبرنت
    ("retro_tech_design", "Retro + Tech Design", -1, 2),  # بعد الريليز بيوم
    ("planning",          "Planning",           -1, 3),  # آخر السبرنت
]
CEREMONY_KEYS = [c[0] for c in CEREMONY_DEFS]
LABELS = {c[0]: c[1] for c in CEREMONY_DEFS}

AR_DAYS = {0: "الاتنين", 1: "الثلاثاء", 2: "الأربع", 3: "الخميس",
           4: "الجمعة", 5: "السبت", 6: "الأحد"}


def _load(path, default):
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as fh:   # context manager: مفيش fd مسرّب
                return json.load(fh)
        except Exception:
            return default
    return default


def _save_json(path, data):
    """كتابة ذرية. 2026-07-26: كان json.dump(..., open(path,"w")) — و open("w")
    بيفضّي الملف **فورًا**، فأي استثناء وسط الكتابة كان بيسيب
    sprint_ceremonies.json فاضي = ضياع كل مواعيد السبرنت اللي آسر أكدها."""
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def _parse_date(s):
    try:
        return datetime.date.fromisoformat((s or "")[:10])
    except Exception:
        return None


def compute_defaults(start_iso, finish_iso):
    """المواعيد المتوقعة لكل إيفنت من قواعد الدورة — {key: date}. تقديرات قابلة
    للتصحيح من آسر، مش حقائق."""
    start, finish = _parse_date(start_iso), _parse_date(finish_iso)
    if not start or not finish:
        return {}
    start_sunday = start - datetime.timedelta(days=(start.weekday() - 6) % 7)
    # الريليز: آخر ثلاثاء يوم نهاية السبرنت أو قبله
    release = finish
    while release.weekday() != 1:
        release -= datetime.timedelta(days=1)
    out = {}
    for key, _label, week, wd in CEREMONY_DEFS:
        if key == "release_day":
            d = release
        elif key == "retro_tech_design":
            d = release + datetime.timedelta(days=1)
        elif key == "planning":
            d = finish
        else:
            offset = (wd - 6) % 7  # الأحد=0، الاتنين=1 ... الخميس=4
            d = start_sunday + datetime.timedelta(days=7 * week + offset)
        # مفيش إيفنت متوقع قبل البداية أو بعد النهاية بأكتر من يوم
        d = max(min(d, finish + datetime.timedelta(days=1)), start)
        out[key] = d
    return out


def _fmt(d):
    return f"{AR_DAYS[d.weekday()]} {d.isoformat()}"


def _snapshot_meta():
    con = snap._db()
    snap._init(con)
    try:
        return snap._meta(con)
    finally:
        con.close()


def confirmed_for(sprint):
    return _load(CEREMONIES, {}).get(sprint or "", {})


def next_event(sprint, start_iso, finish_iso, today=None):
    """أقرب إيفنت جاي — المؤكد من آسر له الأولوية، وإلا المتوقع المحسوب."""
    defaults = compute_defaults(start_iso, finish_iso)
    if not defaults:
        return None
    conf = confirmed_for(sprint)
    today = today or datetime.date.today()
    best = None
    for key in CEREMONY_KEYS:
        text = (conf.get(key) or "").strip()
        d = None
        if text:  # آسر بيكتب حر — ندوّر على تاريخ ISO جوه النص
            for tok in text.replace("،", " ").split():
                d = _parse_date(tok)
                if d:
                    break
        d = d or defaults.get(key)
        if not d or d < today:
            continue
        # الأقرب تاريخيًا يكسب — وعند التعادل، المؤكد من آسر له الأولوية
        if best is None or d < best[0] or (d == best[0] and bool(text) and not best[2]):
            best = (d, key, bool(text), text)
    if not best:
        return None
    d, key, is_conf, text = best
    return {"key": key, "label": LABELS[key],
            "date": text if (is_conf and text) else _fmt(d), "confirmed": is_conf}


# --------------------- rollover / التغيير وسط السبرنت ---------------------
def check_status():
    """JSON للبوت: هل في سبرنت جديد لسه ماتسألش عنه؟ هل نهاية السبرنت اتغيرت؟"""
    m = _snapshot_meta()
    name = m.get("sprint_name") or ""
    finish = (m.get("sprint_finish") or "")[:10]
    st = _load(STATE, {})
    return {
        "sprint": name,
        "start": (m.get("sprint_start") or "")[:10],
        "finish": finish,
        "new_sprint": bool(name) and st.get("last_sprint") != name,
        "finish_changed": (bool(name) and st.get("last_sprint") == name
                           and bool(st.get("last_finish"))
                           and st.get("last_finish") != finish),
        "old_finish": st.get("last_finish", ""),
    }


def mark_seen(name, finish=""):
    _save_json(STATE, {"last_sprint": name, "last_finish": finish,
                       "seen_at": datetime.datetime.now(
                           datetime.timezone.utc).isoformat()})


def check_rollover():
    """توافق مع الاستخدام القديم: (new?, name)."""
    s = check_status()
    return s["new_sprint"], s["sprint"] or None


def compose_dm(name, start_iso=None, finish_iso=None):
    if not (start_iso and finish_iso):
        m = _snapshot_meta()
        start_iso = start_iso or (m.get("sprint_start") or "")[:10]
        finish_iso = finish_iso or (m.get("sprint_finish") or "")[:10]
    defaults = compute_defaults(start_iso, finish_iso)
    prev = {}
    cer = _load(CEREMONIES, {})
    # ترتيب **رقمي**: sorted النصي بيرتب ["MS-9","MS-10","MS-91"] كـ
    # MS-10, MS-9, MS-91 — فـ«السبرنت اللي فات» المعروض لآسر كان ممكن يكون
    # سبرنت من شهور. (2026-07-26)
    def _num(k):
        digits = re.sub(r"\D", "", k)
        return int(digits) if digits else 0
    for k in sorted(cer.keys(), key=_num):
        if k != name and cer[k]:
            prev = cer[k]
    lines = [f"يا آسر، بدأنا سبرنت جديد ({name}: {start_iso} → {finish_iso}) 🎯",
             "دي مواعيد الإيفنتات المتوقعة حسب دورة مارس — راجعها وصحّحلي اللي اتغير:"]
    for key in CEREMONY_KEYS:
        d = defaults.get(key)
        extra = f" (السبرنت اللي فات: {prev[key]})" if prev.get(key) else ""
        lines.append(f"- {LABELS[key]}: {_fmt(d) if d else '؟'}{extra}")
    lines.append("")
    lines.append("رد عليا بالتصحيحات بس (مثال: «الريليز اتأجل لـ 2026-08-05» أو "
                 "«Team Demo الخميس مش الأربع»)، ولو كله مظبوط قول «تمام زي ما هي» — "
                 "وأنا هثبّت المواعيد وأفكّر التيم قبل كل إيفنت.")
    return "\n".join(lines)


def save_answers(name, answers):
    """دمج (مش استبدال): آسر بيبعت التصحيحات بس والباقي بيفضل زي ما هو."""
    bad = [k for k in answers if k not in CEREMONY_KEYS]
    if bad:
        raise SystemExit(f"ERROR: مفاتيح غير معروفة: {bad} — المتاح: {CEREMONY_KEYS}")
    cer = _load(CEREMONIES, {})
    cur = cer.get(name, {})
    cur.update({k: v for k, v in answers.items() if v})
    cer[name] = cur
    _save_json(CEREMONIES, cer)
    return cur


def confirm_defaults(name):
    """آسر قال «تمام زي ما هي» → المتوقع بيتثبت كمؤكد."""
    m = _snapshot_meta()
    defaults = compute_defaults((m.get("sprint_start") or "")[:10],
                                (m.get("sprint_finish") or "")[:10])
    return save_answers(name, {k: _fmt(d) for k, d in defaults.items()})


# ----------------------------- cli -----------------------------
def main():
    p = argparse.ArgumentParser(description="Hadi sprint ceremonies intake.")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("show")
    sub.add_parser("ask")
    sub.add_parser("check")
    sv = sub.add_parser("save")
    sv.add_argument("--sprint", required=True)
    sv.add_argument("--set", action="append", default=[], metavar="key=value")
    cd = sub.add_parser("confirm-defaults")
    cd.add_argument("--sprint", required=True)
    ms = sub.add_parser("mark-seen")
    ms.add_argument("--sprint", required=True)
    ms.add_argument("--finish", default="")
    a = p.parse_args()

    if a.cmd == "check":
        print(json.dumps(check_status(), ensure_ascii=False, indent=2))
    elif a.cmd == "show":
        s = check_status()
        defaults = {k: _fmt(d) for k, d in
                    compute_defaults(s["start"], s["finish"]).items()}
        print(json.dumps({"sprint": s["sprint"], "start": s["start"],
                          "finish": s["finish"],
                          "confirmed": confirmed_for(s["sprint"]),
                          "expected_defaults": defaults,
                          "labels": LABELS}, ensure_ascii=False, indent=2))
    elif a.cmd == "ask":
        s = check_status()
        print(compose_dm(s["sprint"], s["start"], s["finish"]))
    elif a.cmd == "save":
        answers = {}
        for kv in getattr(a, "set"):
            if "=" not in kv:
                raise SystemExit(f"ERROR: صيغة غلط: {kv} — المطلوب key=value")
            k, v = kv.split("=", 1)
            answers[k.strip()] = v.strip()
        saved = save_answers(a.sprint, answers)
        print(json.dumps({"sprint": a.sprint, "saved": saved},
                         ensure_ascii=False, indent=2))
    elif a.cmd == "confirm-defaults":
        saved = confirm_defaults(a.sprint)
        print(json.dumps({"sprint": a.sprint, "saved": saved},
                         ensure_ascii=False, indent=2))
    elif a.cmd == "mark-seen":
        mark_seen(a.sprint, a.finish)
        print("OK")


if __name__ == "__main__":
    main()
