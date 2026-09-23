python app.py corpora# The Unofficial Guide

Michael Egbueze - Corpus: city_guides

> **This file is your submission.** Fill it in as you go — most sections get
> written during the milestone that produces them, not at the end.
>
> How the starter works, and every command you'll need, is in `RUNNING.md`.
> Leave that file alone.
>
> **Paste everything as text.** No screenshots, no video. A typed table gets
> full credit; a picture of the same table gets none.
>
> Delete these instruction blocks as you replace them. The `<!-- -->` comments
> are notes to you and don't show up when the page renders — you can leave them
> or remove them.

---

# Unit 1

## What This Does

This is a retrieval-augmented question-answering system built over a small
corpus of travel guides describing towns in one region, with a focus on
mobility and accessibility (how flat a town is, whether it has step-free
transport, where the stepped lanes and hills are). It answers questions like
"which towns are easy to get around with limited mobility" or "does Halden
Bay have parking," pulling the answer from the specific town or section it
belongs to rather than returning a generic summary. It also refuses
questions the corpus doesn't cover, rather than guessing.

## Chunking Strategy

**Chunk size:** 800 characters (fallback only)
**Overlap:** 80 characters (fallback only)

My corpus mixes short posts and long sectioned guides, so a fixed character
window doesn't fit either: it never triggers on short posts, and on guides
it cuts through town names and facts, since entries range from 150 to 400
characters. I split on structure instead: each paragraph is a chunk, and
headers get prepended as context so a fact keeps its section. I only
fall back to the 800/80 character window for the rare paragraph too long to
keep whole. I originally kept only the nearest header as context, but that
dropped the town name on documents titled after a single town, so I switched
to keeping the full header path.

## Sample Chunks

**Chunk 1** — source: ``guide_accessibility.md#0 — produced by: chunker.py::split_documents``

```
Getting around the region with limited mobility

An honest assessment rather than a promotional one. Some of these places are
difficult and it is better to know in advance.
```

**Chunk 2** — source: ``guide_corry_vale.md#4 — produced by: chunker.py::split_documents``

```
Corry Vale — What to see

The valley itself is the attraction. The footpath network is dense and well marked, and a circuit taking in three of the four villages is about nine miles with 500 metres of ascent. The chapel in the second village is 12th century and always unlocked.
```

**Chunk 3** — source: ``guide_givens_mill.md#4 — produced by: chunker.py::split_documents``

```
Givens Mill — What to see

The mill runs tours on the hour from 11 to 3 and the machinery is operating during them, which is loud and much more impressive than a static exhibit. The church has a Saxon doorway. The river walk downstream reaches Brightwater in about three hours.
```

**Chunk 4** — source: ``guide_marchwood.md#3 — produced by: chunker.py::split_documents``

```
Marchwood — Eat and drink

The best eating is in the Northgate district, a 12-minute tram ride from the station, where about thirty restaurants sit within four streets. The area immediately around the station is uniformly poor and expensive. Marchwood keeps later hours than anywhere else in the region — kitchens serve until 10:30pm, and until midnight on Fridays and Saturdays.
```

**Chunk 5** — source: ``guide_seasons.md#2 — produced by: chunker.py::split_documents``

```
When to visit the region — Summer, June to August

June is excellent everywhere. July and August split: Halden Bay becomes very
busy and the parking problem dominates, Kestrelford fills with walkers, and
Brightwater goes quiet to the point of dullness with the university empty.
```

## Sample Answer

**Question:When should I go to Bridgewater?**

**Answer:**

```
  (best distance 0.457, cutoff 0.6)

May and June are the best months to visit Brightwater, with late May being arguably the best week of the year because of long days, everything running, and the students being gone. Winter is cold, and several riverside businesses close entirely from January to March, while July and August are quiet to the point of being dull. 

*(Sources: guide_brightwater.md and guide_seasons.md)*

Sources retrieved: guide_brightwater.md, guide_seasons.md
```

**My relevance cutoff:0.6**


| Question | In corpus? | Best distance |
|---|---|---|
| Where is the good food?  | Yes | 0.540 |
| When should I go to Bridgewater? | Yes | 0.457 |
| Where is the regional hub? | Yes | 0.590 |
| When do coastal business start closing? | Yes | 0.313 |
| How is mobile coverage? | Yes | 0.486 |
| What is the capital of Mongolia? | No | 0.808 |
| How do I change the oil in a diesel engine? | No | 0.881 |
| Who won the 1994 World Cup? | No | 0.982 |
| What is the recommended dosage of ibuprofen for a headache? | No | 0.853 |
| How do I write a for loop in Rust? | No | 0.859 |

