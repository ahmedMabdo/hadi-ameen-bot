# هادي أمين — إعداد الربط بـ Azure DevOps

الملف ده بيشرح خطوات تفعيل ربط هادي بـ ADO قبل/عند الرفع على السيرفر.

## إيه اللي اتعمل

- **`ado_cli.py`** — أداة CLI بديلة بالكامل لسيرفر `@azure-devops/mcp` — بتكلم ADO REST مباشرة بنفس الـ PAT، من غير أي MCP server أو OAuth. التفاصيل في `HADI_ADO_CLI_INSTRUCTIONS.md`.
- **`CLAUDE.md`** — اتحدّث: أضيف أقسام (الربط بـ ADO عبر `ado_cli.py`، رفع CR/Customer Issue من ديسكورد، أسئلة السبرنت والذاكرة، أمثلة محادثة، حدود أمان).
- **`knowledge/sprints.md`** — ملف ذاكرة السبرنتات (MS-91 / MS-92 + السيكونات + الإجازات + قالب + سجل أسئلة).
- **`setup/`** — قوالب الإعداد (محتاجة تتنسخ لأماكنها لأن ملفات الإعداد المخفية محمية من التعديل المباشر).

## خطوات التفعيل (مرة واحدة)

> ملاحظة: الملفات المخفية (`.env` / `.gitignore` / `.claude/settings.local.json`) محمية، فالقوالب اتحطّت في `setup/` وانت بتنقلها.

1. **الأسرار**: انسخ `setup/env.example` لملف `.env` في الجذر، واملا `AZURE_DEVOPS_PAT` بالتوكن الحقيقي (و`DISCORD_BOT_TOKEN` و`DISCORD_GUILD_ID`).
2. **gitignore**: ضيف سطور `setup/gitignore.txt` لملف `.gitignore` — **مهم جداً عشان `.env` ما يترفعش**.
3. **الصلاحيات**: استبدل محتوى `.claude/settings.local.json` بمحتوى `setup/settings.local.json` (بيديله صلاحية تشغيل السكربتات، من غير أي MCP server).
4. شغّل البوت وجرّب الأوامر تحت.

**ملحوظة:** مفيش MCP server مطلوب لـ ADO خالص — `ado_cli.py` بيغطي كل العمليات (قراءة وإنشاء) عبر REST مباشرة. لو كان عندك `.mcp.json` قديم فيه سيرفر `azure-devops`، تقدر تشيله.

## الصلاحيات المضبوطة

- **قراءة**: كل بوردات `0_Projects_Team` (تذاكر، سبرنت، iterations) — عبر أوامر `ado_cli.py` (`list-projects`, `search`, `get-work-item`, `wiql`, `list-iterations`, ...).
- **كتابة محدودة**: `create-work-item` / `add-comment` / `add-child` فقط.
- **ممنوع**: مفيش أمر update ولا delete في `ado_cli.py` أصلاً — التعديل والحذف مش موجودين كخيار.

## أوامر تجربة على ديسكورد

- "هادي في كام issue مفتوح في السبورت؟" → قراءة عبر `ado_cli.py search` / `wiql`.
- "هادي اعملي CR إن شاشة المنتجات تبقى أسرع" → بيجمع التفاصيل، يأكّد، يرفع بـ `ado_cli.py create-work-item`، يرجّع لينك.
- (مع سبرنت جديد) هادي يسأل آسر عن المواعيد الناقصة ويحفظها في `knowledge/sprints.md`.

## أمان

- التوكن اللي اتشارك في الشات لازم يتعمله **rotate**.
- `.env` لازم يكون في `.gitignore` ومايترفعش أبداً.
