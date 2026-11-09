"""Draw the article's three figures as SVG from results/summary.json.

    python3 make_figures.py <output-folder>

Figures are 680 wide, transparent, and use the site's palette, so they sit on the article's figure
plate in light and dark mode.
"""
import json
import sys
from html import escape
from pathlib import Path

ROOT = Path(__file__).parent
W = 680
INK, SOFT, FAINT, RULE = "#191F1D", "#3F4945", "#5C6964", "#D3DBD7"
GREEN, MUTED = "#1F6B4C", "#A9B7B1"
# Series colours, validated with the dataviz palette checker against a light surface.
SERIES = {"Opus 5.5": "#0B7A4F", "Sonnet 5.5": "#3D5A98", "Haiku 5.5": "#B4690E"}

STYLE = f"""  <style>
    text {{ stroke: none; }}
    .serif {{ font-family: "Iowan Old Style", "Palatino Linotype", Palatino, Georgia, serif; }}
    .sans  {{ font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Helvetica, Arial, sans-serif; }}
    .h1 {{ font-size: 26px; font-weight: 600; fill: {INK}; }}
    .sub {{ font-size: 14.5px; fill: {SOFT}; }}
    .label {{ font-size: 11px; font-weight: 700; letter-spacing: 1.1px; fill: {FAINT}; }}
    .row {{ font-size: 14.5px; fill: {INK}; }}
    .rowb {{ font-size: 14.5px; font-weight: 600; fill: {INK}; }}
    .cell {{ font-size: 13.5px; fill: {SOFT}; }}
    .val {{ font-size: 14px; font-weight: 700; fill: {INK}; }}
    .num {{ font-size: 14px; fill: {SOFT}; }}
    .axis {{ font-size: 12px; fill: {FAINT}; }}
    .foot {{ font-size: 13.5px; fill: {SOFT}; }}
  </style>"""


def wrap(text, width_px, size=13.5):
    """Greedy word wrap using an average glyph width for the sans face."""
    per_line = max(10, int(width_px / (size * 0.53)))
    lines, cur = [], ""
    for word in text.split():
        if cur and len(cur) + 1 + len(word) > per_line:
            lines.append(cur)
            cur = word
        else:
            cur = f"{cur} {word}" if cur else word
    if cur:
        lines.append(cur)
    return lines


class Svg:
    def __init__(self, title, desc):
        self.title, self.desc, self.parts, self.y = title, desc, [], 0

    def text(self, x, y, cls, s, anchor=None):
        a = f' text-anchor="{anchor}"' if anchor else ""
        self.parts.append(f'  <text class="{cls}" x="{x:.1f}" y="{y:.1f}"{a}>{escape(s)}</text>')

    def rule(self, y, x1=32, x2=W - 32, colour=RULE):
        self.parts.append(f'  <line x1="{x1:.1f}" y1="{y:.1f}" x2="{x2:.1f}" y2="{y:.1f}" stroke="{colour}" stroke-width="1"/>')

    def vline(self, x, y1, y2, colour=RULE, width=1):
        self.parts.append(f'  <line x1="{x:.1f}" y1="{y1:.1f}" x2="{x:.1f}" y2="{y2:.1f}" stroke="{colour}" stroke-width="{width}"/>')

    def rect(self, x, y, w, h, fill):
        self.parts.append(f'  <rect x="{x:.1f}" y="{y:.1f}" width="{max(w, 1.5):.1f}" height="{h}" rx="2" fill="{fill}"/>')

    def head(self, subs):
        self.text(32, 44, "serif h1", self.title)
        y = 72
        for s in subs:
            self.text(32, y, "sans sub", s)
            y += 20
        self.rule(y)
        self.y = y + 28

    def foot(self, s):
        for line in wrap(s, W - 64, 13.5):
            self.text(32, self.y, "sans foot", line)
            self.y += 19

    def save(self, path):
        h = int(self.y + 16)
        body = "\n".join(self.parts)
        path.write_text(
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{h}" viewBox="0 0 {W} {h}" '
            f'role="img" aria-labelledby="title desc">\n'
            f'  <title id="title">{escape(self.title)}</title>\n'
            f'  <desc id="desc">{escape(self.desc)}</desc>\n{STYLE}\n{body}\n</svg>\n')


