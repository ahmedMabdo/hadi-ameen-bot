#!/usr/bin/env python3
"""
channel_triage.py - structured "raise all channel issues" workflow for Hadi.

The generic single-turn agent did this badly (split one issue into three, missed
others, ignored images). Per Anthropic "Building Effective Agents", this is a
PROMPT-CHAINING + ROUTING workflow with a HUMAN CHECKPOINT: decompose into fixed,
easier sub-steps instead of one big free-form turn.

Pipeline
  1) collect  - gather channel messages since a time boundary (author, time, text,
                image/video attachment urls). Pure code, no LLM.
  2) extract  - ONE focused LLM call groups related messages into DISTINCT issues
                and returns STRICT JSON. Easier task => higher accuracy.
  3) propose  - post the grouped issues for review. NO tickets created. (checkpoint)
  4) create   - on confirmation, create ONE ADO Customer Issue per issue on the
                Support board (correct details + attach that issue's images) and
                return an ordered list of links.

Images are attached by ASSOCIATION (issue -> its source messages -> their media),
so the right media lands on the right ticket.

discord_bot wires this: on a trigger phrase -> run(..., mode="propose"); on a
confirm phrase -> run(..., mode="create"). Extraction uses hadi_engine.run_oneshot.
"""
import os
import re
import sys
import json
import html
import asyncio
import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
STATE_PATH = os.path.join(HERE, "triage_state.json")
SUPPORT_AREA = os.environ.get("ADO_SUPPORT_AREA", "0_Projects_Team\\Support Team")
LOOKBACK_HOURS = int(os.environ.get("TRIAGE_LOOKBACK_HOURS", "24"))
MAX_MSGS = int(os.environ.get("TRIAGE_MAX_MSGS", "250"))

# trigger: "ارفع/راجع/اجمع ... الايشيوز/issues/المشاكل/القناة"
TRIGGER_RE = re.compile(r"(ارفع|راجع|اجمع|جمّع|لخّص).{0,25}(الايشيوز|الاشيوز|issues|المشاكل|المشكلات|القناة)", re.I)
# confirm to actually create tickets after a proposal
CONFIRM_RE = re.compile(r"(ايوه ارفع|أيوه ارفع|ارفعهم|ارفعها|نفّذ|نفذها|اعملهم|approve|go ahead|create them)", re.I)

_MEDIA_EXT = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".mp4", ".mov", ".webm")


def is_trigger(text):
    if not text: return False
    return bool(re.search("||||||| | | | | | |||", text) and re.search("|||issue||||support||customer", text))


def is_confirm(text):
    return bool(text and CONFIRM_RE.search(text))


# ----------------------------- 1) collect -----------------------------
async def collect_since(channel, client, hours=LOOKBACK_HOURS, limit=MAX_MSGS):
    since = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=hours)
    rows = []
    async for m in channel.history(limit=limit, oldest_first=False):
        if m.created_at < since:
            break
        if m.author.bot or (client.user and m.author.id == client.user.id):
            continue
        text = (m.clean_content or "").strip()
        media = [a.url for a in (m.attachments or [])
                 if (a.content_type or "").startswith(("image/", "video/"))
                 or (a.filename or "").lower().endswith(_MEDIA_EXT)]
        if not text and not media:
            continue
        if is_trigger(text) or is_confirm(text):
            continue  # skip the command messages themselves
        rows.append({
            "author": m.author.display_name,
            "ts": m.created_at.astimezone().strftime("%m-%d %H:%M"),
            "text": text,
            "media": media,
        })
    rows.reverse()  # chronological
    for i, r in enumerate(rows):
        r["idx"] = i
    return rows


