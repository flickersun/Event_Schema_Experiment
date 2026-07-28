# ===========================================================================
# verify_logic.py — validate the Python logic layer with a plain interpreter.
#   python3 psychopy_exp/verify_logic.py
#
# Mirrors the browser invariant checks, and additionally proves the Python port
# is BIT-EXACT with the JS version by matching (a) raw RNG output and (b) the
# full subject-0 state produced by the validated browser build.
# ===========================================================================

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from experiment_logic import (  # noqa: E402
    build_stimuli, init_subject, make_rng,
    build_block1_trials, build_block2_trials,
    ordered_block1_trials, ordered_block2_trials,
    build_order_test_trials, ordered_order_test_trials,
    _min_same_object_lag,
)
from config import CONFIG  # noqa: E402

fails = 0


def ok(cond, msg):
    global fails
    if not cond:
        fails += 1
    print(("PASS " if cond else "FAIL ") + msg)


# Always validate the FULL 8-routine experiment, regardless of demo_routines —
# otherwise a demo setting left switched on would make these checks pass against
# a 1-routine subset and prove nothing about the real study.
if CONFIG.get("demo_routines"):
    print("NOTE: config demo_routines=%s is set (demo mode). Validating the full "
          "8-routine experiment anyway.\n" % (CONFIG["demo_routines"],))
stim = build_stimuli(restrict_routines=None)

# --- 1. bit-exact RNG cross-check against JS makeRng('7') ------------------
JS_REF = [0.9415704873390496, 0.4506456325761974, 0.795575451105833,
          0.23743622424080968, 0.1789892332162708]
rng = make_rng("7")
py_vals = [rng() for _ in range(5)]
ok(all(abs(a - b) < 1e-12 for a, b in zip(py_vals, JS_REF)),
   "PRNG bit-exact with JS for seed '7' (max diff {:.2e})".format(
       max(abs(a - b) for a, b in zip(py_vals, JS_REF))))

# --- 2. subject-0 state matches the validated browser output ---------------
# Ground truth read from the in-browser inspector (schema group, subject 0).
S0_OMIT = {"restaurant": 3, "movie": 4, "clinic": 1, "airport": 4,
           "metro": 6, "hotel": 2, "laundromat": 4, "gym": 5}
S0_VAR = {
    ("restaurant", "bread"): 1, ("restaurant", "cake"): 2, ("restaurant", "drink"): 2,
    ("movie", "snack"): 2, ("movie", "neighbour's clothing"): 1, ("movie", "animal on screen"): 2,
    ("clinic", "reading material"): 2, ("clinic", "wall chart"): 1, ("clinic", "pill bottle"): 2,
    ("airport", "luggage"): 1, ("airport", "headphones"): 2, ("airport", "neck pillow"): 1,
    ("metro", "umbrella"): 2, ("metro", "cup"): 2, ("metro", "book"): 1,
    ("hotel", "suitcase"): 2, ("hotel", "passenger's clothing"): 2, ("hotel", "towel"): 2,
    ("laundromat", "hoodie/shirt"): 1, ("laundromat", "detergent"): 2, ("laundromat", "towel"): 2,
    ("gym", "gym bag"): 2, ("gym", "water bottle"): 2, ("gym", "towel"): 1,
}
s0 = init_subject(0, 0, stim)
omit_match = all(s0["routines"][r]["omitted_step"] == v for r, v in S0_OMIT.items())
ok(omit_match, "subject 0 omissions match ground truth (unchanged by design)")
var_match = all(s0["routines"][r]["variant_seen"][o] == v for (r, o), v in S0_VAR.items())
ok(var_match, "subject 0 variant assignments match ground truth (condition-independent)")

