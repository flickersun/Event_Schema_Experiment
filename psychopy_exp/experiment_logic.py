# ===========================================================================
# experiment_logic.py — stimulus model + THE ONLY source of per-subject
# randomness (PsychoPy version). Pure Python, no psychopy import, so it runs
# and can be validated with a plain interpreter.
#
# This is a faithful port of js/stimuli/parseStimuli.js + js/randomization.js.
# The seeded PRNG is BIT-EXACT with the JS version (xmur3 + mulberry32), so a
# given subject index reproduces the identical experience on both platforms —
# the already-validated browser output is the ground truth this must match.
#
# Design rule (same as JS): nothing outside this module may draw randomness.
# Everything that decides "what did this subject see" is computed here once,
# into a single subject_state dict that all downstream code reads.
# ===========================================================================

import csv
import os

from config import CONFIG

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# routine_id -> routine number used in the image filenames. MUST match the
# scene_<N>_<step>_<variant>.png numbering in schema_stimuli/. Verified.
ROUTINE_NUM = {
    "restaurant": 1, "movie": 2, "clinic": 3, "airport": 4,
    "metro": 5, "hotel": 6, "laundromat": 7, "gym": 8,
}

# --- bit-exact seeded PRNG (port of xmur3 + mulberry32) --------------------
_MASK = 0xFFFFFFFF


def _imul(a, b):
    # JS Math.imul: low-32-bit multiply, returned bit pattern (kept unsigned).
    return (a & _MASK) * (b & _MASK) & _MASK


def _xmur3(s):
    # Returns a seed value (single call of the JS xmur3 closure).
    h = (1779033703 ^ len(s)) & _MASK
    for ch in s:
        h = _imul(h ^ ord(ch), 3432918353)
        h = ((h << 13) | (h >> 19)) & _MASK
    h = _imul(h ^ (h >> 16), 2246822507)
    h = _imul(h ^ (h >> 13), 3266489909)
    h ^= h >> 16
    return h & _MASK


def make_rng(seed_str):
    """Return a zero-arg function yielding floats in [0,1), bit-exact with JS."""
    a = _xmur3(str(seed_str))

    def rng():
        nonlocal a
        a = (a + 0x6D2B79F5) & _MASK
        t = _imul(a ^ (a >> 15), 1 | a)
        t = ((t + _imul(t ^ (t >> 7), 61 | t)) & _MASK) ^ t
        t &= _MASK
        return ((t ^ (t >> 14)) & _MASK) / 4294967296.0

    return rng


def seeded_shuffle(seq, seed_str):
    """Fisher-Yates on a copy of seq using an INDEPENDENT seeded stream. Used
    for instance order and within-block trial order so those draws never shift
    the main encoding stream (variant/scramble) — keeping that stream stable."""
    a = list(seq)
    rng = make_rng(seed_str)
    for i in range(len(a) - 1, 0, -1):
        j = int(rng() * (i + 1))
        a[i], a[j] = a[j], a[i]
    return a


# --- image path -------------------------------------------------------------
def image_file(routine_num, step_num, variant, absolute=False):
    rel = "{}scene_{}_{}_{}{}".format(
        CONFIG["paths"]["images"], routine_num, step_num, variant,
        CONFIG["paths"].get("image_ext", ".png")
    )
    return os.path.join(REPO_ROOT, rel) if absolute else rel


