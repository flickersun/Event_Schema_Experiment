# Implementation notes — decisions & deviations from `experiment_spec.md`

`experiment_spec.md` is the original design document and has **not** been rewritten.
This file records what was actually decided and built, and — importantly — the places
where the implementation now **diverges** from that spec. Read this alongside it.

For how the experiment lines up with the computational model — the axis alignment, why
the design stays 2-group / within-instance, the context-cue decision, and the
schema-dimension recognition fix — see **`EXPERIMENT_MODEL_MAPPING.md`**.

Two builds share the same stimulus CSVs and the same randomization algorithm:
- `psychopy_exp/` — pure-Python PsychoPy build (local / in-lab). Complete.
- `js/` — JavaScript logic layer for a future online (jsPsych) build. Complete and
  **verified to produce identical sessions** to the PsychoPy build (see §6). The
  jsPsych *timeline* (display layer) is not built yet; only the logic layer exists.

---

## 1. Deviations from the spec

| Spec | Spec says | Implementation | Why |
|---|---|---|---|
| §1 | Explicit instance separator ("a new experience…") between routines, for both groups | **Removed.** All 40 scenes play as one continuous stream | Requested. The boundary consistency-dip becomes an implicit event-segmentation *measure* instead of an instruction. Restorable via `use_instance_separator: True` |
| §1 | Constrain the scramble so object scenes occupy matched serial positions across groups | **Not implemented** — plain within-instance Fisher-Yates, with a documented no-op hook | Pinning all 3 object scenes leaves only 2 movable filler scenes, which badly weakens the order manipulation. Deferred; serial position is logged so it can be handled statistically |
| §4 | Pleasantness rating recommended (neutral to both groups) | **Transition rating** — "How well does this picture follow from the one before it?" (1 = doesn't follow at all … 6 = follows perfectly) | Requested. Accepted risk: it makes the order manipulation explicit (demand characteristics), which is exactly what §4 warned about |
| §4 | Pleasantness 1–7 / expectedness 0–100 slider | **1–6** | Unified with the test blocks so the subject sees one scale throughout |
| §5 | Block 2 = 48 trials (target + lure for every object) | **24 trials** — each object tested with ONE version, counterbalanced across subjects | Chosen because the ROC is fit at the **group** level. Nobody ever sees both versions of an object, which removes the direct-comparison strategy entirely. `block2_design: "both"` restores 48 |
| §5 | Object highlighted with a box/arrow | **No highlight.** The question names the object | Requested; no bounding-box coordinates exist for the assets |
| §6 | Clinic step 3 object = magazine A / magazine B | **`reading material`** = magazine / newspaper | The generated lure image is a newspaper. Reframing the question was chosen over redrawing. This one item is easier (cross-category) than the rest |

## 2. Spec §9 open items — resolved

- **Cover task** — decided: consistency (see above).
- **Generate the omitted step's scene?** — all six scenes exist for every routine, so
  omission is fully counterbalanced across subjects.
- **Counterbalance which sub-event is omitted** — yes, by rotation (below).
- **Matched object serial positions** — still open (deferred, see §1 above).
- **Equalise variant-pair difficulty** — still open; a pilot item. The clinic
  reading-material pair is knowingly the easiest.

## 3. Design decisions made during implementation

**Block 1 question wording — the calibration rule.** Every presence question must
describe the sub-event at the level of its most diagnostic *visible action*, and no
finer. Two failure modes to avoid, in both directions:
- **Too functional / abstract** (spec's original worry): "was there a registration
  step?" forces the subject to translate image → function. Bad.
- **Too specific / detailed** (equally bad here): "…drinking orange juice from a tall
  glass?" turns a schema-presence judgment into an episodic-detail test — a subject who
  saw the step but not that detail may answer "no" (false negative on a real target),
  and it leaks the specific dimension into the schema dimension. It also tends to help
  the schema group, biasing the very contrast the study measures.
- The question must still **uniquely identify which sub-event it is** (so it can't be
  so vague it collides with another step in the same routine), and should avoid naming
  the tested object where possible (Block 1 precedes Block 2).

Quick test for each question: *could someone who has ONLY the schema and never saw the
video answer it from common sense?* If yes, it is at the right level (it probes schema
completion — what we want). If it requires recalling a picture detail, it is too
specific — pull it back.

**The distinction that resolves "too vague vs too specific".** These are not two ends of
one dial — two *kinds* of detail behave differently:

| Kind | Examples | Verdict |
|---|---|---|
| **Script-level** — where in the script it happens, who else is involved, the canonical prop | "paid the bill **at the table**", "a doctor listened to their chest **with a stethoscope**", "entered the station **from the street**" | **Keep.** Part of what a schema specifies; answerable from common sense; makes the step identifiable |
| **Perceptual / episodic** — colour, quantity, exact appearance, which variant | "drinking orange juice from a **tall glass**", "the **red** suitcase" | **Remove.** Turns a schema judgment into an episodic-detail test |

A pass that strips detail indiscriminately over-corrects: after one such pass the
questions became genuinely hard to map onto the right sub-event (self-test feedback),
because script-level identifiers had been removed along with perceptual ones. Four were
restored on that basis: `restaurant` 4 ("food was served" → "the waiter brought food to
the table"), `clinic` 5 ("a doctor examined them" → "listened to their chest" — otherwise
it collides with the nurse's blood-pressure step), `metro` 1 ("entered the station" →
"…from the street" — otherwise it collides with the escalator step), `hotel` 6 ("was in
the room" → "was inside the hotel room").

**A residual difficulty is structural, not fixable by wording.** Encoding is pictorial and
Block 1 is textual, so the participant must map picture → text, and that mapping is
inherently fuzzy. The spec chose text deliberately: only text lets the *omitted* step —
whose scene was never displayed — be probed the same way as the shown steps. This is part
of why Block 1 is the weakest measure (see `EXPERIMENT_MODEL_MAPPING.md` §8.2) and why the
Block 3 order test was added, which needs no picture→text mapping.

**Final calibration: script-level gist.** After two audits the questions were rewritten to
name the step the way the script itself would ("looked at the menu", "ordered from the
waiter", "paid the bill"), stripping perceptual and locative detail ("at the table" ×4,
"with a cuff", "with a stethoscope", "at the end of the jet bridge"). Two constraints keep
this from going too far:
- **No cross-routine collisions.** Gist wording makes different routines converge, which
  matters especially if the context cue is ever dropped (`EXPERIMENT_MODEL_MAPPING.md` §4).
  Disambiguating words are therefore retained where needed — "bought a ticket **at the box
  office**" (movie) vs "**at the machine**" (metro); "**filled in a form** at the front desk"
  (clinic) vs "**checked in**" (hotel) vs "**scanned in**" (gym). Verified: no two of the 48
  questions are identical.
- **No leaking of Block 2's tested objects.** Block 1 runs first, so naming a tested object
  pre-cues Block 2. Two questions did this and were fixed: clinic 6 ("a **pill bottle** was
  handed to them" → "picked up medicine at the pharmacy") and hotel 1 ("arrived … with their
  **suitcase**" → "arrived at the hotel"). Three questions still name an object category —
  "had a **drink**", "bought a **snack**", "added **detergent**" — and are left alone: there
  the object *is* the action, and naming the category does not reveal the *variant*, which is
  what Block 2 tests (the orthogonality argument in spec §2).

Questions were audited twice against the images. Five were changed: `restaurant` 5
("eating" → "had a drink" — the plate is empty, he is drinking), `airport` 1 ("dropped
your bag" → "stood at the check-in counter" — the suitcase is still at his feet, belt
empty; the old wording *required* schema inference, contaminating the measure), `hotel`
6 ("settled into the room" → "were in your hotel room" — vaguer verb, and drops the bed
reference that could cue the towel object), `gym` 2 ("changed in the locker room" →
"at your locker in the changing room" — still in street clothes), `gym` 3 (removed the
"warmed up /" slash so the yes/no item isn't double-barrelled).

**Observer framing / grammatical person.** The participant is an *observer* watching a
single protagonist go through the experiences — they do not act in the scenes. So all
scene-content questions are third person: the protagonist is "the person" (never "you",
which wrongly casts the participant as the actor, and never "he" — the character's
gender/pronouns aren't specified and shouldn't be inferred from the drawing; "the
person"/"their" is used throughout, and other characters get distinguishing roles like
"the other person in the elevator"). Block 1 asks "was there a step where the person…?"
and Block 2 "Is THIS the [object] from that experience?" / "…the person was reading?".
The instruction screens keep second person because they address the participant as the
viewer ("you will watch a person going through everyday experiences", "you will be
asked…"), and the encoding screen states up front that they are watching a person, so
the observer frame is consistent from encoding through both test blocks.

**Cover-task wording.** The rating was originally phrased as "how *consistent* is this
picture with the one just before it?" That was replaced, because scrambled scenes are
still perfectly consistent with one another — same protagonist, same setting, same
experience; only their **order** is wrong — so a subject answering the question
literally could rate a scrambled pair highly and the manipulation check would fail even
though the manipulation worked. "Consistent" was also ambiguous across narrative,
visual, and categorical readings, and the visual reading is high regardless of order
(shared art style and setting). The prompt now asks whether the scene **follows from**
the previous one, which targets the transition the order manipulation actually acts on,
and the instruction screen explicitly rules out the visual-similarity reading. All
subject-facing wording is centralised in `cover_rating` in the config files.

**Within-subject design (`config.design = "within-subject"`, default).** Each subject sees
4 routines ordered and 4 within-instance scrambled, counterbalanced (a rotating window) so
each routine is ordered for ~half of subjects and each subject is exactly 4/4. This was chosen
over between-subjects once the model work clarified that the schema benefit is a **per-routine**
mechanism (not an encoding-wide mode), so mixing conditions within a subject is fine
mechanistically, the model's continuous run accommodates mixed routines, and within-subject
gives each subject the full PE range the U-shape analysis wants
(`EXPERIMENT_MODEL_MAPPING.md` §3.1/§8). The known costs — strategic carryover and demand
characteristics (amplified by the rating) — are why `config.design = "between-subject"` (each
subject entirely ordered = schema, or entirely scrambled) is kept as a one-line fallback. The
ordered/scrambled factor is logged per trial as `condition`; there is no subject-level `group`.

**Omission is restricted to the 3 non-object steps**, so all 3 object steps are always
shown and every object always has a seen variant.

**Test order.** Block 1 (text) before Block 2 (images), per spec §5. Block 1 is fully
randomized rather than blocked by routine, so a routine's six items never appear
together — blocking would let subjects deduce the omitted step by elimination, which
would contaminate the key false-alarm measure. Block 2 is likewise fully randomized;
in `"both"` mode an extra constraint keeps an object's two trials ≥ 6 apart.

**Scene duration** is fixed (not self-paced) so encoding time is equated across scenes
and groups; the rating screen is separate and self-paced, so rating RT is the
behavioural measure. `scene.fixed_ms` is currently 10000 and is **the** parameter to
calibrate in the pilot against spec §8's 60–85% target hit rate.

## 4. Randomization — two mechanisms

Deterministic counterbalance, computed from `subject_index`:

| What | Rule |
|---|---|
| Per-routine condition (within-subject) | routine at canonical index `j` is `ordered` iff `(j − subject_index) mod n_routines < n_routines/2` (a rotating window: 4/4 per subject, each routine ordered for ~half of subjects) |
| Omitted step | `(subject_index + routine_num) % 3` over the routine's 3 non-object steps |
| Block 2 test role (`"one"`) | object `j` is target iff `(j + subject_index // 2) % 2 == 0` |

(In `between-subject` mode the condition is instead uniform per subject, from
`assign_group` = `subject_index % 2`.) The condition, omission, and Block-2-role rules are
computed from `subject_index` by three different functions with decorrelated periods, so they
stay mutually balanced — verified empirically (`verify_logic.py` checks role balance holds
*within each condition*, worst diff 0 over 200 subjects).

Seeded random, from a PRNG seeded on the subject id (reproducible, and each drawn from
an independent sub-seed so adding one never shifts another):

| What | Notes |
|---|---|
| Variant seen at encoding (1 or 2) | That variant is this subject's TARGET; the other is the LURE |
| No-schema within-instance order | Within instance only — never across instances |
| Instance presentation order | |
| Within-block trial order | |

`subject_index` **must increment for every participant** (0, 1, 2, …). A repeated or
arbitrary value silently breaks the group balance and all three counterbalances.

No file other than the logic module draws randomness, and re-running a subject index
reproduces that session exactly.

## 5. Stimulus audit

Every one of the 72 scene images was checked against the questions:
- All 48 Block 1 presence questions match their scenes.
- All 24 objects' target/lure roles are structurally correct (target is by definition
  the image the subject saw).
- Seven `shown_variant_desc` labels were wrong and were corrected in
  `test_block2_specific.csv`; one object (clinic) was reframed. Details in
  `test_files_README.md`.

## 6. Validation

`python3 psychopy_exp/verify_logic.py` → 16 checks, all passing. It verifies trial
counts, that omission never lands on an object step, group balance, omission rotation,
variant balance, per-subject determinism, instance-order permutation, that adding
instance order did not shift the encoding PRNG stream, Block 2 role correctness, and
that the Block 2 role balance holds **within each group**, not just overall. It also
cross-checks the Python PRNG against the JS one bit-for-bit.

The display layer cannot be validated headlessly — run `experiment.py` in PsychoPy.

**JS build:** open `test_randomization.html` over a local HTTP server
(`python3 -m http.server`). It runs 13 invariant checks plus a **parity check against
the PsychoPy build**: subject 0 (schema) and subject 3 (no-schema, which exercises the
scramble path) must reproduce Python's exact group, instance order, Block 1 order, and
Block 2 order + roles. All pass. If the two builds ever drift, this is what catches it —
re-generate the reference values in `PY_REF` from Python after any logic change.

## 6.1 Web assets

`schema_stimuli/` holds the original PNGs (1448×1086, ~1.9 MB each, **135 MB total**) — far
too heavy to preload in a browser. `schema_stimuli_web/` holds compressed JPEGs for the online
build: 900 px wide, quality 80, ~115 KB each, **8.3 MB total (6% of the original)**. Regenerate
with:

```
for f in schema_stimuli/*.png; do b=$(basename "$f" .png); \
  sips -s format jpeg -s formatOptions 80 -Z 900 "$f" --out "schema_stimuli_web/$b.jpg"; done
```

Compression quality was checked against the thing that actually matters — **target/lure
discriminability**, which is the DV. Pairs inspected after compression (restaurant cake,
clinic reading material, clinic pill bottle — including small, low-salience objects) remain
clearly distinguishable with no visible artefacts; flat vector art compresses very cleanly.
**Re-run this check if the compression settings change.**

Which set a build uses is config-driven: `paths.images` + `paths.image_ext`
(`schema_stimuli/` + `.png` for PsychoPy, `schema_stimuli_web/` + `.jpg` for the web build).
Image paths are not part of the cross-build parity check, so the two builds can legitimately
use different assets while their randomization stays identical.

## 6.2 Analysis decisions, fixed during the pilot

`analysis/pilot_analysis.py` is the standing analysis. Three decisions were taken at
n = 13 and are recorded here because they were made **while the relevant results were
already visible**, which is exactly when they need to be written down rather than
settled afterwards by whichever choice reads better.

**Primary measure: d′ at the ≥ 4 cutoff.** AUC over the full 6-point scale is reported
alongside as a robustness check, together with the criterion sweep. The two disagree at
this n — Block 1 condition effect d′ −0.47 (p .036) vs AUC −0.061 (p .131); Block 2
d′ +0.37 (p .109) vs AUC +0.029 (p .522) — so the choice is consequential and is fixed
now. d′ is primary because it is standard in this literature and because the criterion
sweep shows the contrast keeps its sign at every cutoff from ≥2 to ≥6, so it is not an
artefact of one criterion. AUC is kept because it uses the whole scale, does not depend
on the criterion, and is the more conservative of the two. **If the confirmatory sample
splits them again, report both; do not switch the primary after the fact.**

**Exclusions are behavioural and per-block**, never on d′ itself (that would be selecting
on the dependent variable). A participant can disengage from one block and do the rest
properly, so:

| rule | scope |
|---|---|
| both blocks' median RT < 800 ms **and** rating SD < 1.0 | whole subject |
| Block 1 median RT < 800 ms (48 text questions; 800 ms does not read one) | Block 1 only |
| Block 2 median RT < 800 ms | Block 2 only |

**Do not trim items by observed difficulty.** Item difficulty is only ~12% reliable at
this n (split-half r ≈ .07), so trimming the ends removes mostly sampling noise while
also shrinking each participant's trial count; measured, every trimming threshold made
the Block 2 contrast *smaller*. The two objects that look hardest (hotel suitcase,
airport headphones) have among the most visually distinct variant pairs in the set,
which is the expected signature of noise rather than difficulty.

**Two structural limits worth knowing before interpreting anything.**
- Block 1's lure is the omitted sub-event, which was never shown, so it carries no
  encoding rating and no boundary status. Boundary and PE analyses on Block 1 therefore
  compare targets against a *shared* lure set; d′ then degenerates to a hit-rate
  difference (the false-alarm term cancels) and must not be used — use AUC there.
- In the continuous-stream design, boundary items are **100% the first shown scene of
  their routine**. Boundary effects and within-routine serial-position effects cannot be
  separated in this design.

## 7. Keeping the two builds in sync
`js/` now has full parity with `psychopy_exp/`: the bit-exact PRNG, group/omission/
Block-2-role counterbalances, per-subject variant assignment, within-instance scramble,
instance-order randomization, within-block shuffling, and both Block 2 designs.
Config values are mirrored (`js/config.js` ↔ `psychopy_exp/config.py`, camelCase vs
snake_case). **Any change to one must be made in the other**, and the parity check in
`test_randomization.html` re-run.

Still JS-only work before an online study: the jsPsych timeline itself (encoding
stream, the two test blocks, data logging/upload) — the display layer, not the logic.

## 8. Still open
- Object serial-position matching (`match_position_hook`).
- Post-test order-plausibility and per-routine familiarity ratings (config hooks exist,
  both off).
- Pilot calibration of `scene.fixed_ms` against the 60–85% hit-rate window.
- Variant-pair difficulty equalisation across routines.
- **Context cue decision** (`EXPERIMENT_MODEL_MAPPING.md` §4): Block 2's "In the X
  experience…" prefix is redundant with the shown image; Block 1's is a source
  restrictor the model lacks. Dropping both is recommended to match the model's
  content-based retrieval — not yet applied to the CSVs, pending the final call.
