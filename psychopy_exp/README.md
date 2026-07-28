# PsychoPy local version

Local, in-lab build of the schema × episodic-memory experiment. Pure-Python
PsychoPy Coder script. Data saved as one long-format CSV per subject in `../data/`.

See `../IMPLEMENTATION_NOTES.md` for the full decision log and the places where
this implementation deliberately diverges from `../experiment_spec.md`.

## Files
- `config.py` — all tunable parameters (cover task, timings, flags). No randomness.
- `experiment_logic.py` — stimulus model built from the two test CSVs + the ONLY
  source of per-subject randomness (seeded, reproducible, bit-exact with the JS
  version). No `psychopy` import, so it runs under a plain interpreter.
- `experiment.py` — the PsychoPy timeline (display + interaction + logging).
- `verify_logic.py` — validates the logic layer without PsychoPy.

## Run the logic checks (no PsychoPy needed)
```
python3 psychopy_exp/verify_logic.py
```
Expect `ALL CHECKS PASSED`.

## Run the experiment
Open `experiment.py` in **PsychoPy Standalone** (Coder view) and press Run, or run
it with PsychoPy's bundled Python. A dialog asks for **`subject_index`** — an
integer that **must increment for every participant** (0, 1, 2, …). It drives which
routines are ordered vs scrambled and every counterbalance, so a repeated or arbitrary
value breaks the balancing. Press `Esc` to abort (data so far is kept — the file is flushed
after every trial). Note: `Esc` is not polled during the fixed scene display; it
takes effect at the next rating/interval screen.

## Session flow
1. **Encoding** — 40 scenes (8 routines × 5 shown of 6) presented as ONE continuous
   stream, no separator screens. Each scene: fixed display (`scene.fixed_ms`), then
   a separate self-paced 1–6 rating — *"How well does this picture follow from the
   one before it?"* (1 = doesn't follow at all … 6 = follows perfectly). Every scene
   is rated except the very first of the whole stream — including scenes that follow
   a routine boundary. All subject-facing rating wording lives in
   `config.py → cover_rating` (`prompts`, `anchors`, `instruction_hint`).
2. **Block 1** (schema dimension, text, runs FIRST) — 48 presence questions, 1–6
   confidence (1 = definitely NO … 6 = definitely YES), fully random order.
3. **Block 2** (specific dimension, scene shown, runs SECOND) — 24 trials by default,
   1–6 confidence (1 = definitely NOT the one … 6 = definitely the one), random order.
   No highlight box; the question names the object.
4. **Block 3 — order test** (runs LAST, `order_test.enabled`) — one trial per routine (8).
   The routine's 5 scenes appear at once in a randomized layout; the subject **clicks them
   in the remembered order** (backspace undoes, SPACE confirms). Scored later as
   `tau_episode` (vs the actual presented order, logged as `serial_pos_encoding`) and
   `tau_schema` (vs `canonical_pos`) — these dissociate only in scrambled routines, giving a
   direct index of schema intrusion. It must run last: its scenes reveal the encoded object
   variants, so it cannot precede Block 2 (see `../EXPERIMENT_MODEL_MAPPING.md` §8.2).

Both test blocks use a **6-point** scale (required for confidence-ROC — even, no
neutral midpoint). The encoding cover rating is also 6-point, purely so the subject
sees one consistent scale throughout.

## Short demo (e.g. showing someone how it runs)
Set one flag in `config.py`:

```python
"demo_routines": ["restaurant"],
```

Everything shrinks automatically — 5 encoding scenes, 6 Block 1 questions, 3 Block 2
trials (~1–2 min). Add more ids to the list for a longer demo. Combine with a shorter
`scene.fixed_ms` to make it faster still.

To actually *show the manipulation* in the default within-subject design, a single run
already contains both conditions — with `demo_routines: ["restaurant", "gym"]`, subject 0
gets restaurant **ordered** and gym **scrambled** (visibly different within one session).

Safeguards, so a demo can never pollute real data:
- Output goes to `demo_sub-<index>_<timestamp>.csv` and every row carries `is_demo=1`.
- `verify_logic.py` always validates the full 8-routine experiment regardless of this
  flag, so a demo setting left switched on can't make the checks pass vacuously.
- An unknown routine id raises immediately with the list of valid ids.

**Set it back to `None` before collecting data.** Demo runs are not valid data: the
counterbalances (12/12 Block 2 roles, omission rotation) are defined over all 8 routines.

## How each per-subject decision is made
Two different mechanisms, deliberately:

| Deterministic counterbalance (arithmetic on `subject_index`) | Rule |
|---|---|
| Per-routine condition (within-subject, default) | routine `j` is `ordered` iff `(j − subject_index) mod n < n/2` — a rotating window: 4 ordered + 4 scrambled per subject, each routine ordered for ~half of subjects |
| Which step is omitted | `(subject_index + routine_num) % 3` over the routine's 3 non-object steps |
| Block 2 test role (`"one"` design) | object `j` is target iff `(j + subject_index // 2) % 2 == 0` |