# --- build the stimulus model from the two CSVs ----------------------------
def _read_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def build_stimuli(block1_path=None, block2_path=None, restrict_routines="__config__"):
    """Build the stimulus model.

    restrict_routines: list of routine_ids to keep (demo mode), or None for the
    full 8-routine experiment. Defaults to whatever CONFIG['demo_routines'] says;
    pass restrict_routines=None explicitly to force the full set regardless of
    config (verify_logic.py does this, so validation always tests the real thing).
    """
    b1_path = block1_path or os.path.join(REPO_ROOT, CONFIG["paths"]["block1_csv"])
    b2_path = block2_path or os.path.join(REPO_ROOT, CONFIG["paths"]["block2_csv"])
    b1 = _read_csv(b1_path)
    b2 = _read_csv(b2_path)

    # index Block 2 object rows by routine_id + step_num.
    # variant 1 <- 'target'-row description, variant 2 <- 'lure'-row description.
    # ASSUMPTION (flagged for visual verification): scene_R_S_1.png depicts the
    # 'target'-row description and scene_R_S_2.png the 'lure'-row one. Affects
    # only the shown_variant_desc label, NOT correctness (roles are per-subject).
    obj_by_key = {}
    for r in b2:
        key = (r["routine_id"], int(r["step_num"]))
        o = obj_by_key.setdefault(key, {
            "object_label": r["object_label"],
            "highlight_object": r["highlight_object"],
            "object_question_text": r["question_text"],
            "object_context_cue": r["context_cue"],
            "response_anchors": r["response_anchors"],
            "variant_desc": {},
        })
        if r["trial_variant"] == "target":
            o["variant_desc"][1] = r["shown_variant_desc"]
        elif r["trial_variant"] == "lure":
            o["variant_desc"][2] = r["shown_variant_desc"]

    routines_map = {}
    for r in b1:
        rid = r["routine_id"]
        rt = routines_map.setdefault(rid, {
            "routine_id": rid,
            "routine_label": r["routine_label"],
            "routine_num": ROUTINE_NUM[rid],
            "steps": [],
        })
        step_num = int(r["step_num"])
        is_obj = r["is_object_step"] == "1"
        obj = obj_by_key.get((rid, step_num)) if is_obj else None
        rt["steps"].append({
            "step_num": step_num,
            "is_object_step": is_obj,
            # Block 1 (schema-dimension, text) content:
            "question_text": r["question_text"],
            "context_cue": r["context_cue"],
            "response_anchors": r["response_anchors"],
            "default_omitted_step": r["default_omitted_step"] == "1",  # NOT used
            # Block 2 (specific-dimension, image) object content (None if non-object):
            "object_label": obj["object_label"] if obj else None,
            "highlight_object": obj["highlight_object"] if obj else None,
            "object_question_text": obj["object_question_text"] if obj else None,
            "object_response_anchors": obj["response_anchors"] if obj else None,
            "variant_desc": obj["variant_desc"] if obj else None,
            "variants": [1, 2] if is_obj else [1],
        })

    routines = list(routines_map.values())
    for rt in routines:
        rt["steps"].sort(key=lambda s: s["step_num"])
    routines.sort(key=lambda r: r["routine_num"])

    # --- demo mode: keep only the requested routines -------------------------
    if restrict_routines == "__config__":
        restrict_routines = CONFIG.get("demo_routines")
    if restrict_routines:
        keep = set(restrict_routines)
        known = {r["routine_id"] for r in routines}
        unknown = keep - known
        if unknown:
            raise ValueError("demo_routines contains unknown routine_id(s): %s. "
                             "Valid ids: %s" % (sorted(unknown), sorted(known)))
        routines = [r for r in routines if r["routine_id"] in keep]

    return {"routines": routines}


# --- group assignment (only used in the 'between-subject' design) -----------
def assign_group(subj_index):
    return "schema" if subj_index % 2 == 0 else "no-schema"


# --- per-routine condition assignment --------------------------------------
# Returns {routine_id: 'ordered' | 'scrambled'} for this subject.
#
# 'within-subject' (default): a rotating window of half the routines is 'ordered'
# for each subject, so the split is balanced within a subject (4/4 for 8) and,
# across subjects, each routine is ordered for ~half of them. Deterministic
# counterbalance (period = number of routines), not random.
# 'between-subject': every routine gets the same condition, from the subject's
# group (schema -> all ordered, no-schema -> all scrambled).
def assign_conditions(subj_index, stimuli):
    ids = [r["routine_id"] for r in stimuli["routines"]]  # canonical routine_num order
    if CONFIG.get("design", "within-subject") == "between-subject":
        c = "ordered" if assign_group(subj_index) == "schema" else "scrambled"
        return {rid: c for rid in ids}
    n = len(ids)
    n_ordered = (n + 1) // 2
    return {rid: ("ordered" if ((j - subj_index) % n) < n_ordered else "scrambled")
            for j, rid in enumerate(ids)}


# --- omitted step: counterbalanced rotation over the 3 non-object steps ----
def pick_omission(subj_index, routine):
    eligible = sorted(s["step_num"] for s in routine["steps"] if not s["is_object_step"])
    n = len(eligible)
    idx = ((subj_index + routine["routine_num"]) % n + n) % n
    return eligible[idx]


