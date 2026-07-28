# Experiment ↔ model mapping and design rationale

How the behavioural experiment lines up with the computational model (see
`simulation_briefing.md` for the model itself), and the design decisions that follow
from requiring the two to correspond. The guiding constraint throughout: **keep the
changes to BOTH the experiment and the simulation small, and keep the predicted
dissociation robust.**

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

## 8.2 The order test (Block 3), and what it says about the model

Added after a critique that Block 1 has no clear predicted effect. That critique is largely
right, and the reason matters.

**Why Block 1 predicts ≈ null between conditions.** False alarms to the omitted step come from
schema completion, and the knowledge "a restaurant visit involves ordering" is **order
independent** — so both conditions complete equally. Hits are also matched (both saw the same
five steps). A condition difference could only come from second-order trace-quality effects.
The spec already conceded half of this (§5: high FA is a property of the schema dimension,
"*not* expected to be a schema-group advantage"), and §5/§6 above show the model stores no
schematic content episodically at all. **Block 1's value is therefore NOT a condition effect**
— it is (a) demonstrating schema-based false memory and (b) supplying the familiarity-dominant
ROC that contrasts with Block 2's recollection-dominant one. Keep it; stop claiming a d′
difference from it.

**Why an order test is where the schema effect should live.** The manipulated variable is
order, and Block 1 measures something order-independent — hence no effect. Order memory is
order-dependent by construction:

| routine condition | schema vs actual order | consequence |
|---|---|---|
| ordered | agree | schema alone suffices → near ceiling |
| scrambled | **conflict** | correct answers require episodic memory; **errors revert toward canonical order** |

So the *direction of error* in scrambled routines is a direct, continuous index of schema
intrusion. Implemented as **sequence reconstruction** (click the scenes in the remembered
order), which yields all 10 pairwise relations per routine and supports two scores that
dissociate only in the scrambled condition:
`tau_episode` (vs actual order) and `tau_schema` (vs canonical order).

**Placement.** Block 1 → Block 2 → **order test last**. It must follow Block 2 because its
scenes contain the tested objects and would reveal the encoded variants. Running Block 2 first
is safe: Block 2's trial order is randomized, so it conveys no information about encoding order
(it refreshes item memory, not sequence memory). Images rather than text were chosen to keep
the scrambled condition off the floor — that cell is the only informative one, and text labels
invite purely semantic responding.

**The structural gap this exposes.** Putting the two points together:
- the measure the model *can* produce (step presence) predicts no condition effect;
- the measure where the condition effect *should* live (order) is one the model **cannot
  currently produce** — the Hopfield stores one trace per sub-event with **no temporal or
  positional tag**, so the model has schema-based order but no *episodic* order memory.

That is not just a missing readout: the model's "schema dimension" is event **identity**, which
is order-independent, while the experiment manipulates **order**. To model the order test, the
stored patterns need a temporal-context / position code (e.g. a slowly drifting context vector).
**Recommendation: do not do this yet.** Get the core specific-dimension dissociation working
first (§2, §6); treat the order test as a behavioural measure the model does not yet cover, and
revisit temporal coding once the core result is stable.

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
- [ ] One frame per sub-event: `event_len → 1`, both schematic and specific dims constant
      per sub-event, fresh specific center per sub-event, prototype per sub-event type.
- [ ] **Drop the working-memory GRU** (redundant once a sub-event is one frame — §6.1) and
      redefine `PE = 1 − cos(s_t, x_t)` on the **schematic dims only**. Keep Hopfield residual
      storage — that is a different mechanism and carries the core claim.
- [ ] Always `use_schema=True`; contrast `schema_order` fixed vs random (driver change).
- [ ] Schema GRU operates per sub-event (predict the next sub-event); trained on fixed order,
      **fixed** at test (pre-learned, not retrained).
- [ ] Retrieval readout: nearest-prototype completion instead of a sequence-conditional /
      borrowed `s_t` (this also removes the monkey-patch in briefing §4.6).
- [ ] Decision stage: memory strength = familiarity(prototype) + recollection(Hopfield) →
      criterion sweep → ROC; balance the two terms per §6.
- [ ] U-shape analysis at the **sub-event grain**: entry-PE vs per-sub-event memory (§8).
- [ ] **8 routines run as ONE continuous stream** (routine1's sub-events → routine2's → … →
      routine8, one memory), mirroring the experiment's 40-scene encoding stream. Required —
      running each routine in isolation drops the cross-routine boundaries the analysis needs
      (§8.1). This also folds in cross-routine interference / memory load (was §9).
- [ ] Schema GRU **trained on all 8 routines** (8 scripts), with routine ORDER randomized in
      training so no spurious meta-order is learned → routine boundaries are high-PE. Bump
      `dim_schema` (≈48 distinct sub-events to separate) and possibly `dim_hidden`.
- [ ] Simulated subjects mirror the **within-subject** design: each run mixes ordered and
      scrambled routines in one stream (4/4), not an all-fixed vs all-random run (§3.1).
- [ ] Tune params so interference dominates the ordered-vs-scrambled contrast while PE-graded
      encoding shows up across items within a condition (§8).
- [ ] De-risk: validate the whole loop on 2–3 routines before scaling to 8.

**Experiment**
- [ ] **Within-subject** design (4 ordered + 4 within-instance-scrambled routines per subject,
      counterbalanced), **within-instance** scramble only. Do **not** add cross-routine mixing
      unless a matching model cell is built and validated first. (`config.design` can switch back
      to between-subject.)
- [ ] Keep the per-scene rating and the weak-schema routines — both are needed for the U-shape (§8).
- [x] Order test (Block 3) added, running last (§8.2). Not model-covered yet — needs temporal
      coding in the stored patterns; deferred until the core dissociation works.
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
