# خطة دمج hadi-ameen-bot + 8orders-posthog-daily-intel — v1.0

**الاستراتيجية:** نقل محدود — البوت يفضل في جذر الريبو زي ما هو (صفر تغيير مسارات على EC2)،
وintel يدخل كمجلد فرعي، والشخصية تتفصل في `HADI_PERSONA.md`.

**محتويات الحزمة دي (تتنسخ للريبو في خطوة 4):**

| الملف | إيه اللي فيه |
|-------|--------------|
| `CLAUDE.md` | السياق المشترك (مشروع/فريق/بوردات/دقة/أمان) — **الشخصية اتشالت منه** + قواعد العملية الديناميكية + alias قناة issues |
| `HADI_PERSONA.md` | **جديد** — شخصية هادي (23 سنة، منصورة، MIS) + التفضيلات المهنية + قواعد فهم السياق + النداء بالاسم + المرونة والأولوية + الذكاء الاجتماعي + قواعد البحث على النت |
| `HADI_ANALYSIS_INSTRUCTIONS.md` | **جديد** — أطر التحليل: تصنيف، أولويات P0–P4، دليل/ثقة، session/release/regression، تواصل حسب الجمهور، قوالب |
| `discord_bot.py` | **معدّل** — (1) رسايل هادي نفسه بقت جزء من الـ history، (2) الريبلاي بيتبعت كسياق أساسي، (3) النداء بالاسم من غير مينشن (NAME_TRIGGER)، (4) الريبلاي على رسالة هادي بيشغّله تلقائيًا، (5) الـ prompt بيوجّه لـ HADI_PERSONA.md |
| `po_channel_cr.py` | **معدّل** — alias `issues` جديد + وصف التذكرة بيذكر القناة الصح بدل "قناة الـ PO" الثابتة + الافتراضي `Change Request` (إصلاح الـ drift) |
| `setup/settings.local.json` | **معدّل** — إضافة WebSearch + WebFetch |
| `.env.example` | **موحّد** — متغيرات البوت + الروتينات + intel في ملف واحد (+ NAME_TRIGGER, HISTORY_LIMIT, ISSUES_CHANNEL_ID) |

---

## المرحلة صفر — قبل أي حاجة

0.1. **Rotate الـ AZURE_DEVOPS_PAT** لو لسه ما اتعملش (الـ README القديم بيقول التوكن اتشارك في شات قبل كده).
0.2. خد rollback points:
```bash
cd ~/hadi-ameen-bot
git tag pre-merge-bot && git push origin pre-merge-bot

cd ~/8orders-posthog-daily-intel
git tag pre-merge-intel && git push origin pre-merge-intel
```

## المرحلة 1 — دمج intel كـ subtree (بالتاريخ الكامل)

```bash
cd ~/hadi-ameen-bot
git checkout master && git pull

git remote add intel https://github.com/assergameel1-crypto/8orders-posthog-daily-intel.git
git fetch intel
git subtree add --prefix=intel intel main
```

## المرحلة 2 — إزالة التكرار من intel/

> ⚠️ **قبل الحذف اعمل diff** — النسختين متفرقتين فعلًا (نسخة intel من po_channel_cr.py افتراضيها
> `Issue` والصح `Change Request`). اتأكد إن مفيش fixes تانية في نسخة intel مش موجودة عندنا:
```bash
diff intel/po_channel_cr.py po_channel_cr.py
diff intel/ado_client.py ado_client.py
```
لو ظهرت فروق منطقية (مش بس الـ default) — راجعها قبل ما تكمل.

```bash
git rm intel/po_channel_cr.py intel/ado_client.py
```

**وصّل imports الـ generator بجذر الريبو** — افتح `intel/8orders_report_generator.py` وقبل
`import ado_client` ضيف:
```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
```
وشغّل فحص:
```bash
grep -rn "import ado_client\|import po_channel_cr\|from ado_client" intel/
cd intel && python3 -c "import sys; from pathlib import Path; sys.path.insert(0, str(Path('.').resolve().parent)); import ado_client; print('IMPORT OK')" && cd ..
```
(اعمل نفس الفحص لـ `intel/discord_delivery.py` لو بيستورد حاجة من الجذر.)

## المرحلة 3 — إصلاح تعارض الذاكرة (لو موجود)

لو في ملف `intel/CLAUDE.md` جه مع الـ subtree — **امسحه أو ادمج محتواه في ROUTINE_INSTRUCTIONS.md**،
عشان الروتين مياخدش تعليمات متضاربة (جذر الريبو فيه CLAUDE.md المشترك الجديد).
```bash
ls intel/CLAUDE.md 2>/dev/null && echo "موجود — راجعه" || echo "مش موجود — تمام"
```

## المرحلة 4 — نسخ ملفات الحزمة