# --- 3. invariants across a run of subjects --------------------------------
N = 200
design_mode = CONFIG.get("design", "within-subject")
n_routines = len(stim["routines"])
obj_omitted = 0
omit_dist = {}
var_split = {}
cond_per_routine = {}       # routine_id -> {'ordered':n, 'scrambled':n}
per_subject_ordered = []    # count of ordered routines per subject
ordered_sorted_ok = True
for i in range(N):
    st = init_subject(i, i, stim)

    b1 = build_block1_trials(st, stim)
    b2 = build_block2_trials(st, stim)
    if len(b1) != 48:
        ok(False, "subj %d B1 len %d" % (i, len(b1)))
    if len(b2) != 48:
        ok(False, "subj %d B2 len %d" % (i, len(b2)))
    yes = sum(1 for t in b1 if t["correct_answer"] == "yes")
    if yes != 40:
        ok(False, "subj %d B1 yes count %d" % (i, yes))

    n_ord = 0
    for r in stim["routines"]:
        rs = st["routines"][r["routine_id"]]
        cond = rs["condition"]
        cond_per_routine.setdefault(r["routine_id"], {"ordered": 0, "scrambled": 0})[cond] += 1
        if cond == "ordered":
            n_ord += 1
            steps = [s["step_num"] for s in rs["shown_order"]]
            if steps != sorted(steps):
                ordered_sorted_ok = False
        om = next(s for s in r["steps"] if s["step_num"] == rs["omitted_step"])
        if om["is_object_step"]:
            obj_omitted += 1
        if len(rs["shown_order"]) != 5:
            ok(False, "subj %d %s shown!=5" % (i, r["routine_id"]))
        omit_dist[(r["routine_id"], rs["omitted_step"])] = \
            omit_dist.get((r["routine_id"], rs["omitted_step"]), 0) + 1
        for o, vv in rs["variant_seen"].items():
            var_split[(r["routine_id"], o, vv)] = var_split.get((r["routine_id"], o, vv), 0) + 1
    per_subject_ordered.append(n_ord)

    # determinism
    if init_subject(i, i, stim) != st:
        ok(False, "subj %d nondeterministic" % i)

    # Block 2 target/lure integrity
    by_obj = {}
    for t in b2:
        by_obj.setdefault((t["routine_id"], t["object_label"]), []).append(t)
    for pair in by_obj.values():
        tgt = next(x for x in pair if x["trial_variant"] == "target")
        lure = next(x for x in pair if x["trial_variant"] == "lure")
        if tgt["image_file"] == lure["image_file"]:
            ok(False, "subj %d target==lure image" % i)
        seen = st["routines"][tgt["routine_id"]]["variant_seen"][tgt["object_label"]]
        if tgt["variant_shown"] != seen or tgt["correct_answer"] != "yes" or lure["correct_answer"] != "no":
            ok(False, "subj %d role/correct mismatch" % i)

ok(obj_omitted == 0, "omitted step is NEVER an object step across %d subjects (got %d)" % (N, obj_omitted))
ok(ordered_sorted_ok, "ordered routines are shown in canonical step order")

# --- condition counterbalance (design-aware) -------------------------------
if design_mode == "within-subject":
    exp_ord = (n_routines + 1) // 2
    ok(all(c == exp_ord for c in per_subject_ordered),
       "within-subject: every subject has exactly %d/%d routines ordered" % (exp_ord, n_routines))
    worst = max(abs(v["ordered"] - v["scrambled"]) for v in cond_per_routine.values())
    ok(worst <= 2, "within-subject: each routine ordered ~= scrambled across subjects (worst diff %d)" % worst)
else:
    ok(all(c in (0, n_routines) for c in per_subject_ordered),
       "between-subject: every subject is entirely one condition")
    tot_ord = sum(1 for c in per_subject_ordered if c == n_routines)
    ok(abs(tot_ord - (N - tot_ord)) <= 1, "between-subject: group sizes balanced (%d/%d)" % (tot_ord, N - tot_ord))

# omission balance: each of a routine's 3 eligible steps used ~N/3
rest_keys = {k: v for k, v in omit_dist.items() if k[0] == "restaurant"}
balanced = all(abs(v - N / 3) <= N / 3 * 0.5 for v in rest_keys.values()) and len(rest_keys) == 3
ok(balanced, "restaurant omission rotates over 3 steps ~evenly: %s" % (
    {k[1]: v for k, v in rest_keys.items()}))

