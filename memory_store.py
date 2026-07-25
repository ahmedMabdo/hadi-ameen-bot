#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""مخزن الذاكرة المتدرجة لهادي (بند 4.1/4.2 — مرحلة أ+ب من تقرير التحسينات).

المعمار:
  - المصدر والـ audit trail: knowledge/memory.md + git — زي ما هما بالظبط (شرط التقرير).
  - النواة: knowledge/memory_core.md — ملف يدوي صغير بيتحقن في *كل* رسالة.
  - الفهرس: knowledge/memory_index.db — SQLite FTS5 *مشتق* من memory.md، بيتبني
    بالكامل بـ `rebuild` في أي وقت، عشان كده في .gitignore (مش مصدر حقيقة).
  - الاسترجاع مع كل رسالة: النواة + قواعد السلوك المتعلمة + الملاحظات:
      * لو حجم الملاحظات النشطة <= HADI_MEMORY_FULL_LIMIT حرف (افتراضي 4000):
        بتتحقن كلها (نفس سلوك النهارده — صفر regression والذاكرة لسه صغيرة).
      * أكبر من كده: أقرب HADI_MEMORY_TOP_K (افتراضي 5) ملاحظات صلة بالرسالة
        (BM25 على نص منورمل عربي) — التدرج بيشتغل أوتوماتيك مع النمو.

أنواع الذاكرة (مرحلة ب):
  semantic    حقائق دائمة (الافتراضي — كل السطور القديمة بتتفهرس كده)
  episodic    أحداث بصلاحية {type=episodic expires=YYYY-MM-DD} — بتسقط من الحقن
              بعد تاريخها (بتفضل في memory.md للأرشيف)
  procedural  قواعد سلوك متعلمة {type=procedural} — بتتحقن دايمًا زي النواة

فورمات السطر في memory.md (متوافق للخلف):
  - [YYYY-MM-DD HH:MM — الاسم] النص
  - [YYYY-MM-DD HH:MM — الاسم] النص {type=episodic expires=2026-07-28}

CLI:
  memory_store.py rebuild                 # فهرسة memory.md من الصفر (idempotent)
  memory_store.py search --query "..." [--k 10]
  memory_store.py block --query "..."     # اللي بيتحقن فعليًا — للتشخيص
  memory_store.py status                  # عدادات الأنواع + المنتهي + تطابق md/فهرس
  memory_store.py selftest                # اختبار ذاتي على ملفات مؤقتة (مايلمسش الحقيقي)

