# هادي — أطر التحليل والتصنيف (عند الطلب)

> اقرأ الملف ده لما الطلب فيه: تحليل جلسة/مشكلة، تصنيف، أولويات، release update، regression status، أو تقرير للبيزنس/التقني/QA.
> دي **أطر مساعدة مش قوالب إلزامية** — لو السؤال بسيط جاوب بسيط. القاعدة: افصل دايمًا بين العرض الظاهر، السبب المحتمل، الدليل، التأثير، الإجراء، ومستوى الثقة.
> ملحوظة أدوات: بيانات الجلسات جاية من تقارير PostHog (روتين intel اليومي) أو من اللي متبعت في القناة — متدعيش إنك شغّلت أداة PostHog تفاعلية (مش متاحة حاليًا). بيانات التذاكر من `ado_cli.py`.

---

## 1. تصنيف المشاكل

| التصنيف | يعني إيه |
|---------|----------|
| UX Issue | المستخدم مفهمش، الفلو مش واضح، الترتيب البصري غلط |
| UI Issue | مشكلة شكل/محاذاة/حالة عرض |
| Technical Issue | API failure، كراش، شاشة فاضية، حالة معلّقة |
| Performance Issue | تحميل بطيء، skeleton طويل، timeout، استجابة متأخرة |
| Business Rule Issue | فاوتشر، tier، audience، حد أدنى للطلب، منطق استحقاق |
| Operational Issue | Deployment، config، branch closing، اعتمادية عملية |
| Content Issue | نص/ترجمة/رسالة ناقصة أو ملخبطة |
| QA Gap | سيناريو مغطهوش التيستنج |
| Analytics Gap | event ناقص أو tracking مش كافي |

مشكلة واحدة ممكن تاخد أكتر من تصنيف — قول الأساسي الأول.

## 2. الأولوية

| الأولوية | التعريف |
|----------|---------|
| P0 Critical | بيمنع checkout / payment / login / order flow أو أثره واسع |
| P1 High | فلو أساسي متأثر والـ workaround محدود |
| P2 Medium | احتكاك واضح من غير منع كامل |
| P3 Low | مشكلة شكلية/نصية أو أثر محدود |
| P4 Backlog | تحسين مستقبلي |

**اطلع P0 فقط لو:** المستخدم مش قادر يكمل طلب، أو checkout/payment/login/العناوين مقفولة، أو شاشة فاضية/loading لا نهائي بيمنع التقدم، أو المشكلة بتضرب مستخدمين كتير، أو فيه خطر مالي/ثقة (خصم/audience/دفع).
**متعملهاش Critical لو:** المشكلة شكلية بس، أو فيه workaround واضح، أو الأثر مش مثبت، أو الدليل ضعيف.

## 3. الدليل والثقة

قوة الدليل:

| نوع الدليل | القوة |
|-----------|-------|
| Error log مباشر | قوي جدًا |
| Replay واضح | قوي |
| Rage clicks + abandonment | قوي |
| تكرار نفس المشكلة عبر مستخدمين | قوي |
| Status من ADO | قوي |
| سكرين شوت | متوسط |
| رسالة سابورت بس | متوسط/ضعيف |
| افتراض من غير داتا | ضعيف |

مستويات الثقة في استنتاجك:

| الثقة | يعني |
|-------|------|
| High | Replay/log/تكرار/status واضح |
| Medium | مؤشر قوي بس محتاج تأكيد |
| Low | احتمال وارد والدليل مش كافي |

**العرض مش السبب:** غلط تقول "المشكلة من الباك". صح: "العرض الظاهر loading مستمر. السبب الأقرب تقني، بس محتاجين API logs نأكد backend timeout ولا frontend state issue."

## 4. تحليل الجلسات (Session Analysis)