# variant ~50/50 spot check
bv1 = var_split.get(("restaurant", "bread", 1), 0)
bv2 = var_split.get(("restaurant", "bread", 2), 0)
ok(min(bv1, bv2) / N > 0.3, "restaurant bread variant split v1=%d v2=%d of %d" % (bv1, bv2, N))

# --- 4. instance order + within-block order --------------------------------
all_rids = set(r["routine_id"] for r in stim["routines"])
order_ok = True
order_positions = {}  # rid -> set of positions seen across subjects
for i in range(N):
    st = init_subject(i, i, stim)
    io = st["instance_order"]
    if set(io) != all_rids or len(io) != 8:
        order_ok = False
    for pos, rid in enumerate(io):
        order_positions.setdefault(rid, set()).add(pos)
    # reproducible
    if init_subject(i, i, stim)["instance_order"] != io:
        order_ok = False
ok(order_ok, "instance_order is a reproducible permutation of all 8 routines")
ok(all(len(p) >= 5 for p in order_positions.values()),
   "each routine appears at many different serial positions across subjects (not stuck)")

# subject-0 main stream unchanged by the additions (variants still match §2)
s0b = init_subject(0, 0, stim)
ok(all(s0b["routines"][r]["variant_seen"][o] == v for (r, o), v in S0_VAR.items()),
   "adding instance_order did NOT shift the encoding RNG stream (subject 0 variants stable)")

# block order: reproducible, actually shuffled
design = CONFIG.get("block2_design", "one")
exp_b2 = 24 if design == "one" else 48
b1o = ordered_block1_trials(s0b, stim)
b2o = ordered_block2_trials(s0b, stim)
ok(len(b1o) == 48 and len(b2o) == exp_b2,
   "ordered block sizes correct (b1=48, b2=%d for '%s' design)" % (exp_b2, design))
ok(ordered_block1_trials(s0b, stim) == b1o and ordered_block2_trials(s0b, stim) == b2o,
   "within-block trial order is reproducible per subject")
key1 = lambda t: (t["routine_id"], t["step_num"])
ok(sorted(map(key1, b1o)) == sorted(map(key1, build_block1_trials(s0b, stim))),
   "Block 1 shuffle preserves the trial set (permutation only)")

# --- 5. Block 2 design-specific checks -------------------------------------
if design == "one":
    role_count = {}     # objkey -> {'target':n,'lure':n} across subjects
    cond_role = {}      # (condition, objkey, role) -> n
    per_subj_ok = True
    correct_ok = True
    for i in range(N):
        st = init_subject(i, i, stim)
        b2 = ordered_block2_trials(st, stim)
        keys = [(t["routine_id"], t["object_label"]) for t in b2]
        if len(b2) != 24 or len(set(keys)) != 24:
            per_subj_ok = False
        if sum(1 for t in b2 if t["trial_variant"] == "target") != 12:
            per_subj_ok = False
        for t in b2:
            k = (t["routine_id"], t["object_label"])
            role_count.setdefault(k, {"target": 0, "lure": 0})[t["trial_variant"]] += 1
            c = st["routines"][t["routine_id"]]["condition"]
            cond_role[(c, k, t["trial_variant"])] = cond_role.get((c, k, t["trial_variant"]), 0) + 1
            # correctness: target->seen variant->yes, lure->unseen->no
            seen = st["routines"][t["routine_id"]]["variant_seen"][t["object_label"]]
            want_yes = (t["trial_variant"] == "target")
            if (t["variant_shown"] == seen) != want_yes:
                correct_ok = False
            if t["correct_answer"] != ("yes" if want_yes else "no"):
                correct_ok = False
    ok(per_subj_ok, "one-design: 24 trials, each object once, 12 target + 12 lure per subject")
    ok(correct_ok, "one-design: target=seen variant->yes, lure=unseen->no (all subjects)")
    ok(all(abs(v["target"] - v["lure"]) <= 2 for v in role_count.values()),
       "one-design: each object tested as target ~= as lure across all subjects")
    # role must not confound with condition: within each condition of an object's
    # routine, target ~= lure (tolerance scaled to the ~N/2 subjects per cell).
    wg_worst = max(abs(cond_role.get((c, k, "target"), 0) - cond_role.get((c, k, "lure"), 0))
                   for c in ("ordered", "scrambled") for k in role_count)
    ok(wg_worst <= max(4, int(0.15 * N)),
       "one-design: role balance holds WITHIN each condition (worst diff %d)" % wg_worst)
