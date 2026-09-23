"""
The judge: does one answer count as correct?

`run_eval.py` finds `judge` here automatically and puts a pass/fail in the Run
columns instead of the raw text.

Why fuzzy matching rather than `expects in answer`. The substring version fails
on things that are plainly correct:

    expects  "May and June"
    answer   "The best time to visit is May–June."          -> substring: fail

The model paraphrases, changes an "and" to an "or", uses an en dash, pluralises
a word. None of that makes the answer wrong, but all of it breaks `in`. RapidFuzz
scores how close two strings are instead of demanding they be identical, so the
judge measures what the criteria actually say — that the answer contains the
thing I decided beforehand a correct answer contains.

What this checks, mapped to criteria.md:

  criterion 1  the retrieved chunks contain the answer   -> Verdict.chunks_have_expects
  criterion 2  every answer names a source               -> Verdict.names_source
  criterion 4  one chunk, one town                       -> audit_chunks()
  criterion 5  near-miss questions get refused           -> audit_near_miss()

Criteria 4 and 5 aren't about a single answer, so they aren't part of `judge`.
Run them with `python scorer.py` — criterion 4 is free and runs by default,
criterion 5 costs one model call per question and needs `--near-miss`.

`Verdict.in_one_chunk` is the old criterion 5, which the revised criteria.md
retired. It still gets measured because it costs nothing to keep and it's the
thing to look at when criterion 1 passes and the answer is wrong anyway.

`judge` returns a single bool, because that's what `run_eval.py` wants: an
answer passes when it isn't a refusal, it contains what I said it should, and it
names a source — criterion 2 is "every answer", so an answer that skips its
source is a fail whatever else it got right. `score` returns all of it, so the
per-criterion rows in the run log come off the same measurement rather than a
second read-through by eye.

Criterion 3 (the gate on out-of-corpus questions) isn't judged here — it never
reaches an answer. `run_eval.py::check_out_of_scope` measures that one.
Criterion 4 is about chunks, not answers, so it isn't here either.

⚠️ On calibration. There are two numbers in this file that could be anything —
MATCH_THRESHOLD and the word-level threshold — and a judge whose numbers were
picked to agree with examples written alongside it has been talked into its
answer rather than measured into it. So there are no example answers in this
file. `calibrate.py` reads the real answers out of results/, takes my labels on
them, and reports where the thresholds can sit. Every number below comes from
that, and the day a run disagrees with me is the day it gets re-run.
"""

import re
from dataclasses import dataclass, field

from rapidfuzz import fuzz, utils

import gate

# How close a match has to be, out of 100.
#
# Calibrated by `calibrate.py` against the answers in results/ — real output
# from real runs, labelled by hand. Not against examples written here to be
# passed, which is a way of measuring nothing.
#
# What the real data says: answers I labelled correct score 78–100, and answers
# scored against a question they don't answer reach 76. Those two numbers are
# two points apart, so the threshold is NOT what separates them and no value
# would be. The content-word check in `contains` is what does that work, and the
# threshold's job is only to keep obviously-unrelated text out.
#
# Re-run `python calibrate.py` after any run that produces a verdict you
# disagree with. A judge nobody re-checks stops being a measurement.
MATCH_THRESHOLD = 75.0

# Stricter, and deliberately. A filename either got named or it didn't; the
# slack here is for punctuation and case ("food.md" vs "Food.md", "per food.md"
# vs "(food.md)"), not for paraphrase.
SOURCE_THRESHOLD = 90.0


def similarity(needle: str, haystack: str) -> float:
    """How well `needle` turns up inside `haystack`, 0–100.

    Two RapidFuzz scorers, and the better of the two wins, because they fail on
    different things:

      partial_ratio    finds the best-matching window of `haystack`, so it
                       handles the phrase being buried in a sentence — but it
                       scores low when the words get reordered.
      token_set_ratio  compares the words as sets, so reordering and filler
                       words cost nothing — but it ignores position entirely.

    "Coverage in the town centre is good" against expects "good in the centre"
    scores 72 on the first and 100 on the second. It's a correct answer. Taking
    the max is what lets the judge say so.

    `utils.default_process` lowercases, strips punctuation and trims, so the
    en-dash-vs-hyphen and trailing-period cases never reach the scorer at all.
    """
    if not needle.strip() or not haystack.strip():
        return 0.0
    return max(
        fuzz.partial_ratio(needle, haystack, processor=utils.default_process),
        fuzz.token_set_ratio(needle, haystack, processor=utils.default_process),
    )


