"""Build the rule pool, the customer emails and the rulebooks. Nothing here calls a model.

Larkfield Home is an invented homeware retailer. Its care team has 800 rules:

  * 3 always-on rules, which apply to every reply;
  * 797 conditional rules drawn from a grid of 40 products by 20 situations, each of which says
    what to do when one situation comes up about one product.

Each customer email triggers exactly three conditional rules, one of each kind:

  code     quote a reference that exists only in that rule
  line     add a separate line naming a desk that exists only in that rule
  wording  use a house term and avoid an ordinary word for the whole reply

    python3 prepare.py        writes data/rules.json and data/emails.json
"""
import hashlib
import json
import random
from pathlib import Path

ROOT = Path(__file__).parent
SEED = 20261109
LENGTHS = [6, 50, 200, 800]  # total rules in the book, always-on rules included
TARGETS = 3

PRODUCTS = [
    "garden bench", "table lamp", "floor lamp", "kettle", "toaster", "bookcase", "desk chair",
    "wardrobe", "bedside table", "coffee table", "sofa bed", "mattress", "duvet", "shower curtain",
    "bath mat", "towel rail", "plant pot", "watering can", "patio heater", "parasol", "hammock",
    "rug", "doormat", "curtain pole", "mirror", "wall clock", "picture frame", "storage basket",
    "laundry hamper", "ironing board", "step ladder", "tool chest", "bike rack", "dog bed",
    "cat tree", "high chair", "play tent", "slow cooker", "stand mixer", "dish rack",
]

ADJECTIVES = [
    "Juniper", "Harbour", "Meadow", "Bracken", "Thistle", "Willow", "Heather", "Sorrel", "Fennel",
    "Hazel", "Rowan", "Alder", "Linden", "Tansy", "Yarrow", "Clover", "Aster", "Bryony", "Campion",
    "Dunlin", "Ember", "Fenwick", "Gorse", "Hollis", "Ivy", "Jasper", "Kestrel", "Larch", "Marram",
    "Nettle", "Oriel", "Plover", "Quill", "Rushden", "Saffron", "Teasel", "Umber", "Vetch", "Wren",
    "Yew",
]