الترقية لاحقًا: عمود embedding محجوز في السكيما — استبدال البحث بـ Voyage/Zep/Mem0
من غير إعادة بناء (بند 4.2: «لو حبيتوا لاحقًا Managed»).
"""
import argparse
import datetime as dt
import os
import re
import sqlite3
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
MEM_PATH = BASE / "knowledge" / "memory.md"
CORE_PATH = BASE / "knowledge" / "memory_core.md"
DB_PATH = BASE / "knowledge" / "memory_index.db"

TOP_K = max(1, int(os.environ.get("HADI_MEMORY_TOP_K", "5") or "5"))
FULL_LIMIT = max(0, int(os.environ.get("HADI_MEMORY_FULL_LIMIT", "4000") or "4000"))

SECTION_HEADERS = {
    "## قرارات": "decisions",
    "## سبرنت": "sprint",
    "## ملاحظات": "notes",
    "## عام": "general",
}
SECTION_LABELS = {
    "decisions": "## قرارات",
    "sprint": "## سبرنت",
    "notes": "## ملاحظات",
    "general": "## عام",
}
SECTION_ORDER = {"decisions": 0, "sprint": 1, "notes": 2, "general": 3}

_LINE_RX = re.compile(r"^-\s*\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2})\s*—\s*([^\]]+)\]\s*(.+)$")
# تحصين الذاكرة: الميتا بقت بتحمل كمان مصدر الملاحظة ومستوى الثقة.
# الجروبات الاختيارية بتخلي السطور القديمة (من غير src/trust) تفضل تتقرا عادي.
_META_RX = re.compile(
    r"\s*\{type=(semantic|episodic|procedural)"
    r"(?:\s+expires=(\d{4}-\d{2}-\d{2}))?"
    r"(?:\s+src=([^\s{}]+))?"
    r"(?:\s+trust=(direct|forwarded|external))?"
    r"\}\s*$"
)
_DIACRITICS_RX = re.compile(r"[ً-ْٰـ]")
_TOKEN_RX = re.compile(r"[0-9A-Za-zء-ي٠-٩]+")

# كلمات وقف (منورملة) — ضجيج مش إشارة صلة
_STOPWORDS = {
    "في", "من", "علي", "الي", "عن", "مع", "ده", "دي", "دا", "اللي", "ان", "انا",
    "انت", "هو", "هي", "احنا", "هم", "يا", "لو", "بس", "مش", "كده", "علشان",
    "عشان", "لان", "او", "ايه", "فيه", "لسه", "كمان", "هل", "ما", "كل", "بعد",
    "قبل", "حاجه", "the", "a", "an", "is", "are", "was", "of", "to", "in", "for",
    "and", "or", "on", "at", "it", "this", "that",
}


def normalize(text: str) -> str:
    """توحيد الحروف العربية + شيل التشكيل — بيتطبق على الفهرس والاستعلام سوا."""
    text = _DIACRITICS_RX.sub("", text or "")
    for src, dst in (("أ", "ا"), ("إ", "ا"), ("آ", "ا"), ("ى", "ي"),
                     ("ة", "ه"), ("ؤ", "و"), ("ئ", "ي")):
        text = text.replace(src, dst)
    return text.lower()


def parse_line(raw: str, section: str = "general"):
    """يحلل سطر ملاحظة من memory.md → dict أو None لو مش سطر ملاحظة."""
    m = _LINE_RX.match(raw.strip())
    if not m:
        return None
    noted_at, author, body = m.group(1), m.group(2).strip(), m.group(3).strip()
    mtype, expires, source, trust = "semantic", "", "", "direct"
    meta = _META_RX.search(body)
    if meta:
        mtype = meta.group(1)
        expires = meta.group(2) or ""
        source = meta.group(3) or ""
        trust = meta.group(4) or "direct"
        body = body[: meta.start()].strip()
    return {
        "section": section, "mtype": mtype, "author": author,
        "noted_at": noted_at, "expires": expires, "body": body,
        "source": source, "trust": trust,
        "raw": raw.strip(), "norm": normalize(body),
    }


def iter_md_notes(md_text: str):
    section = "general"
    for raw in md_text.splitlines():
        stripped = raw.strip()
        if stripped in SECTION_HEADERS:
            section = SECTION_HEADERS[stripped]
            continue
        note = parse_line(raw, section)
        if note:
            yield note


# --- قاعدة البيانات --------------------------------------------------------
_SCHEMA = """
CREATE TABLE IF NOT EXISTS meta(k TEXT PRIMARY KEY, v TEXT);
CREATE TABLE IF NOT EXISTS notes(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  section TEXT NOT NULL DEFAULT 'general',
  mtype TEXT NOT NULL DEFAULT 'semantic',
  author TEXT NOT NULL DEFAULT '',
  noted_at TEXT NOT NULL DEFAULT '',
  expires TEXT NOT NULL DEFAULT '',
  body TEXT NOT NULL,
  raw TEXT NOT NULL UNIQUE,
  norm TEXT NOT NULL,
  -- active: محجوز للإخفاء المؤقت من غير حذف. مفيش كاتب ليه دلوقتي
  -- (السحب بيتم في memory.md نفسه عبر memory_guard.revoke_lines).
  active INTEGER NOT NULL DEFAULT 1,
  embedding BLOB
);
CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts USING fts5(
  norm, content='notes', content_rowid='id',
  tokenize='unicode61 remove_diacritics 2'
);
CREATE TRIGGER IF NOT EXISTS notes_ai AFTER INSERT ON notes BEGIN
  INSERT INTO notes_fts(rowid, norm) VALUES (new.id, new.norm);
