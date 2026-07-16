# أداة ADO — `ado_cli.py` (بديل كامل لسيرفر `@azure-devops/mcp`)

أداة CLI في جذر المشروع بتشغّلها بـ `python3` — بتكلم Azure DevOps REST مباشرة
بنفس التوكن (`AZURE_DEVOPS_PAT`) اللي `ado_client.py` و`po_channel_cr.py` بيستخدموه.
**مفيش MCP server ولا OAuth مطلوب** — لو الـ MCP اتقطع أو مش متاح، الأداة دي بتشتغل عادي.

المشروع الافتراضي `0_Projects_Team` (تقدر تغيره بـ `--project` لو احتجت).

## أوامر القراءة (مفتوحة دايمًا)

| الأمر | بيرجع |
|------|--------|
| `python3 ado_cli.py list-projects` | كل مشاريع المنظمة |
| `python3 ado_cli.py list-teams` | تيمات المشروع |
| `python3 ado_cli.py search "كلمة" "keyword" [--area-path "..."] [--type "Issue"]` | تذاكر عنوانها فيه أي من الكلمات (زي البحث قبل رفع تذكرة جديدة — منع التكرار) |
| `python3 ado_cli.py get-work-item <id>` | تفاصيل تذكرة واحدة |
| `python3 ado_cli.py get-work-items <id1,id2,...>` | تفاصيل كذا تذكرة مرة واحدة |
| `python3 ado_cli.py get-work-item-type "Issue"` | تعريف نوع work item (الحالات والحقول) |
| `python3 ado_cli.py wiql "SELECT ... FROM WorkItems WHERE ..."` | أي استعلام WIQL خام |
| `python3 ado_cli.py my-work-items` | التذاكر المسندة لهوية الـ PAT |
| `python3 ado_cli.py list-backlogs --team "Mars Team"` | مستويات الـ backlog لتيم |
| `python3 ado_cli.py list-backlog-work-items --team "Mars Team" --backlog-id <id>` | تذاكر backlog معين |
| `python3 ado_cli.py list-iterations` | شجرة الـ iterations بتاريخ البداية والنهاية |
| `python3 ado_cli.py list-team-iterations --team "Mars Team" [--timeframe current]` | سبرنتات تيم معين |
| `python3 ado_cli.py team-settings --team "Mars Team"` | إعدادات السبرنت/البورد لتيم |

كل أوامر القراءة بترجع JSON على stdout — اقراها ولخّصها للعضو من غير ما تخترع أرقام.

## أوامر الكتابة (إنشاء فقط — بعد تأكيد صريح من صاحب الطلب)

| الأمر | بيعمل إيه |
|------|-----------|
| `python3 ado_cli.py create-work-item --type "Change Request" --title "..." --area-path "0_Projects_Team\Change Requests" [--description "<html>"] [--tags "from-discord; change-request"]` | ينشئ تذكرة، بيطبع `CREATED #<id> -> <url>` |
| `python3 ado_cli.py add-comment <id> "نص التعليق"` | يضيف تعليق على تذكرة موجودة |
| `python3 ado_cli.py add-child --parent <id> --type "..." --title "..." --area-path "..."` | ينشئ تذكرة فرعية مربوطة بتذكرة أب |

- كل أوامر الكتابة بتقبل `--dry-run` للمعاينة من غير كتابة فعلية.
- **مفيش أمر تعديل ولا حذف في الأداة دي أصلاً** — لو حد طلب تغيير حالة أو حذف تذكرة، ده برّه نطاق الأداة، اعتذر ووجّهه للبورد مباشرة أو لآسر.

## القاعدة الثابتة لنوع الـ work item + الـ Area Path (زي CLAUDE.md)

- **Customer Issue (تذكرة سابورت)** → `--type "Customer Issue"` + `--area-path "0_Projects_Team\Support Team"` — **بالعربي، بحقول منفصلة، ومربوطة بـ parent feature — شوف SOP تذكرة السابورت تحت (إلزامي)**
- **Change Request** → `--type "Change Request"` + `--area-path "0_Projects_Team\Change Requests"`

## SOP تذكرة السابورت (Customer Issue) — إلزامي حرفيًا

**كل محتوى التذكرة بالعربي** (العنوان والوصف والخطوات وكل الحقول). أسماء الشاشات والتطبيقات ممكن تفضل إنجليزي جوة الجملة (زي Order History).

**النوع دايمًا `Customer Issue`** — مش `Issue` ولا `Bug`. الوجهة: `AreaPath = 0_Projects_Team\Support Team` + `IterationPath = 0_Projects_Team\Mars_Cycle`.

**خريطة الحقول — مرجع معتمد مسحوب من تعريف النوع على ADO (متغيّرش الأسماء دي):**

| المحتوى | الحقل في ADO |
|---------|-------------|
| الوصف بالعربي | `System.Description` |
| خطوات إعادة المشكلة (مرقّمة) | `Microsoft.VSTS.TCM.Steps` |
| Case Data — بيانات الحالة (رقم الأوردر/التاجر/الفرع/الحساب/تاريخ الحدوث) | `Microsoft.VSTS.TCM.SystemInfo` (ده اللي بيظهر على الفورم باسم "Case Data") |
| Actual VS Expected Results | `Custom.ActualVSExpectedResults` |
| Due Date (النهارده + شهر) | `Microsoft.VSTS.Scheduling.DueDate` |
| العميل | `myagile.Customer` = `8Orders` |
| الأولوية | `HADAgile.IssuePriority` = `Normal` (أو `High` للحرج) |

كل الحقول النصية HTML — `<div>` و `<b>` كفاية.

