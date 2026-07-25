"""
Media attachments for CR filing (Hadi bot).

When a Change Request is filed from Discord, pull image/video attachments from
the source message (and the message it replies to) plus any extra URLs Hadi
passes, upload them to the ADO work item's Attachments section, and for files
larger than the cap, drop a link into the work item discussion instead.

Self-contained: reuses the same ADO plumbing (ado_client) and Discord bot token
that po_channel_cr.py already relies on.
"""
import os
import re
import datetime as _dt
import html as _html
import requests

import ado_client
from ado_client import ADO_BASE, ADO_API_VERSION

API_BASE = "https://discord.com/api/v10"
MAX_ATTACH_BYTES = 25 * 1024 * 1024  # 25 MB: attach up to the cap, link the rest

_IMG_EXT = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".heic")
_VID_EXT = (".mp4", ".mov", ".webm", ".mkv", ".avi", ".m4v")


def _discord_headers():
    token = os.environ.get("DISCORD_BOT_TOKEN", "")
    return {"Authorization": f"Bot {token}"}


def _is_media_attachment(a):
    ct = (a.get("content_type") or "").lower()
    if ct.startswith("image/") or ct.startswith("video/"):
        return True
    name = (a.get("filename") or "").lower()
    return name.endswith(_IMG_EXT) or name.endswith(_VID_EXT)


def _item(a):
    return {
        "url": a.get("url"),
        "filename": a.get("filename") or "attachment",
        "content_type": a.get("content_type") or "",
        "size": a.get("size"),
    }


def media_from_message(m):
    """Image/video attachments in a message and the message it replies to."""
    out = []

    def collect(msg):
        for a in (msg.get("attachments") or []):
            if _is_media_attachment(a) and a.get("url"):
                out.append(_item(a))

    if m:
        collect(m)
        ref = m.get("referenced_message")
        if ref:
            collect(ref)
    return out


def fetch_message(channel_id, message_id):
    r = requests.get(
        f"{API_BASE}/channels/{channel_id}/messages/{message_id}",
        headers=_discord_headers(), timeout=15)
    r.raise_for_status()
    return r.json()


def _download(url, known_size=None):
    """Return (bytes, oversized). bytes is None if oversized or failed."""
    if known_size and known_size > MAX_ATTACH_BYTES:
        return None, True
    try:
        resp = requests.get(url, timeout=90, stream=True)
        resp.raise_for_status()
    except Exception as e:
        print(f"MEDIA WARN: download failed {url[:80]} - {e}")
        return None, False
    clen = resp.headers.get("Content-Length")
    if clen and clen.isdigit() and int(clen) > MAX_ATTACH_BYTES:
        return None, True
    data = bytearray()
    for chunk in resp.iter_content(65536):
        data += chunk
        if len(data) > MAX_ATTACH_BYTES:
            return None, True
    return bytes(data), False


def _upload(data, filename, ado_headers):
    up = requests.post(
        f"{ADO_BASE}/wit/attachments",
        params={"fileName": filename, "api-version": ADO_API_VERSION},
        headers={**ado_headers, "Content-Type": "application/octet-stream"},
        data=data, timeout=90)
    up.raise_for_status()
    return up.json()["url"]


