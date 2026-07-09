# 8Orders — Daily Product Intelligence Report

مولّد تقرير المنتج اليومي لـ8Orders. يسحب ويتحقق من كل الأرقام من PostHog،
وينتج تقريرًا عربيًا (PDF) ليوم العمل السابق (8ص → 2ص توقيت القاهرة).

## التشغيل
```bash
pip install -r requirements.txt
export POSTHOG_API_KEY=...          # مطلوب
python3 8orders_report_generator.py --outdir .
# اختبار يوم محدد:
python3 8orders_report_generator.py --date 2026-06-18 --outdir .
# نسخة واحدة فقط: --audience business | tech | both (الافتراضي both)

# رفع مشاكل الشيفت تلقائيًا كتذاكر Issue على بورد Support Team في ADO:
export AZURE_DEVOPS_PAT=...         # مطلوب فقط مع --push-ado (Scope: Work Items Read & Write)
python3 8orders_report_generator.py --outdir . --push-ado
# مراجعة بدون كتابة فعلية في ADO:
python3 8orders_report_generator.py --outdir . --push-ado --ado-dry-run
```

## رفع تذاكر ADO
الوجهة دائمًا: مشروع `0_Projects_Team`، Area Path `0_Projects_Team\Support Team`، نوع `Issue`،
حقول إلزامية `Customer=8Orders` و `Application=App - Customer`، تاج `posthog` + تاج تصنيف
(`technical` / `ux-enhancement`) + تاج dedup `posthog-session-<id>`.

**ثابت لكل تذاكر PostHog:** تُنشأ في `State=New` (عمود New)، `Priority=1` (الأعلى)، و`Severity`
حسب الطبيعة: كراش/تعطّل حاجب → `2 - High` (أو `1 - Critical` للأسوأ)، احتكاك UX قابل للتعافي → `3 - Medium`.
وتُثبَّت في **أعلى عمود New** عبر `StackRank` سالب (الأصغر = أعلى؛ دفعة كل يوم فوق سابقتها،
والأهم فوق داخل الدفعة) فتظهر أول شيء بدون سكرول.

**طريقتان (راجع `ROUTINE_INSTRUCTIONS.md` step 1ب):**
1. **★ المفضّلة — المبنية على ملخص PostHog الذكي (في الروتين عبر MCP):** لكل جلسة مرشّحة
   تُولَّد خلاصة AI (بتأكيد بصري)، ثم:
   - **فلترة الإيجابيات الكاذبة**: تُتجاهَل أي جلسة `session_outcome.success = true`
     (طلب اكتمل فعلًا، أو "نقرات غاضبة" = زيادة كمية متعمّدة) — الأحداث وحدها تعطي ~25% إيجابيات كاذبة.
   - **التصنيف من الخلاصة**: كراش/استثناء حاجب → تقني؛ إحباط/التباس بدون كراش → UX.
     (مثال مهم: `UnimplementedError` قد يكون كراشًا حاجبًا فعليًا — الخلاصة تحسم لا نوع الخطأ.)
   - **العنوان والبريف يصفان المشكلة الحقيقية** + deep link للحظة الحرجة (`…/replay/<sid>?t=<sec>`).
2. **◦ البديل — `--push-ado`** (بيئة بلا MCP): يرفع عبر `ado_client.py` (REST + `AZURE_DEVOPS_PAT`)
   مباشرة من الترتيب بالأحداث. أبسط لكن **بدون فلترة إيجابيات كاذبة ولا بريف وصفي**. `--ado-max`
   يحدد أقصى عدد جلسات/تشغيل (افتراضي 8)، و`--ado-dry-run` للمعاينة.

> **معروف/قيد المتابعة**: حقل الـ swimlane (`System.BoardLane`) مقفول ReadOnly على
> مستوى تعريف الحقل لنوع `Issue` في الـ process بتاعكم حاليًا (تأكدنا بالاختبار المباشر،
> حتى `bypassRules=true` مرفوض) — فالتذكرة بتترفع بالتصنيف كـ**تاج** فقط (`technical` /
> `ux-enhancement`)، ولازم حد يسحبها يدويًا للـ swimlane الصح لحد ما أدمن ADO يفك القاعدة
> دي من (Org Settings → Process → Issue → Layout/Rules). أول ما تتفك، الكود جاهز ويبدأ
> يضبط الـ swimlane أوتوماتيك من غير أي تعديل تاني (شغال فعليًا، بس النتيجة بتتجاهَل
> بصمت لو الحقل لسه مقفول).
المخرج (افتراضيًا نسختان) + طباعة SANITY CHECK:
- `PostHog Report DDMonYYYY.pdf` — نسخة الأعمال (كاملة).
- `PostHog Report DDMonYYYY - Tech.pdf` — نسخة الفريق التقني (أخطاء/إصدارات/جلسات، بلا بيانات إيرادات/أعمال).

