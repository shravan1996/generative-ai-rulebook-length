"""The rules, emails and books say what the trial claims they say, and the scorer works."""
import re
import unittest

import prepare
import score

RULES = prepare.build_rules()
EMAILS = prepare.build_emails()
BY_ID = {r["id"]: r for r in RULES}


def perfect_reply(email):
    """A hand-built reply that obeys all six rules, proving they can be satisfied together."""
    t = [BY_ID[x] for x in email["targets"]]
    return (f"Re: order {email['order']}\n\nDear {email['name']},\n\nWe regret the trouble. "
            f"Your reference is {t[0]['token']}. We have noted a {t[2]['token']} for you.\n\n"
            f"Route: desk {t[1]['token']}\n\nWith care, the Larkfield team")


class Materials(unittest.TestCase):
    def test_counts(self):
        self.assertEqual(len(RULES), 800)
        self.assertEqual(len(EMAILS), 36)
        self.assertEqual(sum(r["kind"] == "always" for r in RULES), 3)

    def test_tokens_are_unique(self):
        for kind in ("code", "line"):
            tokens = [r["token"] for r in RULES if r["kind"] == kind]
            self.assertEqual(len(tokens), len(set(tokens)), kind)

    def test_each_email_has_one_rule_of_each_kind_on_three_products(self):
        for e in EMAILS:
            rules = [BY_ID[t] for t in e["targets"]]
            self.assertEqual([r["kind"] for r in rules], ["code", "line", "wording"], e["id"])
            self.assertEqual(len({r["product"] for r in rules}), 3, e["id"])

    def test_emails_name_only_their_own_products(self):
        for e in EMAILS:
            own = {BY_ID[t]["product"] for t in e["targets"]}
            found = {p for p in prepare.PRODUCTS if re.search(rf"\b{p}\b", e["text"])}
            self.assertEqual(found, own, e["id"])

    def test_no_email_asks_for_a_bulk_price_and_bans_discount(self):
        for e in EMAILS:
            sits = {BY_ID[t]["situation"] for t in e["targets"]}
            self.assertFalse({"trade", "promo"} <= sits, e["id"])

    def test_every_situation_is_used_at_least_three_times(self):
        counts = {s: 0 for s in prepare.SITUATIONS}
        for e in EMAILS:
            for t in e["targets"]:
                counts[BY_ID[t]["situation"]] += 1
        self.assertGreaterEqual(min(counts.values()), 3, counts)


class Books(unittest.TestCase):
    def test_lengths_and_contents(self):
        for e in EMAILS:
            for n in prepare.LENGTHS:
                book, thirds = prepare.rulebook(e, RULES, n)
                ids = [r["id"] for r in book]
                self.assertEqual(len(ids), n)
                self.assertEqual(len(set(ids)), n)
                for t in e["targets"]:
                    self.assertIn(t, ids)
                self.assertEqual(sum(r["kind"] == "always" for r in book), 3)

    def test_distractors_nest(self):
        e = EMAILS[0]
        sets = [set(r["id"] for r in prepare.rulebook(e, RULES, n)[0]) for n in prepare.LENGTHS]
        for small, big in zip(sets, sets[1:]):
            self.assertLessEqual(small, big)

    def test_targets_fall_in_the_third_recorded(self):
        for e in EMAILS:
            for n in prepare.LENGTHS[1:]:
                book, thirds = prepare.rulebook(e, RULES, n)
                pos = {r["id"]: i for i, r in enumerate(book)}
                sizes = [0, 0, 0]
                edges = []
                # Each third's size is what the builder put in it, so recover it from the fill.
                for t in e["targets"]:
                    self.assertIn(thirds[t], (0, 1, 2))
                    self.assertLess(abs(pos[t] / n - (thirds[t] + 0.5) / 3), 0.2, (e["id"], n, t))

    def test_each_target_kind_visits_every_third(self):
        seen = {}
        for e in EMAILS:
            _, thirds = prepare.rulebook(e, RULES, 200)
            for t in e["targets"]:
                seen.setdefault(BY_ID[t]["kind"], set()).add(thirds[t])
        for kind, where in seen.items():
            self.assertEqual(where, {0, 1, 2}, kind)

    def test_emphasis_marks_one_target_one_always_and_a_tenth_overall(self):
        for e in EMAILS:
            book, _ = prepare.rulebook(e, RULES, 200)
            m = prepare.marked(e, book)
            self.assertEqual(len(m), 20)
            self.assertEqual(len(m & set(e["targets"])), 1)
            self.assertEqual(sum(BY_ID[x]["kind"] == "always" for x in m), 1)


