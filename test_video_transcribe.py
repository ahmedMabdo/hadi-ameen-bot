#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""اختبار مسار تفريغ صوت الفيديو في discord_bot.py — من غير ديسكورد ومن غير توكن.

    python3 test_video_transcribe.py                 # الفحوصات الأساسية
    python3 test_video_transcribe.py --speech a.mp4  # + تفريغ حقيقي لفيديو عندك

ليه ملف لوحده: discord_bot.py بيطلب DISCORD_BOT_TOKEN و ALLOWED_USER_IDS وقت
الاستيراد وبيستورد discord، فماينفعش يتستورد في اختبار. الحل: بنقص تعريفات دوال
الويسبر بالـ ast وننفّذها في namespace فيه الجلوبالز المطلوبة بس — يعني بنختبر
الكود الحقيقي زي ما هو، مش نسخة منه بتقع من المزامنة.

الفحوصات بتتدرّج مع البيئة:
  • ffmpeg ناقص           → بيقول ويخرج (مفيش حاجة تتقاس)
  • faster-whisper ناقص   → بيتأكد إن التدهور بيحصل بهدوء (وده المطلوب فعلًا)
  • الاتنين موجودين       → بيشغّل تفريغ حقيقي على نغمة وعلى فيديوك لو بعتّه
