# Experiment ↔ model mapping and design rationale

How the behavioural experiment lines up with the computational model (see
`simulation_briefing.md` for the model itself), and the design decisions that follow
from requiring the two to correspond. The guiding constraint throughout: **keep the
changes to BOTH the experiment and the simulation small, and keep the predicted
dissociation robust.**

> **Start with `CURRENT_STATE.md`** — a single self-contained snapshot of where things
> stand (code map, canonical config, results, retractions, what is open). This file is the
> chronological record and keeps the reasoning, including superseded material.
>
> **Canonical configuration — read §20 first.** As of 2026-08-03 the encoding gain is
> `trust` and there is **no PE write-gate**. Numbers in §12–§19 predate this and were
> produced with `gain="hybrid"`, some with a gate; they are kept for the reasoning and
> the negative results, but any effect size quoted there should be re-read at the
> canonical setting before use. Sample sizes below n=400 in those sections are also no
> longer adequate (§20.6).

---

## 1. The correspondence

| Simulation | Experiment |
|---|---|
| one **cycle** (E1→E2→…→E5) | one **routine** (e.g. restaurant) |
| **event** E1..E5 | a **sub-event** of the routine (sit down / read menu / order …) |
| **schematic dims** (predictable from event identity, ~constant within an event) | the **schema dimension** — *which sub-event* (Block 1) |
| **specific dims** (fresh random center per instance, unpredictable) | the **specific dimension** — *which object variant* (Block 2) |
| `schema_order = "fixed"` vs `"random"` (permute events within a cycle) | ordered group vs **within-instance** scrambled group |
| the never-presented `original_E5` in the false-memory test | the **omitted sub-event** (Block 1 lure) |
| per-timestep `PE = 1 − cos(yhat, y_t)` | the encoding rating *"how well does this follow from the one before it?"* |

Two consequences of this table are load-bearing and are developed below:

- The model's order manipulation is a **within-cycle permutation**. Mapped through the
  table, that is a **within-instance** scramble — never cross-routine. §3.
- The model's recognition readout is a content-based associative match with **no
  external "which experience" retrieval cue**; event identity is carried by the probe's
  schematic dims. §4.

---

## 2. Align the manipulation axis: schema network always ON

Currently the two sides manipulate **different axes**:

- Model: `use_schema` True/False — whether the schema-network component is present
  (an *ablation*), on the same input.
- Experiment: ordered vs scrambled — a *stimulus-order* manipulation.

A human cannot switch off their schema network, so the ablation axis does not map onto
people. The fix (small, and on the driver side, not the architecture):

