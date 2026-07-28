# Online build — deployment

Browser version of the same experiment, for piloting through SONA → Qualtrics.
Shares the stimulus CSVs and the randomization logic with the PsychoPy build
(`psychopy_exp/`); cross-build parity is checked by `test_randomization.html`.

## Files

| File | Role |
|---|---|
| `index.html` | Entry point: loads jsPsych, assigns IDs, runs the timeline, saves to DataPipe |
| `js/config.js` | Parameters (mirrors `psychopy_exp/config.py`) |
| `js/stimuli/parseStimuli.js` | Builds the stimulus model from the two CSVs |
| `js/randomization.js` | All per-subject randomness (bit-exact with the Python build) |
| `js/timeline.js` | The jsPsych timeline — encoding, Blocks 1–3 |
| `js/plugin-click-order.js` | Custom plugin for the Block 3 sequence reconstruction |
| `schema_stimuli_web/` | Compressed JPEGs (8.3 MB total — see IMPLEMENTATION_NOTES §6.1) |

## The two identifiers (do not conflate them)

| | Source | Drives |
|---|---|---|
| `subjIndex` | **DataPipe** server-side sequential condition assignment | every **counterbalance** — which routines are ordered/scrambled, omission rotation, Block 2 target/lure roles |
| `subjectId` | participant ID from the redirect (`?pid=…`) | the **seeded PRNG** — scramble orders, variant draws, trial order |

Keeping them separate gives perfect counterbalancing *and* a different shuffle for
each participant. The design closes after **lcm(8 routines, 3 omission, 4 role) = 24**,
so configure DataPipe with **24 conditions** — one full cycle.

Do **not** derive `subjIndex` by hashing the participant ID: that turns a balanced
counterbalance into random assignment.

## Setup

1. **DataPipe** (https://pipe.jspsych.org) — create an experiment linked to an OSF
   component. Set **number of conditions = 24**. Copy the experiment ID into
   `DATAPIPE_ID` in `index.html`. Enable data collection when you start piloting.
2. **Host the folder** — GitHub Pages is enough (static files only). Push the repo,
   enable Pages, and the study URL is `https://<user>.github.io/<repo>/`.
3. **Qualtrics shell** — consent + demographics, then redirect to the study URL,
   passing the participant ID and the return URL:
   `https://<user>.github.io/<repo>/?pid=${e://Field/PID}&next=<qualtrics-or-SONA-completion-URL>`
   The experiment redirects to `next` when it finishes.
4. **SONA** — point the study at the Qualtrics survey; credit is granted by the
   existing SONA↔Qualtrics integration.

⚠️ **The consent form and recruitment text must not mention memory.** Encoding is
incidental and the test is a surprise (spec §1/§4); a consent form headed "memory
study" defeats the whole design. The page title, instructions, and the PsychoPy
dialog are all deliberately neutral for the same reason.

## Local testing

```
python3 -m http.server 8731     # from the repo root
```
- `http://localhost:8731/index.html` — the experiment. Without a real `DATAPIPE_ID`
  the condition request fails and falls back to a random index (fine for checking the
  flow, **not** counterbalanced).
- `http://localhost:8731/test_randomization.html` — invariant checks plus parity
  against the PsychoPy build.

Add `?pid=test&next=` to the URL to simulate the Qualtrics redirect.

## Session structure (identical to the PsychoPy build)

preload (only this subject's ~52 images) → encoding (40 scenes, 10 s each, rating after
every scene but the first) → Block 1 (48, text) → Block 2 (24, image) → Block 3 (8,
click-to-order) → save → redirect. ≈ 21 min.

## Data

One row per jsPsych trial, saved as CSV to DataPipe/OSF. `phase` distinguishes
`encoding`, `encoding_rating`, `block1`, `block2`, `order`.

Block 3 rows store parallel arrays in **screen order** — `items_step_num`,
`items_true_pos`, `items_canonical_pos` — plus `click_order` (screen slots, in the
order clicked) and `click_rts`. Reconstruct the subject's ordering with
`click_order.map(i => items_true_pos[i])`, then correlate against `[1..5]` for
**tau_episode** and against `click_order.map(i => items_canonical_pos[i])` for
**tau_schema**.

## Verified

Built and tested locally: timeline composition (1 preload + 4 instructions + 40
encoding + 39 ratings + 48 + 24 + 8 = matches the PsychoPy build), preload restricted
to the 52 images this subject needs, and the Block 3 plugin end-to-end (click, badge,
dim, backspace undo, Continue gating, and a correct reconstruction round-tripping
through the logged data).

## Still to do before running participants

- [ ] Fill in `DATAPIPE_ID` and create the DataPipe experiment with 24 conditions.
- [ ] Deploy and run yourself end to end, start to finish, checking the saved CSV.
- [ ] Wire the Qualtrics redirect and confirm the return trip grants SONA credit.
- [ ] Decide the minimum window size / whether to add a browser check — Block 3 puts
      five images in a row, so very narrow windows shrink them (they fit, but small).