def maybe_attach_media(args, wi, channel_id, ado_headers):
    """Attach conversation media to a freshly created CR work item.

    Never raises: a media failure must not undo an already-created CR.
    """
    if getattr(args, "no_media", False):
        return
    media, seen = [], set()

    def add(it):
        u = it.get("url")
        if u and u not in seen:
            seen.add(u)
            media.append(it)

    if getattr(args, "source_msg", None):
        try:
            msg = fetch_message(channel_id, args.source_msg)
            for it in media_from_message(msg):
                add(it)
        except Exception as e:
            print(f"MEDIA WARN: could not read source message - {e}")

    for u in (getattr(args, "attach_url", None) or []):
        name = (u.split("?")[0].rstrip("/").split("/")[-1]) or "attachment"
        add({"url": u, "filename": name, "content_type": "", "size": None})

    if not media:
        return

    relations, oversized = [], []
    for it in media:
        data, big = _download(it["url"], it.get("size"))
        if big:
            oversized.append(it)
            continue
        if data is None:
            continue
        try:
            att_url = _upload(data, it["filename"], ado_headers)
        except Exception as e:
            print(f"MEDIA WARN: upload failed {it['filename']} - {e}")
            continue
        relations.append({
            "op": "add", "path": "/relations/-",
            "value": {"rel": "AttachedFile", "url": att_url,
                      "attributes": {"comment": "من محادثة ديسكورد"}},
        })

    patch = list(relations)
    if oversized:
        links = "<br>".join(
            f'&#8226; <a href="{it["url"]}">{it["filename"]}</a>' for it in oversized)
        patch.append({
            "op": "add", "path": "/fields/System.History",
            "value": f"مرفقات أكبر من الحد ({MAX_ATTACH_BYTES // (1024*1024)}MB) - روابط:<br>{links}",
        })

    if not patch:
        return

    try:
        pr = requests.patch(
            f"{ADO_BASE}/wit/workitems/{wi['id']}",
            params={"api-version": ADO_API_VERSION},
            headers={**ado_headers, "Content-Type": "application/json-patch+json"},
            json=patch, timeout=90)
        if pr.status_code not in (200, 201):
            print(f"MEDIA WARN: linking failed HTTP {pr.status_code} {pr.text[:200]}")
            return
    except Exception as e:
        print(f"MEDIA WARN: linking request failed - {e}")
        return

    note = f"ATTACHED {len(relations)} file(s) to CR #{wi['id']}"
    if oversized:
        note += f", {len(oversized)} over cap (linked in discussion)"
    print(note)


# ---------------------------------------------------------------------------
# Required-field defaults + channel resolution (shared by both CR/Issue CLIs)
# ---------------------------------------------------------------------------

def _today_iso():
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# اشتقاق نص عربي للحقول السردية من نص الطلب (تعديل 2)
#
# الترتيب المقصود: هادي هو اللي بيكتب الحقول دي بـ --field لأنه شايف المحادثة
# كلها وقادر يحكم. الاشتقاق هنا **شبكة أمان** بس — بيشتغل لما هادي يفوّت الحقل،
# وبيستخرج اللي موجود فعلًا في نص الطلب من غير ما يخترع.
#
# القاعدة: لو النص مافيهوش الإجابة، الحقل بيقول كده صراحة بدل ما يخمّن. قيمة
# مخترعة في حقل بيزنس أسوأ من قيمة ناقصة معلَّمة — نفس منطق «ربط غلط أسوأ من
# مفيش ربط» في ado_features.
# ---------------------------------------------------------------------------

# علامة بتفضل في النص عشان أي حد يفتح التذكرة يفرق بين اللي هادي كتبه بحكم
# على المحادثة واللي الكود اشتقه آليًا. ده أثر تدقيق مقصود.
_DERIVED_MARK = "مشتق آليًا من نص الطلب — محتاج مراجعة"

# جمل الهدف: اللي بعد الأداة دي هو القيمة اللي العميل قالها بنفسه
_RX_GOAL = re.compile(
    r"(?:عشان|علشان|بحيث|الهدف\s+منها?|الهدف|المطلوب\s+[إا]ن|"
    r"لكي|حتى)\s+(.{8,220})", re.DOTALL)

# إشارات الوجع: بتأكد إن في أثر سلبي قايم دلوقتي (مش مجرد تحسين)
_RX_PAIN = re.compile(
    r"مشكل[ةه]|بيشتك|بتشتك|شكوى|شكاوي|بيضيع|بتضيع|ضايع|بيتأخر|بتتأخر|تأخير|"
    r"بطيء|بطيئ[ةه]|بطء|مابيعرفش|مش\s+بيعرف|مش\s+شغال|مابيشتغلش|بيقع|بيهنج|"
    r"غلط|خطأ|بياخد\s+وقت|صعب|معقد|بيزهق|بنخسر|خسار[ةه]")

# إشارات الإلحاح التشغيلي
_RX_URGENT = re.compile(r"عاجل|ضروري|بسرع[ةه]|فور[اي]|حرج|blocker|urgent|critical",
                        re.IGNORECASE)


