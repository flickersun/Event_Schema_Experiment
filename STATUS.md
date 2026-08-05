# Status — 2026-08-04

Where the project stands, for picking the work back up. Everything else lives in the
documents listed at the bottom; this file holds only what is not already recorded there,
namely the live infrastructure and the pilot results so far.

---

## Data collection is live

| | |
|---|---|
| study URL | `https://flickersun.github.io/Event_Schema_Experiment/` |
| repo | `github.com/flickersun/Event_Schema_Experiment` (push → Pages redeploys in ~1 min) |
| DataPipe experiment | `j6BA3yHMjJzb`, 24 conditions, condition assignment ON |
| data lands in | OSF component `rs84e` (project `dcp6g`), private |
| chain | SONA → lab Qualtrics (consent + demographics) → experiment → SONA credit |
| Qualtrics embedded field | `id`, captured from `?id=%SURVEY_CODE%` |

Qualtrics redirect (already configured; `${e://Field/id}` must stay literal, everything
else percent-encoded):

```
https://flickersun.github.io/Event_Schema_Experiment/?pid=${e://Field/id}&next=https%3A%2F%2Fucdavis.sona-systems.com%2Fwebstudy_credit.aspx%3Fexperiment_id%3D3969%26credit_token%3D7901d074a4f444d68b9d1a78e04d6f77%26survey_code%3D${e://Field/id}
```

**Pending:** OSF maintenance Wed 5 Aug 2026, 15:00–19:00 Pacific — close the SONA
timeslots for that window; saves will fail while OSF is down. Verify with a test POST
before reopening, then delete the test file.

Current config: 8 routines, within-subject (4 ordered / 4 scrambled), scene 6 s,
`block2_design: "one"` (24 trials), order test on, `demo_routines: None`.

---

## Pilot results, n = 13 (12 after exclusions, 10 for Block 1)

Primary measure is d′ at ≥4; AUC reported alongside (see `IMPLEMENTATION_NOTES.md` §6.2).

| | ordered | scrambled | diff | t | p | same dir |
|---|---|---|---|---|---|---|
| encoding rating (within-routine) | 5.39 | 3.73 | **+1.66** | 7.53 | <.0001 | **12/12** |
| boundary vs within rating | 1.77 | 4.56 | **−2.79** | −9.57 | <.0001 | **12/12** |
| Block 3 tau_schema | 0.92 | 0.18 | **+0.74** | 7.03 | <.0001 | **11/12** |
| Block 3 tau_episode | 0.92 | 0.62 | +0.29 | 2.98 | .013 | 9/12 |
| Block 1 d′ (schema) | 1.15 | 1.61 | **−0.47** | −2.47 | .036 | **2/10** |
| Block 1 AUC | 0.75 | 0.81 | −0.06 | −1.66 | .131 | 1/10 |
| Block 2 d′ (specific) | 1.12 | 0.76 | +0.37 | 1.74 | .109 | 8/12 |
| Block 2 AUC | 0.74 | 0.71 | +0.03 | 0.66 | .522 | 7/12 |

Criterion sweep — the condition contrast keeps its sign at every cutoff, so neither
recognition effect is an artefact of the ≥4 criterion:

```
                >=2    >=3    >=4    >=5    >=6
Block 1       -0.19  -0.23  -0.47*  -0.42  -0.31
Block 2       +0.19  +0.18  +0.37   +0.35  +0.22
```

**Solid:** the encoding manipulation (12/12), the boundary drop in the rating (12/12),
and the order test (11/12). These are not in doubt at this n.

**Interesting:** Block 1 runs **backwards** from the original spec — scrambled is better,
9 of 10 participants — and the size (−0.47) matches the rebuilt model's prediction
(−0.52 separate streams, −0.65 mixed; `EXPERIMENT_MODEL_MAPPING.md` §15.4, §18). This is
currently the most theoretically loaded result in the set.

**Not established:** Block 2's condition effect, and both boundary effects on memory.

## Block 2 — what has been ruled out

Four things were tried and none rescued it:

| tried | result |
|---|---|
| exclude participants who cannot discriminate | t barely moves (0.50 → 0.89), 4/7 same direction |
| full-scale AUC instead of dichotomised d′ | effect goes to ≈ 0 |
| drop the hardest objects | every threshold makes it *smaller* |
| drop the easiest objects | same |

Two reliability results explain why, and both matter more than the point estimates:

- **Per-subject condition difference: split-half r = −0.39.** Between-subject spread in
  this quantity is essentially all measurement noise, with no reliable individual-
  differences component. More trials cannot surface a signal that is not there; more
  participants is the only lever.
- **Per-object difficulty: split-half r ≈ .07–.12.** So the difficulty ranking is ~88%
  noise, which is why trimming items only costs trials.

Rough power estimate from the observed spread: ≈ 70–90 participants to detect the
model's +0.25 d′ at 80%. The alternative lever is raising overall discriminability —
pooled Block 2 d′ is only 0.84 with false alarms at 0.28–0.38, i.e. a lot of guessing.
Lengthening the scene from 6 s would be the one-line change, **but it splits the sample**:
data collected before and after cannot be pooled. Decide before collecting many more.

## Housekeeping

- Missing `subj_index`: 5, 10, 11, 14, 15 — drop-outs, plus one save lost to the old
  single-attempt save code (now retried 3× with response checking).
- Indices 0–4 were consumed by connectivity tests, and 12 and 13 have 278 rows rather
  than 276 because they ran during the brief checkpoint-save version. Both harmless.
- One participant (`129204`) is excluded whole: both blocks' median RT < 800 ms, rating
  SD 0.98, Block 1 d′ below chance. Two more (`122257`, `117607`) lose **Block 1 only**
  on the RT rule.
- Two test files may still be on OSF: `PIPELINE-TEST_delete-me.csv`,
  `RETRYTEST_delete-me.csv`.

## Next

1. Keep collecting. Revisit at n ≈ 20: Block 2 either firms up or does not, and Block 1
   should reach p < .01 if it is real.
2. Decide the 6 s vs 8–10 s question **before** collecting much more, since it splits
   the sample.
3. PE-binned analysis (`--pe`) needs more mid-range ratings before it can say anything —
   ordered routines are 66% rated 6, so within-condition PE variance sits almost entirely
   in the scrambled half.
4. The model predicts a **crossover**, not a U: Block 1 rising with PE, Block 2 falling
   (`EXPERIMENT_MODEL_MAPPING.md` §20.10). Test that, not a U-shape.

---

| document | holds |
|---|---|
| `EXPERIMENT_MODEL_MAPPING.md` | the model side: 21 sections, several self-corrections; §15.4, §18, §20.10 carry the current predictions |
| `IMPLEMENTATION_NOTES.md` | design decisions and deviations from the spec; §6.2 fixes the analysis choices |
| `analysis/pilot_analysis.py` | the standing analysis, with the primary-measure decision in its docstring |
| `WEB_DEPLOY.md` | the online build |
| `qualtrics/QUALTRICS_SETUP.md` | the SONA/Qualtrics chain |
| `psychopy_exp/README.md` | the local PsychoPy build |
