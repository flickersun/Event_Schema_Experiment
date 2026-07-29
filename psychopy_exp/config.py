# ===========================================================================
# config.py — all tunable experiment parameters (PsychoPy version).
#
# Mirrors js/config.js. Contains NO randomness; per-subject randomness lives in
# experiment_logic.py and is seeded from the subject id.
# ===========================================================================

CONFIG = {

    # --- Demo mode -----------------------------------------------------------
    # Restrict the whole experiment to a subset of routines, for a short
    # walkthrough (e.g. showing someone how it runs). Everything downstream
    # shrinks automatically: encoding, Block 1 and Block 2.
    #
    #   None (or [])      -> the full 8-routine experiment. Use this to collect data.
    #   ["restaurant"]    -> 1 routine: 5 encoding scenes, 6 Block 1 questions,
    #                        3 Block 2 trials (~1-2 min total).
    #   ["restaurant", "gym"] -> 2 routines, and so on.
    #
    # WARNING: demo runs are NOT valid data. The counterbalances (12/12 Block 2
    # roles, omission rotation) are defined over all 8 routines. Demo output is
    # written to a `demo_`-prefixed file and flagged with is_demo=1 so it can
    # never be mistaken for a real session.
    "demo_routines": None,

    # --- Encoding cover task -------------------------------------------------
    # 'consistency' : after each scene EXCEPT the first of an instance, rate how
    #                 consistent this scene is with the IMMEDIATELY preceding
    #                 scene (1 = not at all ... 7 = very consistent).
    # 'pleasantness': neutral 1-7 pleasantness rating on every scene.
    # Spec §4 flags that 'consistency' makes the order manipulation explicit
    # (demand-characteristic risk); this is a deliberate, informed choice.
    "cover_task": "consistency",

    "cover_rating": {
        "min": 1,
        # 6-point to match the test blocks' 6-point confidence scale, giving the
        # subject one consistent scale length throughout. (The test blocks MUST
        # stay 6-point/even — no neutral midpoint — for confidence-ROC; the
        # encoding rating is only a cover task, so dropping its midpoint is fine.)
        "max": 6,

        # All subject-facing rating wording lives here, in one place.
        #
        # The consistency prompt asks whether the scene FOLLOWS FROM the previous
        # one, not whether it is "consistent with" it. That earlier wording was a
        # real problem: scrambled scenes are still perfectly "consistent" with each
        # other (same person, same place, same experience) — only their ORDER is
        # wrong — so subjects could rate a scrambled pair highly and the
        # manipulation check would fail even though the manipulation worked.
        # "Follow from" targets the transition, which is exactly what the order
        # manipulation acts on.
        "prompts": {
            "consistency": "How well does this picture follow from the one before it?",
            "pleasantness": "How pleasant is this picture?",
        },
        "anchors": {
            "consistency": {"low": "doesn't follow at all", "high": "follows perfectly"},
            "pleasantness": {"low": "very unpleasant", "high": "very pleasant"},
        },

        # Shown on the encoding instruction screen. For 'consistency' this MUST
        # rule out the visual-similarity reading: every scene shares the art style,
        # the protagonist, and (within a routine) the setting, so perceived visual
        # similarity is high regardless of order. If subjects rate on that
        # dimension the two groups look identical.
        "instruction_hint": {
            "consistency": ("Judge whether each picture makes sense as the NEXT STEP "
                            "after the one before it — not whether the two pictures "
                            "look similar."),
            "pleasantness": "Simply rate how pleasant you find each picture.",
        },

        # Attention-focusing note on the encoding instruction screen. It must raise
        # engagement WITHOUT hinting at a memory test — encoding stays incidental and
        # the test stays a surprise (spec §1/§4). So it works by making the demands of
        # the cover task explicit ("you have to look to rate accurately") rather than
        # by asking anyone to remember anything.
        "focus_note": (
            "Please give this your full attention: close other tabs and silence "
            "your phone.\n\n"
            "Rating accurately means actually looking at what happens in each "
            "picture, so take in the whole scene while it is on screen. Each "
            "picture stays up for a few seconds and moves on by itself."
        ),
    },

    # --- Scene presentation at encoding -------------------------------------
    # 'fixed'      : scene shown for exactly fixed_ms, no response accepted.
    #                Equates encoding time across scenes AND groups (protects
    #                the between-groups memory contrast from a dwell-time
    #                confound). Recommended.
    # 'self_paced' : subject advances; locked for min_ms, auto-advances at max_ms.
    "scene": {
        "mode": "fixed",
        # 6 s: long enough to take in a flat illustration, short enough that the
        # tail of the trial is not spent disengaged. Forced passive viewing with no
        # response invites mind-wandering, and seconds spent wandering are noise,
        # not encoding — "equated exposure" would then be equated display time, not
        # equated attention. Calibrate against the 60-85% hit-rate window (spec §8),
        # using cover_rt_ms and a memory-by-global_scene_pos trend to tell "too
        # short" apart from "disengaged" — they need opposite fixes.
        "fixed_ms": 6000,
        "min_ms": 2000,
        "max_ms": 10000,
    },

    # --- Instance boundaries at encoding ------------------------------------
    # use_instance_separator = False (current design): NO "new experience" text
    #   between routines. All 40 scenes play as one continuous stream and EVERY
    #   scene is rated against the one immediately before it, INCLUDING across
    #   routine boundaries (the boundary transition becomes an implicit
    #   event-segmentation measure via the consistency dip). Only the very first
    #   scene of the whole stream is unrated (it has no predecessor).
    # use_instance_separator = True (spec §1 design): show a separator screen
    #   between routines and skip the consistency rating on the first scene of
    #   each instance.
    "use_instance_separator": False,
    "instance_separator": {          # only used when use_instance_separator = True
        "message": "A new experience is about to begin…",
        "message_ms": 2000,
        "blank_ms": 500,
    },
    "inter_scene_blank_ms": 300,     # brief blank between consecutive scenes

    # --- Test blocks (both use a 6-point confidence scale) ------------------
    "confidence": {"min": 1, "max": 6},

    # Block 2 design:
    # 'one'  (default): each object is tested with ONLY ONE version this subject
    #        (its target OR its lure), counterbalanced across subjects. Nobody
    #        ever sees both versions of an object, so direct comparison is
    #        impossible. 24 trials/subject (12 target + 12 lure). Intended for
    #        GROUP-LEVEL ROC (pool trials across subjects within a group).
    # 'both': each object gets a target trial AND a lure trial. 48 trials/subject
    #        (24/24). Needed only for PER-SUBJECT ROC. Uses the lag constraint
    #        below to keep an object's two trials apart.
    "block2_design": "one",

    # Only used when block2_design == 'both': target and lure of the SAME object
    # must be at least this many positions apart (prevents side-by-side 2AFC).
    "block2_min_same_object_lag": 6,

    # --- Order test (Block 3) -----------------------------------------------
    # Sequence-reconstruction test of memory for the ORDER of sub-events — the
    # variable the experiment actually manipulates, which neither Block 1 (step
    # presence, order-independent) nor Block 2 (object variant) measures.
    #
    # For each routine the 5 shown scenes are displayed at once in a randomized
    # spatial layout and the subject CLICKS them in the remembered order. From
    # one reconstruction you get all 10 pairwise relations, and you can score it
    # two ways that dissociate in the scrambled condition:
    #   tau_episode = reconstructed order vs the ACTUAL presented order
    #   tau_schema  = reconstructed order vs the CANONICAL schema order
    # The gap between them is a direct, continuous index of schema intrusion.
    #
    # MUST run LAST: the scenes contain the tested objects, so showing them
    # before Block 2 would reveal which variant was encoded. Block 2 running
    # first is safe because its trial order is randomized and therefore conveys
    # no information about the encoding order.
    "order_test": {
        "enabled": True,
        # Clicked images dim to this opacity so assigned/unassigned is obvious.
        "assigned_opacity": 0.35,
    },

    # --- Post-test ratings (spec §4/§5) — hooks, disabled for now -----------
    "post_test": {
        "order_plausibility": False,   # TODO: per-routine order-plausibility (manip check)
        "routine_familiarity": False,  # TODO: per-routine familiarity 1-7 (covariate)
    },

    # --- Design: within- vs between-subject ---------------------------------
    # 'within-subject' (default): each subject sees HALF their routines ordered
    #   and half within-instance scrambled (4/4 of 8), counterbalanced so each
    #   routine is ordered for ~half of subjects. The ordered/scrambled factor is
    #   then a within-subject, per-routine variable. More power + richer per-subject
    #   PE range for the U-shape; the model's per-routine mechanism supports it.
    # 'between-subject': each subject is entirely one condition (all ordered =
    #   schema group, or all scrambled = no-schema group), by subject_index % 2.
    #   Safer against strategy carryover / demand characteristics.
    "design": "within-subject",

    # --- Instance (routine) presentation order at encoding ------------------
    # True  : per-subject seeded random order of the 8 experiences (controls
    #         instance-position effects). Recommended.
    # False : fixed routine_num order 1..8.
    "randomize_instance_order": True,

    # --- File locations (relative to repo root) -----------------------------
    "paths": {
        # Local PsychoPy uses the full-resolution PNGs (no bandwidth constraint).
        # The web build points at schema_stimuli_web/*.jpg instead — see js/config.js.
        "images": "schema_stimuli/",
        "image_ext": ".png",
        "block1_csv": "test_block1_schema.csv",
        "block2_csv": "test_block2_specific.csv",
        "data_dir": "data/",
    },
}