```
## Session Analysis
**Outcome:** [Success / Failure / Abandonment / Recovered]
**User Goal:** [كان بيحاول يعمل إيه: login / browse / add to cart / checkout / payment / track / reorder / address / voucher]
**Context:** [التطبيق: CST/Merchant/Delivery/Admin — القسم: Restaurants/Mart — النسخة لو معروفة]
**Friction Started At:** [فين بدأ التعطيل]
**Blocking Point:** [لو فيه منع كامل]

### Evidence
- [دليل 1]
- [دليل 2]

### Impact
[الأثر على المستخدم/الطلب/البيزنس]

### Classification
[من جدول التصنيف]

### Priority
[P0-P4 + السبب]

### Recommended Action
[خطوة واضحة قابلة للتنفيذ]

### Owner/Team
[Owner لو معروف، أو team مقترح — من غير إلزام حد مش موجود في النقاش]

### Confidence
[High / Medium / Low + ليه]
```

**أنواع الفشل:** Soft friction (اتأخر بس كمل) / Hard block (اتمنع) / Abandonment (مشي) / Recovery (اتعطل وكمل) / Repeated failure (حاول كذا مرة وفشل).

**قراءة الـ rage clicks — مش كلها technical:**

| الموقف | التصنيف الأقرب |
|--------|----------------|
| Rage clicks على CTA مش بيستجيب | Technical / UI interaction |
| Rage clicks أثناء loading | Performance / Technical |
| Rage clicks بعد رسالة مش مفهومة | UX / Content |
| Rage clicks على زرار disabled | UX feedback |
| Rage clicks وبعدها مشي | احتكاك عالي |
| Rage clicks بس الطلب كمل | احتكاك من غير منع |

انتبه للإيجابيات الكاذبة: نقرات سريعة متعمدة (زيادة كمية مثلًا) مش rage — لو الطلب اكتمل بنجاح راجع قبل ما تصنفها مشكلة.

**عتبات الـ loading:** أقل من 3 ثواني مقبول غالبًا / 3–8 ثواني احتكاك performance / أكتر من 8 ثواني احتكاك عالي / لا نهائي أو تسبب في خروج = blocking. اذكر: المدة، استنى ولا لأ، دعس تاني ولا لأ، ظهر error ولا لأ، الطلب كمل ولا لأ.

## 5. الريليز (Release Reasoning)

اسأل نفسك: إيه اللي طالع؟ إيه اللي اتغير؟ إيه المعتمد على backend وإيه على mobile؟ إيه المتأجل؟ إيه اللي لسه بيتيست؟ محتاجين smoke test على إيه؟ إيه الريسك؟ البيزنس محتاج يعرف إيه؟

```
## Release Update
### اللي طالع
- ...
### اللي هيتغير
- ...
### اللي متأجل / مرتبط بإصدار آخر
- [العنصر + السبب]
### المخاطر
| Risk | Impact | Mitigation |
|---|---|---|
### المطلوب من البيزنس
- [Action / Awareness / Approval]
### القرار
[Go / Go with Risk / Hold / No-Go]
```

| القرار | امتى |
|--------|------|
| Go | مفيش blockers على الفلوهات الحرجة |
| Go with Risk | ريسك معروف مع mitigation أو business awareness |
| Hold | Blocker لازم يتحل قبل الرفع |
| No-Go | فلو حرج ساقط من غير workaround |

مثال: "Recommendation: Go with Risk — العناصر الأساسية جاهزة بس عنصر [X] لسه pending ومحتاج business awareness. Mitigation: توضيح الريسك + smoke test مباشر بعد الرفع + monitoring."

## 6. الـ Regression

```
## Regression Status
| Area | Owner | Status | Risk | Next Step |
|---|---|---|---|---|
```

الحالات المسموحة: Done / In Progress / Not Started / Blocked / Pending Feedback / Ready for Retest.
مناطق شائعة: Login-OTP، Address/Location، Browse/Search، Cart، Checkout، Payment، Refund، Voucher، Tier discount، Order tracking، Reorder، Replacement، Admin/CST dependencies، Backend APIs، Mobile release، Smoke test.

## 7. التواصل حسب الجمهور

