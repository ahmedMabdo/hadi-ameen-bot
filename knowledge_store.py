#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""RAG على /knowledge (بند 4.2) — فهرسة مقاطع بدل قراءة الملف كامل عند كل سؤال.

المشكلة: ملفات المعرفة (مرجع القيود المحاسبية، مراحل الدورة، Robo Call، توثيق
Complaint/Replacement) حوالي 72KB. قراءة الملف كامل عشان سؤال واحد = توكنز
مهدورة وسياق متشتت.

الحل: كل ملف بيتقسّم لمقاطع (chunks) بعنوان مسار (breadcrumb)، وبتتفهرس في
SQLite FTS5 بنفس التطبيع العربي بتاع memory_store — وهادي بيسحب أقرب 3-5 مقاطع
بس. صفر مكتبات خارجية: docx بيتقرا بـ zipfile من stdlib.

الفهرس knowledge/knowledge_index.db حالة مشتقة (في .gitignore) — بيتبني في أي
وقت بـ rebuild، والملفات الأصلية هي مصدر الحقيقة.

CLI (ده اللي هادي بينده):
    knowledge_store.py search --query "..." [--k 4] [--full]
    knowledge_store.py get --id 42            # المقطع كامل
    knowledge_store.py rebuild [--force]      # إعادة بناء (بيتعمل أوتوماتيك لو الملفات اتغيرت)
    knowledge_store.py status
    knowledge_store.py selftest
"""
import argparse
import hashlib
import json
import os
import re
import sqlite3
import sys
import zipfile
from pathlib import Path

BASE = Path(__file__).resolve().parent
KDIR = BASE / "knowledge"
DB_PATH = KDIR / "knowledge_index.db"

# ملفات الذاكرة ليها مخزنها الخاص (memory_store) — متتفهرسش هنا مرتين
# sprints.md متولّد أوتوماتيك من ado_snapshot كل ~15 دقيقة، فوجوده في الفهرس كان
# بيخلي البصمة تتغير باستمرار → rebuild كامل (145 مقطع) عند كل بحث. وحالة
# السبرنت متاحة أصلًا بأمر ado_snapshot brief وهو أدق وأسرع للغرض ده.
SKIP_NAMES = {"memory.md", "memory_core.md", "memory_archive.md", "sprints.md"}
SKIP_SUFFIX = {".db", ".db-wal", ".db-shm", ".json", ".tmp"}
TEXT_SUFFIX = {".txt", ".md"}

CHUNK_TARGET = int(os.environ.get("HADI_RAG_CHUNK", "900") or "900")
CHUNK_MAX = CHUNK_TARGET * 2
TOP_K = max(1, int(os.environ.get("HADI_RAG_TOP_K", "4") or "4"))

try:  # نفس التطبيع بالظبط بتاع الذاكرة — مصدر واحد للمنطق
    from memory_store import normalize, _TOKEN_RX, _STOPWORDS
except Exception:  # نسخة احتياطية لو اتشغل السكربت لوحده
    _DIA = re.compile(r"[ً-ْٰـ]")
    _TOKEN_RX = re.compile(r"[0-9A-Za-zء-ي٠-٩]+")
    _STOPWORDS = set()

    def normalize(text: str) -> str:
        text = _DIA.sub("", text or "")
        for src, dst in (("أ", "ا"), ("إ", "ا"), ("آ", "ا"),
                         ("ى", "ي"), ("ة", "ه"),
                         ("ؤ", "و"), ("ئ", "ي")):
            text = text.replace(src, dst)
        return text.lower()


# --- قراءة الملفات (صفر dependencies) --------------------------------------
def read_docx(path: Path) -> list:
    """فقرات ملف Word — بيقرا word/document.xml من الـ zip مباشرة."""
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml").decode("utf-8", "ignore")
    paras = []
    for block in re.split(r"</w:p>", xml):
        text = "".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", block))
        text = text.replace(" ", " ").strip()
        if text:
            paras.append(text)
    return paras


def read_text(path: Path) -> list:
    raw = path.read_text(encoding="utf-8", errors="ignore")
    return [p.strip() for p in raw.splitlines() if p.strip()]


def load_paragraphs(path: Path):
    suffix = path.suffix.lower()
    if suffix == ".docx":
        return read_docx(path)
    if suffix in TEXT_SUFFIX:
        return read_text(path)
    return None


def indexable_files():
    if not KDIR.exists():
        return []
    out = []
    for p in sorted(KDIR.iterdir()):
        if not p.is_file() or p.name in SKIP_NAMES or p.name.startswith("."):
            continue
        if p.suffix.lower() in SKIP_SUFFIX:
            continue
        if p.suffix.lower() in TEXT_SUFFIX or p.suffix.lower() == ".docx":
            out.append(p)
    return out


# --- التقطيع ---------------------------------------------------------------
_HEADING_HINT = re.compile(r"^(#{1,6}\s+|\d+[\.\)]\s+|[-*]\s*\*\*)")


def looks_like_heading(line: str) -> bool:
    """سطر قصير من غير نقطة نهاية = عنوان على الأرجح (شغال عربي وإنجليزي)."""
    stripped = line.strip()
    if _HEADING_HINT.match(stripped):
        return True
    if len(stripped) > 70:
        return False
    return not stripped.endswith((".", "،", ":", "؛", "!", "؟"))


def chunk_paragraphs(paras: list) -> list:
    """مقاطع بحجم ~CHUNK_TARGET حرف، كل مقطع معاه أقرب عنوان قبله."""
    chunks, buf, size, heading = [], [], 0, ""
    pending_heading = ""

    def flush():
        nonlocal buf, size
        if buf:
            chunks.append({"heading": heading, "text": "\n".join(buf).strip()})
            buf, size = [], 0

    for para in paras:
        clean = re.sub(r"^#{1,6}\s+", "", para).strip()
        if looks_like_heading(para) and len(clean) < 70:
            # عنوان جديد: اقفل المقطع الحالي لو فيه محتوى كفاية
            if size >= CHUNK_TARGET * 0.4:
                flush()
            pending_heading = clean
            if not buf:
                heading = pending_heading
            buf.append(clean)
            size += len(clean) + 1
            continue
        if not buf and pending_heading:
            heading = pending_heading
        buf.append(para)
        size += len(para) + 1
        if size >= CHUNK_MAX or (size >= CHUNK_TARGET and para.endswith((".", "،", "؛"))):
            flush()
            heading = pending_heading
    flush()
    return [c for c in chunks if len(c["text"]) > 25]


# --- قاعدة البيانات --------------------------------------------------------
_SCHEMA = """
CREATE TABLE IF NOT EXISTS meta(k TEXT PRIMARY KEY, v TEXT);
CREATE TABLE IF NOT EXISTS chunks(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  path TEXT NOT NULL,
  ord INTEGER NOT NULL,
  heading TEXT NOT NULL DEFAULT '',
  text TEXT NOT NULL,
  norm TEXT NOT NULL,
  embedding BLOB
);
CREATE INDEX IF NOT EXISTS chunks_path ON chunks(path);
CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
  norm, content='chunks', content_rowid='id',
  tokenize='unicode61 remove_diacritics 2'
);
CREATE TRIGGER IF NOT EXISTS chunks_ai AFTER INSERT ON chunks BEGIN
  INSERT INTO chunks_fts(rowid, norm) VALUES (new.id, new.norm);
