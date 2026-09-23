#!/usr/bin/env python3
"""
Check the judge against real answers instead of flattering examples.

    python calibrate.py --label     label the real answers in results/, once
    python calibrate.py             report where the judge and I disagree

Why this file exists. `scorer.py` has thresholds in it, and a threshold can be
set to whatever makes the results look good. The usual way that happens isn't
dishonest, it's lazy: you write a handful of example answers next to the judge,
pick the number that gets them all right, and now the judge agrees with a set of
examples written by the person who wanted it to agree. It has been talked into
its answer. Nothing has been measured.

So the calibration set here is not written by hand. It is:

  POSITIVES — the actual answers in results/*.md, produced by this system, with
      the labels I gave them by reading them. `--label` walks through them
      one at a time and stores what I said in results/labels.json. That part
      has to be mine: whether an answer is correct is the judgement the whole
      project is about, and it's not one a regex gets to make.

  NEGATIVES — those same real answers, scored against a *different* question's
      `expects`. The answer about mobile coverage is not an answer to "when
      should I go to Bridgewater", so "May and June" must not match it. These
      need no labelling, because the label follows from how they were built,
      and there are 60 of them rather than the three or four I'd have had the
      patience to invent.

The negatives are where the real bugs turned up. Three of them scored 100 —
because the mobile-coverage answers cite `guide_marchwood.md`, and `expects:
"Marchwood"` was matching the filename. The judge was reading citations as
claims. That's in `scorer.claim_text` now, and it is not a bug I would have
thought to write an example for.
"""

import argparse
import hashlib
import itertools
import json
import re
import sys
from pathlib import Path

import config
import questions as qs
import scorer

LABELS = config.RESULTS_DIR / "labels.json"

# The shape `run_eval.py::write_report` writes: a heading, the two bullet lines,
# then the answer in a fenced block.
# No re.DOTALL here, deliberately: with it, the `- ...` bullet lines match
# across newlines and one "section" swallows the rest of the file. The answer
# body is the only part allowed to span lines, so it says so itself.
_SECTION = re.compile(
    r"^### (?P<question>.+?) — run (?P<run>\d+)\n\n"
    r"(?P<meta>(?:- .*\n)+)\n"
    r"```\n(?P<answer>[\s\S]*?)\n```",
    re.M,
)


def load_answers() -> list[dict]:
    """Every real answer in results/, newest file last so later runs win."""
    seen: dict[str, dict] = {}
    for path in sorted(config.RESULTS_DIR.glob("run_*.md")):
        for m in _SECTION.finditer(path.read_text(encoding="utf-8")):
            answer = m.group("answer").strip()
            item = {
                "question": m.group("question"),
                "run": int(m.group("run")),
                "answer": answer,
                "file": path.name,
                "key": _key(m.group("question"), answer),
            }
            seen[item["key"]] = item
    return list(seen.values())


def _key(question: str, answer: str) -> str:
    """Identify an answer by its text, so labels survive new run logs.

    Keyed on the answer rather than on question-plus-run-number because run 2 of
    one eval and run 2 of the next are different answers. Same text, same label;
    new text, and I'm asked again.
    """
    blob = f"{question}\n{answer}".encode("utf-8")
    return hashlib.sha256(blob).hexdigest()[:12]


def read_labels() -> dict[str, bool]:
    if not LABELS.exists():
        return {}
    return json.loads(LABELS.read_text(encoding="utf-8"))


def write_labels(labels: dict[str, bool]) -> None:
    config.RESULTS_DIR.mkdir(exist_ok=True)
    LABELS.write_text(json.dumps(labels, indent=2, sort_keys=True), encoding="utf-8")


def expects_for() -> dict[str, str]:
    return {q["question"]: q.get("expects", "") for q in qs.answered()}


# ─── Labelling ───────────────────────────────────────────────────────────────


def label(answers: list[dict], relabel: bool = False) -> None:
    """Read each real answer and say whether it's correct. y / n / s / q."""
    labels = read_labels()
    expects = expects_for()

    todo = [a for a in answers if relabel or a["key"] not in labels]
    if not todo:
        print(f"All {len(answers)} answers already labelled in "
              f"{LABELS.relative_to(config.ROOT)}. Use --relabel to go again.")
        return

    print(f"{len(todo)} answer(s) to label. y = correct, n = not, s = skip, q = stop.\n")

    for i, item in enumerate(todo, 1):
        print(f"── {i}/{len(todo)}  {item['question']}  (run {item['run']}, {item['file']})")
        print(f"   expects: {expects.get(item['question'], '(unknown question)')!r}\n")
        print("   " + item["answer"].replace("\n", "\n   "))

        reply = ""
        while reply not in {"y", "n", "s", "q"}:
            reply = input("\n   correct? [y/n/s/q] ").strip().lower()

        if reply == "q":
            break
        if reply != "s":
            labels[item["key"]] = reply == "y"
        print()

    write_labels(labels)
    print(f"Wrote {len(labels)} label(s) to {LABELS.relative_to(config.ROOT)}. "
          f"Commit it — it's what the thresholds are calibrated against.")