def text_table(title, subs, rows, left_w=200, foot=None):
    """Two-column table: a bold prompt on the left, wrapped detail on the right."""
    svg = Svg(title, " ".join(f"{a}: {b}" for a, b in rows) + (f" {foot}" if foot else ""))
    svg.head(subs)
    x2 = 32 + left_w + 16
    for left, right in rows:
        top = svg.y
        ll = wrap(left, left_w, 14.5)
        rl = wrap(right, W - 32 - x2, 13.5)
        for i, line in enumerate(ll):
            svg.text(32, top + i * 20, "sans rowb", line)
        for i, line in enumerate(rl):
            svg.text(x2, top + i * 19, "sans cell", line)
        svg.y = top + max(len(ll) * 20, len(rl) * 19) + 4
        svg.rule(svg.y)
        svg.y += 26
    if foot:
        svg.foot(foot)
    return svg


def reading_rule():
    rows = [
        ("IFScale, July 2025",
         "Up to 500 keywords, all required in one business report. The best model reached 68% at 500, and Claude 3.7 "
         "Sonnet 52.7%. Every instruction applies to the same piece of writing."),
        ("Prompt Design at Scale, July 2026",
         "10 to 160 rules on one short essay, marked by code. Getting all of them right fell to almost zero by 80 rules for "
         "every model. Claude Sonnet 5 went from 93.8% at 10 rules to 23.8% at 40."),
        ("Instruction Stacking Collapse, July 2026",
         "Up to 20 rules stacked on one reply. Claude Sonnet 4.6 fell from 96.4% to 60.4%, and much of the fall came "
         "from rules that clash with each other."),
        ("Anthropic's Claude Code docs",
         "Asks for fewer than 200 lines per CLAUDE.md, saying longer files use up context and get followed less "
         "closely. The page doesn't say by how much, and it is written for a coding agent in long sessions."),
    ]
    return text_table(
        "The scary numbers ask for everything at once",
        ["Each study piles many rules onto a single piece of writing. A team's", "rulebook mostly holds rules that don't apply to the reply in hand."],
        rows, left_w=190,
        foot="None of these tested a Claude 5.5 model, and none measured a long list where only a few rules apply.")


def _panel(svg, x0, x1, top, h, title, ymin, ymax, ticks, fmt, series, lengths):
    plot_top = top + 26
    sx = lambda i: x0 + (x1 - x0) * i / (len(lengths) - 1)
    sy = lambda v: plot_top + h * (1 - (v - ymin) / (ymax - ymin))
    svg.text(x0 - 34, top, "sans label", title)
    for t in ticks:
        svg.rule(sy(t), x0, x1)
        svg.text(x0 - 8, sy(t) + 4, "sans axis", fmt(t), "end")
    for i, L in enumerate(lengths):
        svg.text(sx(i), plot_top + h + 22, "sans axis", str(L), "middle")
    for name, values in series:
        c = SERIES[name]
        pts = " ".join(f"{sx(i):.1f},{sy(v):.1f}" for i, v in enumerate(values))
        svg.parts.append(f'  <polyline points="{pts}" fill="none" stroke="{c}" stroke-width="2" stroke-linejoin="round"/>')
        for i, v in enumerate(values):
            svg.parts.append(f'  <circle cx="{sx(i):.1f}" cy="{sy(v):.1f}" r="4.5" fill="{c}" stroke="#FFFFFF" stroke-width="2"/>')
    return sx, sy, plot_top