# --- within-instance scramble (no-schema group) ----------------------------
def _fisher_yates(arr, rng):
    a = list(arr)
    for i in range(len(a) - 1, 0, -1):
        j = int(rng() * (i + 1))
        a[i], a[j] = a[j], a[i]
    return a


# TODO(position-match, spec §1): object serial-position control. Currently a
# plain within-instance Fisher-Yates shuffle. To equate object serial positions
# across groups, implement match_position_hook(shown_steps, rng) to pin object
# steps to their schema-group serial positions (or apply aggregate cross-subject
# counterbalancing) and shuffle only the remaining slots. Changing ONLY this
# hook must suffice. Tradeoff (see discussion): pinning all 3 object steps leaves
# just 2 movable fillers, weakening the order manipulation; revisit at pilot.
def scramble_within_instance(shown_steps, rng, match_position_hook=None):
    if callable(match_position_hook):
        return match_position_hook(shown_steps, rng)
    return _fisher_yates(shown_steps, rng)


# --- per-subject variant assignment ----------------------------------------
def assign_variants(routine, rng):
    v = {}
    for s in routine["steps"]:
        if s["is_object_step"]:
            v[s["object_label"]] = 1 if rng() < 0.5 else 2
    return v


# ===========================================================================
# init_subject — build the single source-of-truth subject_state.
#   subject_id : str/int used to seed all randomness for this subject.
#   subj_index : integer driving counterbalancing (group + omission).
# ===========================================================================
def init_subject(subject_id, subj_index, stimuli, match_position_hook=None):
    rng = make_rng(subject_id)  # variant stream only (condition-independent)
    conditions = assign_conditions(subj_index, stimuli)
    routine_states = {}

    for routine in stimuli["routines"]:
        omitted = pick_omission(subj_index, routine)
        shown = [s for s in routine["steps"] if s["step_num"] != omitted]

        # Variants come from the main stream in a fixed per-routine order, so the
        # variant a subject sees never depends on the routine's condition — only
        # the ORDER of the shown scenes does.
        variant_seen = assign_variants(routine, rng)

        cond = conditions[routine["routine_id"]]
        if cond == "ordered":
            ordered = sorted(shown, key=lambda s: s["step_num"])
        else:
            # Scramble from an INDEPENDENT per-routine sub-seed, so it never
            # perturbs the variant stream (keeps variants condition-independent).
            srng = make_rng(str(subject_id) + ":scramble:" + routine["routine_id"])
            ordered = scramble_within_instance(shown, srng, match_position_hook)

        shown_order = []
        for i, s in enumerate(ordered):
            variant = variant_seen[s["object_label"]] if s["is_object_step"] else 1
            shown_order.append({
                "serial_pos": i + 1,
                "step_num": s["step_num"],
                "is_object_step": s["is_object_step"],
                "object_label": s["object_label"],
                "variant_shown": variant,
                "variant_desc": s["variant_desc"][variant] if s["is_object_step"] else None,
                "image_file": image_file(routine["routine_num"], s["step_num"], variant),
            })

        routine_states[routine["routine_id"]] = {
            "routine_id": routine["routine_id"],
            "routine_num": routine["routine_num"],
            "condition": cond,
            "omitted_step": omitted,
            "variant_seen": variant_seen,
            "shown_order": shown_order,
        }

    # Instance presentation order — drawn from an INDEPENDENT sub-seed AFTER the
    # main stream, so it never shifts variant/scramble draws (keeps them stable).
    routine_ids = [r["routine_id"] for r in stimuli["routines"]]  # routine_num order
    if CONFIG["randomize_instance_order"]:
        instance_order = seeded_shuffle(routine_ids, str(subject_id) + ":order")
    else:
        instance_order = routine_ids

    return {
        "subject_id": str(subject_id),
        "subj_index": subj_index,
        "design": CONFIG.get("design", "within-subject"),
        "cover_task": CONFIG["cover_task"],
        "instance_order": instance_order,
        "routines": routine_states,
    }


# --- ordered (shuffled) test-block trial lists -----------------------------
# Trial order within each block is randomized per subject (spec §5), each from
# its own independent sub-seed so blocks are reproducible and mutually
# independent.
def ordered_block1_trials(subject_state, stimuli):
    trials = build_block1_trials(subject_state, stimuli)
    return seeded_shuffle(trials, subject_state["subject_id"] + ":block1")