else:
    key2 = lambda t: (t["routine_id"], t["object_label"], t["trial_variant"])
    ok(sorted(map(key2, b2o)) == sorted(map(key2, build_block2_trials(s0b, stim))),
       "both-design: Block 2 shuffle preserves the trial set (permutation only)")
    min_lag_cfg = CONFIG["block2_min_same_object_lag"]
    worst_lag = 48
    attempts_ok = True
    for i in range(N):
        st = init_subject(i, i, stim)
        lag = _min_same_object_lag(ordered_block2_trials(st, stim))
        worst_lag = min(worst_lag, lag)
        if lag < min_lag_cfg:
            attempts_ok = False
    ok(attempts_ok, "both-design: same-object target/lure lag >= %d for all %d subjects (worst %d)"
       % (min_lag_cfg, N, worst_lag))

# --- 6. Order test (Block 3) -----------------------------------------------
n_r = len(stim["routines"])
struct_ok = True
layout_reproducible = True
ordered_agree = True      # ordered routines: true_pos == canonical_pos
scrambled_differ = 0      # scrambled routines where the two orders dissociate
scrambled_total = 0
layout_positions = {}     # step_num -> set of screen slots seen (across subjects)
for i in range(N):
    st = init_subject(i, i, stim)
    trials = ordered_order_test_trials(st, stim)
    if len(trials) != n_r:
        struct_ok = False
    for t in trials:
        items = t["items"]
        # every shown scene present exactly once, positions are a permutation
        if len(items) != 5:
            struct_ok = False
        if sorted(x["true_pos"] for x in items) != [1, 2, 3, 4, 5]:
            struct_ok = False
        if sorted(x["canonical_pos"] for x in items) != [1, 2, 3, 4, 5]:
            struct_ok = False
        # true_pos must match the encoding order recorded in subject_state
        enc = {s["step_num"]: s["serial_pos"] for s in st["routines"][t["routine_id"]]["shown_order"]}
        if any(enc[x["step_num"]] != x["true_pos"] for x in items):
            struct_ok = False
        # canonical_pos must be the rank by step_num
        canon = sorted(items, key=lambda x: x["step_num"])
        if any(x["canonical_pos"] != k + 1 for k, x in enumerate(canon)):
            struct_ok = False
        # ordered -> the two orderings coincide; scrambled -> they should differ
        same = all(x["true_pos"] == x["canonical_pos"] for x in items)
        if t["condition"] == "ordered":
            if not same:
                ordered_agree = False
        else:
            scrambled_total += 1
            if not same:
                scrambled_differ += 1
        if t["routine_id"] == "restaurant":
            for slot, x in enumerate(items):
                layout_positions.setdefault(x["step_num"], set()).add(slot)
    if ordered_order_test_trials(st, stim) != trials:
        layout_reproducible = False

ok(struct_ok, "order test: 1 trial/routine, 5 scenes each, true_pos matches encoding order, "
              "canonical_pos = rank by step_num")
ok(layout_reproducible, "order test: screen layout + trial order are reproducible per subject")
ok(ordered_agree, "order test: in ORDERED routines the presented order == canonical order")
ok(scrambled_differ / max(scrambled_total, 1) > 0.9,
   "order test: in SCRAMBLED routines the two orders dissociate (%d/%d) — this is what makes "
   "tau_episode vs tau_schema informative" % (scrambled_differ, scrambled_total))
ok(all(len(s) >= 4 for s in layout_positions.values()),
   "order test: each scene appears at many different screen slots across subjects (layout not stuck)")

print("\n" + ("ALL CHECKS PASSED" if fails == 0 else "%d CHECK(S) FAILED" % fails))
sys.exit(1 if fails else 0)