END;
CREATE TRIGGER IF NOT EXISTS notes_ad AFTER DELETE ON notes BEGIN
  INSERT INTO notes_fts(notes_fts, rowid, norm) VALUES('delete', old.id, old.norm);
END;
CREATE TRIGGER IF NOT EXISTS notes_au AFTER UPDATE ON notes BEGIN
  INSERT INTO notes_fts(notes_fts, rowid, norm) VALUES('delete', old.id, old.norm);
  INSERT INTO notes_fts(rowid, norm) VALUES (new.id, new.norm);
END;
"""

_conn = None


def connect() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        _conn = sqlite3.connect(str(DB_PATH))
        _conn.row_factory = sqlite3.Row
        _conn.execute("PRAGMA journal_mode=WAL")
        _conn.executescript(_SCHEMA)
    return _conn


def _reset_conn():
    global _conn
    if _conn is not None:
        _conn.close()
        _conn = None


_NOT_EXPIRED = "(expires = '' OR date(expires) >= date('now'))"


def rebuild() -> int:
    """يبني الفهرس بالكامل من memory.md — idempotent وآمن التكرار."""
    md = MEM_PATH.read_text(encoding="utf-8") if MEM_PATH.exists() else ""
    conn = connect()
    with conn:
        conn.execute("DELETE FROM notes")
        count = 0
        for note in iter_md_notes(md):
            cur = conn.execute(
                "INSERT OR IGNORE INTO notes(section, mtype, author, noted_at, expires, body, raw, norm)"
                " VALUES (:section, :mtype, :author, :noted_at, :expires, :body, :raw, :norm)",
                note,
            )
            # العدّ على اللي اتسجّل فعلًا: raw عليه UNIQUE، فالسطر المكرر بيتتجاهل.
            # العدّ الأعمى كان بيخلي status().in_sync يقول «مش متزامن» بالباطل.
            count += cur.rowcount if cur.rowcount > 0 else 0
        conn.execute(
            "INSERT OR REPLACE INTO meta(k, v) VALUES ('rebuilt_at', ?)",
            (dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),),
        )
    return count


def index_note(raw_line: str, section: str = "general") -> bool:
    """يفهرس سطر واحد جديد (بيتنادى من memory.py add بعد الحفظ)."""
    note = parse_line(raw_line, section)
    if not note:
        return False
    conn = connect()
    with conn:
        conn.execute(
            "INSERT OR IGNORE INTO notes(section, mtype, author, noted_at, expires, body, raw, norm)"
            " VALUES (:section, :mtype, :author, :noted_at, :expires, :body, :raw, :norm)",
            note,
        )
    return True


def _query_string(text: str, limit: int = 12) -> str:
    tokens, seen = [], set()
    for tok in _TOKEN_RX.findall(normalize(text)):
        if len(tok) < 2 or tok in _STOPWORDS or tok in seen:
            continue
        seen.add(tok)
        tokens.append(tok)
        if len(tokens) >= limit:
            break
    return " OR ".join(f'"{t}"' for t in tokens)


def search(query: str, k: int = None):
    """أقرب الملاحظات النشطة غير المنتهية — مرتبة BM25 (الأقل = الأنسب)."""
    match = _query_string(query)
    if not match:
        return []
    rows = connect().execute(
        "SELECT n.section, n.mtype, n.author, n.noted_at, n.expires, n.body, n.raw,"
        " bm25(notes_fts) AS score"
        " FROM notes_fts JOIN notes n ON n.id = notes_fts.rowid"
        f" WHERE notes_fts MATCH ? AND n.active = 1 AND {_NOT_EXPIRED.replace('expires', 'n.expires')}"
        " ORDER BY score LIMIT ?",
        (match, k or TOP_K),
    ).fetchall()
    return [dict(r) for r in rows]


def _read_core() -> str:
    if not CORE_PATH.exists():
        return ""
    text = CORE_PATH.read_text(encoding="utf-8").strip()
    has_content = any(
        line.strip() and not line.strip().startswith(("#", ">"))
        for line in text.splitlines()
    )
    return text if has_content else ""


def _grouped(rows) -> str:
    parts, current = [], None
    for r in sorted(rows, key=lambda r: (SECTION_ORDER.get(r["section"], 9), r["noted_at"])):
        if r["section"] != current:
            current = r["section"]
            parts.append(SECTION_LABELS.get(current, f"## {current}"))
        parts.append(r["raw"])
    return "\n".join(parts)


def memory_block(query_text: str) -> str:
    """اللي بيتحقن في برومبت هادي: نواة + قواعد سلوك + ملاحظات (كاملة أو top-k)."""
    conn = connect()
    parts = []

    core = _read_core()
    if core:
        parts.append("[نواة الذاكرة — سارية دايمًا]\n" + core)

    procedural = conn.execute(
        "SELECT raw FROM notes WHERE active=1 AND mtype='procedural'"
        f" AND {_NOT_EXPIRED} ORDER BY noted_at LIMIT 10"
    ).fetchall()
    if procedural:
        parts.append("[قواعد سلوك متعلمة — التزم بيها دايمًا]\n"
                     + "\n".join(r["raw"] for r in procedural))

    others = conn.execute(
        "SELECT section, mtype, author, noted_at, expires, body, raw FROM notes"
        f" WHERE active=1 AND mtype != 'procedural' AND {_NOT_EXPIRED}"
    ).fetchall()
    if others:
        total = sum(len(r["raw"]) for r in others)
        if total <= FULL_LIMIT:
            parts.append(_grouped(others))
        else:
            top = [r for r in search(query_text, TOP_K) if r["mtype"] != "procedural"]
            if top:
                parts.append(
                    f"[أقرب {len(top)} ملاحظات صلة برسالتك — في ملاحظات تانية بتظهر حسب الموضوع]\n"
                    + _grouped(top)
                )
            else:
                parts.append(
                    "[مفيش ملاحظات قريبة من موضوع الرسالة — الذاكرة الكاملة في knowledge/memory.md"
                    " وتقدر تدور فيها بـ memory.py search]"
                )
    return "\n\n".join(parts).strip()


def status() -> dict:
    conn = connect()
    md = MEM_PATH.read_text(encoding="utf-8") if MEM_PATH.exists() else ""
    # raw عليه UNIQUE في الفهرس، فالمقارنة لازم تكون على السطور المتميّزة —
    # وإلا أي سطر مكرر في memory.md كان بيخلي in_sync=False للأبد.
    md_count = len({n["raw"] for n in iter_md_notes(md)})
    by_type = dict(conn.execute(
        "SELECT mtype, COUNT(*) FROM notes WHERE active=1 GROUP BY mtype"
    ).fetchall())
    expired = conn.execute(
        "SELECT COUNT(*) FROM notes WHERE active=1 AND expires != ''"
        " AND date(expires) < date('now')"
    ).fetchone()[0]
    db_count = conn.execute("SELECT COUNT(*) FROM notes WHERE active=1").fetchone()[0]
    return {
        "md_notes": md_count, "db_notes": db_count, "by_type": by_type,
        "expired_hidden": expired,
        "in_sync": md_count == db_count,
        "core_active": bool(_read_core()),
        "rebuilt_at": (conn.execute("SELECT v FROM meta WHERE k='rebuilt_at'").fetchone()
                       or ["-"])[0],
    }


# --- اختبار ذاتي على ملفات مؤقتة (مايلمسش الذاكرة الحقيقية) -----------------
def selftest() -> None:
    global MEM_PATH, CORE_PATH, DB_PATH
    import tempfile

    orig = (MEM_PATH, CORE_PATH, DB_PATH)
    tmp = Path(tempfile.mkdtemp(prefix="hadi_mem_test_"))
    try:
        MEM_PATH, CORE_PATH, DB_PATH = (tmp / "memory.md", tmp / "core.md", tmp / "idx.db")
        _reset_conn()
        yesterday = (dt.date.today() - dt.timedelta(days=1)).isoformat()
        tomorrow = (dt.date.today() + dt.timedelta(days=1)).isoformat()
        MEM_PATH.write_text(
            "# ذاكرة\n\n## قرارات\n"
            "- [2026-07-10 18:02 — آسر] قرار الإصدار الأسبوعي يتأجل ليوم الأحد\n"
            "## ملاحظات\n"
            f"- [2026-07-10 17:55 — آسر] أزمة الكوتا شغالة {{type=episodic expires={yesterday}}}\n"
            f"- [2026-07-11 09:00 — آسر] متابعة العرض مستمرة {{type=episodic expires={tomorrow}}}\n"
            "## عام\n"
            "- [2026-07-12 10:00 — آسر] متكتبش توقيع في الردود {type=procedural}\n",
            encoding="utf-8",
        )
        CORE_PATH.write_text("# نواة\n> إرشاد\n- قاعدة نواة: البورد هو مصدر الحقيقة\n",
                             encoding="utf-8")
        count = rebuild()
        assert count == 4, f"rebuild={count} != 4"

        hits = search("الاصدار الاسبوعي")  # ألف من غير همزة → لازم يلاقي «الإصدار»
        assert hits and "الإصدار" in hits[0]["raw"], f"normalize search fail: {hits}"

        block = memory_block("الاصدار")
        assert "نواة الذاكرة" in block and "مصدر الحقيقة" in block, "core missing"
        assert "متكتبش توقيع" in block, "procedural missing"
        assert "متابعة العرض" in block, "active episodic missing"
        assert "أزمة الكوتا" not in block, "expired episodic leaked!"

        globals()["FULL_LIMIT"] = 10  # فرض وضع top-k
        block2 = memory_block("الاصدار الاسبوعي")
        assert "أقرب" in block2 and "الإصدار" in block2, f"top-k mode fail: {block2[:200]}"
        assert "متكتبش توقيع" in block2, "procedural must survive top-k mode"

        st = status()
        assert st["in_sync"] and st["expired_hidden"] == 1, f"status fail: {st}"
        print("SELFTEST PASS — normalize/expiry/procedural/core/top-k كلهم سليمين")
    finally:
        globals()["FULL_LIMIT"] = max(
            0, int(os.environ.get("HADI_MEMORY_FULL_LIMIT", "4000") or "4000"))
        MEM_PATH, CORE_PATH, DB_PATH = orig
        _reset_conn()


def main():
    parser = argparse.ArgumentParser(description="مخزن الذاكرة المتدرجة لهادي (بند 4.2)")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("rebuild")
    s = sub.add_parser("search")
    s.add_argument("--query", required=True)
    s.add_argument("--k", type=int, default=10)
    b = sub.add_parser("block")
    b.add_argument("--query", required=True)
    sub.add_parser("status")
    sub.add_parser("selftest")
    args = parser.parse_args()

    if args.cmd == "rebuild":
        print(f"REBUILT: {rebuild()} ملاحظة اتفهرست من {MEM_PATH.name}")
    elif args.cmd == "search":
        hits = search(args.query, args.k)
        if not hits:
            print("مفيش نتايج.")
        for h in hits:
            print(f"[{h['mtype']}] (score={h['score']:.2f}) {h['raw']}")
    elif args.cmd == "block":
        print(memory_block(args.query) or "(فاضي)")
    elif args.cmd == "status":
        for k, v in status().items():
            print(f"{k}: {v}")
    elif args.cmd == "selftest":
        selftest()


if __name__ == "__main__":
    main()