class Scorer(unittest.TestCase):
    def test_a_perfect_reply_passes_every_rule(self):
        for e in EMAILS:
            reply = perfect_reply(e)
            for t in e["targets"]:
                self.assertTrue(score.check_rule(BY_ID[t], reply, e["order"]), (e["id"], t, reply))
            for r in RULES[:3]:
                self.assertTrue(score.check_rule(r, reply, e["order"]), (e["id"], r["id"]))

    def test_a_blank_reply_fails_the_targets(self):
        for e in EMAILS:
            for t in e["targets"]:
                self.assertFalse(score.check_rule(BY_ID[t], "Dear customer, thanks.", e["order"]))

    def test_code_needs_the_whole_token(self):
        rule = {"kind": "code", "token": "DM-1234", "id": "x"}
        self.assertTrue(score.check_rule(rule, "Your claim is DM-1234."))
        self.assertTrue(score.check_rule(rule, "reference dm-1234"))
        self.assertFalse(score.check_rule(rule, "Your claim is DM-12345."))
        self.assertFalse(score.check_rule(rule, "XDM-1234"))

    def test_line_rule_must_be_its_own_line(self):
        rule = {"kind": "line", "token": "412", "id": "x"}
        self.assertTrue(score.check_rule(rule, "Thanks\n\n**Route: desk 412**\n"))
        self.assertFalse(score.check_rule(rule, "We sent it to Route: desk 412 today."))
        self.assertFalse(score.check_rule(rule, "Route: desk 413"))

    def test_wording_rule_needs_the_term_and_no_banned_word(self):
        rule = {"kind": "wording", "token": "Juniper credit", "situation": "refund", "id": "x"}
        self.assertTrue(score.check_rule(rule, "We have issued a Juniper credit."))
        self.assertFalse(score.check_rule(rule, "Your Juniper credit is a refund."))
        self.assertFalse(score.check_rule(rule, "We refunded you a Juniper credit."))
        self.assertFalse(score.check_rule(rule, "We have issued a credit."))

    def test_fee_rule_leaves_coffee_alone(self):
        rule = {"kind": "wording", "token": "Ivy carriage charge", "situation": "deliveryfee", "id": "x"}
        self.assertTrue(score.check_rule(rule, "The Ivy carriage charge paid for your coffee feet."))
        self.assertFalse(score.check_rule(rule, "The Ivy carriage charge is a fee."))

    def test_stray_tokens_separate_book_from_invented(self):
        book = [{"kind": "code", "token": "DM-1000"}, {"kind": "code", "token": "DM-2000"},
                {"kind": "line", "token": "333"}]
        target = [book[0]]
        known, made_up = score.stray_tokens("DM-1000 DM-2000 PT-9999\nRoute: desk 333", target, book)
        self.assertEqual(known, ["333", "DM-2000"])
        self.assertEqual(made_up, ["PT-9999"])

    def test_order_number_is_not_mistaken_for_a_code(self):
        self.assertEqual(score.stray_tokens("order LK-12345", [], []), ([], []))

    def test_email_part_drops_the_list(self):
        self.assertEqual(score.email_part("3, 7\n---\nHello", True), "Hello")
        self.assertEqual(score.email_part("Hello", True), "Hello")
        self.assertEqual(score.email_part("3\n---\nHello", False), "3\n---\nHello")


class ExploratoryArms(unittest.TestCase):
    def test_mention_names_are_unique_and_never_in_the_rulebook_tokens(self):
        self.assertEqual(len(set(prepare.SERVICES)), 100)
        tokens = {r["token"] for r in RULES if r["kind"] != "always"}
        self.assertFalse(tokens & set(prepare.SERVICES))

    def test_stacked_book_keeps_length_targets_and_always_on(self):
        for e in EMAILS[:6]:
            for k in prepare.ALL_AT_ONCE:
                book = prepare.stacked_book(e, RULES, k)
                ids = {r["id"] for r in book}
                self.assertEqual(len(book), 200)
                self.assertEqual(sum(r["kind"] == "mention" for r in book), k)
                self.assertTrue(set(e["targets"]) <= ids)
                self.assertEqual(sum(r["kind"] == "always" for r in book), 3)

    def test_update_sits_after_the_rule_it_changes_with_a_new_token(self):
        pool = {r["token"] for r in RULES if r["kind"] != "always"}
        for e in EMAILS:
            for n in (6, 200, 800):
                book, target, update = prepare.amended_book(e, RULES, n)
                ids = [r["id"] for r in book]
                self.assertEqual(len(book), n + 1)
                self.assertLess(ids.index(target["id"]), ids.index(update["id"]))
                self.assertNotEqual(update["token"], target["token"])
                self.assertNotIn(update["token"], pool)

    def test_updates_rotate_across_rule_kinds(self):
        kinds = [prepare.amendment(e, RULES)[0]["kind"] for e in EMAILS]
        self.assertEqual({k: kinds.count(k) for k in set(kinds)}, {"code": 12, "line": 12, "wording": 12})