## How I Used AI

**1.** I gave Claude the fixed-size `fallback_split` chunker and asked what
chunk size and overlap actually do. Then I had it run the chunker against a
real document. I found that a Kestrelford paragraph got split so the chunk
containing "is built on a slope..." never mentioned Kestrelford at all. That
showed me overlap alone wouldn't fix it, since town entries in my corpus are
all different lengths.

**2.** I asked Claude to write `split_documents` as a structure-aware
chunker: split on headers and paragraphs instead of character count. Its
first version prepended only the nearest header to each chunk
(`header_stack[-1]`). When I tested it on a document where the H1 was the
town's name ("Halden Bay") and each `##` was a section ("Getting there",
"When to go"), every chunk after the first lost the town name entirely. I
had it fix this by joining the full header stack instead of just the last
entry, so chunks now read "Halden Bay - Getting there [chunk content]".

<!-- ── Stretch features ─────────────────────────────────────────────────────
     Doing one? Say so here BEFORE you start. A feature this README never
     claims earns nothing.
     ───────────────────────────────────────────────────────────────────────── -->

---

# Unit 2

<!-- These sections get ADDED to what's already above. Don't delete or rewrite
     unit 1 — the point is that someone can see what you said before you knew
     how it went. -->

## Run Log — Before

<!-- Your five criteria, three runs each. `python run_eval.py --label before`
     runs the questions, puts the OUT_OF_SCOPE ones through the gate, and
     writes it all into results/ for you. Targets come from criteria.md; the
     verdict column is your call.

     Criterion 3 is measured in one deterministic pass rather than three, so
     the same number goes in all three run columns. That's correct, not lazy.

     Milestone 1. -->

Source: `results/run_2026-09-23_1944_before.md`, three runs with caching off.
Config: `TOP_K=5`, `THRESHOLD=0.6`, `CHUNK_SIZE=800`, `CHUNK_OVERLAP=120`,
115 chunks from `chunker.py::split_documents`.

| Criterion | Target | Run 1 | Run 2 | Run 3 | Verdict |
|---|---|---|---|---|---|
| 1. Retrieved chunk contains the answer | 4 of 5 | 5 of 5 | 5 of 5 | 5 of 5 | MET |
| 2. Every answer cites a real, retrieved document (revised) | 5 of 5 | 5 of 5 | 5 of 5 | 5 of 5 | MET |
| 3. Gate stops out-of-corpus questions | 4 of 5 | 5 of 5 | 5 of 5 | 5 of 5 | MET |
| 4. One chunk, one town (revised) | 80% of chunks | 65% | 65% | 65% | **MISSED** |
| 5. Near-miss questions get refused (revised) | 6 of 6 | — | — | — | not yet measured |

Criteria 1, 3 and 4 are retrieval and chunking only — no model call, nothing
random — so one pass is the whole measurement and the same number goes in all
three columns, as the note above says for criterion 3.

Criterion 5 is still outstanding: it needs `python scorer.py --near-miss`, six
model calls. Its gate half is already measured and already failing (below). The
row says "not yet measured" rather than carrying a number I didn't take.

One answer failed the overall judge in run 1 — "Where is the good food?" — and
it did so without failing any of the three criteria above. That is worth more
than the three METs put together, and it's the first diagnosis below.

### Real output

**Criterion 1** — `store.py::search`, judged by `scorer.py::contains`. The
number after each is the rank at which the answering chunk appeared:

```
yes  rank 3  best d=0.540  'good cooking'       Where is the good food?
yes  rank 1  best d=0.256  'May and June'       When should I go to Brightwater?
yes  rank 1  best d=0.590  'Marchwood'          Where is the regional hub?
yes  rank 1  best d=0.313  'November'           When do coastal business start closing?
yes  rank 1  best d=0.486  'good in the centre' How is mobile coverage?
-> 5 of 5
```

**Criterion 3** — `store.py::search` then `gate.py::check`, cutoff 0.6:

```
0.808  refused  What is the capital of Mongolia?
0.881  refused  How do I change the oil in a diesel engine?
0.982  refused  Who won the 1994 World Cup?
0.835  refused  What is the recommended dosage of ibuprofen for a headache?
0.859  refused  How do I write a for loop in Rust?
-> 5 of 5
```