"""
import argparse
import ast
import asyncio
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

BASE = Path(__file__).resolve().parent
WANT = {"_extract_audio", "_load_whisper", "_transcribe",
        "_transcribe_video", "_get_whisper_lock"}


def load_functions(src_path):
    """بيقص دوال الويسبر من discord_bot.py وينفّذها في namespace معزول."""
    source = Path(src_path).read_text(encoding="utf-8")
    lines = source.splitlines(keepends=True)
    chunks, found = [], set()
    for node in ast.parse(source).body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in WANT:
            chunks.append("".join(lines[node.lineno - 1:node.end_lineno]))
            found.add(node.name)
    missing = WANT - found
    if missing:
        sys.exit(f"ERROR: الدوال دي مش موجودة في {src_path}: {sorted(missing)}")
    ns = {
        "asyncio": asyncio, "subprocess": subprocess, "Path": Path, "os": os,
        "WHISPER_ENABLED": True,
        "WHISPER_MODEL_NAME": os.getenv("HADI_WHISPER_MODEL", "small"),
        "WHISPER_DEVICE": os.getenv("HADI_WHISPER_DEVICE", "cpu"),
        "WHISPER_COMPUTE": os.getenv("HADI_WHISPER_COMPUTE", "int8"),
        "WHISPER_MAX_SECONDS": 300, "WHISPER_MAX_CHARS": 4000,
        "_whisper_model": None, "_whisper_load_failed": False, "_whisper_lock": None,
    }
    exec("".join(chunks), ns)
    return ns


def make_fixtures(tmp):
    """فيديو صامت + فيديو بنغمة — بيتعملوا بـ ffmpeg مفيش ملفات في الريبو."""
    silent, tone = tmp / "silent.mp4", tmp / "tone.mp4"
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=blue:s=320x240:d=3",
         "-c:v", "libx264", "-pix_fmt", "yuv420p", str(silent)],
        capture_output=True, check=True, timeout=120)
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=red:s=320x240:d=3",
         "-f", "lavfi", "-i", "sine=frequency=440:duration=3",
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest",
         str(tone)],
        capture_output=True, check=True, timeout=120)
    return silent, tone


async def run(ns, tmp, speech_file):
    ok = True

    def check(label, cond):
        nonlocal ok
        print(("PASS  " if cond else "FAIL  ") + label)
        ok = ok and bool(cond)

    silent, tone = make_fixtures(tmp)

    # (1) فيديو صامت: لازم يقصّر قبل ما يحمّل الموديل أصلًا
    wav = Path(f"{silent}.wav")
    check("فيديو صامت: _extract_audio بترجّع False",
          ns["_extract_audio"](silent, wav) is False)
    check("فيديو صامت: الموديل مااتحمّلش عالفاضي", ns["_whisper_model"] is None)
    check("فيديو صامت: مفيش ملاحظة للبرومبت",
          await ns["_transcribe_video"](silent, "silent.mp4") == "")

    # (2) استخراج الصوت بالصيغة اللي whisper بيتوقعها
    wav = Path(f"{tone}.wav")
    check("فيديو بصوت: _extract_audio بترجّع True",
          ns["_extract_audio"](tone, wav) is True)
    hdr = wav.read_bytes()[:44] if wav.exists() else b""
    check("الصوت 16kHz مونو PCM",
          hdr[:4] == b"RIFF"
          and int.from_bytes(hdr[24:28], "little") == 16000
          and int.from_bytes(hdr[22:24], "little") == 1)
    wav.unlink(missing_ok=True)

    # (3) التفريغ الحقيقي — أو مسار التدهور لو الموديل مش متاح
    note = await ns["_transcribe_video"](tone, "tone.mp4 (0.0MB)")
    if ns["_whisper_model"] is None:
        print("\nINFO  faster-whisper مش متاح هنا — بنختبر التدهور الهادي بدل التفريغ")
        check("الموديل مش متاح: بيرجّع فاضي من غير ما يرمي", note == "")
        check("العطل اتسجل عشان مايكررش المحاولة كل رسالة",
              ns["_whisper_load_failed"] is True)
        check("النداء التاني بيفضل هادي",
              await ns["_transcribe_video"](tone, "tone.mp4") == "")
    else:
        # نغمة نقية مش كلام: الـ VAD المفروض يبلعها. لو رجّع نص، يبقى الموديل
        # بيهلوس على صوت مش كلام — وده بيوصل لهادي كأنه كلام حقيقي.
        check("نغمة مش كلام: مفيش هلوسة (الـ VAD شغال)", note == "")
    check("مفيش ملف wav متسايب", not Path(f"{tone}.wav").exists())

    # (4) مفتاح الإطفاء
    ns["WHISPER_ENABLED"] = False
    check("HADI_WHISPER_ENABLED=0 بيوقف التفريغ",
          await ns["_transcribe_video"](tone, "tone.mp4") == "")
    ns["WHISPER_ENABLED"] = True

    # (5) ملف مش موجود مايكسرش مسار الرسالة
    check("فيديو مش موجود: بيرجّع فاضي من غير استثناء",
          await ns["_transcribe_video"](tmp / "nope.mp4", "nope.mp4") == "")

    # (6) فيديو كلام حقيقي لو المستخدم بعته
    if speech_file:
        src = Path(speech_file)
        if not src.is_file():
            sys.exit(f"ERROR: الملف مش موجود: {src}")
        note = await ns["_transcribe_video"](src, f"{src.name} (test)")
        print(f"\n--- ناتج التفريغ ---\n{note or '(فاضي)'}\n--------------------")
        check("فيديو بكلام: طلعت ملاحظة تفريغ", note.startswith("- تفريغ صوت"))
        check("الملاحظة فيها اسم الملف", src.name in note)
        check("الملاحظة فيها اللغة المكتشفة", "لغة مكتشفة" in note)
        check("النص متقوّس عشان يتفصل عن الملاحظات", "«" in note and "»" in note)
        check("مفيش ملف wav متسايب جنب فيديوك", not Path(f"{src}.wav").exists())
    else:
        print("SKIP  مفيش --speech — التفريغ الحقيقي لفيديو كلام اتخطى")

    print("\n" + ("ALL PASS" if ok else "THERE ARE FAILURES"))
    return 0 if ok else 1


def main():
    p = argparse.ArgumentParser(description="اختبار تفريغ صوت الفيديو")
    p.add_argument("--speech", help="فيديو فيه كلام حقيقي لاختبار التفريغ فعليًا")
    p.add_argument("--source", default=str(BASE / "discord_bot.py"))
    args = p.parse_args()

    if not (shutil.which("ffmpeg") and shutil.which("ffprobe")):
        sys.exit("ERROR: ffmpeg/ffprobe مش متثبتين — مفيش حاجة تتقاس")

    ns = load_functions(args.source)
    with tempfile.TemporaryDirectory(prefix="hadi_whisper_test_") as tmp:
        return asyncio.run(run(ns, Path(tmp), args.speech))


if __name__ == "__main__":
    sys.exit(main())
