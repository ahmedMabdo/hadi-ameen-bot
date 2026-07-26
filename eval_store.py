#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""مخزن تقييم تفاعلات هادي (بند 5.3 — العمود الفقري لحلقة التحسين).

المشكلة اللي بيحلها: حلقة التحسين المستمرة محتاجة تعرف **أسوأ التفاعلات تقييمًا**،
وده معناه إشارة جودة مش بس تكلفة وزمن. أرخص إشارة بشرية موجودة أصلًا: الرياكشنز
اللي الفريق بيحطها على ردود هادي في Discord.

بيتخزن (logs/evals.db — حالة تشغيل محلية، في .gitignore):
  interactions  صف لكل رسالة اتعالجت: القناة، صاحب الطلب، مقتطف الطلب والرد،
                النتيجة (رد/صمت/خطأ/مهلة)، الزمن، التكلفة، التوكنز، عدد أدوار الأدوات
  feedback      رياكشن على رد هادي → +1 / -1 / 0 مربوط بالتفاعل

الخصوصية: بنخزن **مقتطفات** (أول 400 حرف) مش الرسايل كاملة، والداتابيز محلية على
السيرفر ومابتترفعش. الغرض قياس السلوك، مش أرشفة كلام الناس.

CLI:
    eval_store.py stats [--days 7]
    eval_store.py worst [--days 7] [--limit 10]
    eval_store.py selftest
