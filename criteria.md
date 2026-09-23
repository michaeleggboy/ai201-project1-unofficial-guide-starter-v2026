# Acceptance criteria — The Unofficial Guide

Five criteria that say what "working" means for this system, written in unit 1
**before** any results existed.

An acceptance criterion names a target: a number, a count, a rate, or something
a person could plainly observe. *"Retrieval works"* is an opinion. *"For at
least 4 of my 5 test questions, the top results include a chunk containing the
answer"* is a criterion.

Under each one, write a sentence or two on **why that target** and not a
stricter or looser one. A reason that says something about your corpus or your
pipeline earns credit; *"80% seemed reasonable"* does not.

> Missing your own targets next unit costs you nothing. Setting a target so
> easy you can't miss it does.

---

## 1. Retrieved chunks contain the answer

For at least 4 of my 5 test questions, the retrieved chunks include one that
contains the answer.

**Why this target:**
One of my questions is specific to single document.

---

## 2. Every answer names a source

Every answer the system produces names at least one source document.

**Why this target:**
All my questions are pulled directly from the documents, so all corrects answers should be able to reference a document.

---

## 3. The relevance gate stops out-of-corpus questions

When I ask a question my documents clearly don't cover, the relevance gate
stops it and the system returns "I don't have enough information about that" —
in at least 4 of 5 tries.

<!-- The five questions are the ones in `OUT_OF_SCOPE` at the bottom of
     `questions.py`, and `run_eval.py` puts them through the gate and writes
     what happened into your run log. Swap them for your own if you'd rather —
     just keep five of them, or the "4 of 5" above has nothing to be 4 of. -->

**Why this target:**
It is safe bound as all five questions are fully out of scope of the documents. It allows just enough wriggle room where the RAG does not have to perfect but still good as identifying information it does not have information about.

---

## 4. Something about your chunks

At least 3 of 5 sampled chunks focus on the same topic.

**Why this target:**
This is good indicator that chunking will produce good answers. 3 of 5 allows wiggle room in case
it is difficult to find a topical grouping.

> **Revised in unit 2:** At least 4 of every 5 chunks name exactly one of the
> region's towns — not two or more, and not none. Measured over every chunk
> rather than a sample of five, by `scorer.py::audit_chunks`.
>
> **Why revised:** I couldn't check "focus on the same topic" the same way
> twice. There's no test in it — I'd be reading five chunks and deciding how I
> felt about them, and I'd have felt differently on a different day. Every
> guide in this corpus is organised by town, so "one town per chunk" is the
> same idea with something a program can check.
>
> It's the same idea because a chunk naming four towns is what "unfocused"
> actually costs me: it sits close in embedding space to a question about any
> of the four, answers none of them precisely, and gets retrieved instead of
> the chunk that would have answered. 4 of 5 rather than 5 of 5 because a few
> chunks are genuinely regional — the transport summary compares towns on
> purpose, and should.
>
> The target went up, not down. I measure 75 of 115 — 65% — so this is a
> number I am currently missing, and the point of setting it there is to find
> out whether paragraph-per-chunk splitting can reach it at all.

---

## 5. Your choice

For at least 4 of my 5 test questions, the answer lives entirely within one retrieved chunk, not split across two adjacent chunks.

**Why this target:**
My chunk size is small relative to how some source paragraphs are structured, so the real risk isn't "bad chunks" in the abstract, it's a chunk boundary landing in the middle of the one sentence that answers a question.

> **Revised in unit 2:** For all 6 of my near-miss questions — ones this corpus
> cannot answer but retrieval is confident about — the system says it doesn't
> have enough information instead of answering. Five ask for a specific the
> guides never state (the museum's opening hours, a day ticket's price); the
> sixth asks about a town that does not exist. They're in `NEAR_MISS` in
> `questions.py`, and `scorer.py::audit_near_miss` runs them.
>
> **Why revised:** Not because I missed the original — I met it on all five
> questions on the first run, and it has told me nothing since. It was a
> criterion about a risk that turned out not to exist in this corpus, so it
> can't fail and can't teach me anything. I've kept measuring it anyway
> (`Verdict.in_one_chunk` in `scorer.py`) because it costs nothing to keep and
> it's what I'd look at first if criterion 1 ever passes while the answer is
> wrong. It just isn't worth one of my five criteria any more.
>
> What replaced it is a limit I can show. Criterion 3's questions come from a
> different world and the gate refuses them easily — 0.81 to 0.98 against a 0.6
> cutoff. That flatters the gate. But the guides mention the museum on Fell
> Street without its opening hours, day tickets without a price, taxis that
> must be phoned without a number. Ask for those and retrieval works perfectly:
> the right chunk comes back at 0.26 to 0.47, closer than any of my five real
> test questions. The gate cannot refuse them, by construction — it only sees
> distance, and by that measure these are the best questions it has ever been
> asked. The only thing between a user and an invented bus fare is the "say you
> don't have enough information" line in the prompt, which is a request, not a
> mechanism.
>
> The sixth question came out of a typo in my own test set: I had written
> "Bridgewater" where the corpus says "Brightwater", and the system answered
> about Brightwater without ever mentioning that I'd named somewhere else. That
> isn't a spelling problem. Northwater retrieves at 0.424, Swanmouth at 0.468,
> Reykjavik at 0.597 — every one under the cutoff, every one answered. The gate
> is matching the shape of "when should I go to X?" and never reads X at all,
> so a question about a town I invented is indistinguishable to it from a
> question about a town in the corpus.
>
> All 6 of 6, not 5 of 6, because the failure here is a confident fabricated
> number with a real filename cited next to it. One of those is worse than five
> refusals, so there's no allowance worth making.

---

<!-- ─────────────────────────────────────────────────────────────────────────
     UNIT 2 — read this before you change anything above.

     If a criterion turns out to be BROKEN rather than merely unmet, you can
     revise it, and that earns credit. But never delete or edit the original
     line. Add the revision underneath it, like this:

         ## 1. Retrieved chunks contain the answer

         For at least 4 of my 5 test questions, the retrieved chunks include
         one that contains the answer.

         **Why this target:** ...

         > **Revised in unit 2:** For at least 4 of 5 questions, the top three
         > results contain the answer.
         >
         > **Why revised:** I couldn't judge "the chunks include one that
         > contains the answer" the same way twice — I scored two questions
         > differently on Monday than on Wednesday. The new version is
         > something I can actually check.

     That's a revision because the criterion couldn't be MEASURED.

     Lowering a target because you missed it is not a revision, and it costs
     you the point:

         ✗ "I said 4 of 5 but got 2 of 5, so 2 of 5 is more realistic."

     A number you missed stays where it is, gets diagnosed, and gets a fix
     attempted. That's where the points are.

     The whole reason the originals stay visible is so someone can see what you
     said before you knew the answer.
     ───────────────────────────────────────────────────────────────────────── -->
