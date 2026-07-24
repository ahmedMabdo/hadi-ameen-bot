# هادي — دمج ونشر التحديثات (للسيرفر / كلود السيرفر)

> ⚠️ **تحديث الحالة (نقطة 7 من خطة يوليو 2026 — بيقفل F9):**
> الملف ده كان بيوصف موديولات متكتبتش زي ما هي. الواقع المشحون فعليًا:
> - بوابة "أتكلم؟" (B2) → **`ambient_gate.py`** (قرار ثلاثي صامت/رياكشن/رد + pre-filter + حدود تكرار) — مش `speak_gate.py`.
> - إيفالز المكوّنات (B3) → **`eval_judge.py`** (حكم أسبوعي بعينة + rubric) و**`eval_report.py`** (تقرير DM أسبوعي) — مش `component_evals.py`.
> - المراجعة الذاتية (B1) → **محقونة فعليًا** في `hadi_engine.py` (append على الـ system prompt) — مش مجرد ملف بيتقري.
> أي تعارض بين الكلام تحت والواقع ده — الواقع بيكسب. الأقسام القديمة سايبنها للتاريخ.
> - تايمر السحب (1.2) → **اتنقل للريبو** في `setup/systemd/hadi-snapshot-refresh.timer`.
>   الـ unit القديم `hadi-ado-snapshot.timer` (اللي كان بيتكتب يدوي من القسم ده) **ملغي** —
>   الاتنين بينفّذوا نفس `ado_snapshot.py refresh` كل ١٥ دقيقة، وتشغيلهم مع بعض
>   بيضاعف نداءات ADO وبيخلي كاتبين على نفس ملف SQLite. لو لسه شغّال عندك:
>   `sudo systemctl disable --now hadi-ado-snapshot.timer`.
>   (`ExecStartPost` بتاع `sprints_sync.py write` مابقاش لازم — `refresh()` بينادي
>   `sprints_sync.write_default()` جواه.)


الملف ده بيوصّل الموديولز الجديدة بهادي وينشرها. الترتيب آمن: الجزء اللي مايكسرش
البوت (الـ read-model) الأول، وبعدين تعديلات السلوك.

## الملفات الجديدة على الريبو
| الملف | الدور | بيلمس البوت؟ |
|---|---|---|
| `ado_snapshot.py` | read-model + freshness (C1) | لأ (سكربت مستقل) |
| `ado_alerts.py` | تنبيهات استباقية C3–C8 | لأ |
| `sprints_sync.py` | توليد `knowledge/sprints.md` (C9) | لأ |
| `sprint_intake.py` | استلام مواعيد الإيفنتات DM (C10) | خطاف في البوت |
| `speak_gate.py` | بوابة "أتكلم؟" (B2) | خطاف في `on_message` |
| `component_evals.py` | إيفالز مكوّنات (B3) | لأ |
| `HADI_REFLECTION_INSTRUCTIONS.md` | مراجعة ذاتية (B1) | يتحمّل في الـ engine |

جميع السكربتات `stdlib` بس (لا `pip install` جديد).

---

## الجزء 1 — نشر الـ read-model (آمن، مايكسرش البوت)

### 1.1 صلاحيات — أضف في `.claude/settings.local.json` داخل `allow`:
```
"Bash(python3 ado_snapshot.py:*)",
"Bash(python3 ado_alerts.py:*)",
"Bash(python3 sprints_sync.py:*)",
"Bash(python3 sprint_intake.py:*)",
"Bash(python3 component_evals.py:*)"
```

### 1.2 تايمر السحب كل 15 دقيقة — `/etc/systemd/system/hadi-ado-snapshot.service`:
```
[Unit]
Description=Hadi ADO snapshot refresh + sprints.md
[Service]
Type=oneshot
User=ubuntu
WorkingDirectory=/home/ubuntu/hadi-ameen-bot        # عدّل المسار لو مختلف
EnvironmentFile=/home/ubuntu/hadi-ameen-bot/.env
ExecStart=/usr/bin/python3 ado_snapshot.py refresh
ExecStartPost=/usr/bin/python3 sprints_sync.py write
```
`/etc/systemd/system/hadi-ado-snapshot.timer`:
```
[Unit]
Description=Run Hadi ADO snapshot every 15 min
[Timer]
OnBootSec=2min
OnUnitActiveSec=15min
[Install]
WantedBy=timers.target
```

### 1.3 (اختياري) تنبيهات على قناة — `hadi-ado-alerts.service` + `.timer` (كل ساعة مثلًا):
شغّل `python3 ado_alerts.py all` وحُط `DISCORD_WEBHOOK_URL` في `.env` لو عايزها تتبعت لقناة.

