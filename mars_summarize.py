#!/usr/bin/env python3
"""Mars Team daily summary — fetches last 24h messages and posts a count."""
import subprocess, json, sys
from datetime import datetime

SCRIPT = "/home/ubuntu/hadi-ameen-bot/discord_marsteam.py"
DRY_RUN = "--dry-run" in sys.argv

result = subprocess.run([sys.executable, SCRIPT, "fetch"], capture_output=True, text=True)
if result.returncode != 0:
    print(f"Fetch failed: {result.stderr}", file=sys.stderr)
    sys.exit(1)

try:
    messages = json.loads(result.stdout)
except Exception as e:
    print(f"JSON parse error: {e}", file=sys.stderr)
    sys.exit(1)

count = len(messages)
if count == 0:
    print("No messages in last 24h - skipping summary")
    sys.exit(0)

seen = set()
authors = []
for m in messages:
    a = m.get("author", {})
    if isinstance(a, dict):
        name = a.get("global_name") or a.get("username") or "?"
    else:
        name = str(a)
    if name not in seen:
        seen.add(name)
        authors.append(name)

hour = datetime.now().hour
period = "صباحاً" if hour < 12 else "مساءً"
date_str = datetime.now().strftime("%Y-%m-%d")
summary = (
    f"📊 ملخص Mars Team — {date_str} {period}\n"
    f"عدد الرسائل: {count} | المشاركون: {{', '.join(authors[:8])}"
)

cmd = [sys.executable, SCRIPT] + (["--dry-run"] if DRY_RUN else []) + ["post", summary]
r2 = subprocess.run(cmd, capture_output=True, text=True)
if r2.returncode != 0:
    print(f"Post failed: {r2.stderr}", file=sys.stderr)
    sys.exit(1)

print(f"Summary posted: {count} msgs, {len(authors)} authors")