**الربط بالـ parent feature إلزامي** — استخدم `add-child --parent <FEATURE_ID>` مش `create-work-item`:
- استنتج الموديول المتأثر من وصف المشكلة، ودور على الـ Feature بتاعته:
  `python3 ado_cli.py wiql "SELECT [System.Id], [System.Title] FROM WorkItems WHERE [System.WorkItemType] = 'Feature' AND [System.Title] CONTAINS 'كلمة الموديول'"`
- Features معروفة (استرشادي — اتأكد بالبحث لو في شك): Order History=55524 · Search=66357 · Online Payment=54556 · Voucher Type 2=110274 · Reports=120063 · Chat=53880 · External Delivery Module=117984 · Delivery Men=53856 · System Users=54264 · Merchants Statement=101725 · merchant notification=119875 · Customer Ads=119931
- لو الموديول مش واضح خالص من الطلب → اسأل صاحب الطلب سؤال واحد مجمّع. مترفعش تذكرة سابورت من غير parent.

**النموذج الكامل (المعتمد):**

```bash
python3 ado_cli.py add-child \
  --parent <FEATURE_ID> \
  --type "Customer Issue" \
  --title "8 Orders - <التطبيق/الشاشة> – <المشكلة بالعربي>" \
  --area-path "0_Projects_Team\Support Team" \
  --description "<div><b>الوصف:</b> شرح المشكلة بالعربي</div>" \
  --field "System.IterationPath=0_Projects_Team\Mars_Cycle" \
  --field "Microsoft.VSTS.TCM.Steps=<div><b>خطوات إعادة المشكلة:</b></div><div>1. ...</div><div>2. ...</div>" \
  --field "Microsoft.VSTS.TCM.SystemInfo=<div>رقم الأوردر: ... — التاجر/الفرع: ... — تاريخ الحدوث: ...</div>" \
  --field "Custom.ActualVSExpectedResults=<div><b>المتوقع (Expected):</b> ...</div><div><b>الفعلي (Actual):</b> ...</div>" \
  --field "Microsoft.VSTS.Scheduling.DueDate=$(date -d '+1 month' +%Y-%m-%d)" \
  --field "myagile.Customer=8Orders" \
  --field "HADAgile.IssuePriority=Normal" \
  --tags "from-discord; customer-issue"
```

- معلومة مش متوفرة في الطلب (زي رقم أوردر)؟ اكتب "غير متوفر — يُستكمل من السابورت" في مكانها وكمّل الرفع — ما عدا الـ parent فهو شرط.
- جرّب `--dry-run` الأول لو مش متأكد من حقل.
- بعد الإنشاء ابعت `CREATED #<id> -> <url>` في الرد فورًا.

## أمثلة استخدام حقيقية

**"كام issue مفتوح في السابورت؟"**
```bash
python3 ado_cli.py wiql "SELECT [System.Id] FROM WorkItems WHERE [System.TeamProject] = '0_Projects_Team' AND [System.AreaPath] = '0_Projects_Team\\Support Team' AND [System.State] <> 'Closed' AND [System.State] <> 'Solved'"
```

**رفع Change Request بعد التأكيد:**
```bash
python3 ado_cli.py create-work-item \
  --type "Change Request" \
  --title "تحسين سرعة تحميل شاشة المنتجات" \
  --area-path "0_Projects_Team\Change Requests" \
  --description "<div>طلب من عضو الفريق: ...</div>" \
  --tags "from-discord; change-request"
```
الأمر بيطبع `CREATED #<id> -> <url>` — ابعت اللينك ده في الرد على طول (زي ما هو موثق في CLAUDE.md).

**مواعيد السبرنت الجديد:**
```bash
python3 ado_cli.py list-team-iterations --team "Mars Team"
```

## الأخطاء

كل خطأ بيتطبع بصيغة `ERROR: ...` أو `FAILED ...` على stdout/stderr مع سبب واضح (401 توكن غلط، 403 صلاحية ناقصة، 404 مش موجود، أو نص رسالة ADO). لو حصل خطأ، قول للعضو بصراحة إن في مشكلة تقنية — ما تختلقش رد بديل.

##   +    create-work-item ()
-  /    work item:  `--source-msg <id> --channel support|po|mars`.   : `--attach-url <url>` ().   25MB    .
-            `--field Ref=Value`:
  - Customer Issue ( ): `Custom.IssueSeverity`=  Critical | Major | Minor | Low `Custom.freshdeskid`=<id> `--description`=  `Microsoft.VSTS.TCM.Steps`=  . area-path = `0_Projects_Team\Support Team`.
  - Change Request:    PO (WorkType/CRorStoryCategory/StoryApplication).



## إرفاق ميديا على تذكرة موجودة (attach-media)

لما حد يطلب "ارفع الصورة/الفيديو ده على التذكرة #123" (من غير إنشاء تذكرة جديدة):

```bash
python3 ado_cli.py attach-media 123 --source-msg <msg_id> --channel <channel_id أو po/mars/issues>
```

- بيسحب صور/فيديوهات الرسالة دي (والرسالة اللي هي ريبلاي عليها) وبيرفعها على قسم Attachments بتاع التذكرة.
- الملف لحد 25MB بيترفع كامل؛ الأكبر بيتحط لينكه في الـ discussion تلقائيًا.
- لينكات مباشرة كمان: `--attach-url <url>` (تتكرر). العملية إضافة فقط — مفيش أي تعديل على حقول التذكرة.
- id الرسالة الحالية بيوصلك في البرومبت مع كل رسالة فيها ميديا، وid القناة في سطر "القناة الحالية للرسالة".