END;
CREATE TRIGGER IF NOT EXISTS chunks_ad AFTER DELETE ON chunks BEGIN
  INSERT INTO chunks_fts(chunks_fts, rowid, norm) VALUES('delete', old.id, old.norm);
END;
"""

_conn = None


def connect():
    global _conn
    if _conn is None:
        KDIR.mkdir(parents=True, exist_ok=True)
        _conn = sqlite3.connect(str(DB_PATH))
        _conn.row_factory = sqlite3.Row
        _conn.execute("PRAGMA journal_mode=WAL")
        _conn.executescript(_SCHEMA)
    return _conn


def _fingerprint() -> str:
    """بصمة **محتوى** الملفات — بيها نعرف الفهرس بايت ولا لأ.

    2026-07-26: كانت (اسم+حجم+mtime). أي ملف بيتكتب دوريًا بنفس المحتوى كان
    بيغيّر الـ mtime فيخلي `fresh` تساوي False للأبد → rebuild كامل عند كل بحث.
    الهاش على المحتوى بيقفل الفئة دي كلها مهما اتضاف ملفات متولّدة بكرة.
    """
    h = hashlib.sha256()
    for p in indexable_files():
        h.update(p.name.encode())
        try:
            h.update(p.read_bytes())
        except OSError:
            h.update(b"?")
    return h.hexdigest()[:16]


def rebuild(force: bool = True) -> int:
    conn = connect()
    total = 0
    with conn:
        conn.execute("DELETE FROM chunks")
        for path in indexable_files():
            paras = load_paragraphs(path)
            if not paras:
                continue
            for i, ch in enumerate(chunk_paragraphs(paras)):
                conn.execute(
                    "INSERT INTO chunks(path, ord, heading, text, norm) VALUES (?,?,?,?,?)",
                    (path.name, i, ch["heading"], ch["text"], normalize(ch["text"])),
                )
                total += 1
        conn.execute("INSERT OR REPLACE INTO meta(k,v) VALUES ('fingerprint', ?)", (_fingerprint(),))
        conn.execute("INSERT OR REPLACE INTO meta(k,v) VALUES ('chunks', ?)", (str(total),))
    return total


def ensure_fresh() -> str:
    """بيتنادى عند تشغيل البوت: يعيد البناء بس لو ملفات المعرفة اتغيرت."""
    conn = connect()
    row = conn.execute("SELECT v FROM meta WHERE k='fingerprint'").fetchone()
    current = _fingerprint()
    if row and row[0] == current:
        n = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
        return f"{n} مقطع (الفهرس محدّث)"
    n = rebuild()
    return f"{n} مقطع (اتعمل rebuild — ملفات المعرفة اتغيرت)"


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
    match = _query_string(query)
    if not match:
        return []
    rows = connect().execute(
        "SELECT c.id, c.path, c.heading, c.text, bm25(chunks_fts) AS score"
        " FROM chunks_fts JOIN chunks c ON c.id = chunks_fts.rowid"
        " WHERE chunks_fts MATCH ? ORDER BY score LIMIT ?",
        (match, k or TOP_K),
    ).fetchall()
    return [dict(r) for r in rows]


def get_chunk(chunk_id: int):
    row = connect().execute(
        "SELECT id, path, heading, text FROM chunks WHERE id = ?", (chunk_id,)
    ).fetchone()
    return dict(row) if row else None


def status() -> dict:
    conn = connect()
    per_file = conn.execute(
        "SELECT path, COUNT(*) n, SUM(LENGTH(text)) chars FROM chunks GROUP BY path ORDER BY n DESC"
    ).fetchall()
    row = conn.execute("SELECT v FROM meta WHERE k='fingerprint'").fetchone()
    return {
        "files_indexed": len(per_file),
        "chunks": conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0],
        "fresh": bool(row) and row[0] == _fingerprint(),
        "per_file": [(r["path"], r["n"], r["chars"]) for r in per_file],
    }


def selftest() -> None:
    """اختبار على ملفات مؤقتة — مايلمسش /knowledge الحقيقي."""
    global KDIR, DB_PATH, _conn
    import tempfile

    orig = (KDIR, DB_PATH)
    tmp = Path(tempfile.mkdtemp(prefix="hadi_rag_test_"))
    try:
        KDIR, DB_PATH, _conn = tmp, tmp / "idx.db", None
        (tmp / "guide.txt").write_text(
            "قيد المبيعات\n"
            + "المبيعات اليومية "
            "Sales Daily Journal مدين النقدية "
            "دائن الإيراد. " * 12
            + "\nقيد المرتجع\n"
            + "المرتجعات Refund مدين "
            "الإيراد دائن النقدية. " * 12,
            encoding="utf-8",
        )
        (tmp / "memory.md").write_text("- ملاحظة مفروض تتتخطى\n", encoding="utf-8")
        n = rebuild()
        assert n >= 2, f"chunks={n}"
        assert all("memory.md" != c[0] for c in status()["per_file"]), "memory.md اتفهرس بالغلط"
        hits = search("Refund")
        assert hits and "Refund" in hits[0]["text"], f"search fail: {hits[:1]}"
        hits2 = search("المرتجعات")  # عربي عادي
        assert hits2, "arabic search fail"
        assert status()["fresh"] is True
        (tmp / "guide.txt").write_text("جديد خالص Robo Call flow\n" * 8, encoding="utf-8")
        assert status()["fresh"] is False, "التغيير مش متكتشف"
        msg = ensure_fresh()
        assert "rebuild" in msg and status()["fresh"] is True, msg
        print("SELFTEST PASS — docx/txt وchunking والبحث وكشف التغيير كلهم سليمين")
    finally:
        KDIR, DB_PATH = orig
        _conn = None


def _print_hits(hits, full=False):
    if not hits:
        print("مفيش مقطع قريب من السؤال ده في قاعدة المعرفة.")
        return
    for h in hits:
        text = h["text"] if full else (h["text"][:700] + ("…" if len(h["text"]) > 700 else ""))
        head = f" › {h['heading']}" if h["heading"] else ""
        print(f"\n[#{h['id']}] {h['path']}{head}\n{text}")
    print(f"\n({len(hits)} مقطع — للمقطع كامل: knowledge_store.py get --id N)")


def main():
    parser = argparse.ArgumentParser(description="RAG على /knowledge (بند 4.2)")
    sub = parser.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("search")
    s.add_argument("--query", required=True)
    s.add_argument("--k", type=int, default=TOP_K)
    s.add_argument("--full", action="store_true")
    g = sub.add_parser("get")
    g.add_argument("--id", type=int, required=True)
    r = sub.add_parser("rebuild")
    r.add_argument("--force", action="store_true")
    sub.add_parser("status")
    sub.add_parser("selftest")
    args = parser.parse_args()

    if args.cmd == "search":
        ensure_fresh()
        _print_hits(search(args.query, args.k), args.full)
    elif args.cmd == "get":
        ch = get_chunk(args.id)
        if not ch:
            sys.exit(f"مفيش مقطع بالـ id ده: {args.id}")
        head = f" › {ch['heading']}" if ch["heading"] else ""
        print(f"[#{ch['id']}] {ch['path']}{head}\n{ch['text']}")
    elif args.cmd == "rebuild":
        print(f"REBUILT: {rebuild()} مقطع من {len(indexable_files())} ملف")
    elif args.cmd == "status":
        st = status()
        print(f"files_indexed: {st['files_indexed']} | chunks: {st['chunks']} | fresh: {st['fresh']}")
        for path, n, chars in st["per_file"]:
            print(f"  {n:>4} مقطع | {chars:>7,} حرف | {path}")
    elif args.cmd == "selftest":
        selftest()


if __name__ == "__main__":
    main()