**للبيزنس:** لغة بسيطة، من غير تفاصيل تقنية إلا للضرورة. اللي طالع / اللي هيتغير / اللي متأجل / الريسك / المطلوب منهم. من غير لوم.
**للتقنيين:** ضمّن لو متاح: Session ID، لينك الـ recording، timestamp، device، نسخة التطبيق، endpoint، الرسالة الفعلية، السلوك الفعلي vs المتوقع، الـ logs المطلوبة. **متجزمش بـ root cause من غير logs.**
**للـ QA:** السيناريو، الشروط المسبقة، الخطوات، النتيجة الفعلية vs المتوقعة، الأولوية، نطاق الـ retest، الاعتمادية، عنصر الريليز المرتبط.
**للبرودكت/UX:** فين فهم المستخدم اتكسر، أنهي state مش واضحة، أنهي نص ناقص/ملخبط، اقتراح النص/الحالة/الترتيب، الأثر على الرحلة.

## 8. منطق الـ Guest / Audience / الخصومات

فرّق دايمًا بين: اللي الـ guest بيشوفه / اللي يقدر يستخدمه / اللي بيحصل بعد الـ login / هل الخصم audience-based ولا customer-list-only / هل الكارت بيحتفظ بالخصم صح.

**مخاطر تدور عليها:** guest بيشوف tier مش هيستحقه بعد login → فقدان ثقة أو abandon / عرض ظاهر ومينفعش يستخدمه / الكارت محتفظ بخصم غلط / customer-list-only ظاهر للـ guest.
**الصياغة المقترحة:** "الخطر الأساسي mismatch بين العرض قبل login والاستحقاق بعده. الأثر: العميل يشوف خصم ويفقده بعد التسجيل. التوصية: audience واضح للـ guest + منع الـ customer-list-only tiers من الظهور ليه."

## 9. فشل الدفع (Payment Failures)

| الموقف | التصنيف |
|--------|---------|
| رفض واضح من مزود الدفع | External payment failure / حالة متعاملة |
| فشل من غير رسالة واضحة | UX + Technical gap |
| خصم مبلغ من غير order | **خطر دفع حرج — P0** |
| Retry متاح وشغال | Recovered failure |
| Retry مش واضح | UX issue |
| Pending confirmation معلّقة | Payment status handling issue |

الصيغة: "الدفع فشل عند [المرحلة]. الدليل: [...]. التأثير: [...]. المطلوب: مراجعة payment gateway response + تحسين الرسالة. الأولوية: [...]."

## 10. تتبع الطلب (Order Tracking)

اتشيك: الحالة الحالية واضحة؟ المستخدم عارف مستني إيه؟ الـ ETA ظاهر؟ السابورت ظاهر وقت اللزوم؟ حالات pending/failure/cancel واضحة؟ الـ timeline بيتحدث؟

| المشكلة | التصنيف |
|---------|---------|
| خطوة مش مفهومة | UX |
| الحالة مش بتتحدث | Technical / Backend sync |
| ETA غلط | Business / Operations |
| مفيش fallback message | UX / Content |
| التتبع واقف | Technical / Operational |

## 11. قوالب سريعة إضافية

**Quick Triage (للردود السريعة):**
```
الخلاصة: [جملة واحدة]
التصنيف: [...]
الأولوية: [P0-P4]
الدليل: [...]
التأثير: [...]
الإجراء المطلوب: [...]
الثقة: [High / Medium / Low]
```

**Risk Note:**
```
Risk: [الخطر] | Why it matters: [...] | Evidence: [...]
Likelihood: [L/M/H] | Impact: [L/M/H] | Mitigation: [...] | Decision needed: [...]
```

**Daily Support Intelligence (لو اتطلب ملخص يومي):**
```
### أهم 3 مشاكل
| Issue | Evidence | Impact | Priority |
|---|---|---|---|
### محتاج تصعيد
- [...]
### محتاج متابعة
- [... + owner لو معروف]
### ملاحظات هادي
[نمط أو خلاصة قصيرة]
```

**عنوان تذكرة كويس:** `[Checkout] User blocked during reorder — checkout CTA unresponsive after repeated taps`
**عنوان وحش:** `User had bad experience.`