> **Always run with the schema network on (`use_schema=True`). Manipulate
> `schema_order` (`"fixed"` vs `"random"`) instead.** The schema GRU is trained on the
> fixed order (= the human's *pre-learned* schema) and is **not** retrained; at test it
> simply mispredicts when the order is random.

This makes both sides share one axis — stimulus-order predictability — and encodes the
correct claim: **people always have the schema; the stimulus order decides whether the
schema can be applied.**

Mapping of the two experimental groups onto the aligned model:

- **Ordered group** ≈ `model_sc` on **fixed** order — schema predicts well → residual
  storage removes schematic content cleanly → stored patterns differ mainly in the
  random specific dims → low interference → **good specific memory**.
- **Within-instance scrambled group** ≈ `model_sc` on **random** order — schema
  predictions are wrong → `x − s_t` does not cleanly remove schematic content (and adds
  the wrong thing) → higher interference, corrupted add-back at retrieval → **worse
  specific memory**.

Why it should robustly "work": the effect grows with how wrong `s_t` is under random
order, which grows with prototype separation. Tunable knobs if the effect is weak:
`type_shift` (prototype separation), `noise_specific`, `dim_weight`.

### 2.1 Simulation result — and a correction to the interference claim

> **Superseded in part by §13.** The recall numbers below come from
> `episodic.probe`-style reconstruction cosines, which §13.1 shows are invalid: the cue
> already contains the answer, so the measure reports how much the Hopfield degrades it.
> The order effect is real but far smaller than these numbers imply (§13.2). The
> interference framing is also restated as **load** reduction in §13.4.

**Implemented** in `order_test.py` / `run_order_test.py` (driver change only: the schema
GRU is loaded frozen, `use_schema=True` throughout, and the contrast is `schema_order`).
Ten simulated subjects, each seen under both orders (within-subject, §3.1), checkpoint
`output/seed8000`, paired t-tests:

| measure | ordered | scrambled | p |
|---|---|---|---|
| mean PE | 0.177 | 0.346 | <0.001 |
| interference, **all** dims | 0.105 | 0.165 | 0.052 |
| interference, **schema** dims | 0.048 | 0.165 | **0.011** |
| interference, **specific** dims | 0.143 | 0.145 | 0.13 |
| recall, schema dims | 0.876 | 0.791 | <0.001 |
| **recall, specific dims** | **0.485** | **0.322** | **0.009** |
| n boundaries detected | 5.0 | 4.1 | 0.068 |

**The core prediction holds, untuned:** scrambling makes the schema mispredict (PE roughly
doubles) and specific-dim memory drops. The same contrast in the weaker `"regenerate"`
scramble (fresh stimulus with `schema_order="random"` rather than permuting the ordered
stream's event blocks) is same-signed but smaller — specific recall 0.484 vs 0.377,
p=0.053 — as expected, since regenerating changes content as well as order. The default
`"permute"` mode is the tighter control *and* the faithful analogue of the experiment's
within-instance scramble (§3): identical event blocks, order alone differs.

**But the mechanism above is stated wrongly.** §2 says residual storage makes "stored
patterns differ mainly in the random specific dims → low interference". The learned
`dim_weight` is
`[0.476, 0.355, 1.000, 0.684 | 0.0025, 0.0026, 0.0025, 0.0026]` — **≈ 0 on the four
specific dims**. So the stored residual `x − s_t·dim_weight` is ≈ the raw input there,
and under a within-instance permutation the specific-dim stored patterns are *the same
set of vectors in a different order*. Mean pairwise cosine is permutation-invariant, so
**specific-dim interference cannot show an order effect by construction** — the measured
null (p=0.13) is arithmetic, not evidence. The interference reduction is real but lives
on the **schema** dims.

Two consequences:

- **Measure interference on the schema dims (or all dims), not the specific dims.**
  `test_memory.py:measure_interference_specific` — the repo's default interference
  measure — slices only the specific dims and so reports a null for the central mechanism
  claim. (It also defaults to `n_schema_dims=3` while the configs pass 4, so callers that
  omit the argument fold one schematic dim into the "specific" score.)
  `order_test.py:interference()` reports all three slices.
- **The causal story in §2 needs restating.** Specific-dim *recall* is robustly
  ordered > scrambled while specific-dim *interference* is flat, so the effect does **not**
  propagate through specific-dim interference. It propagates through the schema-dim
  structure of the Hopfield weight matrix: residual quality differs on the schema dims,
  that changes `W`, and that changes the retrieval dynamics for every dimension including
  the specific ones. Worth deciding whether to keep "interference reduction" as the
  headline mechanism or to reframe it as "residual cleanliness on the schematic dims",
  which is what is actually measured. This also bears on §8, where "interference
  reduction" is one of the two competing mechanisms to be traded off against PE-graded
  encoding.

---

## 3. Within-instance scramble, not cross-routine — and why not three groups

A boss suggestion was a "fully mixed up (across routines too)" condition, i.e. a third
group C that scrambles scenes across different routines.

**This has no counterpart in the current model.** `schema_order="random"` permutes
events *within a cycle*; it never destroys the cycle structure or mixes events across
cycles. So a cross-routine condition is something the model, as it stands, does not
simulate and does not predict. Adding it to the experiment would test exactly the thing
we are trying to avoid — a condition the simulation cannot speak to.

It also breaks alignment in two further ways: cross-routine mixing removes schema
*evocation* entirely (there is no coherent script to recognise), and it changes the task
to pure item recognition over a jumble (spec §1). So group C is not a stronger version
of the same manipulation; it is a different, confounded manipulation.

**Rule: the number of experimental groups should equal the number of distinct,
interpretable cells the simulation produces.** Today that is two (fixed vs random, schema
on). If a third group is ever wanted, add and validate a third *model* condition first
(e.g. a "schema-not-evoked" cell), confirm it yields a distinct, ordered prediction, and
only then add the group to the experiment — never the other way round.

**Decision: within-instance scrambling (never cross-routine). The ordered/scrambled factor is
run WITHIN subject** — each subject sees 4 routines ordered and 4 within-instance scrambled,
counterbalanced so each routine is ordered for ~half of subjects. (Between-subjects is kept
available behind `config.design`.) See §3.1 for why within-subject, and §8/§8.1 for why the
model supports it.

### 3.1 Why within-subject

The model's schema benefit is a **per-routine** mechanism (residual storage is applied per
sub-event using the schema's prediction for *that* routine), not an encoding-wide mode. So a
subject who has some routines ordered and some scrambled is fine at the mechanism level, and the
model's continuous run (§8.1) naturally accommodates a mix of ordered and scrambled routines in
one stream. Within-subject also gives each subject the **full PE range** (their ordered routines
are low-PE, their scrambled routines high-PE), which is what the per-item U-shape analysis wants
(§8). The cost is human strategic carryover and demand characteristics (amplified by the rating);
these are the reasons `config.design = "between-subject"` is kept as a fallback.

---

## 4. The "In the X experience…" context cue

The model's recognition readout is a **content-based global associative match**: a probe
(schematic + specific dims) is matched against the Hopfield; the probe's *schematic dims*
carry the event identity. There is **no external cue that restricts retrieval to one
experience** — nothing in the model corresponds to "In the restaurant experience…".

To match that mechanism, the behavioural questions should let their **content** carry the
identity (the wording is already routine-specific — "ordered from the waiter", "waited at
the gate"), rather than an explicit source-restricting cue. So:

- **Block 2:** the scene image already supplies the context; the cue is pure redundancy →
  drop it. (Already largely done.)
- **Block 1:** dropping the cue makes the test a global presence judgment driven by the
  question content — the faithful analogue of the model's probe. It is also better aligned
  with the theoretical claim that the schema dimension runs on **familiarity** (a global
  "have I encountered this" signal) rather than source-bound recollection.

This is a second-order alignment choice; keeping the cue is a minor mismatch (it adds a
source restrictor the model lacks) and does not threaten the core dissociation. Recommended:
drop it, but low stakes.

---

## 5. The schema-dimension recognition problem (the "RNN cheating")

**Symptom.** On the schema dimension the model can look like it is cheating: it "recognises"
schema-consistent probes whether or not they were presented.

**Root cause 1 — residual storage removes schematic content.** In the schema condition the
Hopfield stores `x − s_t`; the schematic dims are subtracted *before* storage and added back
at retrieval (`retrieved + s_t·dim_weight`). So the schematic content of the reconstruction
comes **entirely from `s_t` (the schema), not from an episodic trace**. Recognition on the
schema dimension is therefore schema *re-generation*, not an old/new episodic judgment. (The
specific dimension is fine: the Hopfield genuinely stores specific dims — `s_t` carries almost
no specific content because event-averaging washes it out — so specific-dimension recognition
is real recollection.)

**Root cause 2 — a sequence RNN has no per-item query.** `s_t` is "given the events so far,
predict the next event." It needs sequential context. A recognition test probes **isolated
items** with no preceding sequence, so there is no natural `s_t` for an arbitrary probe. The
current false-memory test works around this by borrowing the `s_t` generated *during
encoding* at the E5 slot (briefing §5) — a hack that does not generalise to a real,
shuffled old/new recognition test. **This is the concrete sense in which "retrieval cannot
find the schema to recognise."**

**This is not simply a bug — half of it is the theory.** "The schema dimension can only be
answered by regenerating the schema, with no episodic recollection" *is* the prediction that
the schema dimension runs on familiarity and the specific dimension on recollection. So the
goal is **not** to force the RNN to do episodic recognition on the schema dimension (that
would contradict the theory) — it is to give the schema a retrieval-time form that can be
queried per item.

---

## 6. The fix: the schema plays two different roles

Give the schema an **order-independent, per-item representation for retrieval** — its learned
**event prototypes** (`base_centers`; note `s_t` itself is ≈ the next event's prototype). Then:

**At encoding — schema is a sequence predictor (unchanged).** Sequence context exists, so use
`s_t` to store the residual `x − s_t`. Fixed order → correct `s_t` → clean residual; random
order → wrong `s_t` → dirty residual. (This is what drives the specific-dimension order
effect — the core claim.)

**At retrieval — schema is a prototype-completion, NOT a sequence RNN.** For a probe `p`:

1. **Schema completion:** find the nearest prototype to `p`'s schematic dims → `s`. (Order
   free, per-item — no sequence needed. This is the missing half.)
2. **Episodic retrieval:** `p − s` → Hopfield → `retrieved`.
3. **Reconstruct:** `retrieved + s`; score against `p`.

Why this makes everything cohere — decompose recognition strength into two additive terms:

| | familiarity (prototype completion — both groups have it) | recollection (Hopfield trace) |
|---|---|---|
| **presented** sub-event | high | **high** |
| **omitted** sub-event | high → **false alarm** | low |

- **d′ (presented vs omitted) comes from the recollection term** — presented steps have a
  trace, omitted ones do not. Trace quality is cleaner under fixed order → **higher d′ in the
  ordered group** (matches the spec's schema-dimension prediction).
- **False alarms to the omitted step come from the familiarity term**, which is order
  independent → **both groups false-alarm** (matches spec §5 and fixes the earlier
  model↔human mismatch, where a sequence-conditional `s_t` would wrongly predict *no* false
  alarm under random order).
- **Schema dimension → familiarity (prototypes); specific dimension → recollection
  (Hopfield).** The dual dissociation falls out.

Turn the strength into a decision the way the briefing (§5) already suggests: treat it as a
memory-strength variable and sweep a criterion → hit/false-alarm rates → **confidence-ROC →
dual process**, which is exactly the behavioural readout. Balance the two terms (`w_epi` /
`w_fam`, or `dim_weight`) so the schema dimension shows high familiarity / low recollection
and the specific dimension the reverse.

**Change footprint:** encoding untouched; only the retrieval readout changes — replace
"borrow the encoding-time `s_t`" with "nearest-prototype completion." `base_centers` are
already loaded at test.

---

### 6.1 The working-memory component becomes redundant

Once each sub-event is **one frame** (§10), the PFC/working-memory GRU has no independent job
and can be dropped.

**Why it collapses.** The original architecture runs two timescales: the WM GRU predicts the
next **timestep** (within-event, fine grain) while the schema GRU predicts the next **event**
(coarse grain). With one frame per sub-event, `timestep == sub-event`, so both are predicting
the same thing. A dependency also disappears: the schema GRU's input is currently the event
mean computed at PE-derived boundaries, and those boundaries come from the WM's PE — but with
discrete sub-events the grain is given by construction, so nothing needs to be segmented in
order to feed the schema.

**PE is then schema-based**, `PE = 1 − cos(s_t, x_t)` on the **schematic dims only**. This is
what briefing §7 already argues for ("congruency should be defined by the schematic dimensions
only"), and it is what the behavioural rating actually measures — "does this follow from the
previous scene" is schema prediction error, not low-level next-frame prediction.

**Boundaries stay emergent.** Only the *sub-event grain* is given by construction; **where a
boundary is perceived is still a model output** — at a routine change the identity jumps, the
schema mispredicts, PE spikes. That is the counterpart of the experiment's
`is_boundary_transition` and of the rating dip.

**What survives (everything load-bearing).** The core claim rests on the Hopfield's residual
*storage* (`x_t − s_t·dim_weight`), which is a different mechanism from the WM's residual
*prediction* (`yhat = s_t + hm2o(h_t)`). So interference reduction (ordered > scrambled),
prototype-completion retrieval (§6), and PE-graded encoding / the U-shape (§8) are all
untouched.

**What is lost — two things, both judgement calls.**
1. The claim *"with a schema, PFC only has to encode the residual."* **This experiment cannot
   test it** — there is no working-memory load manipulation and no maintenance task. Keeping a
   component the data cannot constrain is a liability in a modelling paper.
2. The architecture moves **closer to Spens & Burgess (2024)** — a generative schema plus a
   hippocampal residual store — which the retrieval scheme already follows. Novelty then rests
   on the dimension dissociation, the order manipulation, and the U-shape rather than on the
   architecture itself. Decide whether that framing is acceptable before removing it.

**Recommendation: drop it**, unless the residual-encoding claim in (1) is one you want to keep
as an independent contribution. Dropping it fits the "change little, make it work" goal: one
fewer component to train, one fewer dependency chain, and less exposure to the autograd
problems flagged in briefing §7. The model reduces to a clean two-part system — **schema
(generative) + Hopfield (episodic)** — that maps one-to-one onto the experiment's two
dimensions.

## 7. What this predicts for the behavioural data

- **Specific dimension (Block 2):** ordered > scrambled; ROC with a **recollection**
  signature (asymmetric).
- **Schema dimension (Block 1):** false alarms to the omitted step in **both** groups; higher
  d′ in the ordered group; ROC with a **familiarity** signature (more symmetric/curved, low
  recollection intercept).
- The model's inability to do episodic recognition on the schema dimension is thus a
  **prediction to test in the ROC shapes**, not a defect to hide.

> **Measured — see §12.4.** The familiarity/recollection dissociation and the both-groups
> false alarm are confirmed, and the specific dimension shows ordered > scrambled on d′ and
> ROC AUC. But the schema-dimension prediction above ("higher d′ in the ordered group") is
> **contradicted**: no combined difference, and the recollection component runs the other
> way. Left standing as a prediction to resolve against the behavioural data.

---

### 8.1 Event boundaries require a continuous multi-routine run

The experiment logs and analyses **cross-routine event boundaries** (`is_boundary_transition`)
— the high-PE transition from one routine's last scene to the next routine's first, which the
"follow from" rating drops at. To reproduce them, the model must be run as **one continuous
stream over all 8 routines into one memory**, exactly like the experiment's 40-scene encoding
stream. Running each routine in isolation (a fresh reset memory per routine) gives each
routine's first scene no predecessor, so it produces no PE and cannot be a boundary point —
the boundaries vanish from the analysis. Hence the schema must handle multiple routines in one
run (schema GRU trained on all 8 scripts, routine order randomized so no meta-order is learned;
routine boundaries then fall out as high-PE because the next routine is unpredictable). This
single change also folds in cross-routine interference and the memory-load item that was listed
as a separate mismatch. Practical de-risking: validate on 2–3 routines first.

## 8. Testing the U-shape (why the encoding rating exists)

> **Direction of the Block 2 prediction below is contradicted — see §20.8.** This section
> argues specific memory *rises* with PE. Measured, it falls (0.436 → 0.252). The design
> logic here is otherwise intact and §20.8 builds on it: the block-to-dimension assignment
> stated in the next paragraph is what closes the readout question left open in §20.4.

The behavioural U-shape **is** tested (contrary to the original spec note), and the
per-scene "follow from" rating is its independent variable: the rating is the **per-item
PE**, related to that item's memory (Block 1 for the schema dimension, Block 2 for the
specific dimension).

**One frame per sub-event is sufficient.** The U-shape lives at the **sub-event level**:
each image gives one PE rating and one memory outcome. It does *not* need within-sub-event
frames. The driving mechanism is granularity-independent: the stored residual `x − s_t`
grows with PE (schema misprediction), so episodic-trace strength ∝ PE. Low-PE sub-events
get near-zero residuals (schema-filled → weak specific memory); high-PE sub-events get large
residuals (episodically encoded → strong specific memory). Briefing §6's "within-event vs
boundary" framing is just how this looks when events are multi-timestep; the residual-vs-PE
driver works per sub-event. On the model side, re-run the U-shape analysis at the
**sub-event grain** (each sub-event's *entry* PE vs its memory), not per-timestep.

> **Measured — see §12.5.** The PE-graded-encoding side of the tension below does not
> exist in the model as specified: `dim_weight` ≈ 0 on the specific dims means the schema is
> never subtracted from them, so their residual is independent of PE and trace strength
> cannot scale with it. Only the interference side operates. Read the table below with that
> in mind.

**The tension to resolve in simulation.** The between-group manipulation (ordered vs
scrambled) *is itself a PE manipulation* (ordered = low PE, scrambled = high PE). Two model
mechanisms then predict **opposite** between-group effects on specific memory:

| mechanism | prediction |
|---|---|
| interference reduction (the core claim): ordered → clean, low-interference residuals | ordered > scrambled |
| PE-graded encoding (the U-shape): scrambled → high PE → large residual → strong trace | scrambled > ordered |

Which wins between groups depends on parameters. The target regime: tune so **interference
dominates between groups** (preserves the core claim, ordered > scrambled) while **PE-graded
encoding shows up within condition / across items** (gives the U-shape). Knobs: `type_shift`,
`dim_weight`, and the relative weight of the interference vs encoding-strength terms.

**Design implications.**
- Analyse the U-shape **per item**, with the rating as a continuous PE covariate, *separately*
  from the group contrast — because the group factor is already a PE manipulation.
- This needs **within-condition PE spread**. It comes from routines/sub-events differing in
  how predictable they are, which the rating captures per item.
- Therefore the **weak-schema routines** (gym, laundromat — interchangeable step order) are a
  **feature for the U-shape, not a bug**: they raise within-condition PE variance even in the
  ordered group. Do not drop them for "diluting" the group contrast — they earn their place
  on the U-shape side.

**Both groups feed the U-shape — and the scrambled group is the cleaner PE test.**
Use within-group PE (the rating) with group as a covariate; do **not** use group *as* the PE
axis (that is the confounded between-group contrast where interference opposes PE-encoding).

- **Ordered group** — wide PE range (within-routine low, boundaries high, weak routines mid) →
  the main U-shape carrier. But here PE and residual *cleanliness* are correlated (low-PE items
  are both weakly-traced and low-interference), so the two effects are entangled.
- **Scrambled group** — PE is compressed toward the high end, but the schema is uniformly
  unusable, so **interference is roughly constant while PE varies**. That *isolates the
  PE-encoding (trace-strength) effect from the interference effect* — the cleaner test of "does
  PE per se boost specific memory." It also anchors the high-PE end and replicates the effect.

Analyse with a mixed model: PE (rating) as a within-group continuous predictor, group as a
factor/random effect. Testable interaction: routine **boundaries are high-PE islands** that
stand out (memory boost) in the *ordered* group but much less in the *scrambled* group (whose
within-routine PE is already high) → a group × boundary interaction.

## 9. Known remaining mismatches (note, not urgent)

- **Memory load / number of schemas.** RESOLVED by the continuous 8-routine run (§8.1): the
  Hopfield then holds all 40 sub-events across 8 different pre-learned schemas, so cross-routine
  interference and multi-schema encoding are simulated directly rather than approximated. (This
  is why the earlier "loop over isolated single-schema runs" shortcut was dropped.)
- **Violations.** The model's false-memory test also includes a *violation* (E5′); the
  experiment deliberately has none (spec: violations would create new event boundaries). Only
  the omitted-step half of the model's false-memory test maps to the experiment.

---

## 10. Minimal-change checklist

**Simulation** (roughly in order; several of these *simplify* the code — see §11)
- [x] **DONE (2026-07-30, §12.1).** One frame per sub-event — in a new `stimulus.py`, with
      hierarchical prototypes rather than a patched `generate_data.py`. Note `noise_specific`
      had to fall 2.0 → 0.2: the old value relied on AR(1) averaging that one frame removes.
- [x] **DONE (2026-07-30, §12.1–12.2).** Working-memory GRU dropped; training is a single
      stage. PE is a **dim_weight-weighted** cosine over the full vector rather than a hard
      slice to the schematic dims — same numbers, but nothing tells the model which dims are
      which (§12.2). Hopfield residual storage kept.
- [x] **DONE (2026-07-29).** Always `use_schema=True`; contrast `schema_order` fixed vs
      random (driver change). `order_test.py` / `run_order_test.py`; result and the
      interference correction in §2.1. Two things fell out that the remaining items
      inherit: (a) the retrieval readout no longer needs the `s_t` monkey-patch — see
      §11.1; (b) interference must be read on the schema dims, not the specific dims.
- [x] **DONE (2026-07-30).** Schema GRU predicts the next sub-event from the current frame,
      frozen at test. Cross-routine transitions are masked out of the training loss while the
      stream stays continuous — see §12.1 for why those two must not be conflated.
- [x] **DONE (2026-07-30, §12.2).** Nearest-prototype completion under a dim_weight-weighted
      distance, with prototypes **learned** by clustering the GRU's own predictions rather than
      taken from the generator. Monkey-patch gone. The specific-dim results are identical to the
      oracle readout, so the core effect never depended on the borrowed `s_t`.
- [x] **DONE (2026-07-30, §12.4).** `recognition.py`: lures, probe-only strength, criterion
      sweep, d′ and ROC. The two terms need **no** balancing parameters — dim_weight supplies
      the weighting. §6's dissociation confirmed; §7's schema-dimension prediction contradicted.
- [~] **ATTEMPTED — BLOCKED (§12.5).** Measured corr(PE, specific recall) = −0.017, p = .64.
      The residual grows with PE on the schema dims (r = +0.978) but not at all on the specific
      dims (r = −0.025), so the driver §8 names cannot produce a U-shape in specific memory.
      Not a tuning problem. Needs PE to gate *whether* a trace is written, not how large it is.
- [ ] **8 routines run as ONE continuous stream** (routine1's sub-events → routine2's → … →
      routine8, one memory), mirroring the experiment's 40-scene encoding stream. Required —
      running each routine in isolation drops the cross-routine boundaries the analysis needs
      (§8.1). This also folds in cross-routine interference / memory load (was §9).
- [ ] Schema GRU **trained on all 8 routines** (8 scripts), with routine ORDER randomized in
      training so no spurious meta-order is learned → routine boundaries are high-PE. Bump
      `dim_schema` (≈48 distinct sub-events to separate) and possibly `dim_hidden`.
- [~] **DELIBERATELY NOT DONE — see §18.** The experiment is within-subject (one stream,
      4 ordered + 4 scrambled). The simulation runs each condition as its own stream
      instead. This is a scope decision (2026-08-02): the model is being used to isolate
      mechanism, and separate streams keep the conditions from contaminating each other.
      `recognition.mixed_design` exists if the faithful design is ever wanted.
      **Consequence: every effect size here understates the experiment by roughly 3x**
      (Block 2 d′ +0.074 against +0.246). Do not use these numbers for power analysis.
- [ ] Tune params so interference dominates the ordered-vs-scrambled contrast while PE-graded
      encoding shows up across items within a condition (§8).
- [x] **DONE (2026-07-30).** Whole loop validated on 3 routines / 16+8 dims. Everything in
      §12 is at that scale; the 8-routine run above is the remaining scale-up.

**Experiment**
- [ ] **Within-subject** design (4 ordered + 4 within-instance-scrambled routines per subject,
      counterbalanced), **within-instance** scramble only. Do **not** add cross-routine mixing
      unless a matching model cell is built and validated first. (`config.design` can switch back
      to between-subject.)
- [ ] Keep the per-scene rating and the weak-schema routines — both are needed for the U-shape (§8).
- [ ] Drop the "In the X experience…" cue (Block 2 done; Block 1 recommended).
- [ ] Everything else (encoding stream, 6-point scales, "follow from" rating, third-person
      wording) already matches — no change.

## 11. Note on model effort

The one-frame-per-sub-event change is a moderate refactor of the stimulus pipeline and the
schema-GRU input, but it **net-simplifies** the model: with each sub-event a discrete step,
each step has its own `s_t` directly (removing the fragile monkey-patch flagged in briefing
§4.6/§7), the Hopfield gets exactly one trace per sub-event, and the working-memory GRU can be
removed entirely (§6.1) — leaving a two-part schema + Hopfield system with one less network to
train and one less dependency chain. Do **not** rewrite the Hopfield itself (briefing §7).

The larger piece of work is the **continuous 8-routine run** (§8.1): more stimulus generation
(8 distinct routines concatenated) and retraining the schema GRU on 8 scripts with bigger
`dim_schema`. It is the same architecture — more data and capacity, not new mechanisms — and
it is required, because the boundary analysis needs it. A loop over isolated single-schema
runs is **not** a substitute: it discards the cross-routine boundaries. Slightly more training
risk than one script, so validate on 2–3 routines first.

### 11.1 State of the code — read before estimating any further change

Two facts discovered while implementing §2.1; both change what "small change" means.

**There are two incompatible generations of driver script.** `model.py` was refactored so
the schema GRU predicts `(start, drift)` per event rather than an event mean: the saved
checkpoints (`output/seed*/schema_gru/schema_gru.pth`) take **input size `2*dim_input`**,
and `model.py`'s `forward` unpacks **three** values,
`s_start, s_drift, schema_state = schema_step_fn(...)`. Only the free-recall lineage was
updated. These five still use the old `SchemaGRUSeq(h_dim=dim_input)` with a two-return
`schema_step_fn` and **crash on `load_state_dict`** (`size mismatch [96,16] vs [48,8]`):

> `run_memory_test.py`, `run_false_memory_5.py`, `ushape_test.py`, `threshold_sweep.py`,
> `test_schema_more.py`

Several checklist items are written as edits to exactly those scripts (the U-shape analysis
lives in `ushape_test.py`, the false-memory readout in `run_false_memory_5.py`), so each of
those items carries an unbudgeted "port to the current API" step first. Working references:
`test_free_recall_new.py:47`, or `order_test.py`.

Note also that `simulation_briefing.md` documents the *old* API and names several files that
no longer exist (`stimulus_8d.py`, `gru_hopfield_schema.py`, `false_memory_test.py`,
`ushape_timeline.py`, `analysis.py`); its "Recognition / recall test" file `memory_test.py` is
dead code, while the file actually imported is `test_memory.py`. Treat the briefing as a
description of intent, not of the current tree, and verify against a checkpoint.

**The `s_t` monkey-patch can simply be deleted.** Briefing §4.6 calls the
patch-`hopfield.write`-then-correct-from-boundary-indices scheme "the ugliest part of the code
and the most likely place for an off-by-one bug", and §10 budgets removing it as part of the
retrieval-readout change. It is free: `HopfieldMemory.write` stores the **raw, unnormalized**
residual (`self._patterns.append(v_d.clone())`) and `forward` writes
`residual = y_t − s_t·dim_weight`, so

> `s_t · dim_weight == y_t − stored_pattern`

exactly, with no boundary bookkeeping and no possible off-by-one. `order_test.py:encode_stream`
recovers it this way. Any later readout work (§6 prototype completion, §6.1) can assume the
per-pattern schema term is already available.

---

## 12. Restructured implementation (2026-07-30) — what was built and what it shows

§§1–11 are the plan. This section records the rebuild that followed and the results it
produced. Where a result contradicts an earlier section, the earlier section is left as
written and the contradiction is flagged here rather than silently edited.

### 12.1 What was built

The two-stage pipeline is gone. There is no working-memory GRU, no `all_seg_info.pkl`
intermediary, no `(start, drift)` event descriptors, and no PE-based segmentation feeding
the schema. With one frame per sub-event the input **is** the schema GRU's input, so
training is a single run:

| file | role |
|---|---|
| `stimulus.py` | one frame per sub-event; hierarchical prototypes; within-instance scramble |
| `train_schema.py` | single-stage training; derives `dim_weight`, `target_var`, learned prototypes |
| `episodic.py` | encoding (schema + Hopfield) and reconstructive recall |
| `recognition.py` | recognition test with lures: familiarity/recollection, d′, ROC |

`order_test.py` / `run_order_test.py` remain but target the OLD architecture (§2.1).

Design points worth keeping:

- **Prototypes are hierarchical**, `w_r·routine_dir[r] + w_k·subevent_dir[r][k]` with both
  sets orthogonal, so within-routine cosine equals a single knob `routine_similarity`
  exactly (measured 0.505 for a setting of 0.5) and between-routine is ~0. That knob sets
  how sharp the identity jump at a routine boundary is.
- **`schema_strength` per routine** implements §8's weak-schema routines (gym, laundromat).
  It is applied when building the *training* stream and must not be confused with
  `scrambled_routines`, the experimental manipulation applied at test.
- **`noise_specific` had to drop from 2.0 to 0.2.** The old value was calibrated for
  ~30-frame events where AR(1) averaging suppressed it; with one frame there is no
  averaging and the per-instance identity was swamped roughly 1:2.8. Signal/noise is now
  explicit (`specific_scale / noise_specific`).
- **Cross-routine transitions are excluded from the training loss**, because routine order
  is randomized and that transition is unlearnable; training on it drags the within-routine
  predictions toward the mean first sub-event. **The stream stays continuous and the hidden
  state is not reset** — masking the loss and resetting the state are different things, and
  resetting would destroy the boundary analysis exactly as §8.1 warns. Result: PE is 0.002
  inside a rigid routine, 0.026 inside a weak one, and **0.729 at a routine boundary**.

### 12.2 dim_weight drives everything; the model is never told which dims are which

`dim_weight[d] = 1 − Var(prediction error) / Var(target)` on held-out data — the fraction
of that dimension's variance the schema explains. Measured: **0.863 mean on the schematic
dims, exactly 0.000 on the specific dims.** (The old `1/(relvar+1e-4)` formula from
`schema_training.py` separates far worse — 0.376 vs 0.031 — because normalising by the max
drags most schematic dims down.)

Everything schema-side is then weighted by `dim_weight` rather than sliced at a
hard-coded `n_schema_dims`:

- PE is a `dim_weight`-weighted cosine, `cos(s·√dw, x·√dw)`. It reproduces the hard-split
  numbers almost exactly (0.127/0.414 vs 0.129/0.423) without being told the split, and
  unlike a hard split it degrades gracefully for partially predictable dimensions — which
  is what weak routines and the 8-routine scale-up will produce.
- Nearest-prototype matching uses a `dim_weight`-weighted distance over the full vector.
- **Prototypes are learned, not given.** They are k-means centroids of the trained GRU's
  own predictions (§6 notes `s_t` is already ≈ the next sub-event's prototype). Loading the
  generative prototypes would hand the model ground truth. The learned centroids have
  magnitude **0.942 on the schematic dims and 0.034 on the specific dims** — the model
  discovers the split rather than being handed it.

`n_schema_dims` survives only where results are split into two groups **for reporting**,
which is the experimenter knowing the ground truth, not the model.

### 12.3 The online gain replaces a static dim_weight at encoding

A single `dim_weight` applied at every step keeps trusting the schema by the same amount
at the step right after it mispredicted — so a scrambled routine still stores a residual
taken against a wrong prediction, which is not a defensible encoding rule. The gain is now
recomputed per step and per dimension:

    w_t[d] = dim_weight[d] · clip(1 − (s_t[d] − x_t[d])² / target_var[d], 0, 1)

The instantaneous term alone is a one-sample estimate and is **not** sufficient: on a
dimension the schema cannot predict, the draw sometimes lands near the prediction by
chance and the gain rises to ~0.47 where it should be 0. `dim_weight` supplies the
ceiling; the online term can only pull it down. (A Kalman-style `var/(var+err²)` is also
wrong here — it returns 0.5 for a dimension the schema cannot predict at all.)

Effects, all measured: schema-dim gain is **0.99 inside a rigid routine and 0.37 at a
boundary**; ordered 0.769 vs scrambled 0.450. The boundary pathology under a static gain —
where the residual grew *larger than the input itself* because a wrong prediction was
being added in — disappears: residual norm 6.34 → 5.27, schema-dim reconstruction at
boundaries 0.294 → 0.663.

The ordered > scrambled specific-memory effect survives all of this unchanged
(0.6655 vs 0.5747, p < 0.0001), including the switch from oracle to prototype-completion
retrieval — it is not an artefact of any of these choices.

### 12.4 Recognition test with lures — §6's dissociation confirmed, §7 partly contradicted

> **Superseded — see §14.5 for the current numbers.** Three separate problems affect the
> table below: the lure was created by omitting a RANDOM mid-routine sub-event (an
> asymmetric confound, §13.5); Block 2 used the omitted sub-event as its lure, so it was
> answering Block 1's question (§14.2); and `run_subject` did not pass `noise_schema`,
> so probes were generated at the wrong stimulus setting (§14.2). All three are fixed.

Until now the model measured *reconstruction quality*: cue with a presented item, score
`cos(reconstruction, the original)`. That is not recognition. It probes only presented
items and scores against ground truth, which a lure does not have, so it **cannot produce
a false alarm at all**. `recognition.py` adds the three missing pieces — lures (one
sub-event omitted per routine), a strength computable from the probe alone, and a decision
stage (criterion sweep → d′, ROC).

Strength is decomposed as §6 asks, with **no free parameters**, because `dim_weight`
already states how the labour divides:

    familiarity  = weighted cos(probe, nearest prototype)     — schema regeneration
    recollection = weighted cos(probe, Hopfield retrieval)    — episodic trace
    Block 1 question weights dimensions by dim_weight; Block 2 by 1 − dim_weight

120 simulated subjects, 3 routines, within-subject:

| | Block 1 (schema) ord / scr | Block 2 (specific) ord / scr |
|---|---|---|
| familiarity, presented | 0.959 / 0.931 | 0.487 / 0.472 |
| familiarity, **LURE** | **0.925 / 0.953** | 0.468 / 0.478 |
| recollection, presented | 0.543 / 0.611 | 0.607 / 0.587 |
| recollection, **LURE** | 0.340 / 0.400 | 0.289 / 0.253 |
| **d′ from familiarity** | **0.050 / −0.279** | **0.124 / −0.080** |
| **d′ from recollection** | 1.097 / 1.437 (p=.0005) | 1.762 / 1.735 (p=.80) |
| d′ combined | 0.927 / 0.897 (p=.75) | **1.314 / 1.127 (p=.026)** |
| ROC AUC | 0.751 / 0.750 (p=.93) | **0.814 / 0.783 (p=.039)** |

**Confirmed (§6).** Familiarity gives d′ ≈ 0 in both blocks — it genuinely cannot tell old
from lure — while lures draw familiarity (0.925–0.953) as high as presented items. False
alarms appear in **both** groups and are order-independent. All discrimination comes from
the recollection term. This is the dual-process signature the design predicts, and it is
now measured rather than asserted.

**Confirmed (§7, specific dimension).** Block 2 shows ordered > scrambled on both d′ and
ROC AUC, in proper recognition terms.

**Contradicted (§7, schema dimension).** §7 predicts "higher d′ in the ordered group" on
the schema dimension. Measured: no combined difference (p = .75), and the recollection
component runs the **opposite** way — scrambled 1.437 > ordered 1.097, p = .0005.

The mechanism is a direct consequence of the online gain (§12.3): scrambling drops the
schema-dim gain from 0.77 to 0.45, so roughly 0.55 of the schematic content is stored raw
instead of 0.23. The scrambled condition therefore holds a *stronger* episodic trace for
sub-event identity. In words: when the script cannot help you, you have to memorise the
scenes individually, so episodic memory for scene identity improves — while specific
content suffers from the extra interference.

This is left standing as a **prediction to test**, not patched. It is not a numerical
accident: it follows from the encoding rule "when the schema is not trusted, store the raw
content", and it produces a *double* dissociation (order helps the specific dimension and
hurts the schema dimension) which is a sharper empirical claim than the same-direction
prediction in §7. **Resolve against the behavioural data.**

### 12.5 Still open

- **§8's U-shape mechanism cannot work as written.** §8 says the stored residual grows
  with PE so trace strength ∝ PE. The residual grows with PE on the **schema** dims
  (r = +0.978) but not at all on the specific dims (r = −0.025, p = .48), because
  `dim_weight` ≈ 0 there means the schema is never subtracted from them. Since the U-shape
  is about *specific* memory, the driver §8 names cannot produce it — and this is not
  tunable, since a dimension that is unpredictable by construction must get zero weight.
  Measured: corr(PE, specific recall) = −0.017, p = .64. A separate mechanism is needed —
  most plausibly PE gating *whether* the trace is written rather than *how large* it is
  (`model.py`'s `pe_write_threshold` is a half-implementation, and `threshold_sweep.py`
  was exploring exactly this).
- **Specific-dim interference stays null** (p = .13–.40) across architectures, gain rules
  and scramble modes, for the structural reason in §2.1. The "interference reduction"
  framing in §2 and §8 needs restating around residual cleanliness on the schematic dims.
- **Scale.** Everything above is 3 routines, 16+8 dims, ~15 stored items — far from
  Hopfield capacity pressure. The 8-routine / 48+16 run (§8.1, §10) is not done, and the
  cross-routine interference and memory-load questions cannot be answered until it is.
- **Combination normalisation.** Familiarity and recollection are on different scales, so
  the combined strength z-scores each term before summing. That choice affects ROC shape
  and deserves a sensitivity check.
- **Weak routines are less weak than intended.** Permuting a fixed set of sub-events leaves
  a predictable tail — PE falls monotonically across positions in a weak routine
  (0.053, 0.038, 0.009, 0.003) because the GRU infers the remainder by elimination. If a
  uniformly unpredictable routine is wanted, sample from a pool larger than what is
  presented.
- `model.py` still contains the working-memory GRU and the legacy classes. The new path
  imports only `HopfieldMemory` from it, so this is dead weight rather than a hazard.

---

## 13. PE gating, the 8-routine scale-up, and a broken measure (2026-07-30)

Three things happened in this round, and the third one reframes the first two: the
recall measure §12 relied on turned out to be invalid, so several numbers in §12 are
superseded. Read this section before quoting anything from §12.4 onward.

### 13.1 The reconstruction measure: contaminated levels, valid contrasts

`episodic.probe` cues with the full noisy item and scores `cos(reconstruction, the
original)`. Against a no-memory baseline — just hand the noisy cue back — it loses:

| | schema dims | specific dims |
|---|---|---|
| cue only, **no memory at all** | 0.9907 | **0.9556** |
| Hopfield output only | 0.4236 | 0.5835 |
| full reconstruction (what §12 reported) | 0.9928 | 0.5835 |

On the specific dims the reported "recall" (0.58 ordered / 0.37 scrambled) is far
**worse** than returning the cue untouched, and on the schematic dims memory's net
contribution is +0.002. The *absolute level* of this measure is therefore
uninterpretable as a memory score: the cue already contains the answer.

> **But the between-condition contrast is clean, and an earlier draft of this section
> wrongly dismissed the measure wholesale.** The cue baseline is identical in the two
> conditions — 0.9566 vs 0.9567, diff −0.00001, p = 0.98 — so subtracting it changes the
> order effect not at all: raw +0.1219, baseline-corrected +0.1220. Cue leakage inflates
> the level, not the comparison.
>
> What the measure genuinely cannot do is the other half of the theory: with no lures it
> produces no false alarms, so §6/§7's familiarity predictions are untestable with it.
> That is why the recognition test was added — as an **addition**, not a replacement.
>
> The two also measure different things. Reconstruction is cued recall / pattern
> completion; d′ is old/new recognition. The experiment collects recognition ratings, so
> d′ is the analogue for *this* experiment — but the reconstruction result stands as a
> prediction about a recall task, and it is the larger effect (+0.122 against +0.074),
> which is itself testable: **the same manipulation should move recall more than
> recognition.**

Two separate leaks produce this. The cue carries the answer; and the retrieval-side
schema term adds back a clean prototype carrying **90%** of the true schematic
magnitude, so the prototype alone scores 0.998 while adding the episodic term *lowers*
it to 0.993. Worse, what is added back does not match what was subtracted: encoding
subtracts `s_enc·w_enc` (a sequence prediction, gain collapsing at boundaries) while
retrieval adds `prototype·w_ret` (always a good match, gain high). The gap correlates
with PE at **r = +0.972** and reaches magnitude 10.2 against a signal of 15.0.

That mismatch, not the theory, is what flattened schema-dim recall: with an oracle
readout that adds back exactly what encoding removed, schema recall drops
0.994 → 0.638 across PE quartiles (r = −0.982). The opposing slope the U-shape needs
was there all along and the measure was hiding it.

**Fixing the cue does not rescue it.** Cueing with the specific dims only — so the
schematic dims must come from memory — collapses schema recall to 0.15–0.21 at every
PE level. The Hopfield holds 39 traces in 64 dimensions, roughly 4× classical capacity,
and cannot do pattern completion at all.

### 13.2 What the memory can and cannot do

The overloaded Hopfield is not useless; it fails at some jobs and not others.

| task | result |
|---|---|
| complete a pattern from a partial cue | fails (0.15–0.21) |
| denoise a full cue | fails (worse than the cue) |
| **discriminate stored from unstored content** | **works: 86% 2AFC, d′ ≈ 2.0** |

It behaves as a familiarity/resonance detector rather than a content reconstructor —
the expected behaviour of a Hopfield past capacity, which still yields a graded energy
signal when it can no longer settle into a specific attractor.

**Use `recognition.two_afc` as the recall measure.** It forces a choice between the
presented specific variant and a foil with identical schematic dims, so chance is 50%
and the cue cannot leak the answer.

> **WRONG — corrected in §14.1.** The sentence that stood here called 2AFC "the better
> analogue of the behavioural task, which is a forced choice between object variants".
> It is not. **Both blocks of the experiment collect 6-point confidence ratings about a
> single probe; nothing in it is a forced choice.** Both therefore map onto d′ / ROC.
> 2AFC survives only as a diagnostic. Every 2AFC number below and in §13.4 is
> superseded — and it does not merely rescale them, it reverses the sign of the PE-gating
> conclusion.

**The order effect is real but modest.** Three independent measures agree:

| measure | ordered | scrambled |
|---|---|---|
| 2AFC specific | 86.0% | 84.0% |
| Block 2 d′ combined | 1.350 | 1.251 |
| Block 2 ROC AUC | 0.824 | 0.808 |

That is a couple of percentage points, not the large effect the reconstruction cosine
implied. **§12.3's "+0.208 / p<0.0001" and the interference rows in §2.1 and §12 are
superseded by these.**

### 13.3 Scale-up: `type_shift` is the knob that makes it work

At 8 routines / 48+16 dims the order effect vanished entirely (+0.0004, p=0.96). A load
sweep with the model held fixed showed it was not memory load: the same 14 stored items
gave +0.091 under the 16+8 model and +0.002 under the 48+16 one, despite the latter
being *less* loaded. Dimensionality was the cause. The grid:

| config | diff | p |
|---|---|---|
| 48+16, type_shift 5 | +0.002 | 0.73 |
| 24+8, type_shift 5 | +0.052 | <0.0001 |
| 48+8, type_shift 5 | +0.016 | 0.062 |
| **48+16, type_shift 15** | **+0.208** | **<0.0001** |
| 48+16, noise_specific 0.5 | −0.009 | 0.17 |

This is exactly the knob §2 nominated ("the effect grows with how wrong `s_t` is under
random order, which grows with prototype separation"). Working config:

    --n-routines 8 --n-schema-dims 48 --n-specific-dims 16 --type-shift 15
    --weak-routines 6 7

The scale-up also fixed the PE distribution: weak routines now span a real range
(mean 0.040, sd 0.077) instead of sitting at a point, and boundaries are at 0.97.
Prototype identification stays at 100% even here, so the hoped-for prototype confusion
at scale did not materialise.

### 13.4 PE gating — the capacity-relief framing is wrong, see §17.2

> **Also mis-scoped — see §16.** The section below concludes that "the schema's value is
> that it lets you not store what is predictable". That is what *gating* adds, and it was
> wrongly generalised into a claim about the schema as a whole. The primary benefit is the
> division of labour in the residual code itself, which operates with trace count held
> exactly constant and is far larger.
>
> **Headline reversed — see §14.4.** The claim below that gating *triples* the order
> effect rests on 2AFC, which is blind to the drop in absolute trace strength that gating
> causes. On d′ — the measure the experiment actually corresponds to — gating **costs**
> the order effect (+0.27 ungated → +0.05 at floor 0.35 → −0.27 at floor 0). The
> capacity-relief mechanism itself is real and the load dependence holds; what is wrong
> is the conclusion that gating improves the predicted between-group effect.

`episodic.pe_gate` lets prediction error gate how strongly a trace is written
(`HopfieldMemory.write` gained a `strength` argument; the update is still the plain
outer product). This is the mechanism §12.5 said was missing, and it works on every
dimension, unlike the residual-size route §8 assumed.

The floor must be **blended, not clipped** — clipping parks every low-PE item at the
floor and destroys the gradation the U-shape analysis needs. It also decides which side
of §8's tension wins: at floor 0 the gate is so aggressive that ordered items are barely
written and PE-graded encoding reverses the core effect.

On the trustworthy measure, gating **triples** the order effect and *raises* the ordered
group's absolute accuracy, from 86.0% to 89.9% — while that group stores only about half
as much (20.5 effective traces against 34.6):

| memory load | no gate | gate floor 0.4 |
|---|---|---|
| 9 items | +4.2% | −0.3% |
| 19 items | +3.0% | +3.8% |
| 29 items | +3.2% | +6.2% |
| **39 items** | **+1.8%** | **+6.6%** |

The benefit grows monotonically with load and is absent when memory is uncrowded. That
identifies the mechanism: **the schema's value is that it lets you not store what is
predictable, relieving a capacity-limited episodic store.** Note the pairwise
correlation of stored patterns is actually *higher* in the ordered group (0.137 vs
0.114) and is unchanged by the gate, so the advantage is **not** decorrelation. The
"interference reduction" framing in §2 and §8 should be restated as load reduction —
and on this account the Hopfield's capacity limit stops being an inconvenience and
becomes a precondition for the schema to have any episodic value at all.

The relationship is non-monotonic: at floor 0 and 0.2 the ordered group collapses to
60% and 75%, because specific content is unpredictable and not storing it simply loses
it. The optimum is floor ≈ 0.4–0.6.

### 13.5 A confound in the lure design, now fixed

Creating lures by omitting a random mid-routine sub-event breaks the stream: the schema
jumps from sub-event k to k+2, a transition it never trained on. The damage is
**asymmetric** — it roughly doubles the ordered group's PE (0.18 → 0.37) and opens its
gate from 0.53 to 0.77, while the scrambled group, whose sequence was already broken,
barely moves (0.50 → 0.55). That erases most of the manipulation:

| omission | PE ordered | 2AFC order effect |
|---|---|---|
| random mid-routine position | 0.3704 | −1.7% (p=.064) |
| **last sub-event (now the default)** | **0.2584** | **+2.1% (p=.010)** |

`recognition.run_subject` now omits the last sub-event of each routine, leaving the
within-routine sequence intact and putting the discontinuity at the routine boundary,
which is high-PE anyway. **Any recognition result produced before this fix understates
the ordered group.**

### 13.6 Where this leaves things

- Order effect on specific memory: **real, modest, robust across three measures**, and
  roughly tripled by PE gating at full load.
- §6's familiarity/recollection dissociation: unchanged and now sharper — lure and
  presented items draw *identical* familiarity (0.9997 both), d′ from familiarity ≈ 0.
- §7's schema-dimension prediction: still contradicted, and now significant at scale
  (d′ combined 0.949 ordered vs 1.076 scrambled, p=0.0025). Still left standing for the
  behavioural data to settle.
- U-shape: the opposing slope exists (oracle readout, r = −0.982) but no legitimate
  readout can currently expose it, because prototype completion repairs the schematic
  dims from the probe itself. This is §5's "recognition cannot find the schema" problem
  in its sharpest form and is the main open item.
- Everything in §12 that came from `episodic.probe` reconstruction cosines needs
  re-running with `two_afc` and the fixed lure position.

---

## 14. Correcting the readout, and what changed with it (2026-07-30)

§13 got the response format wrong. Fixing it, plus one real bug it exposed, reverses two
of §13's conclusions. This section supersedes §13.2 and §13.4.

### 14.1 Both blocks are 6-point ratings, so both are d′ / ROC

§13.2 asserted that Block 2 is a forced choice and adopted 2AFC as the primary measure.
It is not: **both blocks collect 6-point confidence ratings about a single probe.**
Neither is a forced choice, so both map onto d′ and an ROC — which is what §6 and §7
said all along ("ROC with a recollection signature", "ROC with a familiarity signature").

The two measures are not interchangeable, and the difference is not cosmetic:

- **2AFC** is a paired, within-item comparison, so a uniform shift in absolute trace
  strength cancels out.
- **d′** is an absolute-criterion measure and moves with both content *and* overall
  strength.

Any manipulation that changes overall trace strength therefore looks different under the
two. PE gating is exactly such a manipulation, which is why §13.4's headline is wrong
(§14.4). `recognition.two_afc` is kept, relabelled DIAGNOSTIC ONLY: it is still the
right tool for asking whether a manipulation changed memory *content* rather than
merely its level.

### 14.2 The Block 2 lure was asking Block 1's question

`make_blocks` now builds a separate probe set per block, because the lure is what makes
the two questions different:

| | old | lure |
|---|---|---|
| **Block 1** — which sub-event | a presented sub-event | the sub-event omitted from that routine |
| **Block 2** — which variant | the presented item | the **same** sub-event with different specific content |

The earlier version used the omitted sub-event as the lure for *both*. That asks "did
this scene occur at all", which is Block 1's question, so Block 2 inherited Block 1's
answer — including its reversal. Fixing it quadrupled the Block 2 effect (d′ +0.099 →
+0.388 at the time) and flipped it into the predicted direction.

**Bug found while fixing this:** `run_subject` never passed `noise_schema` to
`generate_stream`, so every recognition run generated probes at the default 0.05 while
the model had been trained at 0.5. All recognition numbers reported before this point
are affected.

### 14.3 Larger `noise_schema` gives the schema dimension episodic content

At `noise_schema` 0.05 the schematic dims sit essentially on the prototype (the
deviation is ~2% of per-dim magnitude at type_shift 15), so there is nothing about them
that only memory could hold — a schema-dimension 2AFC scores 56%, barely above chance.
Raising it makes each instance deviate from its prototype in a way the schema cannot
predict, `dim_weight` falls accordingly, and the Hopfield has to carry the difference:

| noise_schema | dim_weight (schema dims) | schema 2AFC | specific 2AFC order effect |
|---|---|---|---|
| 0.05 | 0.906 | 56.0% | +6.0% |
| **0.5** | **0.846** | **81.8%** | **+3.9%** |
| 1.0 | 0.710 | 88.9% | +1.5% (n.s.) |
| 2.0 | 0.402 | 93.5% | +0.5% (n.s.) |

0.5 is the operating point: the schema dimension becomes a real memory measure without
the specific dimension washing out.

### 14.4 PE gating trades the order effect for the U-shape — it does not buy both

§13.4 reported that gating *triples* the order effect. That was the 2AFC talking. On
d′, gating **costs** the order effect, monotonically:

| gate | Block 2 d′ (ordered − scrambled) |
|---|---|
| **no gate** | **+0.27** |
| floor 0.40, κ 0.5 | +0.10 |
| floor 0.35, κ 0.5 | +0.05 |
| floor 0.30, κ 0.5 | −0.01 |
| floor 0, κ 0.5 | −0.27 (reversed) |

The capacity-relief mechanism in §13.4 is real — the ordered group does store about half
as much and its *content* discrimination improves, which is what 2AFC sees — but the
drop in absolute trace strength costs more d′ than the content gain buys. Since the
experiment collects ratings, d′ is the number that corresponds to data.

So the §8 tension is **not** resolved by a lucky parameter window, as §13.4 hoped. Both
quantities are positive in a band around floor 0.30–0.40, but the order effect there is
roughly a fifth of its ungated size. **No setting recovers both at full strength.**

### 14.5 What the model now predicts

> **Superseded by §15.4.** The symmetry below comes from a leaky question weighting that
> let 77% schematic energy into the "specific" readout, and from a z-scored combination
> that diluted every d′ by ~45%. With clean masks the dissociation is strongly
> asymmetric: −0.52 on Block 1 against +0.07 on Block 2.

**A symmetric double dissociation** (no gate, `omit_position="type"`, noise_schema 0.5,
120 simulated subjects, both blocks d′):

| | ordered | scrambled | diff | p |
|---|---|---|---|---|
| **Block 2 — specific** | 1.022 | 0.750 | **+0.272** | <0.0001 |
| **Block 1 — schema** | 0.814 | 1.086 | **−0.272** | <0.0001 |
| ROC AUC, Block 2 | 0.763 | 0.700 | +0.063 | <0.0001 |
| ROC AUC, Block 1 | 0.715 | 0.775 | −0.060 | <0.0001 |

The two are almost exactly equal and opposite. §7's Block 2 prediction is confirmed; its
Block 1 prediction is contradicted, now with a matched lure and no gate, so neither the
omission confound (§13.5) nor the gate is responsible.

**§6's dissociation, sharper than before.** Familiarity for lures equals familiarity for
presented items to three decimals in both blocks (0.799 / 0.799 in Block 2; 0.975 /
0.975 in Block 1), and d′ from familiarity alone is ~0. All discrimination comes from
recollection. Maximal false alarms, in both groups, order-independent.

**The U-shape exists, in the form §6 of the briefing describes** — two regression lines
with opposite slopes, split at the encoding threshold, fitted within the ordered group:

- within-routine items: negative, familiarity-driven (per-item r = −0.032, p = .037)
- routine boundaries: positive, recollection-driven (per-item r = +0.087, p = .008)

It requires a gate (κ 0.5, floor 0.35) and it is **shallow** — those are significant
because there are thousands of items, not because the per-item relationship is tight.
Binned means look far steeper than the per-item correlation; both are reported in the
figure for that reason.

It is also carried entirely by the **weak-schema routines**: within rigid routines PE
spans only 0.017–0.036, never reaching the gate, and the curve is monotonic. That
vindicates §8's insistence on keeping gym/laundromat-type routines, and yields a sharper
behavioural prediction than "a U-shape exists": **the U should appear only in routines
with interchangeable steps, and rigid routines should be monotonic.**

### 14.6 Figures

`figures.py` (house rule: every function takes `out_path`; nothing calls `plt.show()`).
Rendered to `output/v2/figures/`:

| file | shows |
|---|---|
| `1_ushape.png` | the two opposite-slope limbs, split panels, per-item r stated alongside binned means |
| `2_components.png` | familiarity falls with PE, recollection rises — the mechanism |
| `3_gate_window.png` | the trade: gating costs Block 2 d′ and buys slope separation |
| `4_dissociation.png` | the symmetric double dissociation, and lure = presented familiarity |
| `5_capacity_and_measure.png` | gate × load, and the cue-baseline result that retired the reconstruction measure |

### 14.7 Open

- **Gate strength is unconstrained.** It sets whether the model predicts an order effect
  or a U-shape, and nothing outside the model fixes it. This is the largest free
  parameter in the account and worth stating as such rather than tuning to taste.
- The schema-dimension reversal (§12.4, §14.5) is unchanged and still awaiting data.
- `episodic.probe`'s reconstruction cosine remains in the codebase for the U-shape
  component analysis only; it must not be used for anything compared against behaviour.

---

## 15. Code review: three defects in the readout (2026-07-30)

A review of the analysis code found three problems in how memory strength was scored.
None of them changes the *direction* of any result, but two change the sizes materially
and one shows an earlier number was meaningless. **§14.5's table is superseded by §15.4.**

### 15.1 z-scoring gave a signal-free term equal weight

The combined strength was `z(familiarity) + z(recollection)`. Familiarity barely differs
between old items and lures (d′ ≈ 0.04) — that is the *central prediction*, not a
defect — so z-scoring inflated a signal-free term to unit variance and gave it the same
weight as the term carrying all the signal. Measured cost: `d′(z-sum) / d′(recollection)`
= **0.643 in both blocks**, against 0.707 for "one signal term plus one pure-noise term
of equal variance". Every d′ and AUC reported before this fix is understated by ~45%.

`recognition.combine` is now a raw sum. Both terms are cosines on the same scale, so
their raw variances already encode how much each contributes; a term that barely moves
contributes barely anything, which is the correct behaviour and exactly what z-scoring
destroys.

### 15.2 The "specific" question was 77% schematic

The question weightings were `dim_weight` and `1 − dim_weight`. The second is **~0.12 on
each of the 48 schematic dims, not 0**, and at their magnitude that is 77% of the
weighted energy — so Block 2 was mostly answered with schematic information. Variance-
standardising first only improves it to 44%.

Both weightings are now **hard masks**: Block 1 reads the schematic dims, Block 2 reads
the specific dims, nothing else. The experiment asks about one property at a time, so
the readout should too.

This is not the model peeking at the dimension split — the *question* is posed by the
experimenter, who built the stimulus; encoding and retrieval still never use it. And it
makes no numerical difference whether the mask is called ground truth or derived:
`dim_weight` is 0.68–0.94 on the schematic dims and exactly 0 on the specific ones, so
thresholding at 0.5 reproduces the mask exactly.

**The fix validates itself.** Block 2 familiarity was 0.799; under the clean mask it is
**−0.003**, which is the right answer — a prototype carries no specific-dim content, so
matching a probe to its prototype should tell you nothing about which variant it was.
The 0.799 was entirely schematic leakage.

### 15.3 Smaller items

- `make_blocks` and `two_afc` built lures with an implicit `specific_scale` of 1.0,
  neither reading it from the config nor recording it. It is now a `train_schema`
  argument, saved to `config.json`, and read by both.
- `run_subject` never passed `noise_schema` to the generator, so probes were built at
  the default 0.05 while the model was trained at 0.5 (§14.2). Fixed.
- Recognition probes carry **no perceptual noise** (`noise_scale=0`): the probe is the
  exact studied vector. That is a modelling choice, not an oversight, but it is part of
  why familiarity sits at ceiling and should be stated when reporting.
- **Block 1 has 31 old items against 8 lures.** The lure distribution is estimated from
  8 points per subject, which is why Block 1's SEM is roughly twice Block 2's
  (±0.030 vs ±0.017). This is a design property — one omitted sub-event per routine —
  and it means the Block 1 prediction needs a larger sample than its effect size alone
  suggests.
- `episodic.probe` leaves its RNG unseeded when `seed=None`; `pe_gate` returns 1.0 for
  the NaN at frame 0 under `mode="none"` but the floor under every other mode (harmless,
  frame 0 is never stored); `figures.py` passes one array through `globals()`.

### 15.4 Corrected results

Hard question masks, strength = familiarity + recollection (one rule, both blocks),
`omit_position="type"`, noise_schema 0.5, no PE gate, 150 simulated subjects:

| | ordered | scrambled | diff | p |
|---|---|---|---|---|
| **Block 2 — specific** d′ | 1.157 | 1.082 | **+0.074** | 0.020 |
| Block 2 ROC AUC | 0.790 | 0.772 | +0.018 | 0.008 |
| **Block 1 — schema** d′ | 1.300 | 1.824 | **−0.523** | <1e-22 |
| Block 1 ROC AUC | 0.819 | 0.899 | −0.080 | <1e-24 |
| Block 2 familiarity, presented / lure | −0.003 / +0.002 | — | — | n.s. |
| Block 1 familiarity, presented / lure | 0.9747 / 0.9749 | — | — | n.s. |

**The symmetry in §14.5 was an artefact of the leaky weighting.** With clean masks the
dissociation is strongly **asymmetric**: scrambling hurts schema memory (−0.52) far more
than it helps specific memory (+0.07). Both directions survive; only Block 1 is large.

Familiarity gives d′ ≈ 0 in **both** blocks — lures draw exactly as much familiarity as
presented items. All discrimination comes from recollection, in both blocks. That is §6's
claim in its strongest form, and it means the combined strength is slightly *worse* than
recollection alone (Block 2: 1.16 vs 1.73). That is a prediction, not a defect: a subject
rating "how much does this feel like something I saw" cannot isolate the recollection
term, so their d′ must fall short of it.

---

## 16. The primary mechanism is a division of labour, not load reduction

> §16 stands as written. The *secondary* mechanism it names — "capacity relief" from
> PE gating — does not: the gate scales write strength, not the number of stored
> patterns, so it cannot relieve crosstalk. §17.2 replaces it.

§13.4 concluded that the schema's episodic value is that it lets you not store what is
predictable — capacity relief. That is one benefit, but it is the *secondary* one, and it
only exists when PE gating is switched on. The primary benefit is in the residual code
itself and needs no gate at all.

**The clean test: hold trace count exactly constant.** With no gate both conditions store
39 traces at strength 1, so any order effect cannot be about how much is stored. 100
simulated subjects:

| | ordered | scrambled | diff | p |
|---|---|---|---|---|
| traces stored (count) | 39.0 | 39.0 | 0.0 | — |
| **trace energy in the specific dims** | **34.8%** | **12.7%** | +22.1pp | 6e-106 |
| **schematic content surviving into the trace** | **24.8%** | **62.8%** | −37.9pp | 2e-113 |
| Block 2 d′ | 1.178 | 1.073 | +0.105 | 0.010 |

When the order is predictable the schema absorbs about three quarters of the schematic
content and the hippocampal trace is left carrying mostly specific information. When it
is scrambled the schema cannot absorb it, so **the hippocampus is forced to carry 63% of
the schematic content**, and that displaces capacity that would otherwise hold the
specific detail.

This is the posterior-medial / hippocampal division of labour stated directly, and it
maps onto the architecture without any extra assumption: `residual = x − s·w` *is* the
handover. It also needs no free parameter — `w` comes from `dim_weight`, which is learned.

So the mechanisms stack:

| mechanism | source | when it operates | free parameters |
|---|---|---|---|
| **division of labour** (primary) | residual coding `x − s·w` | always, including at fixed load | none — `dim_weight` is learned |
| **capacity relief** (secondary) | PE gating | only when memory is crowded, and it costs the order effect (§14.4) | gate strength, unconstrained |

### 16.1 What the division of labour actually protects — and from what

The benefit is **fully mediated** by how much of each hippocampal trace is given over to
specific content. Per item, pooling both conditions (n = 8580):

| | r | p |
|---|---|---|
| specific share of trace energy → 2AFC correct | **+0.139** | 2e-38 |
| condition (ordered vs scrambled) → correct | +0.045 | 4e-05 |
| **condition → correct, controlling the share** | **−0.055** | 4e-07 |
| share → correct, controlling condition | +0.143 | 2e-40 |

Controlling for the share does not merely weaken the order effect, it **reverses** it.
The whole advantage is the share: 0.348 of trace energy in the ordered condition against
0.127 in the scrambled one.

**The competition is inside each trace, not between traces.** Specific-dim content is
stored identically in both conditions — `dim_weight` ≈ 0 there, so
`residual_specific = x_specific` either way — which is why specific-dim interference
measures were null all along (§2.1). And competition *among* the stored specific parts
predicts accuracy in the wrong direction (r = −0.066). What differs is composition:
patterns are L2-normalised before they enter `W`, so each trace has a fixed
representational budget, and schematic content in a trace crowds out specific content
within that budget.

So the mechanism, stated exactly:

    schema predicts well  ->  little schematic content left in the residual
                          ->  after normalisation, specific content holds 0.348 of the trace
                          ->  good specific memory

    schema mispredicts    ->  much schematic content retained
                          ->  specific content squeezed to 0.127
                          ->  poor specific memory

This supersedes the earlier split of the effect into "a baseline advantage plus some
interference resistance" (§17). There is one mechanism, and the resistance-to-added-
material component (ordered degrades 0.86× as fast) is a small consequence of it rather
than a separate contributor.

Two caveats worth keeping:

- **The handover is partial.** Even in the ordered condition 24.8% of the schematic
  content still reaches the hippocampus and only 35% of trace energy is specific, because
  `dim_weight` is ~0.88 rather than 1.0 and the schematic dims are both more numerous
  (48 vs 16) and larger in magnitude. The model does not claim the hippocampus stops
  encoding scene identity, only that it encodes less of it.
- **This is by far the largest effect in the simulation** (p ~ 1e-113 against 1e-2 for the
  behavioural readouts). The mechanism is unambiguous inside the model; what is small is
  how much of it survives into a recognition d′. That gap — huge change in what is stored,
  modest change in what can be discriminated — is itself worth stating, because it
  predicts that measures closer to the trace (cued recall, pattern completion) should show
  the manipulation far more strongly than old/new recognition does.

---

## 17. Interference does not govern this memory (2026-08-01)

A natural reading of the U-shape's rising limb is that high-PE items are more distinctive,
so they suffer less interference and are retrieved better. It was tested directly and it
is **not** what the model does. Two other claims fell with it.

### 17.1 The classical Hopfield here is a global-match device, not a set of attractors

The proper interference measure for a Hebbian outer-product memory is the per-pattern SNR,
signal `g_j` against weighted crosstalk `Σ_{i≠j} g_i·cos(v_i,v_j)²`. Correlating it with
paired-discrimination accuracy:

| condition | items stored | load / capacity | corr(log SNR, accuracy) |
|---|---|---|---|
| gate off | 39 | 4.4× | −0.268 |
| gate on (κ .5, floor .35) | 39 | 4.4× | −0.072 |
| boundary-only, 1 repeat | 7.1 | 0.8× | −0.028 (n.s., at ceiling) |
| boundary-only, 2 repeats | 15.1 | 1.7× | **−0.171** |
| boundary-only, 5 repeats | 39.4 | 4.4× | −0.094 |

**Less interference predicts worse retrieval, at every load, with and without competition.**
Raising `n_repeats` so the same sub-event types recur at boundaries does create real
competition (mean |cos| among stored patterns 0.099 → 0.178) and takes performance off
ceiling (0.993 → 0.747), and the sign only becomes *more* negative.

The reason is structural. Retrieval is `W @ x` iterated and normalised, and
`W @ x = Σ_i g_i v_i ⟨v_i, x⟩`. A pattern similar to many others collects responses from
all of them and comes back with a well-determined direction; an isolated pattern collects
little and comes back noisy. Crowding therefore *helps* (corr +0.22). This is the same
fact seen elsewhere — the memory fails at partial-cue completion (0.15–0.21) and at
denoising (worse than the cue), but discriminates stored from unstored content well. It
behaves as a weighted global-match device throughout, never as separable attractors.

**A modern (softmax) Hopfield does support the interference account — and reverses the
core result.** Same encoding, retrieval swapped for `Σ softmax(β⟨v_i,x⟩ + log g_i)·v_i`:

| retrieval | 2AFC specific | corr(log SNR, acc) | order effect (ordered − scrambled) |
|---|---|---|---|
| classical | 0.856 | −0.080 | **+0.021** (p=.04) |
| modern β=1 | 0.792 | **+0.143** (p=6e-14) | **−0.041** (p=9e-05) |
| modern β=2 | 0.905 | — | **−0.055** (p=3e-13) |

Softmax retrieval keys on similarity to the whole probe, so it rewards storing raw
content — which is what the *scrambled* group does. The interference account and the
central prediction are therefore mutually exclusive across these two memories. **Decision
(2026-08-01): keep the classical Hopfield** — it is what simulation_briefing.md §7
requires and what the core prediction depends on — and drop interference as an
explanation for anything here.

### 17.2 What PE gating is actually for

§13.4 justified gating as capacity relief. That is wrong on the mechanics:
`W += strength · outer(v,v)` scales each trace's weight but leaves all 39 patterns in `W`,
so crosstalk is untouched; and a uniform scaling cancels under retrieval normalisation.
Gating can only *redistribute* weight between items, so some must lose whatever others
gain. Aggregate accuracy falls monotonically with gate strength (0.881 → 0.858 → 0.710 →
0.632), and so does the order effect (§14.4).

The real justification is a phenomenon, not an efficiency:

| | within-routine | boundary |
|---|---|---|
| no gate | 0.907 | **0.760** |
| gate κ .5, floor .35 | 0.842 (−0.065) | **0.930 (+0.170)** |
| gate floor 0 | 0.556 (−0.351) | 0.983 (+0.222) |

**Without a gate the model predicts boundary items are remembered *worse* on specific
content** — backwards from the event-segmentation literature. Gating is what puts that
right. `floor = 0.35` buys +0.170 at boundaries for −0.023 on the weighted average; going
further is a bad trade.

So gate strength selects which phenomenon the model matches:

| target | gate |
|---|---|
| boundary memory advantage | required, floor ≈ 0.35 |
| largest ordered > scrambled effect | off |
| U-shape limbs | on, and stronger is more visible |

It remains the largest unconstrained parameter in the account.

### 17.3 The rising limb is a step, not a slope

> **Superseded by §20.7.** The U-shape analysis behind this section summed
> `z(familiarity) + z(recollection)`, which contradicts `combine()`'s raw sum and
> magnified a 0.009 fluctuation in familiarity into an apparent falling limb. Familiarity
> is effectively constant here (sd 0.0053). The falling limb as described below is an
> artefact; the rising limb is real and survives without the gate. The paired
> discrimination results in this section are unaffected — only the two-limb decomposition
> is.

Measured with a paired discrimination (target vs a foil differing only in the queried
dimension), which cancels the resonance inflation in the raw cosine readout:

| | within-routine | boundary |
|---|---|---|
| schema-dim 2AFC, level | 0.414 | **0.871** |
| corr(PE, accuracy) *within* the group | +0.073 (p<1e-4) | **+0.026 (p=.51)** |

The level difference is large and real. The slope *inside* the boundary group is not:
the +0.087 reported in §14.5 came from the raw recollection measure, which rises with PE
(+0.184) partly because higher-PE traces resonate more.

So the shape is: a **declining familiarity limb** across within-routine items, then a
**step up** to the boundary cluster, which is flat internally. Still U-shaped overall, but
the right-hand side is a level effect from stronger encoding, not a graded relationship.
`figures.py` and `1_ushape.png` are annotated accordingly.

Note also that within-routine schema-dim discrimination is **0.414, below chance** — for
predictable items the hippocampal trace carries essentially no scene-identity information
at all. That is the division of labour (§16) at its limit, and it is the direct reason for
the Block 1 reversal.

---

## 18. Separate streams vs the experiment's mixed design — a deliberate choice

Every effect size in this document is measured with each condition in **its own encoding
stream** — one all-ordered run and one all-scrambled run per simulated subject, paired by
seed. The experiment does not work that way: it is within-subject, with **one encoding
stream carrying 4 ordered and 4 scrambled routines in a single memory** (§3.1).

**This mismatch is deliberate, decided 2026-08-02.** The model is being used to isolate
mechanism, and separate streams stop the two conditions from contaminating each other's
memory — which is exactly what you want when the question is *why* the effect happens.
The faithful design is available (`recognition.mixed_design`, ~13 lines to switch) and
should be used if quantitative predictions are ever needed.

**Every sign is identical under the two designs; only magnitudes differ.** The faithful
design gives larger effects:

| | separate streams | **one mixed stream** |
|---|---|---|
| Block 2 (specific) d′ | +0.074 (p = .020) | **+0.246 (p = 3e-07)** |
| Block 2 ROC AUC | +0.018 (p = .008) | **+0.052 (p = 2e-07)** |
| Block 1 (schema) d′ | −0.523 (p < 1e-22) | **−0.645 (p = 8e-14)** |
| Block 1 ROC AUC | −0.080 | −0.082 |
| 2AFC specific | +0.030 (p = 5e-05) | +0.053 (p = 4e-06) |

**The whole increase comes from the scrambled items getting worse, not the ordered items
getting better.** Ordered items score 0.8774 alone and 0.8759 when sharing a memory with
scrambled ones — no cost at all (−0.001, p = .84). Scrambled items drop from 0.847 to
0.823.

That follows from §16.1. In a shared memory, retrieving a scrambled item picks up
crosstalk from every stored pattern, and the ordered group's patterns carry a much larger
share of specific content (0.331 vs 0.124). So the ordered traces inject more specific-dim
noise into a scrambled item's retrieval than other scrambled traces would. In an
all-scrambled stream every competitor is specific-poor and that noise is smaller.

Consequences of the choice:

- **The effect sizes in this document are conservative by roughly 3x.** They are fine for
  showing that a mechanism produces an effect in a given direction; they are **not** a
  basis for power analysis. Block 2 in particular reads as marginal (p = .02) here and is
  comfortable (p = 3e-07) under the real design.
- **The mixture is asymmetric**, so there is no trade-off in the experiment: the ordered
  routines lose nothing by sharing a memory with scrambled ones. That is an argument for
  the within-subject design on top of the usual variance one.
- Mechanism analyses (§16, §17) should **stay** on separate streams — cross-condition
  crosstalk is a confound there, not a feature.

`recognition.mixed_design(n_routines, seed)` returns the scrambled subset for one subject;
probes are then split by `routine_id` at analysis time.

---

## 19. Where this sits in the literature (2026-08-02)

Full texts read: Spens & Burgess 2024 (PMC10963272), Spens & Burgess 2024b "Hippocampo-
neocortical interaction as compressive retrieval-augmented generation" (bioRxiv
2024.11.04.621950v4), van Kesteren et al. 2013 (PLOS ONE 0056155), Greve et al. 2019
(PMC6390882), Frank & Kafkas 2019 (PMC6491626). Two papers were paywalled (Bein et al.,
Learn Mem 25:352; the bioRxiv "scaffold at the cost of specificity" preprint) and are
cited here only from abstracts.

### 19.1 The division of labour is Spens & Burgess's claim; the quantity is ours

Their paper states the mechanism in words:

> "Unpredictable aspects of experience need to be stored in detail for further learning,
> while fully predicted aspects do not" … "optimizing the use of limited hippocampal
> storage for new and unusual information."

That is §16. **So the mechanism is not a new proposal — it is theirs.** What this work
adds is that it becomes a measurable quantity with a mediation test:

| | Spens & Burgess | here |
|---|---|---|
| claim | predicted content need not be stored | schematic content occupies 24.8% of the trace when the schema fits, 62.8% when it does not (p = 2e-113) |
| link to memory | qualitative | the specific share **fully mediates** the order effect; controlling it reverses the condition effect (+0.045 → −0.055) |

The paper should be positioned as *quantifying and testing* that claim, not as proposing
it. That is both more accurate and easier to defend.

### 19.2 Their hippocampal store is a MODERN Hopfield network

Spens & Burgess use a modern Hopfield network (citing Ramsauer et al. 2021; Krotov &
Hopfield 2021). This model uses the classical Hebbian one, and §17.1 recorded that the
modern version **reverses** the core effect (+0.021 → −0.041). "Classical gives the effect
we want" is not a defensible reason, so the choice needs a real one.

**A stimulus-complexity argument was tested and does not hold.** The proposal was that a
modern Hopfield is needed for rich naturalistic stimuli but is too strong for simple
synthetic ones. Raising the stored material from 39 to 199 items:

| retrieval | 39 items | 79 items | 199 items |
|---|---|---|---|
| classical | +0.042 | +0.040 | **+0.048** |
| modern β=0.5 | −0.017 | −0.017 | −0.016 |
| modern β=1 | −0.039 | −0.030 | −0.026 |
| modern β=4 | +0.001 n.s. | −0.001 n.s. | +0.001 n.s. (still at ceiling, 0.947) |

The reversal does not shrink with more material, and β=4 stays at ceiling even at 199
items. (Caveat: this varies *quantity*, not richness — a real test of complexity would
need higher-dimensional, more varied stimuli and retraining.)

**The defensible reason is about the retrieval operator, not the stimulus.** The two
memories reward different things:

    classical:  W @ x = Σ_i v_i ⟨v_i, x⟩   -> a similarity-weighted blend of all traces
    modern:     softmax                     -> the single best-matching trace wins

The effect here depends on the ordered group's traces having a cleaner composition (0.348
vs 0.127 specific share). A blend rewards composition — a cleaner trace contributes better
specific content to the mixture. Winner-take-all rewards trace-probe similarity, and the
scrambled traces, having retained the raw input, match a full probe *better*. Hence the
sign flip.

Spens & Burgess use the MHN as a **teacher for consolidation**, where faithful recovery of
a specific pattern is exactly what is needed. This model reads out **strength for a
recognition decision**, where a graded global match is the appropriate operator — and it
is also what produces the dual-process signature (familiarity d′ ≈ 0, all discrimination
from recollection). Same memory system, two uses, two readouts.

### 19.2b The RAG paper: same theory, a different decomposition

Spens & Burgess (2024b) is much closer to this work than the Nature Human Behaviour paper.
It is sequential, and its encoding rule reads almost like ours:

> "Sequences are encoded in the hippocampus in compressed form. Specifically, a vector
> from which the sequence can be approximately decoded by neocortex is stored for each
> event, **together with the subsequences that are most surprising** given this compressed
> version of the event."

So the division of labour *and* surprise-based selective storage are both already theirs.
The hippocampus is again a modern Hopfield network, and it also stores one-step
transitions — the heteroassociative machinery this model would need for an ordering task.

**Surprise-based storage is in both models. What differs is the axis it operates on, and
that difference is load-bearing.** Their implementation ranks phrases by perplexity given
the gist vector and stores the top one:

| | Spens & Burgess 2024b | here |
|---|---|---|
| axis of decomposition | the sequence, into **subsequences** | each item, into **dimensions** |
| surprise-based storage | **discrete selection** — store the most surprising phrase | **graded gating** — `pe_gate` scales write strength, with a floor so nothing is ever dropped |
| effect on an item | kept whole or not at all | always written; its *composition* shifts |

Theirs is **selection over time**; ours is **reallocation within an item**, with an
optional graded modulation on top. Only the per-dimension version supports the
schematic/specific split that Block 1 and Block 2 map onto, and only it yields a
trace-composition quantity to mediate on (§16.1).

Two things to be accurate about on our side:

- **The headline results use no gate at all** (`gate="none"` is the default in both
  `episodic.encode` and `recognition.run_subject`). Gating is an available mechanism whose
  parameters are unconstrained (§17.2), not part of the reported effects.
- **When the gate is on it is graded, not a cut.** At `floor=0.35` a within-routine item
  is written at 0.375 and a boundary at 0.783 — a 2x difference, not presence vs absence.

**The discrete version — the one that matches their selection — was tested here and
fails.** `threshold, floor=0` writes 1 above the cut and 0 below. It puts the ordered
group inside capacity (7.8 patterns, 0.8x) and gives near-perfect retrieval *for the items
it kept* (0.996 vs 0.869), but aggregate performance collapses to −0.20, because the
skipped items cannot be recovered: the schema has nothing to contribute on the specific
dimensions, and on the schematic dimensions the prototype supplies content without
discriminating old from new (§17).

That is a boundary condition on discrete selective storage rather than a criticism of
their model — their readout is story recall, where a gist plus one salient detail can
carry the response. It fails here because the test interrogates every item on a dimension
the schema cannot supply.

They also do no recognition-memory analysis: across the full text, "false alarm" and
"d-prime" appear zero times, "lure" twice. Familiarity/recollection separation, false
alarms, ROC and the U-shape are not in either paper.

### 19.3 Consolidation: the design is already aligned

An earlier draft of this section treated the absence of a consolidation stage as the
model's biggest gap, on the strength of van Kesteren et al. (2013), who found the schema
effect on item recognition at 20 h and 48 h **but not at 0 h**.

**That concern does not apply here.** In van Kesteren the schema itself was learned in the
lab (novel visuo-tactile associations), so "requires consolidation" refers to consolidating
a *newly acquired* schema. This experiment uses **pre-existing real-world routine
knowledge** and tests **immediately**, so the schema is available at encoding and can act
at once. The model matches that design exactly: a pre-trained, frozen schema GRU and no
replay stage.

Worth keeping as a discussion-section limitation, not a design problem: even with a
pre-existing schema, *integrating new memories into it* may still take time, so effects
could grow with delay.

van Kesteren et al. (2013) tested item recognition at 0 h, 20 h and 48 h:

> item memory was significantly better for congruent items at **20 h and 48 h but not at
> 0 h**; "the schema effect on visual item recognition only arises after consolidation."

**This model has no time axis and predicts an immediate effect.** If the behavioural test
is immediate, that literature predicts no effect, and a null result would not distinguish
"the model is wrong" from "not enough time has passed." This is the most consequential gap
and it needs resolving before the experiment is interpreted — either by adding a
consolidation stage (replay training the schema GRU on stored traces, which the existing
code can already do) or by stating explicitly that the model predicts an encoding-time
storage difference rather than a delayed behavioural one.

### 19.4 The order manipulation avoids the confound that makes this literature messy

Greve et al. (2019) frame the field as a paradox: congruent material is remembered better
in some studies, incongruent material in others (the von Restorff isolation effect). The
usual reason is that incongruent items are **more distinctive and draw attention**.

Manipulating **order** with content held identical removes that confound entirely. The
same 40 scenes appear in both conditions; only their predictability differs. This is a
genuine methodological advantage over item-level congruency manipulations and is worth
stating explicitly.

Greve et al. also report that the incongruency advantage appears "once the use of prior
knowledge at test was controlled" — which is precisely what the familiarity/recollection
decomposition (§15.4) does. That is a methodological precedent, not something invented
here, and should be cited as such.

### 19.5 What is actually new

The *theory* — hand predictable content to neocortex, keep the surprising remainder in
hippocampus — is Spens & Burgess's, in both papers. What is not in either of them:

1. **A per-dimension decomposition** rather than selection over subsequences (§19.2b).
   This is what lets a single item be split into a schematic and a specific part, which is
   what the two experimental blocks measure.
2. **The mediation result** (§16.1): trace composition is a measurable quantity, and it
   *fully* accounts for the behavioural effect — controlling it reverses the condition
   difference.
3. **Recognition-memory analysis**: lures, false alarms, familiarity vs recollection, d′
   and ROC. Neither paper does any of this; the readout there is reconstruction quality.
4. **The recall/recognition dissociation on the same dimension** (§14.5) — opposite signs
   for the same content depending only on how it is queried.
5. **The U-shape decomposition** (§17.3): a falling familiarity limb and a step up at
   boundaries, with the conditions under which each appears.
6. **An order manipulation free of the distinctiveness confound** (§19.4).
7. **Boundary conditions on their mechanism**, established negatively: PE cannot modulate
   specific-dim traces through residual size (§12.5); interference does not govern a
   classical Hopfield at any load (§17.1); and selection-based storage fails when the
   skipped items cannot be recovered (§17, §19.2b).

---

## 20. The online trust gain, and the resolution of the boundary/order conflict (2026-08-03)

**This section changes the canonical configuration.** Every number reported in §12–§19
was produced with `gain="hybrid"` and, where stated, a PE write-gate. Both are
superseded here. `episodic.encode`, `recognition.run_subject` and `recognition.collect`
now default to `gain="trust"`, gate off.

All numbers below are n=400 simulated subjects per condition, which is now cheap: see
§20.6.

### 20.1 The requirement that ruled out the old settings

The design constraint, stated repeatedly and treated here as binding:

> A scrambled routine must not go on applying the schema regardless, and neither should
> a routine boundary. So there has to be an online decision about *how much* schema to
> use — and it must not get complicated.

This is a theoretical requirement, not a fit criterion, and it disqualifies settings
independently of how large an effect they produce:

| gain | w_t | verdict |
|---|---|---|
| `static` | `dim_weight`, fixed | **Disqualified.** No online judgement at all. Keeps subtracting a prediction it has already got wrong. |
| `online` | `1 − (s−x)²/var`, per dimension per step | Online, but a one-sample estimator per dimension. Measures w ≈ 0.47 on dimensions the schema cannot predict at all — that is noise, not evidence. |
| `hybrid` | the product of the two | Inherits the per-dimension noise; `dim_weight` only caps it. |
| `trust` | `dim_weight × clip(1 − PE_t, 0, 1)` | **Canonical.** |

`static` gives by far the largest Block 2 effect (+0.2497, p < 1e-4, against +0.0537 for
`hybrid`), and it was recommended on that basis before the constraint was applied. It is
recorded here as rejected on theory, so that the effect size is not mistaken for
evidence in its favour.

### 20.2 What `trust` is

```python
w_t = dim_weight * clip(1 - pe[t], 0, 1)          # episodic.py, encode()
```

Two levels, each answering a different question:

- **`dim_weight`** — offline, one value per dimension: *which* dimensions the schema can
  predict at all. Held-out explained variance, computed once after training.
- **`1 − PE_t`** — online, one scalar per frame: *whether it is right just now*.

`PE_t = 1 − wcos(s_t, x_t, dim_weight)` was already being computed and was previously
used only to gate the write. Nothing new is introduced: no new signal, no new parameter.
PE can exceed 1 when the prediction points the wrong way (cosine negative), which the
clip absorbs.

Frame by frame on one stream (`ns_0.5`, seed 70000):

```
=== ORDERED ===                          === SCRAMBLED ===
  t sub-ev bound     PE  trust  share      t sub-ev bound     PE  trust  share
  2      2         0.017 0.983  0.377      1      3         0.628 0.372  0.068
  3      3         0.030 0.970  0.399      3      0         0.690 0.310  0.071
  4      4         0.027 0.973  0.604      4      1         0.060 0.940  0.464
  5      0    <<   0.879 0.121  0.027      5      0    <<   0.923 0.077  0.043
  6      1         0.021 0.979  0.679      8      1         0.485 0.515  0.079
 10      0    <<   1.297 0.000  0.096     12      4         0.028 0.972  0.519
```

(`share` = specific dims' share of residual energy.)

The mechanism is genuinely per-frame, not a condition label. Scrambled t=12 happens to
land on a transition the schema knows: PE 0.028, trust 0.972, share 0.519 — treated
exactly like a good ordered frame. Ordered t=5 and t=10 are boundaries and get trust
≈ 0 — the schema is switched off inside the ordered condition. That is the requirement
in §20.1, met by construction rather than by tuning.

### 20.3 Canonical result

`output/v2/ns_0.5`, gain `trust`, no gate, n_iters 5, n = 400:

```
Block 2 specific (lure = same-scene variant)
                              ordered   scrambled     diff        p
recollection, presented        0.4793      0.3841  +0.0952   0.0000
d' from recollection           1.6627      1.5136  +0.1491   0.0000
d' combined                    1.1288      1.0566  +0.0722   0.0001
ROC AUC                        0.7843      0.7682  +0.0161   0.0000

Block 1 schema (lure = omitted sub-event)
d' combined                    1.3395      1.7983  -0.4588   0.0000
```

Larger than `hybrid` at every n_iters (+0.0722 vs +0.0537 at 5; +0.0921 vs +0.0598 at
8), so the principled setting is also the better-performing one.

The mediator is unchanged from §16.1 — specific share of residual energy, ordered ≈ 0.42
vs scrambled ≈ 0.15. Within one trace, schematic and specific content compete for a
fixed budget; when the schema is trustworthy its share is handed to the GRU and the
Hopfield spends the budget on specific content.

### 20.4 The boundary/order conflict was a readout artefact

§20-prior work reported these two as irreconcilable, on a 17-cell gate grid where they
correlated at **r = −0.971, R² = 0.94** (and where only `floor` mattered, r = +0.90;
`kappa` was irrelevant, r = −0.03). That grid result is correct but was over-read: both
quantities were measured on the **specific-dim readout**. Specific content is one budget,
so of course they trade off — it was one measurement, not two.

Measured properly (ordered stream, no gate, n=200):

```
gain=trust                            within   boundary      diff
frame PE                               0.031      0.989   +0.958
specific share of trace energy         0.445      0.065   -0.380
Block 2 d'  (specific dims)            1.916      0.977   -0.939
Block 1 d'  (schema dims)             -0.072      0.969   +1.041
```

d' against a matched lure, not a 2AFC proportion: both blocks of the experiment collect
a 6-point confidence rating about a single probe, so nothing in it is a forced choice and
the analogue has to be an absolute-criterion measure.

At a boundary PE ≈ 0.99, trust → 0, nothing is subtracted and the whole frame is stored.
But the frame is dominated by its 48 schema dimensions against 16 specific ones, so the
specific share inside that trace collapses from 0.445 to 0.065. The boundary trace is
stronger overall and **its specific component is crowded out by its own schematic
component** — the §16.1 competition mechanism operating within a single frame instead of
across a condition.

So the model makes a **dissociated pair of predictions at boundaries**, not a single one:

| queried content | boundary vs within | Δ d′ |
|---|---|---|
| item-specific detail (Block 2) | **worse** | −0.939 |
| schematic / scene context (Block 1) | **better** | +1.041 |

Note the within-routine Block 1 d′ is **−0.072, i.e. at or just below zero**. Mid-routine
items retain essentially no scene information, because the schema predicts it and it is
therefore subtracted out of the trace. Only boundaries keep it.

Both effects hold simultaneously under one configuration with no gate:

```
Block 2 order effect (specific readout)   +0.0722 d'   p = 0.0001
Boundary advantage  (Block 1 readout)     +1.041  d'
```

**Resolved in §20.8** — the design already answers this. §8 states the rating relates to
"Block 1 for the schema dimension, Block 2 for the specific dimension", so the experiment
queries **both**, in separate blocks. The two rows above are therefore not alternatives:
they are the Block 1 and the Block 2 prediction respectively.

**Do not use raw recollection for this contrast.** It reports boundary +0.116
(p < 1e-4), which looks like support but is confounded: at a boundary the stored pattern
is ≈ the probe itself (nothing was subtracted), whereas mid-routine the stored pattern is
`x − s·w` and differs from the probe. That gap measures cue-trace match, not memory
quality. The d′ measures are immune because the target and the lure get identical
treatment, so the cue-resonance baseline cancels in the difference.

### 20.5 Unresolved: n_iters flips the sign

Not fixed by `trust`, and it must be reported.

```
gain      n_iters   B2 d_comb        p   B2 abs(ord)
trust           1     -0.3348   0.0000       1.686
trust           3     +0.0087   0.6475       1.366
trust           5     +0.0722   0.0001       1.129
trust           8     +0.0921   0.0000       0.918
static          1     -0.1868   0.0000       1.492
static          5     +0.2497   0.0000       1.053
hybrid          1     -0.2728   0.0000       1.736
hybrid          5     +0.0537   0.0042       1.150
```

Same pattern under all three gains, so it is a property of the retrieval dynamics, not
of the gain. Two things about it are uncomfortable:

- Absolute memory is **best** at n_iters = 1 and falls monotonically with iteration.
- The order effect is **negative** at n_iters = 1 and only becomes positive from 3.

So the ordered advantage does not lie in initial trace strength — at a single-shot
readout the scrambled group is ahead, matching Block 1. It lies in which traces survive
iterative attractor convergence. That is a coherent mechanism, but it was read off the
curve after the fact; it is not an independent prediction, and there is currently no
principled basis for fixing n_iters at 5. Treat it as a free parameter with a
sign-flipping dependency until an independent constraint is found.

### 20.6 Hardware note

Recognition and episodic simulation run **faster on CPU than on GPU** — 64-dim tensors,
so kernel-launch latency dominates (2.2 subj/s on one RTX 6000 Ada vs 3.5 subj/s on one
CPU core). Training does fill a GPU (7.0s vs 14.9s per 40 epochs).

`parallel.py` exploits this: `parallel.py recog` shards subjects across the 8 available
CPU cores (n=400 in 12.6s against ~180s serial, verified bit-identical to a serial run),
`parallel.py jobs` round-robins whole commands across the 4 GPUs for training grids.

This matters for the record, not just for speed: several conclusions in §12–§19 were
drawn at n=70–150 and at least one (the `routine_similarity` result) did not survive
n=200. There is no longer any reason to report an effect at n < 400.

### 20.7 The U-shape after the gate was dropped — and a z-scoring correction

> **The U-shape claim in this section is WRONG — see §20.10.** The trough came from an
> invented Block 1 foil that was itself a studied item. Against the real lure (the omitted
> sub-event) Block 1 rises monotonically under every configuration. The z-scoring
> correction below stands, and so does the interference-vs-dilution logic; the U does not.

The U-shape was previously attributed to the PE write-gate (§17.3). With the gate gone
(§20.1) the question is whether it survives. It does, but not in the form previously
reported, and the earlier form contained a methodological error that has to be recorded.

All numbers: `gain="trust"`, no gate, n=300 subjects, 23400 items, `output/v2/ns_0.5`.
Recollection is always a DISCRIMINATION, `wcos(retrieve(x), x, q) − wcos(retrieve(foil),
foil, q)`, never the raw retrieval cosine — see the warning in §20.4, which bites hardest
here, since under `trust` a high-PE frame has nothing subtracted and so its stored
pattern is ≈ the probe itself. That inflates exactly the high-PE end where the rising
limb is claimed.

**The correction.** §17.3's U-shape analysis summed `z(familiarity) + z(recollection)`.
That contradicts `combine()`, which is deliberately a RAW sum for the reason given in its
docstring: z-scoring inflates a signal-free term to unit variance. Under the canonical
raw sum:

```
SCHEMA readout            fam       rec   RAW fam+rec    z-sum
[0.010,0.023]           0.980    -0.008        0.972    0.918
[0.023,0.027]           0.975    -0.012        0.963   -0.007
[0.027,0.035]           0.971    -0.023        0.948   -0.857
[0.035,0.232]           0.972    -0.047        0.925   -0.866
[0.232,0.472]           0.975    -0.001        0.974   -0.036
[0.472,0.611]           0.975    +0.020        0.995    0.104
[0.611,0.914]           0.975    +0.052        1.026    0.306
[0.914,1.453]           0.975    +0.068        1.042    0.437

sd(familiarity) = 0.0053      sd(recollection) = 0.1361
```

Familiarity does not vary: range 0.971–0.980 across the entire PE axis. The steep
"familiarity-driven falling limb" of §17.3 was a 0.009 fluctuation magnified by
z-scoring. **The falling limb as previously described is an artefact.** This is the same
error `combine()` already documents, recurring in a different analysis.

**Why familiarity cannot vary here — a modelling limitation, not a result.** Familiarity
is `wcos(nearest prototype, x, schema dims)`, and the stimulus is generated as prototype
plus small noise, so this cosine sits at ≈ 0.975 for every item. Its sd is 1/26 of
recollection's. Any account in which the low-PE end is held up by *degrading prototype
completion* is currently inexpressible: completion quality is a constant. Giving it
variance (per-item `noise_schema`, unequal sub-event typicality, or completing with the
GRU rather than the nearest prototype) is a live option, untested.

**So the U lives entirely in recollection, i.e. on the hippocampal side.**

**Interference or within-trace dilution?** Decisive test: re-run each item's retrieval
against a Hopfield holding only that one item, where no crosstalk is possible.

All d′ against a matched lure.

```
PE bin           share   B2 FULL  B2 SOLO   B1 FULL  B1 SOLO
[0.012,0.023]    0.490     1.990    5.565    -0.089    4.843
[0.027,0.034]    0.437     1.894    5.615    -0.208    4.904
[0.034,0.233]    0.299     1.669    5.694    -0.422    4.192   <- trough
[0.233,0.474]    0.101     1.280    5.763    +0.010    5.814
[0.613,0.917]    0.069     1.249    5.407    +0.548    6.320
[0.917,1.453]    0.064     1.068    5.700    +0.676    6.069

boundary vs within-routine, ordered stream:
  Block 2   FULL -0.939    SOLO -0.010     <- the disadvantage needs other traces
  Block 1   FULL +1.041    SOLO +0.919     <- the advantage does not
```

The two readouts come apart:

| readout | shape | mechanism | needs other traces? |
|---|---|---|---|
| specific | monotone decline | within-trace dilution, made costly by crosstalk | **yes** |
| schema | U | how much schema content is in the trace at all | **no** — stronger without |

- **Specific (Block 2).** With one trace stored, d′ is flat at ≈ 5.6 regardless of PE, and
  the boundary disadvantage collapses from −0.939 to **−0.010**. The decline requires
  other traces. But *which* items suffer
  is set by within-trace composition, not by PE: r(PE, memory) = −0.194, and the partial
  correlation controlling specific share is **−0.037**, i.e. it vanishes. Writes are
  normalised (`v/‖v‖`), so a schema-dominated residual contributes little specific signal
  to `W` while still having to compete with every other pattern. Dilution decides who
  suffers; crosstalk decides how much it costs. *Caveat:* d′ ≈ 5.6 with a single trace is
  near ceiling, so this test cannot rule out a weak single-trace decline hidden by it.
- **Schema (Block 1).** The U survives with a single trace (4.843 → 4.192 → 6.069) and the
  boundary advantage barely moves (+1.041 → +0.919). Removing all crosstalk does not
  weaken it, so it is not an interference
  phenomenon. The trough at PE ≈ 0.1 is where the schema has been subtracted most
  cleanly and the frame is not yet a boundary — nothing schematic is left in the trace to
  retrieve.

**Total memory has no U.** The declining Block 2 component is much the larger of the two
(d′ range 1.99 → 1.07, against −0.09 → +0.68), so an unsplit measure declines monotonically
and hides the Block 1 curvature entirely.

**Prediction, and it is sharper than §17.3's.** The U-shape appears *only* when the
memory question queries schematic/contextual content. A question about item-specific
detail gives a monotone decline, and an unsplit overall-memory measure gives a decline
too, because the falling component is larger. The experiment queries both, in separate
blocks — see §20.8, which assigns each curve to its block and closes the question raised
in §20.4.

**On the gate as an amplifier.** With `hybrid` + gate (κ=0.5, floor=0.35) the schematic
recollection limb runs −0.453 → +0.843 against −0.389 → +0.452 ungated, roughly double.
The gate is not required for the U but does steepen it, and under the gate the rise is
boundary-specific, whereas under `trust` alone it begins at PE ≈ 0.5 where only 1% of
items are boundaries — i.e. ungated, the rising limb tracks *schema failure* in general,
including scrambled mid-routine items, not *event boundaries* specifically. That is a
substantive difference from the original prediction and is testable in the data.

### 20.8 Which block carries which curve — the readout question, closed

> **The "U-shaped" row of the table below is WRONG — see §20.10.** Block 1 rises
> monotonically; it does not fall first. The block-to-dimension assignment, the boundary
> rows and the reversal-in-every-contrast point are unaffected.

§20.4 and §20.7 both ended on "which content does the behavioural test query?" That was
a false dilemma. §8 already fixes it:

> the rating is the per-item PE, related to that item's memory
> (**Block 1 for the schema dimension, Block 2 for the specific dimension**)

The experiment queries **both**, in separate blocks, on the same items with the same
ratings. So the model's readout-dependent results are not competing candidates needing a
choice — they are the Block 1 and the Block 2 prediction. Forced by the §1 correspondence
table, not chosen.

| | Block 1 — *which sub-event* | Block 2 — *which object variant* |
|---|---|---|
| model readout | schema dims | specific dims |
| memory vs encoding rating | **U-shaped**: falls to a trough at PE ≈ 0.1, then rises | **monotone decline** |
| routine boundaries | **better** (Δd′ +1.041) | **worse** (Δd′ −0.939) |
| ordered vs scrambled | scrambled better (d′ −0.459) | ordered better (d′ +0.072) |
| mechanism | how much schema content survives in the trace; not interference (§20.7) | within-trace dilution × crosstalk (§20.7) |

The headline is that **every one of these rows reverses between the two blocks**, on the
same items. The order effect was already known to dissociate this way (§12, §14.5); the
PE axis and the boundary contrast now dissociate the same way. One mechanism — how much
of the schema is subtracted, decided online by `trust` — produces all three reversals,
because subtracting the schema is exactly the operation that trades schematic trace
content for specific trace content.

That makes the analysis plan concrete, and it is the analysis §8 already specifies (PE as
a within-group continuous predictor, group as a factor): run it **twice**, once per
block, and the model predicts opposite curvature. A single collapsed memory measure would
show a monotone decline and hide the effect, because the falling Block 2 component is the
larger of the two (§20.7, "total memory has no U").

**§8's Block 2 prediction is contradicted and should be read as superseded.** §8 argues
"low-PE sub-events get near-zero residuals (schema-filled → weak specific memory);
high-PE sub-events get large residuals (episodically encoded → strong specific memory)",
i.e. specific memory *rising* with PE. Measured, it falls: 0.436 → 0.252 across the PE
range. §8's own inline note already anticipated the reason (§12.5: `dim_weight` ≈ 0 on the
specific dims, so their residual never scaled with PE in the first place), and §20.7 adds
the positive account — what falls with PE is the specific share of the trace (0.486 →
0.065), so the specific component is progressively crowded out by schematic content.
The U-shape in the data, if it is there, should be in **Block 1**.

### 20.9 Figures

`figures.py` was rewritten to be self-contained — it simulates its own data (cached to
`figdata.npz`, `--refresh` to recompute) instead of stitching together npz files written
by throwaway scripts, which is how it came to be showing `hybrid` + gate long after that
stopped being the configuration. Regenerate with:

    python3 figures.py --run output/v2/ns_0.5 --out output/v2/figures

n=400 subjects for the block d′ panels, n=200 for the per-item panels, ~60 s on the 8 CPU
cores. The previous set is kept at `output/v2/figures_old_hybrid_gate/`.

| | shows |
|---|---|
| `1_ushape_by_block` | the headline: U in Block 1, monotone decline in Block 2, same items and same ratings |
| `2_dissociation` | every contrast reverses between blocks — order effect and boundary effect side by side |
| `3_trust_mechanism` | `trust` against PE, and the specific share of trace energy it costs (r = −0.805) |
| `4_interference_vs_dilution` | the single-trace control: Block 2's decline needs crosstalk, Block 1's U does not |
| `5_gate_negative` | why the gate was dropped, as a floor sweep, with the r = −0.971 grid result in the caption |
| `6_familiarity_ceiling` | the methodological figure: the same data raw and z-scored, side by side |

Two plotting decisions worth recording, because both were wrong in the first pass:

- **PE is plotted at rank, not at value.** It is heavily right-skewed — about half the
  items sit below 0.04 and the rest spread to 1.4 — so quantile bins on a linear PE axis
  pile the entire falling limb onto the origin and the U vanishes. Ticks carry the real PE
  values.
- **Everything is d′ against a matched lure — never a 2AFC proportion.** Both blocks of
  the experiment collect a 6-point confidence rating about a single probe, so nothing in
  it is a forced choice and the analogue must use an absolute criterion. `figures.py`
  stores raw target and foil strengths per item and computes d′ over whatever group is
  being reported (a PE bin, boundary vs within-routine); error bars are bootstrapped,
  since d′ is not a mean. `recognition.two_afc` remains diagnostic-only and no figure or
  reported number uses it.
- **The boundary contrast uses the ordered stream only.** Pooling the scrambled stream in
  compares boundaries against within-routine items that are already high-PE, which
  roughly halves the contrast.

### 20.10 Correction: there is no U-shape. The Block 1 foil was wrong.

**§20.7 and §20.8 are wrong about the U-shape and are superseded here.** The trough they
report is an artefact of the foil used in the per-item analysis, not a property of the
model.

**The error.** The per-item PE analysis invented its own Block 1 foil: take the target and
replace its schema dimensions with those of *another stored frame*. That foil is itself a
studied item. At low PE the target's own schema content has been subtracted out of its
trace, while the foil's borrowed scene is sitting in memory at full strength — so the foil
out-retrieves the target and d′ goes negative. The "trough" was the foil winning, not the
target being forgotten.

`recognition.make_blocks` never had this problem: its Block 1 lure is the **omitted
sub-event**, which was never encoded. The figures diverged from it.

**Corrected result.** Each old item scored against its own routine's omitted sub-event
(Block 1) and a same-scene variant (Block 2), binned by that item's encoding PE, d′ per
bin, n=200 subjects:

```
PE octile             1      2      3      4      5      6      7      8
Block 1 d'         0.95   0.95   0.99   1.66   1.76   1.85   1.97   2.04
Block 2 d'         2.11   2.12   1.87   1.58   1.39   1.50   1.26   1.19
```

Both monotone, in opposite directions. No trough in either.

**It is not a configuration choice.** Block 1 d′ rises monotonically under every setting
tried — the minimum sits in bin 1 or 2 in all of them:

```
config                  1      2      3      4      5      6      7      8
trust / no gate       0.91   0.94   0.95   1.62   1.72   1.81   1.95   2.01
trust / gate f=0.35   0.04   0.05   0.08   0.98   1.48   1.86   2.46   2.83
hybrid / no gate      0.89   0.92   1.07   1.74   1.74   1.81   1.91   1.94
static / no gate     -0.09  -0.10   0.11   0.25   0.67   0.84   0.64   0.79
```

**So the model does not produce a U-shape on either block.** What it produces is a
crossover: as prediction fails, the trace trades specific detail for scene identity.
Figure `1_division_of_labour` shows the mechanism directly — the schema-dimension residual
grows from ‖·‖ 4.1 to 15.4 across the PE range while the specific-dimension residual stays
flat at 4.0, because `dim_weight` ≈ 0 there means specific content is never subtracted at
all. Block 1 rides the growing term; Block 2 is diluted by it.

**One thing the gate does restore.** With the gate on, **Block 2 reverses to rising**
(0.66 → 2.31). That is the PE-graded encoding §8 predicted for specific memory, and it
exists only under gating. Ungated, Block 2 declines (2.14 → 1.22). This is a clean
empirical discriminator between the two mechanisms and a reason to keep the gated variant
as a reported alternative rather than only as a rejected one.

**Consequences for earlier sections.** §17.3's rising limb was measured against "a foil
differing only in the queried dimension", so it is subject to the same objection and
should not be cited for a U. §20.7's interference/dilution conclusion is *not* affected in
its logic — the single-trace control is a within-measure comparison — but its numbers were
computed with the bad foil and are restated in §20.9's figures with the correct one.

**Rule going forward:** any per-item analysis must use the same lures as
`recognition.make_blocks`. A foil built by borrowing content from another studied item is
not a lure; it is a second target.
