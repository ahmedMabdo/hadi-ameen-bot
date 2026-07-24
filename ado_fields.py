#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ado_fields.py — مصدر الحقيقة الواحد لأنواع الـ work items والبوردات والحقول.

(نقطة 4 — بيقفل F3/F12/F13 من الأوديت. أي writer جديد لازم يستورد من هنا،
وممنوع يعرّف نوع أو area path عنده لوكال.)

خريطة المسارات التلاتة (قرار آسر — التنوع مقصود، مش تناقض):

| المسار | النوع | البورد (Area Path) |
|--------|-------|---------------------|
| مشكلة/شكوى اتقالت في أي قناة من التلاتة | `Customer Issue` | Support Team |
| روتين PostHog اليومي (من التقرير الصباحي) | `Issue` (+ تاج posthog) | Support Team |
| فكرة/مطلب جديد | `Change Request` | Change Requests — أو Support Team لو فريق الدعم هيشتغل عليها |

يعني بورد الـ Support بيشيل نوعين عن قصد: `Customer Issue` (مصدره المحادثات)
و`Issue` (مصدره PostHog). قاعدة «النوع دايمًا Customer Issue» في الـ SOP نطاقها
التذاكر اللي مصدرها المحادثات فقط.

حقايق متحقق منها من ADO الحي (2026-07-24):
- `Custom.Application` مش من حقول نوع Change Request (وممنوع على Customer Issue)
  → بيتبعت لنوع `Issue` بس (F13).
