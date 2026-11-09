"""Score every reply and write results/summary.json. Standard library only; no key needed."""
import json
import random
from collections import defaultdict
from pathlib import Path

import prepare
import score

ROOT = Path(__file__).parent
MODELS = ["claude-haiku-5-5", "claude-sonnet-5-5", "claude-opus-5-5"]
SHORT = {"claude-haiku-5-5": "Haiku 5.5", "claude-sonnet-5-5": "Sonnet 5.5", "claude-opus-5-5": "Opus 5.5"}
N_BOOT = 10000


def load(path=None):
    path = Path(path or ROOT / "results" / "calls.jsonl")
    rows = [json.loads(x) for x in path.read_text().splitlines()]
    return [r for r in rows if r.get("status") == "ok"]


def score_all(calls):
    """One record per reply, one sub-record per rule that mattered to it."""
    rules = json.loads((ROOT / "data" / "rules.json").read_text())
    emails = {e["id"]: e for e in json.loads((ROOT / "data" / "emails.json").read_text())}
    by_id = {r["id"]: r for r in rules}
    always = [r for r in rules if r["kind"] == "always"]
    out = []
    for c in calls:
        e = emails[c["email"]]
        reply = score.email_part(c["content"] or "", c["arm"] == "list_first")
        targets = [by_id[t] for t in e["targets"]]
        book, thirds = prepare.rulebook(e, rules, c["length"]) if c["length"] else ([], {})
        marked = prepare.marked(e, book) if c["arm"] == "emphasis" else set()
        rec = {"model": c["model"], "arm": c["arm"], "length": c["length"], "email": c["email"],
               "reply": reply, "cost": c["cost_usd"], "in": c["input_tokens"], "out": c["output_tokens"],
               "targets": [], "always": []}
        for t in targets:
            item = {"id": t["id"], "kind": t["kind"], "ok": score.check_rule(t, reply, e["order"]),
                    "third": thirds.get(t["id"]), "marked": t["id"] in marked}
            if t["kind"] == "wording":
                item["term"], item["no_ban"] = score.wording_parts(t, reply)
            if t["kind"] == "line":
                item["desk_said"] = t["token"] in reply
            rec["targets"].append(item)
        for a in always:
            rec["always"].append({"id": a["id"], "ok": score.check_rule(a, reply, e["order"]),
                                  "third": thirds.get(a["id"]), "marked": a["id"] in marked})
        rec["stray_known"], rec["stray_invented"] = score.stray_tokens(reply, targets, book) if book else ([], [])
        rec["all_six"] = all(x["ok"] for x in rec["targets"]) and all(x["ok"] for x in rec["always"])
        out.append(rec)
    return out


def mean(xs):
    return sum(xs) / len(xs) if xs else float("nan")


def boot_ci(per_email, rng_seed=7):
    """Percentile interval on the mean across emails."""
    if not per_email:
        return (float("nan"), float("nan"))
    rng = random.Random(rng_seed)
    n = len(per_email)
    stats = sorted(mean([per_email[rng.randrange(n)] for _ in range(n)]) for _ in range(N_BOOT))
    return stats[int(0.025 * N_BOOT)], stats[int(0.975 * N_BOOT) - 1]


def pick(recs, model=None, arm=None, length=None):
    return [r for r in recs if (model is None or r["model"] == model) and (arm is None or r["arm"] == arm)
            and (length is None or r["length"] == length)]


def applied(rec, which="targets", test=lambda x: True):
    items = [x for x in rec[which] if test(x)]
    return mean([x["ok"] for x in items]) if items else None


def rate_table(recs, arm="plain", lengths=(0, 6, 50, 200, 800), which="targets", test=lambda x: True):
    table = {}
    for m in MODELS:
        table[m] = {}
        for L in lengths:
            per = [v for v in (applied(r, which, test) for r in pick(recs, m, arm, L)) if v is not None]
            table[m][L] = {"rate": mean(per), "ci": boot_ci(per), "n_replies": len(per)}
    return table