# Each situation has three phrasings, so the book doesn't read like one sentence 800 times.
SITUATIONS = {
    # code: quote a reference
    "damaged": ("code", "DM", [
        "If a customer says their {p} arrived damaged, give them claim reference {x}.",
        "A {p} that turned up damaged gets claim reference {x}; put it in the reply.",
        "When a {p} has been delivered damaged, the reply must give claim reference {x}.",
    ]),
    "parts": ("code", "PT", [
        "If a customer's {p} came with parts missing, give them parts request number {x}.",
        "Missing parts on a {p}: the reply gives parts request number {x}.",
        "When parts are missing from a {p}, include parts request number {x} in the reply.",
    ]),
    "assembly": ("code", "AS", [
        "If a customer needs help putting together a {p}, give them assembly guide number {x}.",
        "Anyone stuck assembling a {p} gets assembly guide number {x} in the reply.",
        "When someone can't work out how to assemble a {p}, the reply gives assembly guide number {x}.",
    ]),
    "warranty": ("code", "WR", [
        "If a customer's {p} has stopped working and they want to claim on the guarantee, give them warranty code {x}.",
        "A guarantee claim on a {p} that has stopped working gets warranty code {x}.",
        "When a {p} fails and the customer wants to use the guarantee, the reply gives warranty code {x}.",
    ]),
    "wrongitem": ("code", "EX", [
        "If a customer received the wrong colour or size of {p}, give them exchange code {x}.",
        "Wrong colour or size on a {p}: the reply gives exchange code {x}.",
        "When the {p} delivered is the wrong colour or size, include exchange code {x} in the reply.",
    ]),
    "invoice": ("code", "IV", [
        "If a customer asks for a VAT invoice for a {p}, give them invoice request code {x}.",
        "A VAT invoice request for a {p} gets invoice request code {x} in the reply.",
        "When someone needs a VAT invoice for a {p}, the reply gives invoice request code {x}.",
    ]),
    "restock": ("code", "WL", [
        "If a customer asks when a {p} will be back in stock, give them waitlist code {x}.",
        "A question about when a {p} returns to stock gets waitlist code {x}.",
        "When someone wants to know when a {p} will be available again, the reply gives waitlist code {x}.",
    ]),
    # line: add a routing line
    "late": ("line", "", [
        "If a customer's {p} is late, add a separate line reading: Route: desk {x}",
        "A late delivery of a {p} needs a separate line in the reply reading: Route: desk {x}",
        "When a {p} hasn't arrived on the promised day, add a separate line reading: Route: desk {x}",
    ]),
    "misdelivered": ("line", "", [
        "If a courier left a customer's {p} in the wrong place, add a separate line reading: Route: desk {x}",
        "A {p} left at the wrong place by the courier needs a separate line reading: Route: desk {x}",
        "When the courier has put a {p} somewhere it shouldn't be, add a separate line reading: Route: desk {x}",
    ]),
    "cancel": ("line", "", [
        "If a customer wants to cancel a {p} before it ships, add a separate line reading: Route: desk {x}",
        "A request to cancel a {p} that hasn't shipped needs a separate line reading: Route: desk {x}",
        "When someone cancels an unshipped {p}, add a separate line reading: Route: desk {x}",
    ]),
    "safety": ("line", "", [
        "If a customer raises a safety worry about a {p}, add a separate line reading: Route: desk {x}",
        "Any safety concern about a {p} needs a separate line reading: Route: desk {x}",
        "When someone says a {p} doesn't feel safe, add a separate line reading: Route: desk {x}",
    ]),
    "address": ("line", "", [
        "If a customer wants a {p} sent to a different address, add a separate line reading: Route: desk {x}",
        "A change of delivery address for a {p} needs a separate line reading: Route: desk {x}",
        "When someone asks for a {p} to go to another address, add a separate line reading: Route: desk {x}",
    ]),
    "doublecharge": ("line", "", [
        "If a customer has been charged twice for a {p}, add a separate line reading: Route: desk {x}",
        "A double charge for a {p} needs a separate line reading: Route: desk {x}",
        "When a card has been billed twice for a {p}, add a separate line reading: Route: desk {x}",
    ]),
    "trade": ("line", "", [
        "If a business asks for a bulk price on a {p}, add a separate line reading: Route: desk {x}",
        "A request for a business or bulk price on a {p} needs a separate line reading: Route: desk {x}",
        "When a company wants a volume price for a {p}, add a separate line reading: Route: desk {x}",
    ]),
    # wording: use a house term, avoid an ordinary word anywhere in the reply
    "refund": ("wording", "credit", [
        "If a customer wants their money back on a {p}, call what they get a '{x}' and don't use any form of the word 'refund' anywhere in that reply.",
        "Money back on a {p} is called a '{x}'; don't use any form of the word 'refund' anywhere in that reply.",
        "When someone wants their money back for a {p}, write '{x}' and avoid any form of the word 'refund' in that whole reply.",
    ]),
    "replace": ("wording", "renewal", [
        "If a customer asks for another {p} to take the place of one they broke themselves, call it a '{x}' and don't use any form of the word 'replace' anywhere in that reply.",
        "A customer who broke their own {p} and wants another gets a '{x}'; don't use any form of the word 'replace' anywhere in that reply.",
        "When someone has broken a {p} themselves and asks for another, write '{x}' and avoid any form of the word 'replace' in that whole reply.",
    ]),
    "deliveryfee": ("wording", "carriage charge", [
        "If a customer queries what they paid to have a {p} delivered, call that a '{x}' and don't use the word 'fee' or 'fees' anywhere in that reply.",
        "A question about the delivery cost of a {p}: call it a '{x}' and don't use the word 'fee' or 'fees' anywhere in that reply.",
        "When someone challenges the cost of delivering a {p}, write '{x}' and avoid the word 'fee' or 'fees' in that whole reply.",
    ]),
    "promo": ("wording", "voucher", [
        "If a customer says a promotional code didn't work on a {p}, call the code a '{x}' and don't use any form of the word 'discount' anywhere in that reply.",
        "A promotional code that failed on a {p} is called a '{x}'; don't use any form of the word 'discount' anywhere in that reply.",
        "When someone's money-off code won't work on a {p}, write '{x}' and avoid any form of the word 'discount' in that whole reply.",
    ]),
    "takeback": ("wording", "take-back", [
        "If a customer wants their old {p} taken away, call that a '{x}' and don't use any form of the word 'collect' anywhere in that reply.",
        "Taking away someone's old {p} is called a '{x}'; don't use any form of the word 'collect' anywhere in that reply.",
        "When someone asks you to remove their old {p}, write '{x}' and avoid any form of the word 'collect' in that whole reply.",
    ]),
    "instalments": ("wording", "spread plan", [
        "If a customer wants to spread the cost of a {p} over several months, call that a '{x}' and don't use any form of the word 'instalment' anywhere in that reply.",
        "Paying for a {p} over several months is called a '{x}'; don't use any form of the word 'instalment' anywhere in that reply.",
        "When someone asks to pay for a {p} in monthly parts, write '{x}' and avoid any form of the word 'instalment' in that whole reply.",
    ]),
}

