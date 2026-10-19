#!/usr/bin/env python3
"""verify.py — машинная проверка артефактов AgentOS. stdlib-only.

Usage:
  python3 verify.py <file> [...]     проверить артефакт(ы), exit 0 = Passed
  python3 verify.py --staged         проверить git staged-файлы (для pre-commit)
  python3 verify.py --machine ...    префиксы ERR_/OK_ в выводе (для скриптов)
  python3 verify.py --selftest       прогнать good/bad фикстуры

Вердикт: Passed = 0 fail И 0 skipped. fail(retryable=False) — не ретраить,
сразу block (секреты, path-jail). skipped = проверка не смогла выполниться,
это НЕ успех (фаза 4a: «не смогли проверить» != «успех»).
"""
import os
import py_compile
import re
import subprocess
import sys
import tempfile
from pathlib import Path

MIN_SIZE = 16  # байт; меньше = заглушка

# Корень path-jail (фаза 4c): артефакт обязан лежать внутри. Только для режима
# проверки артефактов; --staged не джейлится (verify-gate чужих репо).
def jail_root() -> Path:
    return Path(os.environ.get("AGENTOS_WORKSPACE",
                               Path(__file__).resolve().parent / "workspace")).resolve()

SECRET_PATTERNS = [
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\bghp_[A-Za-z0-9]{36}"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{22,}"),
    re.compile(r"\bsk-[A-Za-z0-9]{20,}"),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]+"),
    # фаза 4d, порт из SapienXai redaction.ts:
    re.compile(r"[?&](api_key|apikey|token|secret|password|access_token)=\S{8,}", re.I),
    re.compile(r"(?im)^\s*(api_key|apikey|secret_?key|password|passwd|access_token)"
               r"\s*[:=]\s*['\"]?[A-Za-z0-9_-]{8,}"),
]

# (status, retryable, msg); status: fail | skipped
results = []


def fail(path, msg, retryable=True):
    results.append(("fail", retryable, f"{path}: {msg}"))


def skip(path, msg):
    results.append(("skipped", True, f"{path}: {msg}"))


def redact(s):
    return re.sub(r"[A-Za-z0-9_-]{8,}", lambda m: m.group(0)[:4] + "…", s)


def verify(path: Path, check_size: bool = True, jail: bool = False) -> None:
    if jail:
        rp = path.resolve()
        if not str(rp).startswith(str(jail_root()) + os.sep):
            fail(path, f"вне workspace {jail_root()} — path-jail", retryable=False)
            return
    if not path.is_file():
        fail(path, "не существует (или не файл)")
        return
    try:
        data = path.read_bytes()
    except OSError as e:
        skip(path, f"нечитаем: {e}")
        return
    text = data.decode("utf-8", errors="replace")
    if check_size and len(data) < MIN_SIZE:
        fail(path, f"слишком мал ({len(data)}B < {MIN_SIZE}B) — заглушка?")
        return
    for pat in SECRET_PATTERNS:
        m = pat.search(text)
        if m:
            fail(path, f"секрет в файле: {redact(m.group(0))} (не ретраить)",
                 retryable=False)
    if path.suffix == ".html":
        low = text.lower()
        if "</html>" not in low:
            fail(path, "HTML без </html>")
        if "<title>" not in low:
            fail(path, "HTML без <title>")
    elif path.suffix == ".py":
        try:
            py_compile.compile(str(path), cfile=tempfile.mktemp(), doraise=True)
        except py_compile.PyCompileError as e:
            fail(path, f"py_compile: {e}")
        except OSError as e:
            skip(path, f"py_compile не смог выполниться: {e}")


def staged_files():
    out = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
        capture_output=True, text=True, check=True,
    ).stdout
    return [Path(p) for p in out.splitlines() if Path(p).is_file()]