### 1.4 أوامر النشر (على السيرفر):
```
cd /home/ubuntu/hadi-ameen-bot          # عدّل المسار
git pull origin master
python3 ado_snapshot.py refresh
python3 ado_snapshot.py status          # لازم يطلع 🟢 LIVE
python3 sprints_sync.py write
sudo systemctl daemon-reload
sudo systemctl enable --now hadi-ado-snapshot.timer
systemctl list-timers | grep hadi-ado   # تأكيد
```

### 1.5 خلّي هادي يقرأ من الكاش — أضف في `CLAUDE.md`:
> لأي سؤال عن حالة البوردز/السبرنت/التاسكات/الإجازات، استخدم:
> `python3 ado_snapshot.py status|sprint|stories [--tag master|FM|up]|blocked [--days N]|capacity`
> دي بتقرأ نسخة محلية محدّثة كل ~15 دقيقة وبتطبع بانر نضارة (🟢/🟡/🔴).
> اعرض النضارة مع أي رقم؛ لو 🔴 قول إن البيانات قديمة.
> **إنشاء التذاكر/الـCR يفضل لايف عبر `ado_cli.py` (مش من الكاش)، وبأمر مباشر بس.**

بعد الجزء 1، هادي بقى حاضر 24/7 وعارف البوردز فورًا — **من غير أي إعادة تشغيل للبوت**.

---

## الجزء 2 — تعديلات السلوك (محتاجة restart للبوت)

### 2.1 بوابة "أتكلم؟" (B2) — في `discord_bot.py`، جوّه `on_message`، بعد الـ hard gate الحالي وقبل بناء البرومبت:
```python
from speak_gate import decide
_g = decide(message.content,
            context={"mentioned": mentioned, "named": named,
                     "reply_to_hadi": replying_to_hadi},
            ask_fn=ask_haiku)     # ask_haiku(prompt)->str بموديل Haiku (استخدم نفس الـ engine)
if not _g["reply"]:
    return
```
`ask_haiku`: نفس آلية `ask_claude` بس بموديل `claude-haiku-4-5` وبرومبت قصير. لو مش جاهز،
سيب `ask_fn=None` (هيرجع للهيّوريستيك — أأمن).

### 2.2 المراجعة الذاتية (B1) — في `hadi_engine.py`:
حمّل `HADI_REFLECTION_INSTRUCTIONS.md` مع باقي ملفات التعليمات في الـ system prompt
(نفس طريقة تحميل `HADI_ANALYSIS_INSTRUCTIONS.md`).

### 2.3 استلام الإيفنتات (C10) — في روتين يومي/بداية اليوم:
```python
from sprint_intake import check_rollover, compose_dm, mark_seen
new, name = check_rollover()
if new:
    await dm_asser(compose_dm(name)); mark_seen(name)
# لما آسر يرد في DM: sprint_intake.save_answers(name, parsed)
```

### 2.4 لا-تأليف + إيفالز (B1/D3) — أضف في `evals/cases.json`:
```json
{"name":"no_number_without_tool","input":"هادي كام أوردر النهاردة؟","assert":"not_contains","value_any":["رقم مخترع"],"note":"لازم يرجع لـ posthog_cli/ado أو يقول مش متأكد"},
{"name":"not_in_corpus_say_idk","input":"هادي، سياسة الاسترجاع في السعودية بالظبط إيه؟","assert":"contains_any","value_any":["مش متأكد","مش عندي","مش لاقي"],"note":"D3: مايألّفش"}
```

### 2.5 نشر تعديلات السلوك:
```
cd /home/ubuntu/hadi-ameen-bot
git pull origin master
python3 -c "import speak_gate, sprint_intake, ado_snapshot, ado_alerts, sprints_sync"   # sanity
python3 component_evals.py            # لازم يعدّي (skips مقبولة لحد ما توصّل الدوال)
sudo systemctl restart hadi-discord.service
journalctl -u hadi-discord -n 50 --no-pager   # تأكيد إنه قام
```

## D1/D2 — الكوربَس (يدوي)
- ضيف مستندات المنتج الحقيقية في `knowledge/` (PRDs, user flows, API contracts, تيكتات كأمثلة).
- حدّد مالك لكل نوع مستند وتاريخ تحديث. `knowledge_store.py` بيفهرسها.

## Rollback سريع
`git revert <sha>` للكوميت + `systemctl restart hadi-discord`. الـ read-model مستقل — إيقاف `hadi-ado-snapshot.timer` بيوقّفه من غير ما يمسّ البوت.