BANNED = {
    "refund": r"\brefund\w*",
    "replace": r"\breplac\w*",
    "deliveryfee": r"\bfees?\b",
    "promo": r"\bdiscount\w*",
    "takeback": r"\bcollect\w*",
    "instalments": r"\binstal+ment\w*",
}

ALWAYS = [
    {"id": "always-signoff", "kind": "always",
     "text": "Close every reply with exactly these words: With care, the Larkfield team"},
    {"id": "always-sorry", "kind": "always",
     "text": "Never use the word 'sorry' or any form of 'apologise' in a reply; write 'we regret' instead."},
    {"id": "always-order", "kind": "always",
     "text": "Begin every reply with a line reading 'Re: order' followed by the customer's order number."},
]

# (name, body, code rule, line rule, wording rule), each rule as (situation, product).
EMAILS = [
    ("Priya", "The kettle from my order turned up with a cracked lid and a dent in the side. The bookcase on the same order was promised for last Tuesday and still hasn't come. And I've gone off the toaster, which is still sealed in its box, so I'd like my money back for that one.", ("damaged", "kettle"), ("late", "bookcase"), ("refund", "toaster")),
    ("Tom", "The desk chair came with only three of its five castors. Your driver left the rug behind the bins at number 14, which isn't my house (I'm at 41), and it's soaked through. Separately, my son put a football through the mirror I bought from you, which is entirely on us. Could you send me another?", ("parts", "desk chair"), ("misdelivered", "rug"), ("replace", "mirror")),
    ("Aisha", "I've been staring at the instructions for the wardrobe for two hours and can't work out how the doors go on. Please also cancel the parasol, it hasn't left you yet and I've found one locally. And why did I pay £35 to have the sofa bed brought round when the website said free?", ("assembly", "wardrobe"), ("cancel", "parasol"), ("deliveryfee", "sofa bed")),
    ("Callum", "My slow cooker stopped heating after eight months and I'd like to claim on the guarantee. The gas hose on the patio heater feels loose and I honestly don't feel safe lighting it. And the 20% off code from your newsletter wouldn't go through on the bath mat.", ("warranty", "slow cooker"), ("safety", "patio heater"), ("promo", "bath mat")),
    ("Beth", "I ordered a king size duvet and you've sent a single. Could the ironing board go to my office at 7 Mill Lane rather than home? And when the new bed comes on Friday, can your men take away the old mattress?", ("wrongitem", "duvet"), ("address", "ironing board"), ("takeback", "mattress")),
    ("Marek", "I need a VAT invoice for the tool chest for my business accounts. My card statement shows the step ladder twice, same amount, same day. Can I pay for the hammock over three months rather than in one go?", ("invoice", "tool chest"), ("doublecharge", "step ladder"), ("instalments", "hammock")),
    ("Sofia", "Do you know when the dog bed will be back on the shelves? It's been out for weeks. We run a small chain of cafes and want fourteen of the wall clock, is there a bulk price for businesses? Also the plant pot turned out too big for the windowsill and I'd like my money back.", ("restock", "dog bed"), ("trade", "wall clock"), ("refund", "plant pot")),
    ("Hassan", "The picture frame arrived with the glass in pieces. The coffee table was due on Monday and nobody has been. And I left your watering can out in the frost and it split, my own fault, but could I have another one?", ("damaged", "picture frame"), ("late", "coffee table"), ("replace", "watering can")),
    ("Olivia", "The bike rack box had none of the wall bolts in it. The courier left my storage basket in the car park of the flats next door. And I was charged £12 to get a curtain pole delivered, which seems a lot for a stick.", ("parts", "bike rack"), ("misdelivered", "storage basket"), ("deliveryfee", "curtain pole")),
    ("Dan", "I can't for the life of me work out how to assemble the high chair, the tray won't clip on. Could you cancel the doormat please, it's not been dispatched yet. Your welcome code keeps being rejected on the laundry hamper too.", ("assembly", "high chair"), ("cancel", "doormat"), ("promo", "laundry hamper")),
    ("Nadia", "The stand mixer stopped turning last week, only ten months old, and I want to use the guarantee. The floor lamp gave me a small shock when I touched the switch, which has me worried. And when you bring the new settee could you take away my old sofa bed?", ("warranty", "stand mixer"), ("safety", "floor lamp"), ("takeback", "sofa bed")),
    ("Rui", "The shower curtain I got is grey and I ordered blue. Can the cat tree be sent to my mother's address in Leeds instead of mine? And is there a way of spreading the cost of the wardrobe across six months?", ("wrongitem", "shower curtain"), ("address", "cat tree"), ("instalments", "wardrobe")),
    ("Greta", "Please could I have a VAT invoice for the mattress. My bank has taken the money for the towel rail twice. And the dish rack doesn't fit my sink, so I'd like my money back on that.", ("invoice", "mattress"), ("doublecharge", "towel rail"), ("refund", "dish rack")),
    ("Ife", "When will you have the bedside table in stock again? I run a nursery and we'd like twenty of the play tent, so is there a bulk price for that? And our cat knocked my kettle off the counter and smashed it, all her doing, so can I get another?", ("restock", "bedside table"), ("trade", "play tent"), ("replace", "kettle")),
    ("Liam", "The hammock arrived with a big tear along one edge. The ironing board should have been here on Saturday. And I paid £9 to get the bookcase delivered even though I spent over the limit where you said delivery was free.", ("damaged", "hammock"), ("late", "ironing board"), ("deliveryfee", "bookcase")),
    ("Yuki", "My step ladder arrived without the rubber feet that are meant to be in the box. Your driver dumped my parasol at the neighbour's gate when I was home all day. And the code from the flyer says invalid when I try it on the mirror.", ("parts", "step ladder"), ("misdelivered", "parasol"), ("promo", "mirror")),
    ("Amara", "The bike rack has defeated me, I can't see how the arms fit together at all. Please cancel the slow cooker while it's still in your warehouse. When the new rug arrives, can the driver please take the old rug away with him?", ("assembly", "bike rack"), ("cancel", "slow cooker"), ("takeback", "rug")),
    ("Jonas", "The patio heater won't light any more, it's eleven months old, and I'd like to make a claim under the guarantee. My daughter's high chair wobbles when she leans over and one leg looks like it could give way, so I don't feel she's safe in it. Also I'd like to pay for the tool chest monthly over a few months if you offer that.", ("warranty", "patio heater"), ("safety", "high chair"), ("instalments", "tool chest")),
    ("Chloe", "You've sent the small bath mat and I ordered the large. Could the dog bed go to my sister's at 22 Fern Road instead? The picture frame also isn't what I wanted after all, so I'd like my money back on it.", ("wrongitem", "bath mat"), ("address", "dog bed"), ("refund", "picture frame")),
    ("Farid", "My accountant wants a VAT invoice for the desk chair. I've looked at my statement and the coffee table has been charged twice. I tripped and fell into the floor lamp and bent it beyond repair, which is my fault, but can you send me another?", ("invoice", "desk chair"), ("doublecharge", "coffee table"), ("replace", "floor lamp")),
    ("Mei", "Any idea when the towel rail will be available again? We're fitting out a hotel and need sixty of the storage basket, what can you do on price for a company? And I paid £15 to have a dish rack delivered, which was more than the rack.", ("restock", "towel rail"), ("trade", "storage basket"), ("deliveryfee", "dish rack")),
    ("Owen", "The stand mixer was dented when I opened the box and the bowl has a crack. The plant pot was meant to be here by Wednesday and still isn't. And the spring sale code didn't apply when I tried it on the bookcase.", ("damaged", "stand mixer"), ("late", "plant pot"), ("promo", "bookcase")),
    ("Zara", "The cat tree came without the post that holds up the top shelf. The courier put my kettle in the recycling bin outside, of all places. And could you take away the old wardrobe when you deliver the new one?", ("parts", "cat tree"), ("misdelivered", "kettle"), ("takeback", "wardrobe")),
    ("Ben", "Could someone explain how to assemble the sofa bed, because the frame doesn't line up the way the leaflet shows. Please cancel the laundry hamper, I can see it hasn't been sent. And can I split the cost of the mattress over several months?", ("assembly", "sofa bed"), ("cancel", "laundry hamper"), ("instalments", "mattress")),
    ("Dina", "My wall clock has stopped working after a few months and I'd like to claim on the guarantee. The top step of the step ladder bends when I stand on it and I don't feel safe using it. I've also decided against the curtain pole, so I'd like my money back on that.", ("warranty", "wall clock"), ("safety", "step ladder"), ("refund", "curtain pole")),
    ("Kofi", "The plant pot you delivered is terracotta and I ordered white. Could the rug go to our new flat, 3 Canal Street, rather than the old one? And our puppy chewed the dog bed to bits, our own fault, so can you send me another?", ("wrongitem", "plant pot"), ("address", "rug"), ("replace", "dog bed")),
    ("Ines", "Please send me a VAT invoice for the dish rack. I've been billed twice for the bedside table according to my banking app. And why does it cost £18 to deliver a high chair?", ("invoice", "dish rack"), ("doublecharge", "bedside table"), ("deliveryfee", "high chair")),
    ("Harry", "When is the shower curtain going to be back in stock? The toaster was promised for yesterday and hasn't turned up. And the friends and family code won't work on the duvet.", ("restock", "shower curtain"), ("late", "toaster"), ("promo", "duvet")),
    ("Leila", "The doormat came with one corner ripped off. The courier left my laundry hamper at the post office without telling me. And when you drop off the new one, could you take away my old bike rack?", ("damaged", "doormat"), ("misdelivered", "laundry hamper"), ("takeback", "bike rack")),
    ("Sam", "The bookcase is short of two shelf pins so I can't finish it. Please cancel the towel rail before it goes out. And is it possible to pay for the patio heater over several months?", ("parts", "bookcase"), ("cancel", "towel rail"), ("instalments", "patio heater")),
    ("Anya", "I need someone to tell me how to assemble the cat tree, because the diagram makes no sense. The handle on the kettle gets so hot that it burned my hand, and I'm worried it isn't safe. I'd also like my money back on the slow cooker, which I've decided I don't need.", ("assembly", "cat tree"), ("safety", "kettle"), ("refund", "slow cooker")),
    ("Reza", "The floor lamp has stopped working and I'd like to make a claim under its guarantee. Could you send the picture frame to my work address, 40 Quay Road, instead? And I reversed over the tool chest in the drive, completely my doing, so could you send another?", ("warranty", "floor lamp"), ("address", "picture frame"), ("replace", "tool chest")),
    ("Holly", "The rug is green and I ordered the navy. My card has been charged twice for the parasol. And I'd like someone to explain the £22 I paid to have a hammock delivered, as it weighs almost nothing.", ("wrongitem", "rug"), ("doublecharge", "parasol"), ("deliveryfee", "hammock")),
    ("Dev", "I need a VAT invoice for the play tent, please. The mirror is hanging from a fixing that pulled out of the wall, and I'm frightened it will fall on someone. And your code from the email wouldn't take on the stand mixer.", ("invoice", "play tent"), ("safety", "mirror"), ("promo", "stand mixer")),
    ("Noor", "Will the watering can be back in stock this month? We're a landscaping firm and want thirty of the garden bench, do you offer a bulk price to businesses? And can you take away my old desk chair when the new one comes?", ("restock", "watering can"), ("trade", "garden bench"), ("takeback", "desk chair")),
    ("Erik", "The wardrobe has a split right down one door and it came like that. The table lamp was due on Thursday and I've heard nothing. And could I pay off the sofa bed in monthly amounts rather than all at once?", ("damaged", "wardrobe"), ("late", "table lamp"), ("instalments", "sofa bed")),
]


