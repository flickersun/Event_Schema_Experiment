# Test files — how to use

Two CSVs, one per test block. Block 1 runs FIRST (see spec §5: showing scenes first
would reveal which sub-events occurred and contaminate the schema-dimension judgments).

Both blocks use the SAME response: a 6-point confidence scale → confidence ROC →
dual-process. The 6 points are deliberate — an even scale with no neutral midpoint
is what the ROC analysis needs. Do not change it to 7.

**These CSVs are the single source of truth for both implementations.** The PsychoPy
build (`psychopy_exp/`) and the JS build (`js/`) both parse them at runtime, so a fix
here propagates to both with no code change.

---

## Block 1 — `test_block1_schema.csv`  (schema dimension, TEXT)

48 rows = 8 routines × 6 sub-events. Text-only presence judgment (no scene shown), so
the omitted step is tested identically to the others.

Per trial, present: `context_cue` + `question_text`, then collect 1–6
(`response_anchors`: 1 = definitely NO … 6 = definitely YES).

Columns:
- `routine_id`, `routine_label` — which experience.
- `step_num` — 1–6, the sub-event's canonical position.
- `is_object_step` — 1 if that sub-event also carried a tested object. **The code
  reads this** to decide which steps are object steps (3 per routine) and which are
  eligible for omission (the other 3).
- `default_omitted_step` — a suggested fixed omission. **Not used**: omission is
  counterbalanced per subject (see below).
- `question_text` — phrased as a VISIBLE ACTION ("was there a step where the doctor
  listened to your chest with a stethoscope?"), never the functional name.
- `context_cue` — "In the {routine} experience..." shown before the question.

All 48 questions have been visually verified against their scene images.

**Omission is COUNTERBALANCED**, not fixed. `default_omitted_step` is ignored; the
program picks the omitted step per subject by rotation over that routine's 3
non-object steps. All six scenes exist for every routine, so any step can be the
omitted one. The correct answer is computed at runtime: omitted step → NO, all shown
steps → YES.

---

## Block 2 — `test_block2_specific.csv`  (specific dimension, SCENE shown)

48 rows = 24 objects × 2 versions. The scene is shown and the subject judges whether
the object named in the question is the one they saw.

**Rows are the two IMAGE VERSIONS of each object, not a fixed target/lure assignment.**
Which version counts as target is decided per subject at runtime (see below).

Per trial, present: the image + `context_cue` + `question_text`, then collect 1–6
(`response_anchors`: 1 = definitely NOT the one … 6 = definitely the one).

Columns:
- `trial_variant` — `target` / `lure`. Read by the code **only** as "which physical
  image version this row describes": the `target` row describes `scene_R_S_1.png`,
  the `lure` row describes `scene_R_S_2.png`.
- `correct_answer` — **not used.** Computed at runtime from what the subject saw.
- `image_file` — **not used.** These are placeholder stubs that never matched the real
  assets. The code builds the path at runtime as
  `schema_stimuli/scene_<routine_num>_<step_num>_<variant>.png`, where routine_num is
  1 restaurant, 2 movie, 3 clinic, 4 airport, 5 metro, 6 hotel, 7 laundromat, 8 gym.
- `highlight_object` — legacy. **No highlight box is drawn**; the question names the
  object instead.
- `shown_variant_desc` — bookkeeping label for the version this row describes. Audited
  against the actual images and corrected (see below).
- `object_label` — the object's key. Must be identical on both rows of a pair.
- `question_text` — context-bound source question ("Is THIS the cake you saw in that
  experience?").

### How target/lure are assigned per subject
At encoding the subject sees version 1 or 2 at random (seeded). **Whatever they saw is
their target; the other is their lure** — regardless of which row this file calls
"target". Correctness therefore never depends on the row labels or on
`shown_variant_desc`.

By default (`block2_design: "one"`) each object is tested with only ONE version per
subject — 24 trials, 12 target + 12 lure — counterbalanced across subjects so each
object serves as target for half of them. Set `block2_design: "both"` for the full
48-trial version.

### Audit corrections applied
All 48 object images were checked against this file:
- metro `cup` — descriptions were reversed; `_1` is the steel tumbler, `_2` the paper
  cup. Swapped.
- laundromat `detergent` — colours were wrong; `_1` is orange, `_2` is blue. Fixed.
- restaurant `bread` (`_1` is a roll + sliced bread, not a croissant), restaurant
  `cake` (`_2` is a berry cheesecake), airport `headphones` (`_2` is grey, not purple),
  airport `luggage` (`_2` is a soft-shell roller, not a duffel) — labels corrected.
- clinic step 3 — the `_2` image is a **newspaper**, not a second magazine. Rather than
  redraw it, the object was reframed: `object_label` is now `reading material` and the
  question is "Is THIS what you were reading in that experience?". Accepted trade-off:
  magazine vs newspaper is a cross-category (easier, more gist-solvable) pair, so this
  one item is easier than the rest.

---

## Shared notes
- Response: 6-point confidence in both blocks → ROC / Yonelinas dual-process (no
  Remember/Know).
- Trial order is randomized within each block; Block 1 is fully random so that a
  routine's six items never appear together (which would let subjects deduce the
  omitted step by elimination).
- Counts: Block 1 = 48 trials; Block 2 = 24 trials by default (48 in `"both"` mode).
