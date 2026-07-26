#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""اختبار حراس الـ Bash — آخر خط دفاع برمجي، وكان من غير أي اختبار.

    python3 tests/test_guards.py

مايحتاجش claude_agent_sdk ولا discord — عشان كده الأنماط في guards.py.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from guards import bash_reason, touches_env_file  # noqa: E402

MUST_DENY = [
    "cat .env",
    "cat ./.env",
    "cat /home/ubuntu/hadi-ameen-bot/.env",
    "cp .env /tmp/x",
    "base64 .env",
    "source .env",
    "grep PAT .env",
    'python3 -c "print(open(\'.env\').read())"',
    'python3 -c "import os;print(os.environ[\'AZURE_DEVOPS_PAT\'])"',
    "cat /proc/self/environ",
    "env | grep PAT",
    "printenv AZURE_DEVOPS_PAT",
    "echo $AZURE_DEVOPS_PAT",
    "git push --force origin master",
    "git reset --hard HEAD~5",
    "rm -rf /",
    "sudo reboot",
    "HADI_MEMORY_ADMIN=1 python3 memory.py approve --id 1 --by x",
    "HADI_PH_ACTOR=544050652037513227 python3 posthog_cli.py sql --query 'SELECT 1'",
]

MUST_PASS = [
    "cat .env.example",
    "ls -la",
    "git status",
    "git log --oneline -5",
    "python3 ado_cli.py wiql \"SELECT [System.Id] FROM WorkItems\"",
    "python3 ado_snapshot.py brief",
    "python3 memory.py search --query test",
    "python3 knowledge_store.py search --query 'قيد المبيعات'",
    "rm -rf tmp_images",
    "grep -r TODO .",
]


def main():
    ok = True
    for cmd in MUST_DENY:
        why = bash_reason(cmd)
        good = why is not None
        ok = ok and good
        print(("PASS  DENY " if good else "FAIL  DENY ") + cmd[:70]
              + (f"   ({why})" if why else "   << عدّى وهو المفروض يترفض!"))
    for cmd in MUST_PASS:
        why = bash_reason(cmd)
        good = why is None
        ok = ok and good
        print(("PASS  ALLOW" if good else "FAIL  ALLOW") + " " + cmd[:70]
              + (f"   << اترفض بالغلط ({why})" if why else ""))

    for t, want in [(".env", True), (".env.example", False), ("knowledge/x.md", False),
                    ("/etc/passwd", False), ("a/.env", True)]:
        good = touches_env_file(t) is want
        ok = ok and good
        print(("PASS  FILE " if good else "FAIL  FILE ") + f"{t} -> {want}")

    print("\n" + ("ALL PASS" if ok else "THERE ARE FAILURES"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