## الاستخدام كروتين (Claude Code on the web)
- اربط هذا المستودع كـ Source للروتين.
- الموديل: claude-opus-4-8 + Ultracode.
- الجدولة: يوميًا 07:00 — Africa/Cairo (مؤجَّلة من 03:00 حتى ينتهي PostHog من إزالة تكرار أحداث اليوم المنتهي فتستقر الأرقام).
- env: `POSTHOG_API_KEY`. الشبكة تسمح بـ us.posthog.com و fonts.googleapis.com و discord.com (لإرسال الـ DM).
- نص تعليمات الروتين كامل في `ROUTINE_INSTRUCTIONS.md`.

## إرسال تلقائي على ديسكورد
السكربت بيبعت **نسخة الأعمال فقط** ("PostHog Report DDMonYYYY.pdf") كرسالة خاصة (DM)
لواحد أو أكتر من المستلمين تلقائيًا في نهاية كل تشغيل (عبر `discord_delivery.py`)،
باستخدام Discord REST API مباشرة (مش بوت هادي التفاعلي) عشان يشتغل كل يوم حتى لو
مفيش حد متابع جلسة الروتين. نسخة الفريق التقني (Tech) لا تُرسَل لأي مستلم.

env مطلوب:
```
DISCORD_BOT_TOKEN=...          # توكن البوت
MAHMOUD_DISCORD_USER_ID=...    # id واحد، أو أكتر مفصولين بفاصلة/مسافة — كل id يبعتله DM لوحده
DISCORD_GUILD_ID=...           # بديل فقط: يستخدم للبحث بالاسم لو الـ id غير مضبوط (مستلم واحد بس)
```

مثال لإرسال نفس التقرير لمحمود وللمستخدم نفسه للتأكيد:
```
MAHMOUD_DISCORD_USER_ID=111111111111111111,222222222222222222
```

كل مستلم بيُحاول الإرسال له بشكل مستقل — فشل واحد (id غلط، الـ DM مقفول، ...) بيتسجّل
في اللوج وبيكمل للباقي، ومايكسرش الروتين سواء فشل مستلم واحد أو الكل. للتعطيل اليدوي:
`--no-discord`.

اختبار يدوي مباشر:
```bash
python3 discord_delivery.py "PostHog Report 25Jun2026.pdf"
```

## هادي: تلخيص قناة الـ PO ورفع الأفكار كـ CRs
`po_channel_cr.py` — أداة CLI لبوت هادي التفاعلي (على AWS): يقرأ بها آخر رسايل
قناة الـ PO (`1358833733699899704`)، وبعد ما يلخّص ويحدد الأفكار الجديدة بنفسه،
يرفع كل فكرة كـ CR على بورد **Change Requests / Stories** (Area Path
`0_Projects_Team\Change Requests`، منع تكرار بتاج `po-msg-<message_id>`)،
ثم يرد بالملخص ولينكات التذاكر في نفس القناة.

```bash
python3 po_channel_cr.py fetch --limit 50 --json     # قراءة الرسايل
python3 po_channel_cr.py file-cr --title "..." --brief "..." --source-msg <id>
python3 po_channel_cr.py post --text "الملخص + اللينكات"
```

نفس الأمر `post` بيستخدمه هادي للتبليغ من الشات الخاص: لما آصر يطلب منه في الـ DM
يبعت رسالة لجروب، يبعتها بـ `--channel po` (الافتراضي) أو `--channel mars`
(جروب مارس `1136668686044909761`) أو أي channel id خام.

env: نفس `DISCORD_BOT_TOKEN` و `AZURE_DEVOPS_PAT` المستخدمين أعلاه، و`DISCORD_GUILD_ID`
للينكات الرسايل. البوت محتاج View Channel + Read Message History + Send Messages على
القناة. تعليمات هادي كاملة (تضاف له كـ skill) في `HADI_PO_CHANNEL.md`.