"""
import argparse
import os
import sqlite3
import time
from pathlib import Path

BASE = Path(__file__).resolve().parent
DB_PATH = BASE / "logs" / "evals.db"
EXCERPT = int(os.environ.get("HADI_EVAL_EXCERPT", "400") or "400")

# رياكشنز إيجابية/سلبية — القائمة قابلة للتعديل من غير كود
POSITIVE = set("👍 ✅ 🔥 💪 ❤️ 🎉 🙏 💯 🫡".split())
NEGATIVE = set("👎 😕 ❌ 🤦 😑 ⛔ 🙄".split())

_SCHEMA = """
CREATE TABLE IF NOT EXISTS interactions(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts REAL NOT NULL,
  conv_key TEXT NOT NULL DEFAULT '',
  channel TEXT NOT NULL DEFAULT '',
  author TEXT NOT NULL DEFAULT '',
  user_message_id TEXT NOT NULL DEFAULT '',
  reply_message_id TEXT NOT NULL DEFAULT '',
  prompt_excerpt TEXT NOT NULL DEFAULT '',
  reply_excerpt TEXT NOT NULL DEFAULT '',
  outcome TEXT NOT NULL DEFAULT '',
  error_type TEXT NOT NULL DEFAULT '',
  error_msg TEXT NOT NULL DEFAULT '',
  latency_ms INTEGER NOT NULL DEFAULT 0,
  cost_usd REAL,
  input_tokens INTEGER NOT NULL DEFAULT 0,
  cache_read INTEGER NOT NULL DEFAULT 0,
  output_tokens INTEGER NOT NULL DEFAULT 0,
  num_turns INTEGER NOT NULL DEFAULT 0,
  engine TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS ix_inter_ts ON interactions(ts);
CREATE INDEX IF NOT EXISTS ix_inter_reply ON interactions(reply_message_id);
CREATE TABLE IF NOT EXISTS feedback(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  interaction_id INTEGER NOT NULL,
  ts REAL NOT NULL,
  emoji TEXT NOT NULL,
  sentiment INTEGER NOT NULL DEFAULT 0,
  user_id TEXT NOT NULL DEFAULT '',
  UNIQUE(interaction_id, emoji, user_id)
);
"""

_conn = None


def connect():
    global _conn
    if _conn is None:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        _conn = sqlite3.connect(str(DB_PATH), timeout=10)
        _conn.row_factory = sqlite3.Row
        _conn.execute("PRAGMA journal_mode=WAL")
        _conn.executescript(_SCHEMA)
        # ترقية جداول قديمة (2026-07-26): نص الخطأ كان مش متخزّن خالص — بس
        # error_type — فأي تشخيص كان محتاج SSH + journalctl. حادثة 2026-07-23
        # (رصيد خلص + logged out) عدّت أسبوعين قبل ما نعرف سببها.
        cols = {r[1] for r in _conn.execute("PRAGMA table_info(interactions)")}
        if "error_msg" not in cols:
            _conn.execute("ALTER TABLE interactions ADD COLUMN"
                          " error_msg TEXT NOT NULL DEFAULT ''")
            _conn.commit()
    return _conn


def _clip(text: str) -> str:
    text = (text or "").strip().replace("\n", " ")
    return text[:EXCERPT]


def record_interaction(conv_key="", channel="", author="", user_message_id="",
                       reply_message_id="", prompt="", reply="", outcome="",
                       error_type="", latency_ms=0, stats=None, engine="",
                       error_msg=""):
    """صف واحد لكل رسالة اتعالجت. فشل التسجيل عمره ما يوقف الرد (best-effort)."""
    stats = stats or {}
    usage = stats.get("usage") or {}
    try:
        conn = connect()
        with conn:
            cur = conn.execute(
                "INSERT INTO interactions(ts, conv_key, channel, author, user_message_id,"
                " reply_message_id, prompt_excerpt, reply_excerpt, outcome, error_type,"
                " error_msg, latency_ms, cost_usd, input_tokens, cache_read, output_tokens,"
                " num_turns, engine)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (time.time(), conv_key, channel, author, str(user_message_id or ""),
                 str(reply_message_id or ""), _clip(prompt), _clip(reply), outcome, error_type,
                 str(error_msg or "")[:300],
                 int(latency_ms), stats.get("cost"),
                 int(usage.get("input_tokens") or 0),
                 int(usage.get("cache_read_input_tokens") or 0),
                 int(usage.get("output_tokens") or 0),
                 int(stats.get("num_turns") or 0), engine),
            )
            return cur.lastrowid
    except Exception as error:
        print(f"EVAL STORE WARN: {type(error).__name__}: {error}")
        return None


def attach_feedback(reply_message_id, emoji: str, user_id: str = "") -> bool:
    """يربط رياكشن على رد هادي بالتفاعل بتاعه. بيرجّع True لو اتسجل."""
    sentiment = 1 if emoji in POSITIVE else (-1 if emoji in NEGATIVE else 0)
    try:
        conn = connect()
        row = conn.execute(
            "SELECT id FROM interactions WHERE reply_message_id = ? ORDER BY id DESC LIMIT 1",
            (str(reply_message_id),),
        ).fetchone()
        if not row:
            return False
        with conn:
            conn.execute(
                "INSERT OR IGNORE INTO feedback(interaction_id, ts, emoji, sentiment, user_id)"
                " VALUES (?,?,?,?,?)",
                (row["id"], time.time(), emoji, sentiment, str(user_id)),
            )
        return True
    except Exception as error:
        print(f"EVAL STORE WARN (feedback): {type(error).__name__}: {error}")
        return False


def remove_feedback(reply_message_id, emoji: str, user_id: str = "") -> None:
    """لو حد شال الرياكشن — التقييم يتشال معاه."""
    try:
        conn = connect()
        with conn:
            conn.execute(
                "DELETE FROM feedback WHERE emoji = ? AND user_id = ? AND interaction_id IN"
                " (SELECT id FROM interactions WHERE reply_message_id = ?)",
                (emoji, str(user_id), str(reply_message_id)),
            )
    except Exception as error:
        print(f"EVAL STORE WARN (unreact): {type(error).__name__}: {error}")


def _since(days: float) -> float:
    return time.time() - days * 86400


def stats(days: float = 7.0) -> dict:
    conn = connect()
    cutoff = _since(days)
    row = conn.execute(
        "SELECT COUNT(*) n, AVG(latency_ms) avg_ms, SUM(COALESCE(cost_usd,0)) cost,"
        " SUM(outcome='error') errors, SUM(outcome='timeout') timeouts,"
        " SUM(outcome='no_reply') silences, SUM(outcome='replied') replies"
        " FROM interactions WHERE ts >= ?", (cutoff,)).fetchone()
    lat = [r[0] for r in conn.execute(
        "SELECT latency_ms FROM interactions WHERE ts >= ? ORDER BY latency_ms", (cutoff,))]
    fb = conn.execute(
        "SELECT SUM(sentiment > 0) pos, SUM(sentiment < 0) neg, COUNT(*) total"
        " FROM feedback WHERE ts >= ?", (cutoff,)).fetchone()
    n = row["n"] or 0
    return {
        "interactions": n,
        "replies": row["replies"] or 0,
        "no_reply": row["silences"] or 0,
        "errors": row["errors"] or 0,
        "timeouts": row["timeouts"] or 0,
        "p50_ms": lat[len(lat) // 2] if lat else 0,
        "p90_ms": lat[int(len(lat) * 0.9)] if lat else 0,
        "cost_usd": round(row["cost"] or 0, 4),
        "cost_per_1000": round((row["cost"] or 0) * 1000 / n, 2) if n else 0,
        "feedback_pos": fb["pos"] or 0,
        "feedback_neg": fb["neg"] or 0,
        "feedback_total": fb["total"] or 0,
    }


def error_rate(days: float = 7.0) -> dict:
    """معدل الفشل + أكتر خطأ متكرر بنصه — غذاء تنبيه heartbeat (2026-07-26)."""
    conn = connect()
    cutoff = _since(days)
    row = conn.execute(
        "SELECT COUNT(*) n, SUM(outcome IN ('error','timeout')) e"
        " FROM interactions WHERE ts >= ?", (cutoff,)).fetchone()
    n, e = row["n"] or 0, row["e"] or 0
    top = conn.execute(
        "SELECT error_type, error_msg, COUNT(*) c FROM interactions"
        " WHERE ts >= ? AND outcome IN ('error','timeout')"
        " GROUP BY error_type, error_msg ORDER BY c DESC LIMIT 3",
        (cutoff,)).fetchall()
    return {
        "total": n, "failures": e,
        "pct": round(100.0 * e / n, 1) if n else 0.0,
        "top": [{"type": r["error_type"], "msg": (r["error_msg"] or "")[:160],
                 "count": r["c"]} for r in top],
    }


def interaction_for_reply(reply_message_id):
    """صف التفاعل اللي رده هو الرسالة دي — للتنبيه الفوري عند فيدباك سلبي (نقطة 7)."""
    conn = connect()
    row = conn.execute(
        "SELECT * FROM interactions WHERE reply_message_id = ? ORDER BY id DESC LIMIT 1",
        (str(reply_message_id),)).fetchone()
    return dict(row) if row else None


def sample_replied(days: float = 7.0, limit: int = 20):
    """عينة عشوائية من الردود الحقيقية للفترة — غذاء الحكم الأسبوعي (LLM-as-judge)."""
    conn = connect()
    rows = conn.execute(
        "SELECT * FROM interactions WHERE ts >= ? AND outcome = 'replied'"
        " AND LENGTH(reply_excerpt) > 0 ORDER BY RANDOM() LIMIT ?",
        (_since(days), limit)).fetchall()
    return [dict(r) for r in rows]


def worst(days: float = 7.0, limit: int = 10):
    """أسوأ التفاعلات: السلبي بالرياكشن أولًا، ثم الأخطاء والمهل، ثم الأبطأ."""
    conn = connect()
    rows = conn.execute(
        "SELECT i.*, COALESCE(SUM(f.sentiment), 0) score, COUNT(f.id) votes"
        " FROM interactions i LEFT JOIN feedback f ON f.interaction_id = i.id"
        " WHERE i.ts >= ? GROUP BY i.id", (_since(days),)).fetchall()
    def rank(r):
        severity = 0
        if r["score"] < 0:
            severity = 3
        elif r["outcome"] in ("error", "timeout"):
            severity = 2
        elif r["latency_ms"] > 120000:
            severity = 1
        return (-severity, -abs(min(r["score"], 0)), -r["latency_ms"])
    return [dict(r) for r in sorted(rows, key=rank)[:limit]]


def selftest():
    global DB_PATH, _conn
    import tempfile
    orig = DB_PATH
    tmp = Path(tempfile.mkdtemp(prefix="hadi_eval_test_"))
    try:
        DB_PATH, _conn = tmp / "evals.db", None
        i1 = record_interaction(conv_key="ch:1", author="آسر", reply_message_id="m1",
                                prompt="سؤال عن التذاكر", reply="فيه 3 تذاكر",
                                outcome="replied", latency_ms=5000,
                                stats={"cost": 0.01, "num_turns": 2,
                                       "usage": {"input_tokens": 10, "output_tokens": 5}})
        record_interaction(conv_key="ch:1", outcome="error", error_type="EngineError",
                           latency_ms=1000, prompt="طلب فشل")
        record_interaction(conv_key="ch:2", outcome="no_reply", latency_ms=800, prompt="هزار")
        assert i1, "insert فشل"
        assert attach_feedback("m1", "👎", "u1") is True, "feedback مااتسجلش"
        assert attach_feedback("m_unknown", "👍", "u1") is False, "ربط برسالة مش موجودة!"
        attach_feedback("m1", "👎", "u1")  # تكرار — مايتسجلش مرتين
        st = stats(1)
        assert st["interactions"] == 3 and st["errors"] == 1 and st["no_reply"] == 1, st
        assert st["feedback_neg"] == 1 and st["feedback_total"] == 1, st
        w = worst(1, 5)
        assert w[0]["reply_message_id"] == "m1", "السلبي مش في الأول"
        assert w[1]["outcome"] == "error", "الخطأ مش تاني"
        remove_feedback("m1", "👎", "u1")
        assert stats(1)["feedback_total"] == 0, "شيل الرياكشن مااشتغلش"
        print("SELFTEST PASS — التسجيل والتقييم والترتيب والحذف كلهم سليمين")
    finally:
        DB_PATH, _conn = orig, None


def main():
    parser = argparse.ArgumentParser(description="مخزن تقييم تفاعلات هادي (بند 5.3)")
    sub = parser.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("stats"); s.add_argument("--days", type=float, default=7)
    w = sub.add_parser("worst"); w.add_argument("--days", type=float, default=7)
    w.add_argument("--limit", type=int, default=10)
    sub.add_parser("selftest")
    args = parser.parse_args()

    if args.cmd == "stats":
        for k, v in stats(args.days).items():
            print(f"{k}: {v}")
    elif args.cmd == "worst":
        rows = worst(args.days, args.limit)
        if not rows:
            print("مفيش تفاعلات في المدة دي.")
        for r in rows:
            print(f"\n#{r['id']} [{r['outcome']}{'/' + r['error_type'] if r['error_type'] else ''}]"
                  f" score={r['score']} {r['latency_ms']/1000:.0f}s {r['channel']} — {r['author']}")
            print(f"  طلب: {r['prompt_excerpt'][:120]}")
            if r["reply_excerpt"]:
                print(f"  رد : {r['reply_excerpt'][:120]}")
    elif args.cmd == "selftest":
        selftest()


if __name__ == "__main__":
    main()