def selftest():
    base = Path(tempfile.mkdtemp(prefix="verify-selftest-"))
    os.environ["AGENTOS_WORKSPACE"] = str(base)  # jail = база фикстур
    good = {
        "ok.html": "<html><head><title>Hi</title></head><body>x</body></html>",
        "ok.py": "x = 41\nprint(x + 1)\n",
        "ok.txt": "just some plain text artifact\n",
    }
    bad = {
        "empty.html": "<html></html>",
        "bad.py": "def f(:\n",
        "tiny.txt": "ab",
        "secret.txt": "aws_key = AKIAIOSFODNN7EXAMPLE\n",
        "missing.py": None,  # не создаём
        # фаза 4d: новые классы секретов
        "query.txt": "curl https://x.io/r?token=abcdefgh12345678\n",
        "assign.txt": "password = hunter2hunter2x\n",
    }
    for name, content in good.items():
        (base / name).write_text(content)
    for name, content in bad.items():
        if content is not None:
            (base / name).write_text(content)
    # фаза 4c: симлинк наружу jail
    (base / "escape.txt").symlink_to("/etc/passwd")
    bad["escape.txt"] = None
    # good должны проходить по одному
    for name in good:
        results.clear()
        verify(base / name, jail=True)
        assert not results, f"good {name} не прошёл: {results}"
    # bad должны падать
    for name in bad:
        results.clear()
        verify(base / name, jail=True)
        assert results, f"bad {name} прошёл, а не должен"
    # секрет и path-jail — не ретраибельные
    for name in ("secret.txt", "escape.txt"):
        results.clear()
        verify(base / name, jail=True)
        assert results[0][0] == "fail" and not results[0][1], f"{name} должен быть fail+!retryable"
    # 4a: skipped существует и это не успех
    noread = base / "noread.txt"
    noread.write_text("secret stuff here\n")
    noread.chmod(0o000)
    results.clear()
    verify(noread, jail=True)
    assert results and results[0][0] == "skipped", "нечитаемый файл должен дать skipped"
    noread.chmod(0o644)
    # 4e: после Passed артефакт становится read-only (через CLI-режим)
    rc = subprocess.run([sys.executable, str(Path(__file__).resolve()),
                         str(base / "ok.txt")], capture_output=True, text=True)
    assert rc.returncode == 0, f"CLI verify ok.txt: {rc.stdout}{rc.stderr}"
    assert (base / "ok.txt").stat().st_mode & 0o222 == 0, "Passed-артефакт должен быть read-only"
    print("SELFTEST PASSED")


def main():
    args = sys.argv[1:]
    machine = "--machine" in args
    args = [a for a in args if a != "--machine"]
    if not args:
        print(__doc__)
        return 2
    if args[0] == "--selftest":
        selftest()
        return 0
    staged = args[0] == "--staged"
    paths = staged_files() if staged else [Path(a) for a in args]
    if not paths:
        print("нет файлов для проверки")
        return 0
    check_size = not staged  # размер = проверка артефакта, не коммита
    for p in paths:
        verify(p, check_size=check_size, jail=not staged)

    def out(kind, msg):
        if machine:
            pre = {"fail": "ERR_VERIFY_FAIL", "noretry": "ERR_VERIFY_NORETRY",
                   "skip": "ERR_VERIFY_SKIP"}[kind]
            print(f"{pre}: {msg}")
        else:
            print(" -", msg)

    if results:
        for status, retryable, msg in results:
            if status == "skipped":
                out("skip", msg)
            else:
                out("fail" if retryable else "noretry", msg)
        n = sum(1 for s, _, _ in results if s == "fail")
        print(f"ERR_VERIFY_FAILED: {n} fail, {len(results) - n} skipped" if machine
              else f"FAILED ({n} fail, {len(results) - n} skipped)")
        return 1
    for p in paths:  # 4e: write-once принятого артефакта
        try:
            os.chmod(p, 0o444)
        except OSError:
            pass  # не смогли заморозить — не повод фейлить принятое
    print(f"OK_VERIFY_PASSED: {len(paths)} файл(ов)" if machine
          else f"Passed ({len(paths)} файл(ов))")
    return 0


if __name__ == "__main__":
    sys.exit(main())