# ===========================================================================
# Order test (Block 3) — sequence reconstruction, one trial per routine.
#
# Each trial holds the routine's 5 shown scenes with, per scene:
#   true_pos      — its ACTUAL serial position at encoding (1..5)
#   canonical_pos — its rank in canonical schema order (by step_num, 1..5)
# In an 'ordered' routine these two are identical; in a 'scrambled' routine they
# dissociate, which is what makes tau_episode vs tau_schema informative.
#
# 'items' is in SCREEN order (slot 1..n), shuffled from an independent sub-seed
# so that spatial position never cues the answer.
# ===========================================================================
def build_order_test_trials(subject_state, stimuli):
    trials = []
    for routine in stimuli["routines"]:
        rid = routine["routine_id"]
        st = subject_state["routines"][rid]
        shown = st["shown_order"]
        canon_rank = {s["step_num"]: i + 1
                      for i, s in enumerate(sorted(shown, key=lambda s: s["step_num"]))}
        items = [{
            "step_num": s["step_num"],
            "image_file": s["image_file"],
            "true_pos": s["serial_pos"],
            "canonical_pos": canon_rank[s["step_num"]],
            "is_object_step": s["is_object_step"],
            "object_label": s["object_label"],
        } for s in shown]
        trials.append({
            "routine_id": rid,
            "routine_label": routine["routine_label"],
            "routine_num": routine["routine_num"],
            "condition": st["condition"],
            "items": seeded_shuffle(items, subject_state["subject_id"] + ":order_layout:" + rid),
        })
    return trials


def ordered_order_test_trials(subject_state, stimuli):
    """Order-test trials with routine order randomized per subject."""
    return seeded_shuffle(build_order_test_trials(subject_state, stimuli),
                          subject_state["subject_id"] + ":ordertest")


def _same_object_key(t):
    return (t["routine_id"], t["object_label"])


def _min_same_object_lag(order):
    """Smallest gap between the two trials of any single object in this order."""
    pos = {}
    for i, t in enumerate(order):
        pos.setdefault(_same_object_key(t), []).append(i)
    return min(abs(p[0] - p[1]) for p in pos.values())


def _block2_halves_shuffle(trials, seed_str):
    """Put one trial of each object in the first half and the other in the
    second half, then shuffle each half independently. This separates every
    object's target/lure by ~half the block by construction; the caller still
    enforces the exact minimum lag."""
    by_obj = {}
    for t in trials:
        by_obj.setdefault(_same_object_key(t), []).append(t)
    rng = make_rng(seed_str)
    first, second = [], []
    for key in sorted(by_obj):          # deterministic object order before rng
        pair = by_obj[key]
        if rng() < 0.5:                 # seeded: which variant lands in which half
            first.append(pair[0]); second.append(pair[1])
        else:
            first.append(pair[1]); second.append(pair[0])
    # Fisher-Yates each half with the same stream
    for half in (first, second):
        for i in range(len(half) - 1, 0, -1):
            j = int(rng() * (i + 1))
            half[i], half[j] = half[j], half[i]
    return first + second


def ordered_block2_trials(subject_state, stimuli, min_lag=None):
    """Randomized Block 2 order, seeded and reproducible.

    'one' design: one trial per object (24) -> plain seeded shuffle (no object
    appears twice, so no separation constraint is needed).
    'both' design: 48 trials -> constrained shuffle keeping each object's target
    and lure at least block2_min_same_object_lag apart."""
    if CONFIG.get("block2_design", "one") == "one":
        trials = build_block2_trials_one(subject_state, stimuli)
        return seeded_shuffle(trials, subject_state["subject_id"] + ":block2")

    if min_lag is None:
        min_lag = CONFIG["block2_min_same_object_lag"]
    trials = build_block2_trials(subject_state, stimuli)
    base = subject_state["subject_id"] + ":block2"
    order = None
    for attempt in range(1000):
        order = _block2_halves_shuffle(trials, base + ":" + str(attempt))
        if _min_same_object_lag(order) >= min_lag:
            return order
    return order  # best effort (should never be reached for feasible min_lag)