def paired_drop(recs, model, length, base=6, arm="plain"):
    """Mean rate at `base` minus rate at `length`, paired by email, with a bootstrap interval."""
    a = {r["email"]: applied(r) for r in pick(recs, model, arm, base)}
    b = {r["email"]: applied(r) for r in pick(recs, model, arm, length)}
    diffs = [a[e] - b[e] for e in a if e in b]
    return {"drop": mean(diffs), "ci": boot_ci(diffs)}


def summarise(recs):
    s = {}
    s["calls"] = len(recs)
    s["cost_by_model"] = {m: sum(r["cost"] or 0 for r in pick(recs, m)) for m in MODELS}
    s["cost_total"] = sum(r["cost"] or 0 for r in recs)
    s["applied"] = rate_table(recs)
    s["always"] = rate_table(recs, which="always")
    s["drops"] = {m: {L: paired_drop(recs, m, L) for L in (50, 200, 800)} for m in MODELS}
    s["kinds"] = {k: rate_table(recs, test=lambda x, k=k: x["kind"] == k) for k in ("code", "line", "wording")}
    s["all_six"] = {m: {L: mean([r["all_six"] for r in pick(recs, m, "plain", L)]) for L in (6, 50, 200, 800)} for m in MODELS}
    s["thirds"] = {m: {L: {t: mean([x["ok"] for r in pick(recs, m, "plain", L) for x in r["targets"] if x["third"] == t])
                           for t in (0, 1, 2)} for L in (200, 800)} for m in MODELS}
    s["always_each"] = {m: {L: {a: mean([x["ok"] for r in pick(recs, m, "plain", L) for x in r["always"] if x["id"] == a])
                                for a in ("always-signoff", "always-sorry", "always-order")}
                            for L in (0, 6, 50, 200, 800)} for m in MODELS}
    s["stray_known"] = {m: {L: mean([bool(r["stray_known"]) for r in pick(recs, m, "plain", L)]) for L in (6, 50, 200, 800)} for m in MODELS}
    s["stray_invented"] = {m: {L: mean([bool(r["stray_invented"]) for r in pick(recs, m, "plain", L)]) for L in (6, 50, 200, 800)} for m in MODELS}
    s["line_buried"] = {m: {L: mean([x["desk_said"] and not x["ok"] for r in pick(recs, m, "plain", L) for x in r["targets"] if x["kind"] == "line"])
                            for L in (6, 50, 200, 800)} for m in MODELS}
    s["wording_parts"] = {m: {L: {"no_term": mean([not x["term"] for r in pick(recs, m, "plain", L) for x in r["targets"] if x["kind"] == "wording"]),
                                   "banned_used": mean([not x["no_ban"] for r in pick(recs, m, "plain", L) for x in r["targets"] if x["kind"] == "wording"])}
                              for L in (6, 50, 200, 800)} for m in MODELS}
    s["emphasis"] = emphasis(recs)
    return s


def emphasis(recs):
    out = {}
    for m in MODELS:
        out[m] = {}
        for L in (200, 800):
            plain = {r["email"]: r for r in pick(recs, m, "plain", L)}
            marked_diffs, other_diffs, always_marked = [], [], []
            for r in pick(recs, m, "emphasis", L):
                base = plain.get(r["email"])
                if not base:
                    continue
                base_ok = {x["id"]: x["ok"] for x in base["targets"]}
                base_a = {x["id"]: x["ok"] for x in base["always"]}
                marked_diffs.append(mean([x["ok"] - base_ok[x["id"]] for x in r["targets"] if x["marked"]]))
                other_diffs.append(mean([x["ok"] - base_ok[x["id"]] for x in r["targets"] if not x["marked"]]))
                always_marked.append(mean([x["ok"] - base_a[x["id"]] for x in r["always"] if x["marked"]]))
            out[m][L] = {
                "marked_gain": mean(marked_diffs), "marked_ci": boot_ci(marked_diffs),
                "unmarked_gain": mean(other_diffs), "unmarked_ci": boot_ci(other_diffs),
                "always_marked_gain": mean(always_marked), "n": len(marked_diffs),
                "applied_emph": mean([applied(r) for r in pick(recs, m, "emphasis", L)]),
                "marked_rate": mean([x["ok"] for r in pick(recs, m, "emphasis", L) for x in r["targets"] if x["marked"]]),
                "unmarked_rate": mean([x["ok"] for r in pick(recs, m, "emphasis", L) for x in r["targets"] if not x["marked"]]),
            }
    return out