**Criterion 2** — `scorer.py::cite_check`, which sorts every filename an answer
mentions into retrieved, real-but-not-retrieved, and invented. All 15 answers
in this run cite a real document that was actually retrieved; none invented a
filename and none cited a real file it hadn't been given. Checked across both
of today's run logs, that's **24 of 24 answers**. Two examples, run 3:

```text
Coastal businesses begin closing by November. This information comes from `guide_seasons.md`.
    -> grounded: guide_seasons.md | unretrieved: none | invented: none

The regional hub is Marchwood, according to the document `guide_marchwood.md`.
    -> grounded: guide_marchwood.md | unretrieved: none | invented: none
```

**Criterion 4** — `scorer.py::audit_chunks`, over all 115 chunks rather than a
sample of five:

```
Criterion 4 — one chunk, one town
  75 of 115 chunks name exactly one town (65%), target 80%  -> MISS
  37 name two or more · 3 name none
  the most mixed:
    guide_accessibility.md#9   Brightwater, Corry Vale, Elder Ness, Givens Mill, Halden Bay, Kestrelford, Marchwood
    guide_eating.md#5          Givens Mill, Halden Bay, Kestrelford, Thornby Wells
    guide_eating.md#0          Brightwater, Halden Bay, Pellew Sands
```

## Verdicts

<!-- MET or MISSED for each of the five, against the target you wrote last
     unit — not a new one. Plus a sentence on how you decided. That sentence
     matters most where it was close.

     If your target said 4 of 5 and your runs came out 4, 3, 4, that's a MISS.
     The target has to hold, not show up occasionally.

     Milestone 2. -->

| # | Criterion | Verdict | How I decided |
|---|---|---|---|
| 1 | Retrieved chunk contains the answer (4 of 5) | MET | 5 of 5. Not close, but not as comfortable as it looks: on "Where is the good food?" the answering chunk came back at rank 3, and the criterion only asks that it be retrieved at all. At `TOP_K=3` this would be 4 of 5. |
| 2 | Every answer cites a real, retrieved document (5 of 5) | MET | 5 of 5 in all three runs; 24 of 24 across both of today's logs. Every citation resolved to a file that exists and was retrieved — no invented filenames, and none cited a real file it hadn't been given. The original wording ("names at least one source document") couldn't be checked, because it never said the file had to exist; `scorer.py::cite_check` decides that by exact match. |
| 3 | Gate stops out-of-corpus questions (4 of 5) | MET | 5 of 5, at distances 0.808–0.982 against a 0.6 cutoff. See the diagnosis below — this one is met and still misleading. |
| 4 | One chunk, one town (80%) | **MISSED** | 65%, measured over all 115 chunks by `scorer.py::audit_chunks`. 37 chunks name two or more towns, 3 name none. |
| 5 | Near-miss questions get refused (6 of 6) | not yet measured | The gate half is measured and it fails completely: all six questions clear the cutoff at 0.256–0.471, so the gate refuses none of them. Whether the system as a whole refuses depends on the prompt, which needs `python scorer.py --near-miss`. |

## Diagnoses

<!-- For each miss: which stage caused it, and how. The stage alone isn't
     enough — you need the mechanism.

     Not a diagnosis: "Question 3 didn't work."
     A diagnosis:     "Question 3 asks about laundry costs. The answer is in
                       one sentence that got split across two chunks, so
                       neither chunk on its own contains it."

     The five stages: loading → chunking → embedding → retrieval → generation.

     Look for a pattern. If three misses all ask about numbers, that's one
     problem, not three.

     Missed nothing? Say so, then say honestly whether your targets were set
     low, and which one you'd tighten and to what.

     Milestone 3. -->

### "Where is the good food?" — the stage is my judge, not the pipeline

Run 1 failed. Runs 2 and 3 passed. Nothing about the system changed between
them, and the retrieval was byte-identical each time — best distance 0.5399,
same three sources. What changed is one word the model chose:

```text
run 1 (fail): "good food is generally found one street back from wherever the visitors are"
run 2 (pass): "good cooking is typically found one street back from where the visitors are"
```

My `expects` for that question is `"good cooking"`. The judge requires every
content word of `expects` to appear, so "food" where I wrote "cooking" scores
67 out of 100 and fails. The answer is correct — the corpus sentence is "the
good cooking is one street back from wherever the visitors are", and run 1 is a
faithful paraphrase of it that happens to reuse the noun from my own question.

The same thing happened in the earlier log at 19:32, on run 2 rather than run 1.
Two failures out of six attempts at that question, both the identical
food/cooking substitution.

