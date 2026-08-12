#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""اختبارات كشف الرد على نقاط المتابعة (نقطة آسر: النبض ما يفضلش يفكّر بنقطة اترد عليها).

بيغطي routines_common.find_reply_since / snowflake_after / channel_id_for_digest —
المنطق اللي النبض بيستخدمه عشان يقفل النقطة لو حد ردّ عليها في القناة.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import routines_common as rc  # noqa: E402


def _fake_pages(*pages):
    """يرجّع دالة بديلة لـ api_get بترجّع الصفحات دي بالترتيب (وبعدين []) ."""
    state = {"i": 0}

    def fake_api_get(path, params=None):
        i = state["i"]
        state["i"] += 1
        return list(pages[i]) if i < len(pages) else []

    return fake_api_get


def _msg(mid, content="", bot=False, reply_to=None, mentions=None):
    m = {"id": str(mid), "author": {"bot": bot}, "content": content,
         "mentions": [{"id": str(u)} for u in (mentions or [])]}
    if reply_to is not None:
        m["message_reference"] = {"message_id": str(reply_to)}
    return m


# --------------------------------------------------------------- reply / mention
def test_detects_direct_reply_to_source():
    rc.api_get = _fake_pages([_msg(1001, "تمام اتظبط", reply_to="999")])
    hit = rc.find_reply_since("123", 0, owner_id="", source_msg_id="999")
    assert hit and hit["id"] == "1001"


def test_detects_owner_mention_in_list():
    rc.api_get = _fake_pages([_msg(1002, "يا جماعة", mentions=["555"])])
    hit = rc.find_reply_since("123", 0, owner_id="555", source_msg_id="")
    assert hit and hit["id"] == "1002"


def test_detects_owner_mention_in_content():
    rc.api_get = _fake_pages([_msg(1003, "<@555> شوفلي دي")])
    hit = rc.find_reply_since("123", 0, owner_id="555", source_msg_id="")
    assert hit and hit["id"] == "1003"


# --------------------------------------------------------------- سلبيات
def test_ignores_bot_messages():
    # البوت (هادي) نفسه بيمنشن المسؤول في النبض — ده ماينفعش يقفل النقطة
    rc.api_get = _fake_pages([_msg(1004, "<@555>", bot=True, reply_to="999")])
    assert rc.find_reply_since("123", 0, owner_id="555", source_msg_id="999") is None


def test_unrelated_messages_no_hit():
    rc.api_get = _fake_pages([_msg(1005, "كلام تاني خالص"),
                              _msg(1006, "<@777> ده حد تاني", mentions=["777"])])
    assert rc.find_reply_since("123", 0, owner_id="555", source_msg_id="999") is None


def test_no_channel_or_no_signal_returns_none():
    rc.api_get = _fake_pages([_msg(1007, "<@555>", mentions=["555"])])
    assert rc.find_reply_since("", 0, owner_id="555", source_msg_id="999") is None
    assert rc.find_reply_since("123", 0, owner_id="", source_msg_id="") is None


# --------------------------------------------------------------- الترقيم
def test_anchor_uses_source_msg_id_when_present():
    """المرساة لازم تكون الرسالة نفسها (after=message_id) لما تكون متاحة."""
    seen = {}

    def spy(path, params=None):
        seen["after"] = (params or {}).get("after")
        return []

    rc.api_get = spy
    rc.find_reply_since("123", 999999, owner_id="555", source_msg_id="777")
    assert seen["after"] == "777", seen


def test_anchor_falls_back_to_snowflake_without_source():
    seen = {}

    def spy(path, params=None):
        seen["after"] = (params or {}).get("after")
        return []

    rc.api_get = spy
    rc.find_reply_since("123", 42, owner_id="555", source_msg_id="")
    assert seen["after"] == "42", seen


def test_paginates_until_hit():
    page1 = [_msg(1000 + n, "بلا") for n in range(100)]          # 100 من غير رد
    page2 = [_msg(2000, "أهو الرد", reply_to="999")]             # الرد في الصفحة 2
    rc.api_get = _fake_pages(page1, page2)
    hit = rc.find_reply_since("123", 0, owner_id="", source_msg_id="999", max_pages=5)
    assert hit and hit["id"] == "2000"


def test_pagination_bounded_by_max_pages():
    # كل صفحة مليانة 100 من غير رد؛ max_pages=1 يعني نبص صفحة واحدة بس
    page = [_msg(1000 + n, "بلا") for n in range(100)]
    rc.api_get = _fake_pages(page, [_msg(2000, "رد متأخر", reply_to="999")])
    assert rc.find_reply_since("123", 0, source_msg_id="999", max_pages=1) is None


# --------------------------------------------------------------- snowflake
def test_snowflake_monotonic_and_after_epoch():
    early = rc.snowflake_after("2020-01-01")
    late = rc.snowflake_after("2026-01-01")
    assert 0 < early < late


def test_snowflake_before_epoch_is_zero():
    assert rc.snowflake_after("2000-01-01") == 0


def test_snowflake_bad_input_is_zero():
    assert rc.snowflake_after("مش تاريخ") == 0


# --------------------------------------------------------------- channel routing
def test_channel_id_for_digest_default():
    for env in ("SUPPORT_CHANNEL_ID", "ISSUES_CHANNEL_ID"):
        os.environ.pop(env, None)
    assert rc.channel_id_for_digest("followup") == "1179369466279235584"


def test_channel_id_for_digest_env_override():
    os.environ["SUPPORT_CHANNEL_ID"] = "42"
    try:
        assert rc.channel_id_for_digest("followup") == "42"
    finally:
        os.environ.pop("SUPPORT_CHANNEL_ID", None)


def test_channel_id_for_unknown_digest():
    assert rc.channel_id_for_digest("nope") is None


def _run_all():
    fns = [v for k, v in sorted(globals().items())
           if k.startswith("test_") and callable(v)]
    passed = 0
    for fn in fns:
        fn()
        print(f"PASS  {fn.__name__}")
        passed += 1
    print(f"\nALL PASS ({passed} tests)")


if __name__ == "__main__":
    _run_all()