# Words that carry no information about whether the answer is right. A phrase
# matching on nothing but these has matched on nothing.
_FILLER = {
    "a", "an", "the", "and", "or", "of", "in", "on", "at", "to", "is", "are",
    "was", "were", "be", "for", "it", "its", "that", "this", "with", "by",
    "from", "as", "you", "your", "there",
}


def _content_words(phrase: str) -> list[str]:
    return [w for w in utils.default_process(phrase).split() if w not in _FILLER]


def _every_content_word_present(needle: str, haystack: str, threshold: float = 85.0) -> bool:
    """Does each real word of `needle` turn up somewhere in `haystack`?

    The similarity score on its own is too easy to reach with a short phrase
    made of common words. "in the centre but patchy on the coast" scores 84
    against expects "good in the centre" — three words out of four — and 84 is
    a pass. But "good" is the whole claim. Dropping it inverts the answer.

    So a match has to clear the similarity bar *and* account for every content
    word. Word-level matching is fuzzy too, at a tighter 85, which is the range
    where "centre"/"center" and "close"/"closes" still match and two different
    words don't.
    """
    haystack_words = utils.default_process(haystack).split()
    if not haystack_words:
        return False
    return all(
        any(fuzz.ratio(word, candidate) >= threshold for candidate in haystack_words)
        for word in _content_words(needle)
    )


def contains(needle: str, haystack: str, threshold: float = MATCH_THRESHOLD) -> bool:
    """`needle in haystack`, with room for paraphrase but not for missing words."""
    return (
        similarity(needle, haystack) >= threshold
        and _every_content_word_present(needle, haystack)
    )


# Filenames and "Source: ..." lines, however the model decided to punctuate
# them this time: `guide_seasons.md`, (guide_seasons.md), "Source: guide_x.md".
_CITATION = re.compile(
    r"""(?mix)
      ^\s*sources?\s*:.*$                             # a whole Source: line
    | [`'"(\[]*\b[\w-]+\.(?:md|txt|pdf)\b[`'")\]]*    # a filename, any dressing
    """
)


def claim_text(answer: str) -> str:
    """The answer with its citations removed — what it actually claims.

    Measured, not guessed at: scoring the raw answer put three false passes in
    the run log. The mobile-coverage answers cite `guide_marchwood.md`, and
    `expects: "Marchwood"` matched that filename at 100. The judge was reading
    a citation as if it were a claim, and would have scored those answers
    correct for a question about the regional hub.

    Citations still count for criterion 2 — `sources_named` reads the raw
    answer. They just don't count as *content* any more.
    """
    return _CITATION.sub(" ", answer)


# Ways of declining, beyond the gate's own fixed string. The gate refuses in
# exactly one wording; the model, when it declines, uses its own — and criterion
# 5 is measured on questions the gate never sees, so these are the wordings that
# decide it.
_REFUSALS = (
    gate.REFUSAL,
    "don't have enough information",
    "do not have enough information",
    "documents don't say",
    "documents do not say",
    "documents don't specify",
    "documents do not specify",
    "not specified in the documents",
    "no information about",
    "does not contain",
    "doesn't contain",
    "cannot answer",
    "can't answer",
)


def refused(answer: str) -> bool:
    """Did the system decline rather than answer?

    Deliberately literal: it looks for the phrasings above rather than trying to
    work out whether an answer is hedged. An answer that refuses and then
    answers anyway ("the documents don't give a price, but it's about £4") reads
    as a refusal here, and that is the wrong way round — so criterion 5's report
    prints every answer in full underneath its verdict. The judge proposes; the
    reason the text is there is so I can overrule it.
    """
    return any(contains(phrase, answer, threshold=90.0) for phrase in _REFUSALS)


def sources_named(answer: str, results) -> list[str]:
    """Which of the retrieved filenames the answer actually cites.

    Checks the stem as well as the full filename: "says food.md" and "the food
    guide" both name the source, and only the first one contains ".md".
    """
    named = []
    for source in sorted({r.source for r in results}):
        stem = source.rsplit(".", 1)[0]
        if contains(source, answer, SOURCE_THRESHOLD) or contains(
            stem, answer, SOURCE_THRESHOLD
        ):
            named.append(source)
    return named


