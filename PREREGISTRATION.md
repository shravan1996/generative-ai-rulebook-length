# Pre-registration

Written on 9 November 2026, after an 18-call smoke test (kept in `logs/smoke.jsonl`, not used in
any result, with no email or rule changed because of it) and before the main run. Committed before
the first main-run call.

## The question

As a team's custom instructions grow, how long can the list get before Claude starts missing the
rule that applies?

Published tests pile every rule onto one output at once: IFScale (arXiv 2507.11538) asks for up to
500 keywords in one report, "Prompt Design at Scale" (arXiv 2607.19257) puts up to 160 rules on one
short essay, and "Instruction Stacking Collapse" (arXiv 2608.02639) stacks up to 20 constraints.
Anthropic's Claude Code docs say to target under 200 lines per CLAUDE.md because longer files
"reduce adherence". A real team rulebook is mostly rules that don't apply to the reply in hand. This
trial measures that case on Claude Haiku 5.5, Sonnet 5.5 and Opus 5.5.

## Data

`prepare.py` builds an invented retailer, Larkfield Home, with 800 rules: 3 always-on rules and 797
conditional rules, each about one of 40 products in one of 20 situations. There are 36 hand-written
customer emails, each triggering exactly three conditional rules, one of each kind:

- **code**: quote a reference that appears only in that rule;
- **line**: add a separate line, `Route: desk NNN`, with a desk that appears only in that rule;
- **wording**: use a house term and avoid an ordinary word for the whole reply.

A rulebook has T rules in total: the 3 targets, the 3 always-on rules, and T minus 6 others drawn
from the pool. T is 6, 50, 200 or 800. The others nest, so the book of 200 contains the book of 50's
others. Each target goes in a different third of the book and each always-on rule in a different
third, rotated by email.

## Procedure

Every call is a fresh chat through the Claude Code CLI, with tools off and the rulebook as the
system prompt. The email is the user message. The CLI cannot set temperature, so replies are sampled
and the models think adaptively. One reply per email per condition.

The runs, in the order collected, for each of the three models:

1. `plain`, lengths 0 (no rulebook at all, the baseline), 6, 50, 200, 800: 180 calls per model.
2. `emphasis`, lengths 200 and 800: 72 calls per model. One rule in ten gets the prefix
   `IMPORTANT: `. That always includes exactly one of the email's three targets, rotated across rule
   kinds, and exactly one always-on rule, rotated too. Otherwise the book is identical to `plain`.
3. `list_first`, conditional, 36 calls per model at each length it triggers on: run at length L for
   any model whose `plain` applied rate at L is 5 or more points below its rate at 6. The system
   prompt also asks for the numbers of the rules that apply, then a `---` line, then the email. Only
   the text after the last `---` is scored.

## Scoring

`score.py` is plain string matching. A code rule passes if the exact token appears. A line rule
passes only if `Route: desk NNN` is a line of its own, ignoring markdown, case and a trailing full
stop. A wording rule passes if the house term appears and no form of the banned word does. The
always-on rules: the sign-off appears in the last 90 characters; no "sorry" or form of "apologise";
the first non-empty line contains `re: order` and the order number.

## What I'll report

The primary number is the **applied rate**: the share of the three target rules a reply got right,
per model and length, with a 95% interval from a bootstrap over emails (10,000 resamples, seed 7).

- **H1, length.** A drop counts as real if the applied rate at length L is 5 or more points below
  the rate at 6 and the interval on the paired difference excludes zero. Below 5 points I'll call it
  no meaningful change.
- **H2, always-on rules.** Reported the same way, as a separate rate.
- **H3, position.** Applied rate by third of the book, at 200 and 800.
- **H4, emphasis.** The marked target against the same target in the `plain` book, and the two
  unmarked targets against the same two in the `plain` book, which is the cost of marking one.
- **H5, wrong rule.** Share of replies containing a code or desk belonging to a rule that didn't
  apply, plus any code or desk that exists nowhere in the book.
- Also: share of replies with all six rules right, by rule kind, and cost.

## What I expect, written down so I can be wrong

Sonnet and Opus lose under 2 points at 200 rules and under 5 at 800. Haiku loses 5 to 10 points at
800. Always-on rules hold at 97% or better everywhere. The middle third of a long book is the worst
place for a rule to be, by a few points. IMPORTANT adds a couple of points to the marked rule and
costs the others nothing. Wrong-rule firing stays under 1% of replies.

## Limits, stated before seeing results

The rulebook is invented, tidier than any real one, and made of rules that can be checked by string
matching; judgement rules are not tested. Each reply is one turn, so rules fading over a long
conversation are not tested. Only Claude is tested, through the CLI rather than the Claude app. I
wrote the emails and the rules, with Claude Code's help.

## Deviations and additions

Written on 9 November 2026 after the `plain` and `emphasis` runs, before any call below. Everything
here is exploratory and will be labelled that way.

1. **`list_first` did not run.** No model dropped 5 points at any length, so its condition was never
   met.
2. **The main result looks like a ceiling.** Sonnet and Opus got every target rule right at 800
   rules. Every email names its product, so the rule that applies can be found by matching a word.
   Two arms test whether that is why.
3. **`stacked`** (18 odd-numbered emails, all three models). The book is always 200 rules. k of them,
   10, 30 or 100, become always-on rules requiring the reply to mention one invented Larkfield service
   by name, the same many-rules-at-once shape as the published studies. Scored: share of the k names
   present, and the applied rate on the same three conditional targets, which shows whether a heavy
   always-on load costs the rules that apply only sometimes.
4. **`amended`** (all 36 emails). The usual book plus one extra rule, placed somewhere after the rule
   it changes, saying that case now uses a new code, desk or house term. The original stays in the
   book unchanged. Lengths 6, 200 and 800 for Haiku and Sonnet, 6 and 200 for Opus, to hold down cost.
   Scored as four outcomes: new token only (correct), old token only (stale), both, neither.

Predictions: `stacked` applied rate on mentions falls below 90% at k=100 for Haiku and stays above
95% for Opus; conditional targets are unaffected. `amended` is right at least 95% of the time at 6
rules and drops by 10 points or more at 800 on Haiku.

5. **The `stacked` scorer changed after I read replies.** My first scorer needed the exact phrase, such
   as "Juniper helpline", and scored a reply listing "helplines: Juniper, Hazel, Rowan" as zero. I
   found this by reading the replies behind an odd all-or-nothing pattern. Both are reported: `strict`
   is the original, `grouped` also counts a shared-noun list. Replies are classified as naming
   everything, saying that they had not, or skipping quietly; that classifier is a regular expression
   I wrote after seeing replies, and every reply it marks "said_so" is checked by hand.