# ----------------------------- 2) extract -----------------------------
def _extract_prompt(rows):
    lines = []
    for r in rows:
        tag = f" [مرفق {len(r['media'])} صورة/فيديو]" if r["media"] else ""
        lines.append(f"#{r['idx']} ({r['ts']}) {r['author']}: {r['text']}{tag}")
    body = "\n".join(lines)
    return (
        "إنت محلل دعم فني خبير. تحت رسائل قناة سابورت (لكل رسالة رقم #، توقيت، صاحبها، ونصها).\n"
        "المطلوب: اقرأ الكل، وافهم الترابط، واطلع **إيشيوز منفصلة**، بالقواعد دي:\n"
        "- الرسائل اللي عن نفس المشكلة (حتى لو أرقام أوردرات متعددة أو رسالة متابعة بتزوّد تفاصيل) = إيشيو **واحد**.\n"
        "- المواضيع المختلفة = إيشيوز مختلفة.\n"
        "- تجاهل التحية والونسة وأي رسالة مش بتوصف مشكلة أو طلب.\n"
        "- لكل إيشيو: عنوان قصير، وصف واضح فيه كل التفاصيل المهمة (أرقام أوردرات، تواريخ، أسماء مندوبين، أماكن...)، أولوية (عادية/عالية)، وأرقام الرسائل المصدر.\n"
        "- رجّع **JSON فقط** بالشكل ده (من غير أي كلام قبله أو بعده):\n"
        '{"issues":[{"title":"...","description":"...","priority":"عادية","source":[0,3],"is_problem":true}]}\n\n'
        "الرسائل:\n" + body
    )


def _parse_json(text):
    if not text:
        return None
    s = text.find("{")
    e = text.rfind("}")
    if s == -1 or e == -1 or e <= s:
        return None
    try:
        return json.loads(text[s:e + 1])
    except Exception:
        return None


async def extract(rows, hadi_engine):
    if not rows:
        return []
    raw = await hadi_engine.ask_haiku(_extract_prompt(rows), timeout=200, model="sonnet", cwd="/tmp")
    data = _parse_json(raw) or {}
    issues = []
    for it in data.get("issues", []):
        if not it.get("is_problem", True):
            continue
        src = [i for i in (it.get("source") or []) if isinstance(i, int) and 0 <= i < len(rows)]
        media = []
        for i in src:
            media.extend(rows[i]["media"])
        issues.append({
            "title": (it.get("title") or "").strip()[:200],
            "description": (it.get("description") or "").strip(),
            "priority": "عالية" if "عال" in str(it.get("priority", "")) else "عادية",
            "source": src,
            "media": media,
        })
    return issues


# ----------------------------- 2b) reflect (Hadi critiques himself) -----------------------------
def _reflect_prompt(rows, issues):
    msgs = "\n".join(
        f"#{r['idx']} ({r['ts']}) {r['author']}: {r['text']}"
        + (f" [مرفق {len(r['media'])}]" if r["media"] else "")
        for r in rows
    )
    cur = json.dumps(
        [{"title": it["title"], "description": it["description"],
          "priority": it["priority"], "source": it["source"]} for it in issues],
        ensure_ascii=False,
    )
    return (
        "دي رسائل قناة سابورت، ودي محاولتك الأولى في تجميعها لإيشيوز. راجع شغلك بنفسك بعين ناقد خبير:\n"
        "- فيه إيشيو واحد اتقسم غلط لأكتر من واحد؟ ادمجه.\n"
        "- فيه إيشيوز مختلفة اتدمجت غلط في واحد؟ افصلها.\n"
        "- فيه مشكلة حقيقية اتفاتت؟ ضيفها. فيه حاجة مش مشكلة (تحية/ونسة/نقاش)؟ شيلها.\n"
        "- الوصف فيه كل التفاصيل الصح (أرقام، تواريخ، أسماء)؟ والأولوية منطقية؟ صحّح.\n"
        "رجّع **JSON فقط** بنفس الشكل بعد التصحيح، من غير أي كلام تاني:\n"
        '{"issues":[{"title":"...","description":"...","priority":"عادية","source":[0,3],"is_problem":true}]}\n\n'
        "الرسائل:\n" + msgs + "\n\nمحاولتك الأولى:\n" + cur
    )