def _plain(text, limit=1500):
    """نص مسطّح: بيشيل أي HTML جاي من ريتشرن ديسكورد ويوحّد المسافات."""
    t = re.sub(r"<[^>]+>", " ", text or "")
    t = re.sub(r"\s+", " ", t).strip()
    return t[:limit]


def _sentence(text, limit=220):
    """أول جملة كاملة من نص — بيقطع عند علامة وقف مش في نص كلمة."""
    t = _plain(text, limit + 80)
    if len(t) <= limit:
        return t
    cut = t[:limit]
    for sep in (". ", "،", "؛", " - ", " "):
        idx = cut.rfind(sep)
        if idx > limit * 0.5:
            return cut[:idx].strip()
    return cut.strip()


def derive_cr_narrative(context_text):
    """يشتق {Description, CustomerBusinessValue, Impact} عربي من نص الطلب.

    بيرجع dict بالحقول اللي قدر يشتقها بثقة بس. الحقل اللي النص مافيهوش إجابته
    بيترجع بصيغة صريحة إنه محتاج تحديد — مش قيمة مخترعة ومش "غير محدد" صامتة.
    """
    body = _plain(context_text)
    if not body:
        return {}

    out = {}

    # (1) الوصف — نص الطلب نفسه كما قيل. ده أضمن محتوى عندنا وأصدقه.
    out["System.Description"] = (
        f"<div><strong>الطلب كما ورد:</strong></div>"
        f"<div>{_html.escape(body)}</div>"
        f"<div><em>({_DERIVED_MARK})</em></div>"
    )

    # (2) القيمة للعميل — الهدف اللي الطالب قاله بنفسه، لو قاله.
    goal = _RX_GOAL.search(body)
    if goal:
        out["Custom.CustomerBusinessValue"] = (
            f"الهدف كما ذُكر في الطلب: {_sentence(goal.group(1))} "
            f"({_DERIVED_MARK})")
    else:
        out["Custom.CustomerBusinessValue"] = (
            f"الطلب مافيهوش قيمة بيزنس صريحة — محتاجة تحديد من فريق المنتج "
            f"قبل التقدير. ({_DERIVED_MARK})")

    # (3) الأثر — المنصة المتأثرة من الاستنتاج القايم + وجود وجع حالي من النص.
    parts = []
    try:
        import ado_fields
        inferred = ado_fields.infer_cr_fields(body)
        if inferred.get("_inferred"):
            parts.append(f"يمس {inferred.get('Custom.StoryApplication')} "
                         f"(تصنيف: {inferred.get('Custom.CRorStoryCategory')})")
    except Exception:
        pass
    if _RX_PAIN.search(body):
        parts.append("في أثر سلبي قايم دلوقتي مذكور في الطلب")
    else:
        parts.append("مافيش أثر سلبي صريح في الطلب — يرجّح تحسين مش عطل")
    if _RX_URGENT.search(body):
        parts.append("الطلب متوصّف بإلحاح")
    out["Custom.Impact"] = "؛ ".join(parts) + f". ({_DERIVED_MARK})"

    return out


# Fields the ADO process marks required on each work item type but the Discord
# intake flow does not naturally have. Hadi may override any of these from the
# ticket context via --field; these are only fallbacks so creation never fails.
# value None on a date field means "today at runtime".
REQUIRED_DEFAULTS = {
    "Change Request": {
        "Microsoft.VSTS.Scheduling.TargetDate": None,
        "Microsoft.VSTS.Scheduling.StartDate": None,
        "Microsoft.VSTS.Scheduling.DueDate": None,
        "Custom.EstimatedHours": 0,
        "Custom.CompletedHours": 0,
        "Custom.Impact": "غير محدد",
        "Custom.CustomerBusinessValue": "غير محدد",
        "Custom.WorkAround": "غير محدد",
        "Custom.4f258631-e07a-4b4f-af0f-d824fb21d410": "غير محدد",
        "Custom.CRorStoryCategory": "New Feature",
        "Custom.StoryApplication": "Customer Web",
        "Custom.WorkType": "Web",
        # حقول إلزامية إضافية على Change Request (متأكد منها من ADO الحي — CR #102666):
        "System.Description": "غير محدد",
        "Custom.ContractFeature": False,
        "Custom.FreeFeature": False,
        "Custom.UserStoryStatus": "1 Not started",
    },
    "Customer Issue": {
        "System.Description": "غير محدد",
        "Microsoft.VSTS.TCM.SystemInfo": "غير محدد",
        "Microsoft.VSTS.TCM.Steps": "غير محدد",
        "Microsoft.VSTS.Scheduling.DueDate": None,
        # حقول إلزامية على Customer Issue (متأكد منها من ADO الحي — CI #122273-5):
        "HADAgile.IssuePriority": "Normal",
        "Custom.IssueSeverity": "Minor",
        "Custom.IssueOrdatahelp": False,
        "Custom.Repeated": False,
        "Custom.CoveredWithTestCase": False,
        "Custom.freshdeskid": "N/A",
    },
}

