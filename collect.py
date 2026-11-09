"""Send each customer email to Claude under a rulebook of a given length, and record the reply.

Claude is called through the Claude Code CLI (`claude -p`) with no tools, no MCP servers and no
settings. The rulebook goes in the system prompt, which is where custom instructions live. The CLI
cannot set temperature, so every reply is sampled at its default and the models think adaptively.
Each call is a fresh chat.

    python3 collect.py --models claude-haiku-5-5 --arm plain --lengths 0 6 50 200 800
    python3 collect.py --models claude-sonnet-5-5 --arm emphasis --lengths 200 800

Every call is appended to results/calls.jsonl (or $RULEBOOK_CALLS). A rerun skips calls that
already have an ok record, so collection can be stopped and restarted at any point.
"""
import argparse
import hashlib
import json
import os
import subprocess
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

import prepare

ROOT = Path(__file__).parent
CALLS = Path(os.environ.get("RULEBOOK_CALLS", ROOT / "results" / "calls.jsonl"))
SCRATCH = os.environ.get("RULEBOOK_CLAUDE_CWD", os.path.join(tempfile.gettempdir(), "rulebook-claude"))
ARMS = ("plain", "emphasis", "list_first", "stacked", "amended")

_lock = threading.Lock()


def call_claude(model, system, prompt, timeout=540):
    os.makedirs(SCRATCH, exist_ok=True)
    fd, path = tempfile.mkstemp(suffix=".txt", dir=SCRATCH)
    with os.fdopen(fd, "w") as f:
        f.write(system)
    cmd = ["claude", "-p", "--tools", "", "--strict-mcp-config", "--setting-sources", "",
           "--no-session-persistence", "--output-format", "json", "--system-prompt-file", path,
           "--model", model]
    t = time.time()
    try:
        proc = subprocess.run(cmd, input=prompt, capture_output=True, text=True, timeout=timeout, cwd=SCRATCH)
    except subprocess.TimeoutExpired:
        return {"status": "error", "error": "timeout", "seconds": round(time.time() - t, 3)}
    finally:
        os.unlink(path)
    if proc.returncode != 0:
        return {"status": "error", "error": (proc.stderr or proc.stdout)[-500:], "seconds": round(time.time() - t, 3)}
    out = json.loads(proc.stdout)
    if out.get("is_error"):
        return {"status": "error", "error": str(out.get("result"))[-500:], "seconds": round(time.time() - t, 3)}
    u = out.get("usage", {})
    return {
        "status": "ok",
        "content": out.get("result"),
        "stop_reason": out.get("stop_reason"),
        "input_tokens": (u.get("input_tokens") or 0) + (u.get("cache_creation_input_tokens") or 0)
                        + (u.get("cache_read_input_tokens") or 0),
        "output_tokens": u.get("output_tokens"),
        "thinking_tokens": (u.get("output_tokens_details") or {}).get("thinking_tokens"),
        "cost_usd": out.get("total_cost_usd"),
        "seconds": round(time.time() - t, 3),
    }


def build_system(email, rules, length, arm):
    if length == 0:
        return prepare.system_prompt()
    if arm == "stacked":
        # `length` here is k, the number of always-on mention rules; the book is always 200 long.
        return prepare.system_prompt(prepare.stacked_book(email, rules, length))
    if arm == "amended":
        return prepare.system_prompt(prepare.amended_book(email, rules, length)[0])
    book, _ = prepare.rulebook(email, rules, length)
    emphasised = prepare.marked(email, book) if arm == "emphasis" else ()
    return prepare.system_prompt(book, emphasised, list_first=arm == "list_first")


def load_done():
    done = set()
    if CALLS.exists():
        for line in CALLS.read_text().splitlines():
            r = json.loads(line)
            if r.get("status") == "ok":
                done.add((r["model"], r["arm"], r["length"], r["email"], r["rep"]))
    return done


def append(rec):
    with _lock:
        CALLS.parent.mkdir(exist_ok=True)
        with CALLS.open("a") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def run_one(model, arm, length, email, rules, rep):
    system = build_system(email, rules, length, arm)
    out = call_claude(model, system, email["text"])
    rec = {"model": model, "arm": arm, "length": length, "email": email["id"], "rep": rep,
           "system_sha": hashlib.sha256(system.encode()).hexdigest()[:16],
           "at": datetime.now().isoformat(timespec="seconds"), **out}
    append(rec)
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", required=True)
    ap.add_argument("--arm", default="plain", choices=ARMS)
    ap.add_argument("--lengths", nargs="+", type=int, required=True)
    ap.add_argument("--reps", type=int, default=1)
    ap.add_argument("--workers", type=int, default=20)
    ap.add_argument("--deadline", type=float, default=520, help="stop submitting new calls after this many seconds")
    ap.add_argument("--only", nargs="*", default=None, help="only these email ids")
    args = ap.parse_args()

    root = Path(__file__).parent / "data"
    rules = json.loads((root / "rules.json").read_text())
    emails = json.loads((root / "emails.json").read_text())
    if args.only:
        emails = [e for e in emails if e["id"] in args.only]
    done = load_done()
    jobs = [(m, args.arm, n, e, rules, r)
            for r in range(args.reps) for n in args.lengths for m in args.models for e in emails
            if (m, args.arm, n, e["id"], r) not in done]
    print(f"{len(jobs)} calls to make", flush=True)
    start = time.time()
    ok = err = 0
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        pending = set()
        queue = list(jobs)
        while queue or pending:
            while queue and len(pending) < args.workers and time.time() - start < args.deadline:
                pending.add(pool.submit(run_one, *queue.pop(0)))
            if not pending:
                break
            for fut in as_completed(list(pending)):
                pending.discard(fut)
                rec = fut.result()
                if rec["status"] == "ok":
                    ok += 1
                else:
                    err += 1
                    print("error", rec["model"], rec["length"], rec["email"], rec.get("error", "")[:200], flush=True)
                break
    print(f"ok {ok}, errors {err}, not started {len(queue)}, {time.time() - start:.0f} s", flush=True)


if __name__ == "__main__":
    main()