In `between-subject` mode the condition is uniform per subject (`subject_index % 2`:
even = all ordered = schema group, odd = all scrambled). The three rules use decorrelated
functions of `subject_index`, so they stay mutually balanced (verified: role balance holds
within each condition, worst diff 0 over 200 subjects).

| Seeded random (PRNG seeded from the subject id) | Notes |
|---|---|
| Which object variant is seen at encoding (1 or 2) | That variant = this subject's TARGET; the other = LURE |
| No-schema within-instance scene order | Full Fisher-Yates, within instance only |
| Instance (routine) presentation order | Independent sub-seed, so it cannot shift the encoding stream |
| Within-block trial order | Independent sub-seed per block |

Everything is reproducible: the same `subject_index` always regenerates the exact
same session. Nothing outside `experiment_logic.py` draws randomness.

## Key config flags
- `design`: `"within-subject"` (default — 4 ordered + 4 scrambled routines per subject,
  counterbalanced) or `"between-subject"` (each subject entirely ordered or scrambled).
- `demo_routines`: `None` for the real experiment; a list like `["restaurant"]` for a
  short demo (see above). **Must be `None` when collecting data.**
- `scene.fixed_ms` — scene display duration. **Calibrate this in the pilot**: spec
  §8 wants a target hit rate of 60–85%. Above 85% → shorten; below 60% → lengthen.
- `scene.mode`: `"fixed"` (default) or `"self_paced"` (uses `min_ms`/`max_ms`;
  viewing time then varies and is a covariate rather than an equated constant).
- `cover_task`: `"consistency"` (default) or `"pleasantness"`.
- `use_instance_separator`: `False` (default) — continuous stream, every scene rated
  including across boundaries (`is_boundary_transition` marks those). `True` restores
  the spec-§1 design (separator screen + first scene of each instance unrated).
- `block2_design`: `"one"` (default) — each object tested with a single version,
  counterbalanced; 24 trials/subject (12 target + 12 lure); for **group-level ROC**.
  `"both"` — target AND lure trial per object (48), with the
  `block2_min_same_object_lag` separation constraint; for **per-subject ROC**.
- `randomize_instance_order`: `True` (default).
- `order_test.enabled`: `True` (default) — the Block 3 sequence-reconstruction test.
- `post_test.*`: order-plausibility / familiarity ratings — TODO hooks, off.

## Data file
One row per trial, long format, `../data/sub-<index>_<timestamp>.csv`. Key columns:
`phase` (`encoding`/`block1`/`block2`/`order`), `design`, `condition` (ordered/scrambled, per
routine), `routine_id`, `step_num`,
`object_label`, `trial_variant` (target/lure), `variant_shown`, `encoded_target_variant`,
`response` (1–6), `correct_answer`, `rt_ms`, plus encoding-phase columns
`serial_pos_encoding`, `global_scene_pos`, `is_boundary_transition`, `prev_routine_id`,
`prev_step_num`, `omitted_step`, `is_omitted_lure`, `viewing_time_ms`, `cover_rating`,
`cover_rt_ms`, `instance_pos`.

Block 3 (`phase="order"`) writes **one row per placement** — five rows per routine — with
`serial_pos_encoding` (true position), `canonical_pos` (schema position), `order_click_pos`
(the position the subject assigned) and `order_slot` (where it sat on screen). Compute
`tau_episode` from click-position vs `serial_pos_encoding` and `tau_schema` from
click-position vs `canonical_pos`.

For analysis, Block 2 target vs lure trials pool across subjects within a condition to
fit the confidence ROC.

## Known TODO hooks
- Object serial-position matching across groups: `scramble_within_instance`'s
  `match_position_hook` is a no-op placeholder. Note the trade-off documented there —
  pinning all 3 object scenes leaves only 2 movable filler scenes, weakening the
  order manipulation.
- Post-test order-plausibility and per-routine familiarity ratings.

## Variant descriptions — audited
All 48 object images were visually checked against the CSV. The convention is: the
`target`-row `shown_variant_desc` describes `scene_R_S_1.png`, the `lure`-row
describes `scene_R_S_2.png`. Correctness never depended on this — target is always
whichever image the subject actually saw — only the logged `shown_variant_desc`
label did. Corrections applied to `test_block2_specific.csv` after the audit:
- metro `cup`: the two descriptions were reversed (`_1` is the steel tumbler, `_2`
  the paper cup) — swapped.
- laundromat `detergent`: colours were wrong (`_1` orange, `_2` blue) — fixed.
- restaurant `bread`/`cake`, airport `headphones`/`luggage`: minor colour/word fixes
  so the label matches the drawing.
- clinic step 3: the lure image is a newspaper, not a second magazine. Rather than
  redraw, the object was reframed to `reading material` and the question changed to
  "Is THIS what you were reading…". Magazine vs newspaper is an easier, more
  gist-based pair for that one item — an accepted trade-off.

Block 1's 48 presence questions were all verified to match their scenes.