_DATE_FIELDS = {
    "Microsoft.VSTS.Scheduling.TargetDate",
    "Microsoft.VSTS.Scheduling.StartDate",
    "Microsoft.VSTS.Scheduling.DueDate",
}


def required_field_ops(wit_type, provided_paths, context_text=None):
    """json-patch 'add' ops for required fields of wit_type not already provided.

    نقطة 4 (F12): لو النوع Change Request ومعانا نص الفكرة (context_text)،
    المنصة والتصنيف بيتستنتجوا من النص بـ ado_fields.infer_cr_fields بدل الـ
    defaults العمياء (Web/Customer Web/New Feature) — والـ fallback القديم بيفضل
    آخر حل لو مفيش أي إشارة في النص.

    تعديل 2: الحقول السردية التلاتة (Description / CustomerBusinessValue /
    Impact) بقت تتشتق عربي من نص الطلب بدل "غير محدد" الصامتة. الأولوية
    دايمًا لهادي: أي حقل جه في --field بيغلب الاشتقاق وبيغلب الـ default."""
    defaults = dict(REQUIRED_DEFAULTS.get(wit_type, {}))
    if wit_type == "Change Request" and context_text:
        try:
            import ado_fields
            inferred = ado_fields.infer_cr_fields(context_text)
            was = inferred.pop("_inferred", False)
            defaults.update(inferred)
            if was:
                print(f"CR FIELDS: استنتاج من النص — {inferred}")
        except Exception as error:  # الاستنتاج اختياري — فشله ميوقفش الإنشاء
            print(f"CR FIELDS WARN: {type(error).__name__}: {error}")
    if context_text:
        try:
            narrative = derive_cr_narrative(context_text)
            # بس الحقول اللي النوع ده محتاجها فعلًا — مانضيفش حقل مش في تعريفه
            narrative = {k: v for k, v in narrative.items() if k in defaults}
            if narrative:
                defaults.update(narrative)
                print(f"CR NARRATIVE: اشتقاق عربي لـ {sorted(narrative)}")
        except Exception as error:  # شبكة أمان — فشلها ميوقفش الإنشاء
            print(f"CR NARRATIVE WARN: {type(error).__name__}: {error}")
    provided = set(provided_paths or [])
    ops = []
    for path, val in defaults.items():
        if path in provided:
            continue
        if val is None and path in _DATE_FIELDS:
            val = _today_iso()
        ops.append({"op": "add", "path": f"/fields/{path}", "value": val})
    return ops


_CHANNEL_DEFAULTS = {
    "po": "1358833733699899704",
    "mars": "1136668686044909761",
    "issues": "1179369466279235584",
    "support": "1179369466279235584",
}
_CHANNEL_ENV = {
    "po": "PO_CHANNEL_ID",
    "mars": "MARS_CHANNEL_ID",
    "issues": "ISSUES_CHANNEL_ID",
    "support": "ISSUES_CHANNEL_ID",
}


def resolve_channel_id(channel):
    """Map 'po'/'mars'/'issues'/'support' aliases (or a raw id) to a channel id."""
    if not channel:
        return None
    raw = str(channel).strip().lower()
    if raw in _CHANNEL_DEFAULTS:
        return os.environ.get(_CHANNEL_ENV[raw], _CHANNEL_DEFAULTS[raw])
    return str(channel).strip()


