# Hand checks

Done on 9 November 2026 by reading the replies, not by scoring them.

## Every reply the classifier marked "said_so" in the stacked arm

Two replies, both Haiku 5.5 at 100 always-on rules (e23 and e31), both real: each ends with a note
addressed to the team saying the naming rules would make the email unreadable and asking whether they
should stand. In both, the note sits inside the reply the customer would receive, after a `---` line.

## Replies with a code or desk from a rule that wasn't a target, plain arm at 800 rules

| Model | Email | Wrote | Should have written | Reading |
| --- | --- | --- | --- | --- |
| Opus 5.5 | e02 | `damaged:rug` DM-7553 | nothing else | Correct on the facts: the customer said the rug was soaked through. My "exactly three rules apply" was wrong for this email. It also applied its three targets. |
| Opus 5.5 | e07 | `wrongitem:plant pot` EX-1516 | nothing else | Defensible: the pot was too big, and it offered a smaller size. It also applied its three targets. |
| Haiku 5.5 | e01 | `late:high chair` desk 691 | `late:bookcase` desk 385 | Wrong. Right situation, wrong product. |
| Haiku 5.5 | e19 | `doublecharge:wardrobe` desk 711 | `address:dog bed` | Wrong. Different product and situation. |

The other Haiku miss at 800 rules, e32, is an omission: it asked for a photo and gave no warranty code.

## The scorer change in the stacked arm

The first scorer needed the exact phrase ("Juniper helpline"). Reading the replies showed Sonnet and
Haiku often wrote one shared noun and a list of names, so grouped scoring was added. Both scores are
reported. See deviation 5 in PREREGISTRATION.md.

## Numbers checked by hand

- Haiku 5.5 "sorry" misses at 800 (e04, e13, e26): the word appears in each.
- None of the 108 no-rulebook replies contains a code or house term from the rule pool.
