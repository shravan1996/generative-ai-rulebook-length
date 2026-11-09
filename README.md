# generative-ai-rulebook-length

As a team's custom instructions grow, how long can the list get before Claude starts missing the
rule that applies? This trial puts 36 customer emails, each needing three particular rules, through
lists of 6, 50, 200 and 800 rules on Claude Haiku 5.5, Sonnet 5.5 and Opus 5.5.

It is the trial behind the Generative AI article on shravanpendem.com, "Eight hundred rules and a
soaked rug".

**What this is not.** It doesn't test ChatGPT, Gemini or any non-Claude model. The rules are invented
and can all be checked by string matching, and each names the product it covers, so nothing here
speaks to rules that need judgement. Every reply is one turn, so rules fading over a long chat are
not tested. Claude was called through the Claude Code command-line tool, not the Claude app. Whether
a reply was any good is not scored, only whether it did what the rules asked.

## Results

Run on 9 November 2026: 1,206 fresh chats, about nine minutes of calls, $60.82 at list price as the
tool reports it ($42.10 of it on the pre-registered part).

Share of the three rules that applied that a reply got right:

| | No rulebook | 6 rules | 50 | 200 | 800 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Opus 5.5 | 0.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| Sonnet 5.5 | 0.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| Haiku 5.5 | 0.0% | 98.1% | 100.0% | 98.1% | 97.2% |

Replies with all six rules right, the three that applied plus the three always-on ones:

| | 6 rules | 50 | 200 | 800 |
| --- | ---: | ---: | ---: | ---: |
| Opus 5.5 | 100.0% | 100.0% | 100.0% | 100.0% |
| Sonnet 5.5 | 97.2% | 100.0% | 97.2% | 97.2% |
| Haiku 5.5 | 91.7% | 97.2% | 86.1% | 83.3% |

What the pre-registered questions came to (`PREREGISTRATION.md`):

1. **H1, length: no meaningful change.** Nothing crossed the 5-point line. Haiku's drop at 800 rules
   was 0.9 points (95% interval -2.8 to 4.6).
2. **H2, always-on rules: held,** at 97.2% or better. Haiku's weak spot was the word "sorry".
3. **H3, position: my guess was wrong.** Haiku's three misses at 800 were all in the last third, and
   no other model missed anything.
4. **H4, IMPORTANT: nothing to measure.** Sonnet and Opus were at the ceiling. Haiku's marked rule
   gained 5.6 points at 800 (0 to 13.9), with no cost to the others.
5. **H5, wrong rule: above my 1% guess, and not always wrong.** 2 of 36 Haiku replies at 800 rules
   used the wrong desk. 2 of 36 Opus replies used a rule I hadn't marked as a target; on reading
   them, both rules fitted, so my "exactly three rules apply" was wrong for those emails.

Exploratory, added after those results and logged as deviations:

- **`amended`.** One update placed after the rule it changes, with the old rule left in the list. All
  288 replies used the new version.
- **`stacked`.** 10, 30 or 100 always-on rules in a list of 200, each requiring one named service. My
  first scorer needed the exact phrase and scored a shared-noun list as zero; deviation 5 records the
  change. With grouped lists counted, Sonnet and Opus named everything. Haiku got 70.0%, 73.9% and
  88.9%, and two of its replies at 100 stopped and wrote a note saying the rules were unreasonable.

## Run it

No key is needed to check the materials and the analysis:

```bash
python3 -m unittest discover -s tests -t .
python3 analyze.py
python3 make_figures.py figures
```

The tests include a hand-built reply that passes all six rules for every email, which shows the rules
can be satisfied at once, and checks that each email names only its own products. `analyze.py` scores
every reply in `results/calls.jsonl` and writes `results/summary.json`.

To collect fresh replies you need the Claude Code command-line tool, signed in. `collect.py` resumes
where it stopped:

```bash
python3 collect.py --models claude-haiku-5-5 claude-sonnet-5-5 claude-opus-5-5 --lengths 0 6 50 200 800
python3 collect.py --models claude-haiku-5-5 claude-sonnet-5-5 claude-opus-5-5 --arm emphasis --lengths 200 800
```

## Files

- `prepare.py`: the rules, emails and rulebooks. Nothing here calls a model.
- `score.py`: string-matching checks for each rule.
- `collect.py`: the calls to Claude.
- `analyze.py`: scoring and intervals.
- `make_figures.py`: the article's three figures.
- `PREREGISTRATION.md`: the plan written before the main run, and the deviations from it.
- `logs/hand_read.md`: replies I read by hand. `logs/smoke.jsonl`: the 18-call test before the run.
- `results/calls.jsonl`: every reply.

MIT licensed.
