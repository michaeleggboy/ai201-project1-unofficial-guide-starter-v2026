"""
Your test questions.

Milestone 2 asks you to write five questions your system should be able to
answer from your corpus, specific enough to have a right answer.

  ✗ "What are good dining halls?"          — no right answer
  ✓ "What do students say about wait times at Commons during lunch?"

Fill in `QUESTIONS` below. `expects` is a word or short phrase you'd expect a
correct answer to contain — you'll use it in unit 2 when you build a scorer,
and having written it now means you decided what "correct" meant before you saw
any results.

`OUT_OF_SCOPE` holds five questions your documents clearly don't cover. You
need these in Milestone 4 to find where your relevance cutoff belongs, and
again in unit 2, where `run_eval.py` runs them through the gate and writes what
happened into your run log — that's the evidence for criterion 3.

Swap them for your own if you like. Keep five of them either way: criterion 3
names a target of "4 of 5", and four of three is not a thing.
"""

QUESTIONS = [
    # {"question": "...", "expects": "..."},
    {"question": "Where is the good food?", "expects": "good cooking"},
    {"question": "When should I go to Brightwater?", "expects": "May and June"},
    {"question": "Where is the regional hub?", "expects": "Marchwood"},
    {"question": "When do coastal business start closing?", "expects": "November"},
    {"question": "How is mobile coverage?", "expects": "good in the centre"},
]

# Questions from a different world entirely. Your gate should refuse all five.
#
# There are five of these because criterion 3 in criteria.md names a target of
# "at least 4 of 5" — you need five things to try before you can report 4 of 5.
# `run_eval.py` runs these through retrieval and the gate on every eval and
# records what happened, so criterion 3 has evidence in the run log alongside
# the others. They cost no model calls: a refusal never reaches the model.
OUT_OF_SCOPE = [
    "What is the capital of Mongolia?",
    "How do I change the oil in a diesel engine?",
    "Who won the 1994 World Cup?",
    "What is the recommended dosage of ibuprofen for a headache?",
    "How do I write a for loop in Rust?",
]

# Criterion 5. The hard ones: questions this corpus cannot answer, which
# retrieval is nonetheless confident about.
#
# Two kinds, and they fail the same way for the same reason.
#
# The first five name something the guides genuinely cover — the museum on Fell
# Street, Marchwood's day ticket, Kestrelford's phone-only taxis — and then ask
# for the one specific the guides never state. The corpus has no opening hours,
# no prices, no phone numbers and no population figures in it anywhere; I
# checked before writing these.
#
# The last one names a town that does not exist. I found this by typing
# "Bridgewater" instead of "Brightwater" in one of my own test questions and
# getting a confident answer about Brightwater back. Following it up: Northwater
# retrieves at 0.424, Swanmouth at 0.468, and Reykjavik at 0.597 — all three
# under the 0.6 cutoff, all three answered. The gate is matching the SHAPE of
# "when should I go to X?" and never looks at X. Northwater stands in for that
# whole class here; "Bridgewater" itself would be a worse test, because a typo
# has a defensible right answer and an invented town does not.
#
# What they have in common is that retrieval succeeds and the corpus still can't
# answer, so the gate is blind to all six: the distances are 0.26–0.47, better
# than my five real questions score. Criterion 3's questions get refused for
# being far away. These are close and unanswerable, which is the failure a
# distance cutoff cannot catch by construction.
#
# `scorer.py::audit_near_miss` runs them. It costs one model call each, because
# unlike the gate questions these DO reach the model — that's the whole point.
NEAR_MISS = [
    "What time does the museum on Fell Street open?",
    "How much does a day ticket cost in Marchwood?",
    "What is the phone number for a taxi in Kestrelford?",
    "How many people live in Brightwater?",
    "Does the hospital in Brightwater have an A&E department?",
    "When should I go to Northwater?",
]


def answered() -> list[dict]:
    """The questions you've actually filled in."""
    return [q for q in QUESTIONS if q.get("question", "").strip()]