def result(s):
    lengths = [6, 50, 200, 800]
    names = {"claude-haiku-5-5": "Haiku 5.5", "claude-sonnet-5-5": "Sonnet 5.5", "claude-opus-5-5": "Opus 5.5"}
    rate = {names[m]: [100 * s["applied"][m][str(L)]["rate"] for L in lengths] for m in names}
    cost = {names[m]: [s["cost_per_reply"][m][str(L)] for L in lengths] for m in names}
    desc = ("Two line charts. Left, share of the rules that applied which each reply got right, by number of rules in the list, 6, 50, 200, 800. "
            + "; ".join(f"{k}: {', '.join(f'{v:.1f}%' for v in rate[k])}" for k in rate)
            + ". Right, cost per reply in US dollars as the tool reported it. "
            + "; ".join(f"{k}: {', '.join(f'${v:.4f}' for v in cost[k])}" for k in cost) + ".")
    svg = Svg("Claude didn't lose the rule. The bill grew.", desc)
    svg.head(["36 customer emails, three rules applying to each, inside lists of 6 to 800",
              "rules. Note the left axis starts at 90%."])
    top = svg.y
    x = 32
    for name, c in SERIES.items():
        svg.parts.append(f'  <circle cx="{x + 5}" cy="{top - 4}" r="4.5" fill="{c}"/>')
        svg.text(x + 15, top, "sans cell", name)
        x += 106
    top += 30
    h = 170
    series = [(k, rate[k]) for k in SERIES]
    sx, sy, plot_top = _panel(svg, 74, 302, top, h, "RULES THAT APPLIED, GOT RIGHT", 90, 100, (90, 95, 100), lambda v: f"{v:g}%", series, lengths)
    svg.text(sx(3), sy(100) + 19, "sans val", "Sonnet, Opus 100%", "end")
    svg.text(sx(3), sy(rate["Haiku 5.5"][3]) + 22, "sans val", f"Haiku {rate['Haiku 5.5'][3]:.1f}%", "end")
    svg.text((74 + 302) / 2, plot_top + h + 42, "sans axis", "Rules in the list", "middle")

    series = [(k, cost[k]) for k in SERIES]
    sx2, sy2, _ = _panel(svg, 410, 590, top, h, "COST PER REPLY", 0, 0.30, (0, 0.10, 0.20, 0.30), lambda v: f"${v:.2f}", series, lengths)
    svg.text(sx2(3) + 8, sy2(cost["Opus 5.5"][3]) + 5, "sans val", "$0.26")
    svg.text(sx2(3) + 8, sy2(cost["Sonnet 5.5"][3]) + 5, "sans val", "$0.13")
    svg.text(sx2(3) + 8, sy2(cost["Haiku 5.5"][3]) + 3, "sans val", "$0.007")
    svg.text((410 + 590) / 2, plot_top + h + 42, "sans axis", "Rules in the list", "middle")
    svg.y = plot_top + h + 66
    svg.rule(svg.y)
    svg.y += 26
    svg.foot("Sonnet's and Opus's lines sit on top of each other at 100%. Each point is 108 rule checks over 36 emails. "
             "Costs are what the command-line tool reported, which writes every list to its cache at full price. "
             "A system reusing one list would pay far less for each reply after the first.")
    return svg


def working_default():
    rows = [
        ("The file is long and the replies are fine",
         "Leave it alone. On Sonnet and Opus every rule that applied was followed at 800 rules, so trimming buys you a "
         "smaller bill and an easier file to read, not better replies."),
        ("You're adding a rule",
         "Say when it applies, in words the task will contain. Every rule in my list did that, and I can't separate "
         "that from the result."),
        ("A rule has changed",
         "Delete the old one anyway. Claude used the update in all 288 replies, but the next person editing the "
         "file won't work that out."),
        ("A rule has to show up in every reply",
         "Keep that group short and check it on Haiku. Given ten of them, it named only one or two in 6 of 18 "
         "replies."),
        ("A rule can never be broken",
         "Check the reply with a script before it goes out. Haiku still wrote a banned word in up to 1 reply in 12, "
         "and the wrong desk twice."),
        ("Something got missed and you reach for IMPORTANT",
         "Look for the reason first. I couldn't measure any benefit from it, though Sonnet and Opus left no room "
         "to improve."),
    ]
    return text_table(
        "What I'd do with a long instructions file",
        ["For replies written from a list of rules on Claude, as of November 2026."],
        rows, left_w=190,
        foot="Written for one-turn replies from rules I could check by code. Long conversations and rules that take "
             "judgement are untested.")


def main():
    out = Path(sys.argv[1] if len(sys.argv) > 1 else ROOT / "figures")
    out.mkdir(parents=True, exist_ok=True)
    s = json.loads((ROOT / "results" / "summary.json").read_text())
    reading_rule().save(out / "reading-rule.svg")
    result(s).save(out / "prototype-result.svg")
    working_default().save(out / "working-default.svg")
    print("wrote", out)


if __name__ == "__main__":
    main()