- القيم المستخدمة فعليًا في الإنتاج للحقول التلاتة موثقة تحت (عينة 40 CR حديثة).
"""
import re

PROJECT = "0_Projects_Team"
AREA_SUPPORT = r"0_Projects_Team\Support Team"
AREA_CR = r"0_Projects_Team\Change Requests"
ITERATION_SUPPORT = r"0_Projects_Team\Mars_Cycle"

TYPE_CONVERSATION_ISSUE = "Customer Issue"  # مشاكل من محادثات القنوات
TYPE_POSTHOG_ISSUE = "Issue"                # روتين PostHog اليومي
TYPE_CHANGE_REQUEST = "Change Request"      # الأفكار والمطالب

# المسارات الرسمية — بالاسم عشان الكود يبقى صريح عن «مين بيكتب إيه فين وليه»
PATHS = {
    "conversation_support": {
        "type": TYPE_CONVERSATION_ISSUE, "area": AREA_SUPPORT,
        "iteration": ITERATION_SUPPORT,
        "note": "مشكلة/شكوى من محادثة — SOP السابورت (عربي + حقول منفصلة + parent)"},
    "posthog_support": {
        "type": TYPE_POSTHOG_ISSUE, "area": AREA_SUPPORT,
        "note": "روتين PostHog اليومي — تاج posthog"},
    "cr_board": {
        "type": TYPE_CHANGE_REQUEST, "area": AREA_CR,
        "note": "فكرة/مطلب — بورد الـ CR"},
    "cr_support": {
        "type": TYPE_CHANGE_REQUEST, "area": AREA_SUPPORT,
        "note": "فكرة هيشتغل عليها فريق الدعم — نفس النوع على بورد السابورت"},
}

# Custom.Application ("App - Customer") صالح لنوع Issue بس (F13)
APPLICATION_VALID_TYPES = {TYPE_POSTHOG_ISSUE}

# القيم الرسمية (من HADI_PO_CHANNEL_INSTRUCTIONS.md بعد ترميم F11) + الزيادات
# المرصودة في الإنتاج فعليًا (عينة 40 CR — 2026-07-24: "API+Desktop" و"Ang").
# الاستنتاج تحت بيختار من دول بس — مفيش اختراع قيم.
WORK_TYPES = ["API", "Automation", "Desktop", "Desktop + Mobile", "Desktop + Web",
              "Desktop + Web + Mobile", "Mobile", "Web", "Web + Mobile",
              "API+Desktop", "Ang"]
STORY_APPLICATIONS = ["Admin Web", "CST App", "Customer Web", "Delivery App",
                      "Delivery Web", "Merchant App", "Stores Web - Operator Web"]
CR_CATEGORIES = ["Admin Enhancement", "Cust App Enhancement", "Delivery Enhancement",
                 "Design Revamp", "Integration / New Feature",
                 "Merchant App Enhancement", "New Feature", "New Report",
                 "Operation Automation", "Stores Web Enhancement"]

# fallback الأخير لو الاستنتاج ملقاش أي إشارة (نفس سلوك ما قبل الإصلاح — موثق بقى)
CR_FALLBACK = {
    "Custom.WorkType": "Web",
    "Custom.StoryApplication": "Customer Web",
    "Custom.CRorStoryCategory": "New Feature",
}

# --------------------- استنتاج حقول الـ CR من النص (F12) ---------------------
_RX_ADMIN = re.compile(r"أدمن|ادمن|لوحة التحكم|\badmin\b|dashboard", re.IGNORECASE)
_RX_MERCHANT = re.compile(r"تاجر|التاجر|التجار|مطعم|المطاعم|merchant|\bstores?\b|ستورز|المحل",
                          re.IGNORECASE)
_RX_DELIVERY = re.compile(r"دليفري|كابتن|الكباتن|طيار|سائق|السواقين|deliver|driver|courier",
                          re.IGNORECASE)
_RX_CST = re.compile(r"تطبيق العميل|ابليكيشن|أبلكيشن|الأبلكيشن|\bcst\b|كستمر", re.IGNORECASE)
_RX_MOBILE = re.compile(r"موبايل|أندرويد|اندرويد|android|\bios\b|آيفون|ايفون|iphone|"
                        r"\bapp\b|أب ستور|بلاي ستور|store version", re.IGNORECASE)
_RX_WEB = re.compile(r"الويب|ويب سايت|الموقع|website|\bweb\b|المتصفح|browser", re.IGNORECASE)
_RX_API = re.compile(r"\bapi\b|باك ?اند|باك ?إند|الباك\b|backend|endpoint|"
                     r"انتجريشن|integration|\bwebhook\b", re.IGNORECASE)
_RX_DESIGN = re.compile(r"تصميم|التصميم|ديزاين|\bui\b|\bux\b|revamp|ريفامب", re.IGNORECASE)


def infer_cr_fields(text):
    """استنتاج WorkType/StoryApplication/CRorStoryCategory من نص الفكرة (F12).

    بيرجع dict فيه الحقول التلاتة + "_inferred": True لو في إشارة حقيقية اتلقطت،
    وإلا الـ fallback القديم مع "_inferred": False (عشان اللوج يفرق بينهم).
    الاستنتاج بيختار من القيم المرصودة في الإنتاج بس — مفيش اختراع قيم جديدة."""
    t = text or ""
    admin = bool(_RX_ADMIN.search(t))
    merchant = bool(_RX_MERCHANT.search(t))
    delivery = bool(_RX_DELIVERY.search(t))
    cst = bool(_RX_CST.search(t))
    mobile = bool(_RX_MOBILE.search(t))
    web = bool(_RX_WEB.search(t))
    api = bool(_RX_API.search(t))
    design = bool(_RX_DESIGN.search(t))

    app = category = None
    if admin:
        app, category = "Admin Web", "Admin Enhancement"
    elif merchant:
        app, category = "Merchant App", "Merchant App Enhancement"
    elif delivery:
        app = "Delivery Web" if (web and not mobile) else "Delivery App"
        category = "Delivery Enhancement"
    elif cst or mobile:
        app, category = "CST App", "Cust App Enhancement"
    elif web:
        app, category = "Customer Web", "New Feature"

    if app is None and not api:
        out = dict(CR_FALLBACK)
        out["_inferred"] = False
        return out

    if design:
        category = "Design Revamp"

    if mobile and web:
        work_type = "Web + Mobile"
    elif mobile or app in ("CST App", "Merchant App", "Delivery App"):
        work_type = "Mobile"
    elif api and not (web or admin):
        work_type = "API"
    else:
        work_type = "Web"

    return {
        "Custom.WorkType": work_type,
        "Custom.StoryApplication": app or CR_FALLBACK["Custom.StoryApplication"],
        "Custom.CRorStoryCategory": category or CR_FALLBACK["Custom.CRorStoryCategory"],
        "_inferred": True,
    }
