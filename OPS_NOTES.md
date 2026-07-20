# ملاحظات تشغيل وصيانة — hadi-server

> **الملف ده مش موجّه لهادي.** هو للبشر وللجلسات اللي بتعدّل السيرفر من برّه.
> هادي شغال على السيرفر مباشرة ومش واقع عليه أغلب القيود دي.

---

## ⚠️ فخ: الطرفية في المتصفح بتاكل الأحرف العربية

**الأعراض:** تكتب أمر فيه نص عربي في طرفية EC2 Instance Connect (المتصفح) — الأمر بينفّذ من غير خطأ، لكن النص العربي بيوصل **فاضي**.

| اللي بتكتبه | اللي بيوصل للسيرفر |
|---|---|
| `grep -c 'ماكو' file.md` | `grep -c '' file.md` |
| `t.replace('ماكو','ماركو')` | `t.replace('','')` |

**ليه ده خطير:** النمط الفاضي بيطابق كل حاجة والاستبدال الفاضي عملية بلا أثر — **فالأمر بينجح شكلياً وما بيعملش أي حاجة**. مفيش رسالة خطأ تنبّهك.

نتائج شفناها فعلياً:
- `grep -r ''` مسح `.venv` كله وغرّق الطرفية بعشرات الآلاف من السطور
- عملية استبدال اتنفذت 3 مرات وكل مرة رجّعت "نجاح" والملف ما اتغيرش

**كمان مش شغّال:** ترميز `ما...` بيتطبّع لعربي قبل ما يوصل، فمش حل.

### الحل: ابعت السكريبت نفسه بـ base64

اكتب السكريبت محلياً، اضغطه، وابعته كـ ASCII خالص:

```bash
# محلياً
gzip -9 -c fix.py | base64 -w0 > fix.b64
# لو كبير: split -b 1250 -d fix.b64 chunk_

# على السيرفر (كله ASCII)
printf '%s' '<base64>' > /tmp/fix.b64
base64 -d /tmp/fix.b64 | gunzip > /tmp/fix.py
md5sum /tmp/fix.py        # قارنه بالمحلي
python3 /tmp/fix.py
```

### قاعدة إلزامية

**أي تعديل فيه نص عربي لازم يطبع عدّاد قبل وبعد.**

```python
n_before = text.count(OLD)
# ... التعديل ...
print(f"{f}: replaced={n_before} old_left={after.count(OLD)} new_now={after.count(NEW)}")
```

من غير العدّاد ده مش هتعرف إن التعديل فشل. ده اللي كشف المشكلة أصلاً.

---

## الخدمة

| البند | القيمة |
|---|---|
| systemd unit | `hadi-discord.service` |
| ExecStart | `/home/ubuntu/hadi-ameen-bot/.venv/bin/python discord_bot.py` |
| المسار الفعلي | **SDK** (`claude_agent_sdk` متثبت في الـ venv) |
| `MAX_CONCURRENCY` | **2** — طلبين بالتوازي في نفس العملية |

بعد أي تعديل: `sudo systemctl restart hadi-discord` ثم اتأكد `systemctl is-active`.

### ⚠️ التوازي وهوية الطالب

`MAX_CONCURRENCY=2` معناه إن `os.environ` **مشترك بين الطلبات**. أي هوية أو صلاحية
لازم تعدي في `contextvars.ContextVar` مش في `os.environ`، وتوصل للعملية الفرعية عبر
`ClaudeAgentOptions.env` لكل استدعاء على حدة.

قياس فعلي على 200 طلب متشابك:

| الطريقة | تسريب هوية |
|---|---|
| `os.environ` العام | **100 / 200** |
| `ContextVar` | **0 / 200** |

---

## طبقة صلاحيات PostHog

- `posthog_guard.py` — الأدمن والتيم، والحجب والتقنيع
- نقطة الاختناق الوحيدة: `intel/8orders_report_generator.py::hogql()`
- كل نداءات `posthog_cli.py` بتعدي من `gen()` المغلّف بـ `GuardedGen`
- الهوية بتيجي من `HADI_PH_ACTOR` = `message.author.id`

**قاعدة حاكمة:** الهوية تتاخد من `message.author.id` حصراً — **ممنوع** استخراجها من نص
الرسالة. الاسم الظاهر في Discord أي حد بيغيّره من إعداداته في ثانية.

`intel/8orders_report_generator.py` لو اتشغّل مباشرة **بيتخطى الحارس** — ده مقصود عشان
التقرير المجدول يفضل شغال، بس خليه في بالك.

---

## مشاكل قائمة

### 1. بيانات PostHog متوقفة

| اليوم | الأحداث |
|---|---|
| 2026-07-19 → 07-20 | **صفر** |
| 2026-07-18 | 2 |
| 2026-07-16 | 1 |
| 2026-07-14 | 4 |

**9 أحداث في 7 أيام.** مرتبط بتجاوز كوتا PostHog (موثّق في `knowledge/memory.md`).
أي رقم البوت بيطلّعه دلوقتي بلا قيمة تحليلية.

### 2. القرص عند 88%

`/` مستخدم 88.1% من 6.71GB. محتاج تنضيف — في نسخ احتياطية كتير (`*.bak-*`,
`.env.backup.*`) و `tmp_images/`.

### 3. سجل التدقيق في نسخة واحدة

`logs/posthog_guard.log` مستبعد بـ `.gitignore` (`*.log`) — يعني موجود على قرص
السيرفر بس. لو القرص امتلا أو الـ instance ضاعت، الـ audit trail راح بالكامل.
محتاج rotation ونسخ لبرّه.

### 4. remote اسمه `intel` ميت

```
intel  git@github.com:assergameel1-crypto/8orders-posthog-daily-intel.git
```

الـ fetch منه بيفشل (مفيش صلاحية أو الريبو مش موجود). ملفات `intel/` نفسها متتبعة
عادي جوه `origin` فمفيش خطر فقد، لكنه remote مضلل. يتصلح أو يتشال:
`git remote remove intel`

### 5. مفتاح PostHog باسم شخص

`POSTHOG_API_KEY` في `.env` مفتاح شخصي مربوط بحساب آسر. كل نشاط البوت بيتسجّل في
PostHog باسمه، فالـ activity log بيفقد قيمته الرقابية. الأفضل service account منفصل.

---

## قبل ما تسيب السيرفر

```bash
git status --porcelain          # لازم يبقى فاضي
git rev-list --left-right --count origin/master...HEAD   # لازم 0 0
systemctl is-active hadi-discord                          # لازم active
```