def pct(x):
    return f"{100 * x:.1f}" if x == x else "-"


def report(s):
    print(f"replies scored: {s['calls']}, cost at list ${s['cost_total']:.2f}", {SHORT[m]: round(v, 2) for m, v in s["cost_by_model"].items()})
    print("\nApplied rate, plain (target rules a reply got right)")
    for m in MODELS:
        print(" ", SHORT[m], " | ".join(f"{L}: {pct(s['applied'][m][L]['rate'])} [{pct(s['applied'][m][L]['ci'][0])}-{pct(s['applied'][m][L]['ci'][1])}]" for L in (0, 6, 50, 200, 800)))
    print("\nDrop from 6 rules")
    for m in MODELS:
        print(" ", SHORT[m], " | ".join(f"{L}: {pct(d['drop'])} [{pct(d['ci'][0])},{pct(d['ci'][1])}]" for L, d in s["drops"][m].items()))
    print("\nAlways-on rate")
    for m in MODELS:
        print(" ", SHORT[m], " | ".join(f"{L}: {pct(s['always'][m][L]['rate'])}" for L in (0, 6, 50, 200, 800)))
    for k, t in s["kinds"].items():
        print(f"\nKind {k}")
        for m in MODELS:
            print(" ", SHORT[m], " | ".join(f"{L}: {pct(t[m][L]['rate'])}" for L in (0, 6, 50, 200, 800)))
    print("\nAll six right")
    for m in MODELS:
        print(" ", SHORT[m], " | ".join(f"{L}: {pct(v)}" for L, v in s["all_six"][m].items()))
    print("\nBy third (first, middle, last)")
    for m in MODELS:
        print(" ", SHORT[m], " | ".join(f"{L}: " + "/".join(pct(v[t]) for t in (0, 1, 2)) for L, v in s["thirds"][m].items()))
    print("\nStray code/desk from another rule, share of replies; invented share")
    for m in MODELS:
        print(" ", SHORT[m], " | ".join(f"{L}: {pct(s['stray_known'][m][L])}/{pct(s['stray_invented'][m][L])}" for L in (6, 50, 200, 800)))
    print("\nLine rule: desk said but not on its own line, share of line rules")
    for m in MODELS:
        print(" ", SHORT[m], " | ".join(f"{L}: {pct(v)}" for L, v in s["line_buried"][m].items()))
    print("\nWording: no house term / banned word used")
    for m in MODELS:
        print(" ", SHORT[m], " | ".join(f"{L}: {pct(v['no_term'])}/{pct(v['banned_used'])}" for L, v in s["wording_parts"][m].items()))
    print("\nAlways-on each")
    for m in MODELS:
        print(" ", SHORT[m], {L: {a[7:]: pct(x) for a, x in v.items()} for L, v in s["always_each"][m].items()})
    print("\nEmphasis (gain over the same rule in the plain book, points)")
    for m in MODELS:
        for L, v in s["emphasis"][m].items():
            print(" ", SHORT[m], L, f"marked {pct(v['marked_gain'])} [{pct(v['marked_ci'][0])},{pct(v['marked_ci'][1])}] rate {pct(v['marked_rate'])}; unmarked {pct(v['unmarked_gain'])} [{pct(v['unmarked_ci'][0])},{pct(v['unmarked_ci'][1])}] rate {pct(v['unmarked_rate'])}; always {pct(v['always_marked_gain'])}; n={v['n']}")


def main():
    recs = score_all(load())
    s = summarise(recs)
    (ROOT / "results" / "summary.json").write_text(json.dumps(s, indent=1, default=str))
    report(s)


if __name__ == "__main__":
    main()