@dataclass
class Verdict:
    """One answer, measured against every criterion that applies to it."""

    answered: bool                 # not the gate's refusal string
    answer_has_expects: bool       # the answer says what I said it should
    names_source: bool             # criterion 2
    chunks_have_expects: bool      # criterion 1
    in_one_chunk: bool             # criterion 5
    answer_score: float
    best_chunk_score: float
    cited: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        """The bool `run_eval.py` puts in the Run column."""
        return self.answered and self.answer_has_expects and self.names_source

    def summary(self) -> str:
        """One line, for when a verdict is surprising and you want to know why."""
        if not self.answered:
            return "refused (gate or model declined to answer)"
        bits = [
            f"answer {self.answer_score:.0f}/100",
            f"best chunk {self.best_chunk_score:.0f}/100",
            f"cited {', '.join(self.cited) if self.cited else 'nothing'}",
        ]
        if not self.chunks_have_expects:
            bits.append("retrieval missed it (criterion 1)")
        elif not self.in_one_chunk:
            bits.append("split across chunks (criterion 5)")
        return " · ".join(bits)


def score(question: str, expects: str, answer: str, results) -> Verdict:
    """Measure one answer. Everything `judge` knows, kept rather than thrown away.

    `question` isn't used. It stays in the signature because `run_eval.py` calls
    with it and because the obvious next version of this judge — handing the
    question, the answer and the chunks to a model and asking it to grade them —
    needs it.
    """
    answered = not refused(answer)
    claim = claim_text(answer)

    # Criterion 1 vs criterion 5. Criterion 1 asks whether the answer is in the
    # retrieved chunks at all, so it's allowed to be spread over two of them —
    # that's the joined text. Criterion 5 asks whether it sits whole inside one,
    # which is the per-chunk check. When the first passes and the second doesn't,
    # a chunk boundary landed in the middle of the sentence that answers the
    # question, which is the exact failure criterion 5 was written to catch.
    joined = "\n".join(r.text for r in results)

    cited = sources_named(answer, results)

    return Verdict(
        answered=answered,
        answer_has_expects=contains(expects, claim),
        names_source=bool(cited),
        chunks_have_expects=contains(expects, joined),
        in_one_chunk=any(contains(expects, r.text) for r in results),
        answer_score=similarity(expects, claim),
        best_chunk_score=max((similarity(expects, r.text) for r in results), default=0.0),
        cited=cited,
    )


def judge(question: str, expects: str, answer: str, results) -> bool:
    """Did this answer pass? The entry point `run_eval.py` looks for."""
    return score(question, expects, answer, results).passed


# ─── Criterion 4: one chunk, one town ────────────────────────────────────────

# The towns this corpus is organised around, which is corpus knowledge and
# belongs next to the thing that measures it. Change the corpus and this list
# changes with it — `audit_chunks` says so out loud rather than reporting 0%.
TOWNS = [
    "Brightwater", "Corry Vale", "Elder Ness", "Givens Mill", "Halden Bay",
    "Kestrelford", "Marchwood", "Pellew Sands", "Thornby Wells",
]

CHUNK_TARGET = 0.8  # "at least 4 of every 5", from criteria.md


def towns_in(text: str) -> list[str]:
    """Which towns a piece of text names. Fuzzy, so possessives and typos count."""
    return [town for town in TOWNS if contains(town, text)]


@dataclass
class ChunkAudit:
    total: int
    single: list[tuple[str, list[str]]]      # (label, [one town])
    mixed: list[tuple[str, list[str]]]       # names two or more
    placeless: list[tuple[str, list[str]]]   # names none

    @property
    def rate(self) -> float:
        return len(self.single) / self.total if self.total else 0.0

    @property
    def passed(self) -> bool:
        return self.rate >= CHUNK_TARGET

    def report(self) -> str:
        lines = [
            f"Criterion 4 — one chunk, one town",
            f"  {len(self.single)} of {self.total} chunks name exactly one town "
            f"({self.rate * 100:.0f}%), target {CHUNK_TARGET * 100:.0f}%"
            f"  -> {'PASS' if self.passed else 'MISS'}",
            f"  {len(self.mixed)} name two or more · {len(self.placeless)} name none",
        ]
        worst = sorted(self.mixed, key=lambda x: -len(x[1]))[:5]
        if worst:
            lines.append("  the most mixed:")
            lines += [f"    {label:34} {', '.join(towns)}" for label, towns in worst]
        if self.placeless:
            lines.append("  naming no town at all:")
            lines += [f"    {label}" for label, _ in self.placeless[:5]]
        return "\n".join(lines)


