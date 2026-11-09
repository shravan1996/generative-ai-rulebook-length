"""Mark a reply against the rules. Every check is plain string matching; no model is involved."""
import re

from prepare import BANNED


def clean_line(line):
    return re.sub(r"\s+", " ", re.sub(r"[*_`#>]", "", line)).strip().rstrip(".").lower()


def lines_of(reply):
    return [clean_line(x) for x in reply.splitlines() if clean_line(x)]


def check_rule(rule, reply, order=None):
    """True if the reply did what this rule asks."""
    kind = rule["kind"]
    if kind == "code":
        return re.search(rf"(?<![\w-]){re.escape(rule['token'])}(?![\w-])", reply, re.I) is not None
    if kind == "line":
        return f"route: desk {rule['token']}" in lines_of(reply)
    if kind == "wording":
        return (re.search(re.escape(rule["token"]), reply, re.I) is not None
                and re.search(BANNED[rule["situation"]], reply, re.I) is None)
    if rule["id"] == "always-signoff":
        tail = re.sub(r"[*_`]", "", " ".join(reply.split()))[-90:].lower()
        return "with care, the larkfield team" in tail
    if rule["id"] == "always-sorry":
        return re.search(r"\bsorry\b|\bapolog", reply, re.I) is None
    if rule["id"] == "always-order":
        got = lines_of(reply)
        return bool(got) and f"re: order {order}".lower() in got[0]
    raise ValueError(rule["id"])


def wording_parts(rule, reply):
    """(house term used, banned word avoided), for reporting which half of a wording rule failed."""
    return (re.search(re.escape(rule["token"]), reply, re.I) is not None,
            re.search(BANNED[rule["situation"]], reply, re.I) is None)


CODE_LIKE = re.compile(r"(?<![\w-])([A-Z]{2}-\d{4})(?![\w-])")
DESK_LIKE = re.compile(r"route:\s*desk\s*(\d{3})\b", re.I)


def stray_tokens(reply, target_rules, book):
    """Codes and desks in the reply that belong to no target.

    Returns (from another rule in the book, not in the book at all). Order numbers have five
    digits, so they never match a four-digit code.
    """
    allowed = {r["token"].upper() for r in target_rules if r["kind"] in ("code", "line")}
    known = {r["token"].upper() for r in book if r["kind"] in ("code", "line")}
    found = {m.upper() for m in CODE_LIKE.findall(reply)} | set(DESK_LIKE.findall(reply))
    extra = found - allowed
    return sorted(extra & known), sorted(extra - known)


def email_part(reply, list_first=False):
    """In the list-first arm only the text after the --- line counts as the email."""
    if not list_first:
        return reply
    parts = re.split(r"^\s*-{3,}\s*$", reply, flags=re.M)
    return parts[-1].strip() if len(parts) > 1 else reply