def stable(*parts):
    return int(hashlib.sha256("|".join(map(str, parts)).encode()).hexdigest(), 16)


def build_rules():
    """All 800 rules: 3 always-on, then 797 of the 800 product-by-situation pairs."""
    rng = random.Random(SEED)
    digits = rng.sample(range(1000, 10000), 800)
    desks = rng.sample(range(100, 1000), 800)
    rules = []
    used = 0
    for si, (sit, (kind, tag, phrasings)) in enumerate(SITUATIONS.items()):
        for pi, product in enumerate(PRODUCTS):
            if kind == "code":
                token = f"{tag}-{digits[used]}"
            elif kind == "line":
                token = str(desks[used])
            else:
                token = f"{ADJECTIVES[(pi + si * 7) % 40]} {tag}"
            used += 1
            text = phrasings[(pi + si) % 3].format(p=product, x=token)
            rules.append({"id": f"{sit}:{product}", "kind": kind, "situation": sit, "product": product,
                          "token": token, "text": text})
    # Three conditional rules make way for the always-on rules, and none of them is a target.
    targets = {(s, p) for _, _, *ts in EMAILS for s, p in ts}
    spare = [r for r in rules if (r["situation"], r["product"]) not in targets]
    drop = {r["id"] for r in random.Random(SEED + 1).sample(spare, len(ALWAYS))}
    return ALWAYS + [r for r in rules if r["id"] not in drop]