انسخ من `hadi-merge-kit/` فوق الملفات الموجودة (الجذر):
```bash
cp hadi-merge-kit/CLAUDE.md .
cp hadi-merge-kit/HADI_PERSONA.md .
cp hadi-merge-kit/HADI_ANALYSIS_INSTRUCTIONS.md .
cp hadi-merge-kit/discord_bot.py .
cp hadi-merge-kit/po_channel_cr.py .
cp hadi-merge-kit/.env.example .
cp hadi-merge-kit/setup/settings.local.json setup/
git add -A && git commit -m "Merge intel + split persona + context fixes + name trigger + web search"
git push
```

## المرحلة 5 — تحديث EC2 (hadi-server)

```bash
ssh ubuntu@<server>
cd ~/hadi-ameen-bot && git pull
# صلاحيات Claude Code (WebSearch/WebFetch):
cp setup/settings.local.json .claude/settings.local.json
# متغيرات جديدة (اختيارية — الافتراضيات شغالة):
#   NAME_TRIGGER=on   HISTORY_LIMIT=30   ISSUES_CHANNEL_ID=1179369466279235584
nano .env
# أعد تشغيل البوت (systemd أو screen حسب تشغيلكم):
sudo systemctl restart hadi-bot   # أو الطريقة المستخدمة عندكم
```

## المرحلة 6 — Golden Tests على ديسكورد (قبل ما تعلن إنه خلص)

| # | الاختبار | المتوقع |
|---|----------|---------|
| 1 | مينشن عادي: "@هادي في كام issue مفتوح؟" | يرد بأرقام من ADO + لينكات |
| 2 | اطلب تقرير، وبعدها **من غير ريبلاي**: "هادي اعملها 48 ساعة" | يفهم إنها نفس التقرير ويصرّح بافتراضه |
| 3 | اعمل **ريبلاي** على رد قديم لهادي واكتب "زوّد التفاصيل" (من غير مينشن) | يرد في نفس السياق تلقائيًا |
| 4 | "ازيك يا هادي؟" من غير مينشن | يرد رد قصير طبيعي |
| 5 | "الوضع هادي النهاردة والشغل ماشي" | **ميردش خالص** |
| 6 | "التقرير بتاع هادي كويس" | **ميردش خالص** |
| 7 | رفع CR كامل | يجمع التفاصيل → يأكد → يرفع → **لينك في نفس الرد** |
| 8 | "هادي، إيه الـ best practice لرسالة payment pending؟" | يبحث على النت ويفصل المرجع الخارجي عن قراركم |
| 9 | "هادي ابعت update لباشمهندس أحمد" | يبدأ بـ "باشمهندس أحمد..." مش "يا أحمد" |
| 10 | "هادي حلل المشكلة دي" (وصف مشكلة من القناة) | يستخدم Quick Triage: خلاصة/تصنيف/أولوية/دليل/ثقة |

## المرحلة 7 — إعادة ربط الروتين اليومي

1. في Claude Code on the web: غيّر الـ Source من الريبو القديم للريبو المدموج.
2. التعليمات بقت في `intel/ROUTINE_INSTRUCTIONS.md` — حدّث الـ prompt بتاع الروتين لو بيشاور على مسار.
3. **تشغيل تجريبي** قبل الاعتماد:
```bash
python3 intel/8orders_report_generator.py --date 2026-07-07 --outdir . --push-ado --ado-dry-run
```
4. راقب أول تشغيلين حقيقيين (07:00) — الـ PDF وصل في الـ DM + التذاكر اترفعت صح.

## المرحلة 8 — التثبيت والأرشفة

- أسبوع تشغيل سليم → **Archive** لريبو `8orders-posthog-daily-intel` من Settings (مش Delete).
- اختياري (موصى بيه): برانش `stable` يقرأ منه الروتين، والتطوير على `master` — يمنع commit تجريبي بالليل يكسر تقرير الصبح.

## Rollback (لو حاجة اتكسرت)

```bash
# البوت:
cd ~/hadi-ameen-bot && git reset --hard pre-merge-bot && git push --force
# على EC2: git pull ثم restart
# الروتين: رجّع الـ Source للريبو القديم (لسه موجود لحد ما يتأرشف)
```

---

## ملاحظات مهمة

1. **مرحلة 2 (PostHog التفاعلي) مش في النسخة دي** بقرارك — لما البوت يثبت، الخطوة الجاية:
   استخراج `posthog_client.py` من الـ generator + بناء `posthog_cli.py` على نمط `ado_cli.py`.
2. `HADI_ANALYSIS_INSTRUCTIONS.md` مكتوب بحيث هادي **ميدعيش** إن عنده أداة PostHog تفاعلية —
   لما تتبني في المرحلة الجاية، حدّث السطر ده في الملف.
3. لو `discord_followup.py` و`discord_orderpo.py` مش موجودين في الريبو (شغالين على السيرفر بس) —
   دي فرصة تعمللهم commit مع الدمج عشان مفيش كود على السيرفر مش في git.
4. الـ regex بتاع النداء بالاسم متجرب على 11 حالة (منها "الوضع هادي" و"خليك هادي" — مبيردش عليهم).
   لو ظهرت حالة غلط في الاستخدام الفعلي، عطّل مؤقتًا بـ `NAME_TRIGGER=off` وابعتلنا الجملة.