def audit_chunks(chunks=None) -> ChunkAudit:
    """Measure criterion 4 over every chunk. Local, no model calls, free.

    Over all of them rather than a sample of five: the chunker is deterministic,
    reading them costs nothing, and "4 of 5 sampled" was only ever a sample
    because a person was going to do it by hand.
    """
    if chunks is None:
        from chunker import split_documents
        from ingest import load_documents

        chunks = split_documents(load_documents())

    single, mixed, placeless = [], [], []
    for chunk in chunks:
        found = towns_in(chunk.text)
        entry = (chunk.label, found)
        if len(found) == 1:
            single.append(entry)
        elif found:
            mixed.append(entry)
        else:
            placeless.append(entry)

    return ChunkAudit(len(chunks), single, mixed, placeless)


# ─── Criterion 5: near-miss questions ────────────────────────────────────────


def audit_near_miss(questions=None, top_k=None, threshold=None) -> list[dict]:
    """Measure criterion 5. ⚠️ One model call per question.

    These questions reach the model, which is the point of them: the gate can't
    refuse a question whose retrieval is this good, so what's being tested is
    whether the grounding instruction holds when the chunks are relevant and the
    answer still isn't in them.

    Caching is off. A cached refusal from yesterday is not evidence about today.
    """
    import config
    import gate as gate_module
    import questions as qs
    from generate import answer_from_chunks
    from store import search

    questions = questions if questions is not None else getattr(qs, "NEAR_MISS", [])
    rows = []

    for question in questions:
        results = search(question, top_k=top_k or config.TOP_K)
        decision = gate_module.check(results, threshold=threshold)

        if decision.passed:
            answer = answer_from_chunks(question, results, cache=False)
            stopped_by = "prompt" if refused(answer) else None
        else:
            answer = gate_module.REFUSAL
            stopped_by = "gate"

        rows.append(
            {
                "question": question,
                "best_distance": decision.best_distance,
                "gate_passed": decision.passed,
                "answer": answer,
                "refused": refused(answer),
                "stopped_by": stopped_by,
                "sources": sorted({r.source for r in results}),
            }
        )

    return rows


def near_miss_report(rows: list[dict]) -> str:
    """Criterion 5's verdict, with every answer printed under it.

    The full text is not padding. `refused` is a phrase match, and the answer
    that matters most — a refusal followed by a number anyway — is exactly the
    one it gets wrong. Reading them is part of the measurement.
    """
    kept = sum(r["refused"] for r in rows)
    lines = [
        "Criterion 5 — near-miss questions get refused, not answered",
        f"  refused {kept} of {len(rows)}, target {len(rows)} of {len(rows)}"
        f"  -> {'PASS' if kept == len(rows) else 'MISS'}",
        "",
    ]
    for row in rows:
        by = f", stopped by the {row['stopped_by']}" if row["stopped_by"] else ""
        lines += [
            f"  {'refused' if row['refused'] else 'ANSWERED IT'}  "
            f"(best distance {row['best_distance']:.3f}, "
            f"gate {'passed' if row['gate_passed'] else 'refused'}{by})",
            f"    Q: {row['question']}",
            f"    A: " + row["answer"].replace("\n", "\n       "),
            "",
        ]
    if all(r["gate_passed"] for r in rows):
        lines.append("  The gate let every one of these through — as expected. "
                     "Whatever refusals happened came from the prompt.")
    return "\n".join(lines)


if __name__ == "__main__":
    import sys

    print(audit_chunks().report())

    if "--near-miss" in sys.argv:
        print()
        rows = audit_near_miss()
        print(near_miss_report(rows))
    else:
        print("\nCriterion 5 — near-miss questions")
        print("  Not run: it costs one model call per question. "
              "`python scorer.py --near-miss` to measure it.")