def build_emails():
    rng = random.Random(SEED + 2)
    numbers = rng.sample(range(10000, 100000), len(EMAILS))
    out = []
    for i, (name, body, code, line, word) in enumerate(EMAILS):
        order = f"LK-{numbers[i]}"
        out.append({
            "id": f"e{i + 1:02d}", "name": name, "order": order,
            "text": f"Order {order}\n\nHello,\n\n{body}\n\nThanks,\n{name}",
            "targets": [f"{s}:{p}" for s, p in (code, line, word)],
        })
    return out


def rulebook(email, rules, total):
    """The list of rules one email sees at one length.

    Distractors nest: the book of 200 holds the book of 50's distractors, and so on. The three
    targets and three always-on rules each go one to a third of the book, rotated by email so no
    rule kind always sits first. Returns (ordered rules, {rule id: third}).
    """
    by_id = {r["id"]: r for r in rules}
    n = int(email["id"][1:])
    targets = [by_id[t] for t in email["targets"]]
    always = [r for r in rules if r["kind"] == "always"]
    others = [r for r in rules if r["kind"] != "always" and r["id"] not in email["targets"]]
    random.Random(stable(SEED, email["id"], "others")).shuffle(others)
    fill = others[: total - len(targets) - len(always)]

    size = total // 3
    thirds = [[], [], []]
    for i, r in enumerate(fill):
        thirds[i % 3].append(r)
    third_of = {}
    for i, r in enumerate(targets):
        t = (i + n) % 3
        thirds[t].append(r)
        third_of[r["id"]] = t
    for i, r in enumerate(always):
        t = (i + n + 1) % 3
        thirds[t].append(r)
        third_of[r["id"]] = t
    book = []
    for t, part in enumerate(thirds):
        random.Random(stable(SEED, email["id"], total, t)).shuffle(part)
        book.extend(part)
    assert len(book) == total and size >= 2
    return book, third_of