async def reflect(rows, issues, hadi_engine):
    """Hadi critiques and corrects his own extraction (evaluator-optimizer)."""
    if not issues:
        return issues
    try:
        raw = await hadi_engine.ask_haiku(_reflect_prompt(rows, issues), timeout=200, model="sonnet", cwd="/tmp")
    except Exception:
        return issues
    data = _parse_json(raw)
    if not data or "issues" not in data:
        return issues  # keep first pass if reflection failed to return valid JSON
    out = []
    for it in data["issues"]:
        if not it.get("is_problem", True):
            continue
        src = [i for i in (it.get("source") or []) if isinstance(i, int) and 0 <= i < len(rows)]
        media = []
        for i in src:
            media.extend(rows[i]["media"])
        out.append({
            "title": (it.get("title") or "").strip()[:200],
            "description": (it.get("description") or "").strip(),
            "priority": "عالية" if "عال" in str(it.get("priority", "")) else "عادية",
            "source": src,
            "media": media,
        })
    return out or issues


# ----------------------------- 3) propose -----------------------------
def format_proposal(issues):
    if not issues:
        return "راجعت القناة ومفيش إيشيوز واضحة محتاجة تيكت."
    out = [f"راجعت القناة ولقيت **{len(issues)}** إيشيو. راجعهم، ولو تمام قول «ارفعهم»:\n"]
    for n, it in enumerate(issues, 1):
        media = f" · 📎 {len(it['media'])} مرفق" if it["media"] else ""
        out.append(f"**{n}) {it['title']}** _(أولوية {it['priority']}{media})_\n{it['description']}\n")
    return "\n".join(out)


def save_proposal(channel_id, issues):
    state = {}
    if os.path.exists(STATE_PATH):
        try:
            state = json.load(open(STATE_PATH, encoding="utf-8"))
        except Exception:
            state = {}
    state[str(channel_id)] = {"ts": datetime.datetime.utcnow().isoformat(), "issues": issues}
    json.dump(state, open(STATE_PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


def load_proposal(channel_id):
    if not os.path.exists(STATE_PATH):
        return None
    try:
        return json.load(open(STATE_PATH, encoding="utf-8")).get(str(channel_id))
    except Exception:
        return None


# ----------------------------- 4) create -----------------------------
TICKET_TYPE = os.environ.get("TRIAGE_WIT_TYPE", "Issue")


def _prio_field(priority):
    # ADO priority 1..4 (1 highest). high -> 2, normal -> 3
    return "Microsoft.VSTS.Common.Priority=" + ("2" if priority == "عالية" else "3")


async def _create_one(issue, dry_run=False):
    cmd = [sys.executable, os.path.join(HERE, "ado_cli.py"), "create-work-item",
           "--type", TICKET_TYPE,
           "--title", issue["title"] or "issue",
           "--area-path", SUPPORT_AREA,
           "--description", issue["description"] or issue["title"] or "-",
           "--field", _prio_field(issue["priority"])]
    for u in issue.get("media", []):
        cmd += ["--attach-url", u]
    if dry_run:
        cmd.append("--dry-run")
    try:
        p = await asyncio.create_subprocess_exec(
            *cmd, cwd=HERE,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        o, e = await asyncio.wait_for(p.communicate(), timeout=120)
        out = (o or b"").decode("utf-8", "replace") + (e or b"").decode("utf-8", "replace")
    except Exception as ex:  # noqa
        return None, None, str(ex)
    m = re.search(r"https?://\S+/_workitems/edit/(\d+)", out) or re.search(r"/_workitems/edit/(\d+)", out)
    return (m.group(0) if m else None), (m.group(1) if m else None), out


async def create_tickets(issues, dry_run=False):
    links = []
    for it in issues:
        url, wid, raw = await _create_one(it, dry_run)
        links.append({"title": it["title"], "url": url, "id": wid,
                      "media": len(it.get("media", [])),
                      "error": "" if url else (raw or "")[-160:]})
    return links


def format_links(links):
    if not links:
        return "مفيش تيكتات اترفعت."
    out = ["اترفعت التذاكر دي على السابورت:\n"]
    for n, l in enumerate(links, 1):
        if l.get("url"):
            m = f" · 📎 {l.get('media',0)}" if l.get("media") else ""
            out.append(f"{n}) {l['title']}: {l['url']}{m}")
        else:
            out.append(f"{n}) {l['title']}: ⚠️ فشل الرفع ({l.get('error','?')[:80]})")
    return "\n".join(out)