# --- Block 1 correct answer (runtime, from the omission) -------------------
def block1_correct_answer(subject_state, routine_id, step_num):
    return "no" if subject_state["routines"][routine_id]["omitted_step"] == step_num else "yes"


# --- Block 1 trial list ----------------------------------------------------
def build_block1_trials(subject_state, stimuli):
    trials = []
    for routine in stimuli["routines"]:
        rid = routine["routine_id"]
        omitted = subject_state["routines"][rid]["omitted_step"]
        for step in routine["steps"]:
            trials.append({
                "routine_id": rid,
                "routine_label": routine["routine_label"],
                "condition": subject_state["routines"][rid]["condition"],
                "step_num": step["step_num"],
                "is_object_step": step["is_object_step"],
                "question_text": step["question_text"],
                "context_cue": step["context_cue"],
                "response_anchors": step["response_anchors"],
                "correct_answer": block1_correct_answer(subject_state, rid, step["step_num"]),
                "is_omitted_lure": omitted == step["step_num"],
            })
    return trials


# --- Block 2 trial builders ------------------------------------------------
def _b2_trial(routine, step, subject_state, role):
    """Build ONE Block 2 trial for the given test role ('target' shows the
    variant the subject saw at encoding -> correct 'yes'; 'lure' shows the
    unseen variant -> correct 'no')."""
    st = subject_state["routines"][routine["routine_id"]]
    target_variant = st["variant_seen"][step["object_label"]]
    lure_variant = 2 if target_variant == 1 else 1
    shown_variant = target_variant if role == "target" else lure_variant
    return {
        "routine_id": routine["routine_id"],
        "routine_label": routine["routine_label"],
        "routine_num": routine["routine_num"],
        "condition": st["condition"],
        "step_num": step["step_num"],
        "object_label": step["object_label"],
        "highlight_object": step["highlight_object"],
        "question_text": step["object_question_text"],
        "context_cue": step["context_cue"],
        "response_anchors": step["object_response_anchors"],
        "trial_variant": role,
        "variant_shown": shown_variant,
        "variant_desc": step["variant_desc"][shown_variant],
        "encoded_target_variant": target_variant,
        "image_file": image_file(routine["routine_num"], step["step_num"], shown_variant),
        "correct_answer": "yes" if role == "target" else "no",
    }


def canonical_object_list(stimuli):
    """Stable ordered list of (routine, object_step), by routine_num then
    step_num. Gives every tested object a fixed index j for counterbalancing."""
    objs = []
    for routine in stimuli["routines"]:
        for step in routine["steps"]:
            if step["is_object_step"]:
                objs.append((routine, step))
    return objs


def assign_test_roles(subject_state, stimuli):
    """One-per-object counterbalance (block2_design == 'one'): each object is
    tested with EITHER its target or its lure version this subject.
    role(object j) = 'target' iff (j + k) is even, where k = subj_index // 2.
    Using k (a WITHIN-GROUP subject counter) rather than subj_index keeps the
    balance holding inside each group — not just overall — because group itself
    is subj_index % 2. Deterministic: exactly 12 target + 12 lure per subject."""
    k = subject_state["subj_index"] // 2
    roles = {}
    for j, (routine, step) in enumerate(canonical_object_list(stimuli)):
        role = "target" if (j + k) % 2 == 0 else "lure"
        roles[(routine["routine_id"], step["object_label"])] = role
    return roles


def build_block2_trials(subject_state, stimuli):
    """'both' design: a target trial AND a lure trial for every object (48)."""
    trials = []
    for routine in stimuli["routines"]:
        for step in routine["steps"]:
            if not step["is_object_step"]:
                continue
            trials.append(_b2_trial(routine, step, subject_state, "target"))
            trials.append(_b2_trial(routine, step, subject_state, "lure"))
    return trials


def build_block2_trials_one(subject_state, stimuli):
    """'one' design: exactly one trial per object, role from assign_test_roles (24)."""
    roles = assign_test_roles(subject_state, stimuli)
    trials = []
    for routine in stimuli["routines"]:
        for step in routine["steps"]:
            if not step["is_object_step"]:
                continue
            role = roles[(routine["routine_id"], step["object_label"])]
            trials.append(_b2_trial(routine, step, subject_state, role))
    return trials