def marked(email, book):
    """Rules marked IMPORTANT in the emphasis arm: one target, one always-on, and enough others
    picked at random to reach one rule in ten, rotated so each target kind gets marked equally."""
    n = int(email["id"][1:])
    target = email["targets"][n % 3]
    always = [r["id"] for r in book if r["kind"] == "always"][n % 3]
    rest = [r["id"] for r in book if r["id"] not in email["targets"] and r["kind"] != "always"]
    random.Random(stable(SEED, email["id"], len(book), "mark")).shuffle(rest)
    return {target, always, *rest[: max(0, len(book) // 10 - 2)]}


INTRO = ("You write email replies for the customer care team at Larkfield Home, a homeware retailer. "
         "Reply with only the email to send, ready to go.")
LIST_FIRST = ("Before the email, list the numbers of the rules that apply to this customer's message, "
              "then write a line containing only ---, then the email.")


def system_prompt(book=None, emphasised=(), list_first=False):
    if book is None:
        return INTRO
    lines = []
    for i, r in enumerate(book, 1):
        mark = "IMPORTANT: " if r["id"] in emphasised else ""
        lines.append(f"{i}. {mark}{r['text']}")
    tail = f"\n\n{LIST_FIRST}" if list_first else ""
    return f"{INTRO}\n\nThe team's rules:\n\n" + "\n".join(lines) + tail


def main():
    (ROOT / "data").mkdir(exist_ok=True)
    (ROOT / "data" / "rules.json").write_text(json.dumps(build_rules(), indent=1, ensure_ascii=False))
    (ROOT / "data" / "emails.json").write_text(json.dumps(build_emails(), indent=1, ensure_ascii=False))
    print(len(build_rules()), "rules,", len(build_emails()), "emails")


if __name__ == "__main__":
    main()