So the stage is generation, but the defect is mine in two places. The narrower
one: `expects: "good cooking"` pins a correct answer to a specific noun when
the guide's point is about *location*, not vocabulary — "one street back" is
the thing a right answer has to contain, and I didn't ask for it. The wider
one: a string-similarity judge cannot know that food and cooking are the same
claim here, and this is the shape of the error it will always make.

I am leaving the failure in the table. Editing `expects` to "one street back"
now would turn two fails into passes, and I only know to prefer that phrasing
because I watched it fail — which is the same move as adopting the chunk metric
that happens to pass, further down. The fix belongs in the next unit's
questions, declared before the run.

### Criterion 4 — chunking, and a paragraph that was never about one town

65% against a target of 80%. The stage is chunking, and the mechanism is that
`chunker.py::split_documents` makes one chunk per paragraph, so a chunk is
about exactly as many towns as its source paragraph is. `guide_eating.md#0` is
one paragraph that names Brightwater, Halden Bay and Pellew Sands, because it
is making a point that holds across all three ("the good cooking is one street
back from wherever the visitors are"). Splitting it would damage it.

Where the 37 mixed chunks come from matters, and it isn't where I expected:

- **16 of 37 are from the topic guides** — eating, accessibility, transport,
  seasons, walking. These compare towns on purpose. A chunk of
  `guide_accessibility.md#9` names seven towns because it is a regional summary
  of step-free access, and it is doing its job.
- **21 of 37 are from town guides** — `guide_givens_mill.md` mentioning
  Marchwood, `guide_thornby_wells.md` mentioning Brightwater. These are
  cross-references: "the nearest full hospital is in Brightwater." The chunk is
  *about* Givens Mill and *mentions* Marchwood, and my measurement can't tell
  those apart.

So the miss is partly the chunker and partly the criterion, and the honest
split is that the second is larger. See **What I'd Do Differently**.

### Criterion 3 — met, and still telling me the wrong thing

This one passed 5 of 5 and I don't trust it. The five out-of-corpus questions
come back at 0.808–0.982 against a 0.6 cutoff, which looks like a wide margin
until you ask what the gate is actually measuring. It isn't reading the
question. `store.py::search` with `gate.py::check` gives:

```text
0.424  LET THROUGH  When should I go to Northwater?     (a town I invented)
0.468  LET THROUGH  When should I go to Swanmouth?      (also invented)
0.597  LET THROUGH  When should I go to Reykjavik?      (real, 1,500 miles away)
```

The gate is matching the *shape* of "when should I go to X?" against the
seasons guide and never reading X at all. Reykjavik clears the cutoff by three
thousandths. My five out-of-scope questions pass not because the gate
understands scope but because I happened to choose questions whose grammar is
also unlike the corpus — "How do I write a for loop in Rust?" is far away in
both senses at once. Criterion 3's target was met by a system that cannot tell
a town in the corpus from one that does not exist.

I found this because of a typo. One of my own test questions said "Bridgewater"
where the corpus says "Brightwater", and the system answered confidently about
Brightwater without ever mentioning I'd named somewhere else. That is criterion
5's question, which is why criterion 5 now includes an invented town.

## The Improvement

**What I changed:** *Not yet done.* The diagnosis above is finished and the fix
is not, so this section is empty rather than filled with something I haven't
run. The candidate, and the diagnosis it comes from, are below.

**Why I picked it:**

The candidate is a second relevance signal in `gate.py` that reads the question
rather than only its distance: if a question names a capitalised place that
appears nowhere in the corpus, refuse it regardless of distance. It comes
directly from the criterion 3 diagnosis — a cutoff on cosine distance cannot
see entities, so no amount of tuning `THRESHOLD` fixes Northwater, and the
0.597 on Reykjavik shows that moving the cutoff down far enough to catch it
would start refusing real questions (my own "Where is the regional hub?" sits
at 0.590).

I have deliberately not touched the chunker for criterion 4, because the
diagnosis says most of that miss is my measurement rather than my chunks, and
changing the pipeline to satisfy a measurement I already distrust is the wrong
order to do things in.

<!-- Connect it to a specific diagnosis above in one sentence. If you can't,
     you picked a fix because it sounded impressive. -->

### Run Log — After

<!-- Same format, same five criteria, three runs each.
     `python run_eval.py --label after` -->

*Not run — there is no change to measure yet.*

| Criterion | Target | Run 1 | Run 2 | Run 3 | Verdict |
|---|---|---|---|---|---|
| 1. Retrieved chunk contains the answer | 4 of 5 |  |  |  |  |
| 2. Every answer cites a real, retrieved document (revised) | 5 of 5 |  |  |  |  |
| 3. Gate stops out-of-corpus questions | 4 of 5 |  |  |  |  |
| 4. One chunk, one town (revised) | 80% of chunks |  |  |  |  |
| 5. Near-miss questions get refused (revised) | 6 of 6 |  |  |  |  |

**Did it help?**

<!-- Say plainly whether it did, and how you know. If it made things worse,
     say that — a change that backfired, honestly reported, earns full credit
     and is more interesting than one that worked. What matters is that you can
     tell.

     Milestone 4. -->

## What's Still Broken

<!-- For each criterion still missed after your fix: what you'd do about it,
     and why you stopped where you did.

     "I ran out of time" is fine if it's true. Pretending nothing is left is
     not.

     Milestone 5. -->

**The gate cannot see entities.** Northwater, Swanmouth and Reykjavik all clear
the cutoff. The fix is sketched above and not built. I'd start by extracting
capitalised place names from the question and refusing when none of them appear
in the corpus, because that is a check on the question rather than on a
distance, and distance is the thing that has been shown not to work here.

**Criterion 5 is unmeasured.** It needs `python scorer.py --near-miss`, six
model calls. The gate half is already measured and already failing, so what's
outstanding is only how often the prompt saves it — the more interesting half,
and the half I can't guess at.

**One question is unstable under my own judge.** "Where is the good food?"
passed 4 of its 6 runs across two logs, and the two failures are the same
food/cooking substitution described above. A criterion measured on that question
will come out differently depending on which run I happen to look at, which is
the thing three runs exist to expose. Fixing it means choosing an `expects`
that names the claim rather than the vocabulary — before the next run, not
after it.

**Criterion 4's measurement is the thing to fix before the chunker is.**
Explained below.

**The judge is a proxy and should be read as one.** `scorer.py` decides
correctness with RapidFuzz string similarity plus a check that every content
word appears, not by understanding the answer. It already caught one thing I
would have missed — it was scoring citations as content, so an answer about
mobile coverage that cited `guide_marchwood.md` matched `expects: "Marchwood"`
at 100 and counted as a correct answer about the regional hub. That's fixed
(`scorer.py::claim_text`). What it cannot catch is an answer that contains the
right phrase inside a wrong claim.

**The judge's thresholds should be re-derived from today's logs.**
`calibrate.py` scores the real answers in `results/` against my own labels, and
builds negatives by pairing each real answer with a different question's
`expects`. That's what found the citation bug. There are now 24 real answers to
calibrate against — `python calibrate.py --label`, then `python calibrate.py` —
and the food/cooking failure is exactly the case where my label and the judge's
verdict will disagree, which is what the labelling pass is for.

## What I'd Do Differently

<!-- Knowing what you know now — which of your five criteria would you write
     differently, and why?

     Milestone 5. -->

**Criterion 4, and I'm leaving the miss standing rather than fixing it by
redefinition.**

I wrote it as "names exactly one town". Having measured it, the right property
was "is *about* one town" — a chunk of `guide_givens_mill.md` that says the
nearest hospital is in Brightwater is a focused chunk containing a
cross-reference, and counting it as unfocused is my measurement's mistake, not
the chunker's.

I measured the alternative, because not knowing seemed worse than knowing:
counting a chunk as focused when its own document's town is among those named
gives **96 of 115, or 83%** — above the 80% target.

I have not adopted that number. Swapping in a metric *after* seeing that it
turns a miss into a pass is the move criteria.md warns about, and the fact that
I can reach either verdict by choosing a definition is the actual finding. The
verdict stays MISSED at 65%. Written from the start, the criterion should have
said "the chunk's subject town", defined subject as the town in the chunk's
header path, and allowed other towns to be mentioned — and it would have been a
harder criterion to satisfy honestly, because it would have required me to
decide what "about" meant before I knew which answer I wanted.

**Criterion 5, as originally written, could not fail.** "The answer lives
entirely within one retrieved chunk" was met on all five questions on the first
run and every run since. A criterion with no way to come out badly measures
nothing; it just feels like a pass. The revised version — near-miss questions
must be refused — is one I can already prove the gate fails.

**Test questions should be checked against the corpus before they're used.**
Mine said "Bridgewater" where every document says "Brightwater". Three runs
passed that question and my scorer agreed, because `expects: "May and June"`
appeared in an answer about a town I hadn't asked about. That is exactly the
failure criterion 5 now exists to catch, and it was sitting inside my own test
set for the whole of unit 1.