def selftest():
    """اختبار محلي من غير شبكة: python3 cr_media.py"""
    ok = True

    def check(label, cond):
        nonlocal ok
        print(("PASS  " if cond else "FAIL  ") + label)
        ok = ok and bool(cond)

    UNSET = "غير محدد"
    NARRATIVE = ("System.Description", "Custom.CustomerBusinessValue", "Custom.Impact")

    def value_of(ops, path):
        for op in ops:
            if op["path"] == f"/fields/{path}":
                return op["value"]
        return None

    # النص ده فيه هدف صريح (بعد «عشان») + إشارة وجع + منصة واضحة
    text = ("التجار بيشتكوا إن صفحة الأصناف في تطبيق التاجر بطيئة جدًا، "
            "عايزين نضيف بحث فوري عشان التاجر يلاقي الصنف من غير ما يفضل ينزل "
            "في القايمة كلها ويضيع وقت على العميل")
    ops = required_field_ops("Change Request", set(), context_text=text)

    for path in NARRATIVE:
        val = value_of(ops, path)
        check(f"{path} اتملى", bool(val))
        check(f"{path} مش «غير محدد»", val != UNSET)
    check("الوصف بيحتوي نص الطلب", "بحث فوري" in (value_of(ops, "System.Description") or ""))
    check("القيمة بتلتقط الهدف بعد «عشان»",
          "يلاقي الصنف" in (value_of(ops, "Custom.CustomerBusinessValue") or ""))
    check("الأثر بيرصد الوجع القايم",
          "أثر سلبي قايم" in (value_of(ops, "Custom.Impact") or ""))
    check("الأثر بيرصد المنصة",
          "Merchant App" in (value_of(ops, "Custom.Impact") or ""))
    check("كل حقل مشتق متعلّم للتدقيق",
          all(_DERIVED_MARK in (value_of(ops, p) or "") for p in NARRATIVE))

    # نص من غير هدف صريح: لازم يقول كده صراحة مش يخترع قيمة
    ops2 = required_field_ops("Change Request", set(), context_text="زرار الحفظ لونه وحش")
    bv = value_of(ops2, "Custom.CustomerBusinessValue") or ""
    check("من غير هدف صريح: بيعلن النقص مش بيخترع", "محتاجة تحديد" in bv)
    check("من غير وجع: بيوصفها تحسين",
          "تحسين مش عطل" in (value_of(ops2, "Custom.Impact") or ""))

    # أولوية هادي: أي حقل بعته بـ --field مايتلمسش
    ops3 = required_field_ops("Change Request", {"Custom.Impact"}, context_text=text)
    check("حقل هادي بيغلب الاشتقاق", value_of(ops3, "Custom.Impact") is None)

    # مفيش سياق = السلوك القديم بالظبط (مفيش انحدار)
    ops4 = required_field_ops("Change Request", set())
    check("من غير سياق: الافتراضي القديم زي ما هو",
          value_of(ops4, "Custom.Impact") == UNSET)

    # Customer Issue: الوصف بس بيتشتق — الحقول التانية مش من تعريف النوع
    ops5 = required_field_ops("Customer Issue", set(), context_text=text)
    check("Customer Issue: الوصف اتشتق", value_of(ops5, "System.Description") != UNSET)
    check("Customer Issue: مافيش حقول CR دخيلة",
          value_of(ops5, "Custom.Impact") is None)

    # الحقول الإلزامية التانية مالمستش
    check("WorkAround فضل زي ما هو", value_of(ops, "Custom.WorkAround") == UNSET)
    check("تواريخ الجدولة لسه بتتملى", bool(value_of(ops, "Microsoft.VSTS.Scheduling.DueDate")))

    # HTML من ديسكورد مابيتسربش للوصف
    ops6 = required_field_ops("Change Request", set(),
                              context_text="<script>x</script> عايز تقرير جديد")
    check("مفيش HTML خام في الوصف",
          "<script>" not in (value_of(ops6, "System.Description") or ""))

    print("\n" + ("ALL PASS" if ok else "THERE ARE FAILURES"))
    return 0 if ok else 1


if __name__ == "__main__":
    import sys
    sys.exit(selftest())