# ─── The report ──────────────────────────────────────────────────────────────


def build_pairs(answers: list[dict], labels: dict[str, bool]) -> tuple[list, list]:
    """(labelled positives, negatives). Each entry is (score, passes, note)."""
    expects = expects_for()
    positives, negatives = [], []

    for item in answers:
        mine = expects.get(item["question"])
        if mine is None:
            continue
        claim = scorer.claim_text(item["answer"])
        note = f"{item['question'][:36]!r} run{item['run']}"

        labelled = labels.get(item["key"])
        if labelled is not None:
            entry = (scorer.similarity(mine, claim), scorer.contains(mine, claim),
                     f"{mine!r} <- {note}")
            (positives if labelled else negatives).append(entry)

        # Cross-pairs. Real answer, wrong question's expects, label implied.
        for other, e in expects.items():
            if other != item["question"]:
                negatives.append((
                    scorer.similarity(e, claim),
                    scorer.contains(e, claim),
                    f"{e!r} <- {note}",
                ))

    return positives, negatives


def report(answers: list[dict]) -> int:
    labels = read_labels()
    unlabelled = [a for a in answers if a["key"] not in labels]
    positives, negatives = build_pairs(answers, labels)

    print(f"{len(answers)} real answer(s) in {config.RESULTS_DIR.name}/ · "
          f"{len(labels)} labelled · {len(positives)} positive, "
          f"{len(negatives)} negative pair(s)\n")

    if unlabelled:
        print(f"⚠️  {len(unlabelled)} answer(s) not labelled and so not counted. "
              f"Run `python calibrate.py --label`.\n")

    false_passes = [p for p in negatives if p[1]]
    false_fails = [p for p in positives if not p[1]]

    print("The judge disagrees with me on:" if (false_passes or false_fails)
          else "The judge agrees with every labelled answer and every cross-pair.")
    for s, _, note in sorted(false_passes, reverse=True):
        print(f"  FALSE PASS  {s:5.1f}  {note}")
    for s, _, note in sorted(false_fails):
        print(f"  FALSE FAIL  {s:5.1f}  {note}")

    if not positives:
        print("\nNo labelled positives yet, so there's nothing to calibrate against.")
        return 1

    pos = sorted(s for s, *_ in positives)
    neg = sorted(s for s, *_ in negatives)

    print(f"\n  correct answers score  {pos[0]:.0f}–{pos[-1]:.0f}")
    print(f"  wrong pairings score   {neg[0]:.0f}–{neg[-1]:.0f}")
    print(f"  threshold now          {scorer.MATCH_THRESHOLD:.0f}")

    # Can the score alone do the job, or is the content-word check carrying it?
    if neg[-1] < pos[0]:
        low, high = neg[-1], pos[0]
        print(f"\nThe score alone separates them: any threshold in ({low:.0f}, {high:.0f}] "
              f"would give the same verdicts. Middle of that is {(low + high) / 2:.0f}.")
    else:
        overlap = sum(1 for s in neg if s >= pos[0])
        print(f"\nThe score alone does NOT separate them — {overlap} wrong pairing(s) "
              f"score at or above the lowest correct answer ({pos[0]:.0f}).")
        print("No threshold fixes that, which is the whole reason `contains` also "
              "requires every content word. Those pairings fail on the words.")

    return 1 if (false_passes or false_fails) else 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--label", action="store_true", help="label unlabelled answers")
    parser.add_argument("--relabel", action="store_true", help="label all of them again")
    args = parser.parse_args()

    answers = load_answers()
    if not answers:
        print(f"No run logs in {config.RESULTS_DIR.name}/ to calibrate against.\n"
              f"Run `python run_eval.py` first — this needs real output, and "
              f"answers written by hand to be passed are not that.", file=sys.stderr)
        sys.exit(1)

    if args.label or args.relabel:
        label(answers, relabel=args.relabel)
        return

    sys.exit(report(answers))


if __name__ == "__main__":
    main()
