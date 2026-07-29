// ===========================================================================
// config.js — all tunable experiment parameters (JS / future online build).
//
// Mirrors psychopy_exp/config.py. Keep the two in sync: both builds read the
// same stimulus CSVs and use the same randomization algorithm, so a given
// subject index must reproduce the identical session on either platform.
//
// This file contains NO randomness. Every per-subject random decision lives in
// randomization.js and is seeded from the subject id.
// ===========================================================================

const CONFIG = {

  // --- Demo mode -----------------------------------------------------------
  // Restrict the whole experiment to a subset of routines, for a short
  // walkthrough. Everything downstream shrinks automatically.
  //   null (or [])   -> the full 8-routine experiment. Use this to collect data.
  //   ['restaurant'] -> 1 routine: 5 encoding scenes, 6 Block 1 questions,
  //                     3 Block 2 trials.
  // WARNING: demo runs are NOT valid data — the counterbalances are defined over
  // all 8 routines.
  demoRoutines: null,

  // --- Encoding cover task -------------------------------------------------
  // 'consistency' : rate how consistent this scene is with the IMMEDIATELY
  //                 preceding scene. 'pleasantness': neutral rating per scene.
  // Spec §4 flags that 'consistency' makes the order manipulation explicit
  // (demand-characteristic risk); this is a deliberate, informed choice.
  coverTask: 'consistency',

  coverRating: {
    min: 1,
    // 6-point to match the test blocks, so the subject sees one consistent
    // scale throughout. (The test blocks MUST stay 6-point/even — no neutral
    // midpoint — for confidence-ROC; the cover rating is not ROC data.)
    max: 6,

    // All subject-facing rating wording lives here, in one place.
    //
    // The consistency prompt asks whether the scene FOLLOWS FROM the previous
    // one, not whether it is "consistent with" it. That earlier wording was a
    // real problem: scrambled scenes are still perfectly "consistent" with each
    // other (same person, same place, same experience) — only their ORDER is
    // wrong — so subjects could rate a scrambled pair highly and the
    // manipulation check would fail even though the manipulation worked.
    prompts: {
      consistency: 'How well does this picture follow from the one before it?',
      pleasantness: 'How pleasant is this picture?'
    },
    anchors: {
      consistency: { low: "doesn't follow at all", high: 'follows perfectly' },
      pleasantness: { low: 'very unpleasant', high: 'very pleasant' }
    },

    // Shown on the encoding instruction screen. For 'consistency' this MUST rule
    // out the visual-similarity reading: every scene shares the art style, the
    // protagonist, and (within a routine) the setting, so perceived visual
    // similarity is high regardless of order. If subjects rate on that dimension
    // the two groups look identical.
    // Wording is kept deliberately plain — many participants are undergraduates and
    // non-native English speakers, so avoid formal or idiomatic phrasing.
    instructionHint: {
      // The clause about other people removes a real ambiguity a pilot participant
      // hit: strangers appear in one scene (the elevator passenger, the neighbouring
      // viewer) and are gone in the next. It mentions ONLY people — do NOT generalise
      // it to "ignore the details of the scene", which would discourage encoding the
      // objects that are Block 2's dependent variable.
      consistency: 'Decide whether each picture makes sense as the NEXT STEP after ' +
                   'the one before it — not whether the two pictures look alike. ' +
                   'Other people may appear or leave between pictures; that is normal.',
      pleasantness: 'Simply rate how pleasant you find each picture.'
    },

    // Attention-focusing note. Must raise engagement WITHOUT hinting at a memory
    // test — encoding stays incidental, the test stays a surprise (spec §1/§4).
    // It works by making the cover task's demands explicit, not by asking anyone
    // to remember anything.
    focusNote: 'Please give this your full attention: close other tabs and silence ' +
               'your phone. To rate well you have to see what happens in each picture, ' +
               'so look at the whole picture while it is on screen. Each picture stays ' +
               'up for a few seconds and then moves on by itself.'
  },

  // --- Scene presentation at encoding -------------------------------------
  // 'fixed'      : shown for exactly fixedMs, no response accepted. Equates
  //                encoding time across scenes AND groups. Recommended.
  // 'self_paced' : locked for minMs, auto-advances at maxMs.
  // Calibrate fixedMs in the pilot against spec §8's 60-85% target hit rate.
  scene: {
    mode: 'fixed',
    // 6 s: long enough to take in a flat illustration, short enough that the tail
    // of the trial is not spent disengaged. Forced passive viewing with no response
    // invites mind-wandering, and wandering seconds are noise, not encoding.
    fixedMs: 6000,
    minMs: 2000,
    maxMs: 10000
  },

  // --- Instance boundaries at encoding ------------------------------------
  // false (current design): NO "new experience" screen. All 40 scenes play as
  //   one continuous stream and EVERY scene is rated against the one before it,
  //   INCLUDING across routine boundaries (the boundary transition becomes an
  //   implicit event-segmentation measure). Only the very first scene of the
  //   whole stream is unrated.
  // true (spec §1 design): separator screen between routines, and the first
  //   scene of each instance is unrated.
  useInstanceSeparator: false,
  instanceSeparator: {          // only used when useInstanceSeparator = true
    message: 'A new experience is about to begin…',
    messageMs: 2000,
    blankMs: 500
  },
  interSceneBlankMs: 300,       // brief blank between consecutive scenes

  // --- Test blocks (both use a 6-point confidence scale) ------------------
  confidence: { min: 1, max: 6 },

  // Block 2 design:
  // 'one'  (default): each object tested with ONLY ONE version this subject
  //        (its target OR its lure), counterbalanced across subjects. Nobody
  //        ever sees both versions of an object. 24 trials/subject
  //        (12 target + 12 lure). For GROUP-LEVEL ROC.
  // 'both': target AND lure trial per object. 48 trials/subject (24/24).
  //        For PER-SUBJECT ROC. Uses the lag constraint below.
  block2Design: 'one',

  // Only used when block2Design === 'both': target and lure of the SAME object
  // must be at least this many positions apart (prevents side-by-side 2AFC).
  block2MinSameObjectLag: 6,

  // --- Instance (routine) presentation order at encoding ------------------
  // true : per-subject seeded random order of the 8 experiences (controls
  //        instance-position effects). Recommended.
  // false: fixed routine_num order 1..8.
  randomizeInstanceOrder: true,

  // --- Order test (Block 3) -----------------------------------------------
  // Sequence reconstruction: the routine's 5 shown scenes are displayed at once
  // in a randomized layout and the subject clicks them in the remembered order.
  // Scored two ways that dissociate in the scrambled condition:
  //   tau_episode = reconstruction vs the ACTUAL presented order
  //   tau_schema  = reconstruction vs the CANONICAL schema order
  // MUST run last — its scenes reveal the encoded object variants.
  orderTest: {
    enabled: true,
    assignedOpacity: 0.35
  },

  // --- Post-test ratings (spec §4/§5) — hooks, disabled for now -----------
  postTest: {
    orderPlausibility: false,   // TODO: per-routine order-plausibility (manip check)
    routineFamiliarity: false   // TODO: per-routine familiarity 1-7 (covariate)
  },

  // --- Design: within- vs between-subject ---------------------------------
  // 'within-subject' (default): each subject sees HALF their routines ordered
  //   and half within-instance scrambled (4/4 of 8), counterbalanced so each
  //   routine is ordered for ~half of subjects. ordered/scrambled is then a
  //   within-subject, per-routine factor.
  // 'between-subject': each subject is entirely one condition (all ordered =
  //   schema group, or all scrambled), by subjIndex % 2.
  design: 'within-subject',

  // --- Group assignment (only used in the 'between-subject' design) --------
  // Even index -> schema, odd -> no-schema.

  // --- File locations ------------------------------------------------------
  paths: {
    // Web build uses the compressed JPEGs: 900px wide, ~115 KB each, 8.3 MB
    // total instead of 135 MB of PNGs. Verified that target/lure pairs remain
    // clearly distinguishable after compression (that is the DV, so it matters).
    // Regenerate with: sips -s format jpeg -s formatOptions 80 -Z 900 ...
    images: 'schema_stimuli_web/',
    imageExt: '.jpg',
    block1Csv: 'test_block1_schema.csv',
    block2Csv: 'test_block2_specific.csv'
  }
};

// Make available to non-module scripts and (optionally) Node.
if (typeof module !== 'undefined' && module.exports) module.exports = { CONFIG };
