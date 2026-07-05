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

- **Customer Issue** → `--type "Issue"` + `--area-path "0_Projects_Team\Support Team"`
- **Change Request** → `--type "Change Request"` + `--area-path "0_Projects_Team\Change Requests"`

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
