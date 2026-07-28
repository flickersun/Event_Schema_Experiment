// ===========================================================================
// randomization.js — THE ONLY place that produces per-subject randomness.
//
// Design rule: no other file may call Math.random(). Everything that decides
// "what did this subject actually see" is computed here, once, into a single
// subjectState object that all downstream code (encoding timeline, Block 1
// correct answers, Block 2 target/lure images) reads from. This is what keeps
// the logged "shown" value and the actually-displayed stimulus from silently
// diverging.
//
// All randomness is SEEDED from the subject id, so re-running initSubject with
// the same id reproduces the identical experience — auditable and testable.
//
// This is a faithful port of psychopy_exp/experiment_logic.py: the PRNG is
// bit-exact and every counterbalance uses the same arithmetic, so a given
// subject index produces the identical session on either platform.
// ===========================================================================

// --- seeded PRNG (xmur3 seed hash + mulberry32 generator) ------------------
function xmur3(str) {
  let h = 1779033703 ^ str.length;
  for (let i = 0; i < str.length; i++) {
    h = Math.imul(h ^ str.charCodeAt(i), 3432918353);
    h = (h << 13) | (h >>> 19);
  }
  return function () {
    h = Math.imul(h ^ (h >>> 16), 2246822507);
    h = Math.imul(h ^ (h >>> 13), 3266489909);
    h ^= h >>> 16;
    return h >>> 0;
  };
}

function mulberry32(a) {
  return function () {
    a |= 0; a = (a + 0x6D2B79F5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// A fresh reproducible RNG for a given subject id string.
function makeRng(seedStr) {
  return mulberry32(xmur3(String(seedStr))());
}

// Fisher-Yates on a copy, using an INDEPENDENT seeded stream. Used for instance
// order and within-block trial order so those draws never shift the main
// encoding stream (variant/scramble) — keeping that stream stable.
function seededShuffle(seq, seedStr) {
  const a = seq.slice();
  const rng = makeRng(seedStr);
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(rng() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

// --- group assignment (only used in the 'between-subject' design) ----------
function assignGroup(subjIndex) {
  return (subjIndex % 2 === 0) ? 'schema' : 'no-schema';
}

// --- per-routine condition assignment --------------------------------------
// Returns { routine_id: 'ordered' | 'scrambled' } for this subject.
// 'within-subject' (default): a rotating window of half the routines is ordered
// per subject (4/4 for 8), so each routine is ordered for ~half of subjects.
// 'between-subject': every routine gets the subject's group condition.
function assignConditions(subjIndex, stimuli) {
  const ids = stimuli.routines.map(r => r.routine_id);  // canonical routine_num order
  if ((CONFIG.design || 'within-subject') === 'between-subject') {
    const c = (assignGroup(subjIndex) === 'schema') ? 'ordered' : 'scrambled';
    const out = {}; ids.forEach(rid => { out[rid] = c; }); return out;
  }
  const n = ids.length;
  const nOrdered = Math.floor((n + 1) / 2);
  const out = {};
  ids.forEach((rid, j) => {
    out[rid] = (((j - subjIndex) % n + n) % n) < nOrdered ? 'ordered' : 'scrambled';
  });
  return out;
}

// --- omitted step: counterbalanced rotation over the 3 non-object steps ----
// Omission is restricted to non-object steps (all 3 object steps are always
// shown). Across subjects, each eligible step is omitted equally often. The
// + routine_num term decorrelates which rotation slot each routine sits at for
// a given subject.
function pickOmission(subjIndex, routine) {
  const eligible = routine.steps
    .filter(s => !s.is_object_step)
    .map(s => s.step_num)
    .sort((a, b) => a - b);
  const n = eligible.length;
  const idx = (((subjIndex + routine.routine_num) % n) + n) % n;
  return eligible[idx];
}

// --- within-instance scramble (no-schema group) ----------------------------
function fisherYates(arr, rng) {
  const a = arr.slice();
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(rng() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

// TODO(position-match, spec §1): object serial-position control.
// Currently a plain within-instance Fisher-Yates shuffle. To equate object
// serial positions across groups, implement matchPositionHook(shownSteps, rng)
// to pin object-bearing steps to their schema-group serial positions (or apply
// aggregate cross-subject counterbalancing) and shuffle only the remaining
// slots. Wiring is already in place: changing ONLY this hook must suffice.
// NOTE the tradeoff — pinning all 3 object steps leaves just 2 movable filler
// scenes, which weakens the order manipulation; revisit at pilot.
function scrambleWithinInstance(shownSteps, rng, matchPositionHook) {
  if (typeof matchPositionHook === 'function') return matchPositionHook(shownSteps, rng);
  return fisherYates(shownSteps, rng);
}

// --- per-subject variant assignment ----------------------------------------
// For each object slot, the subject sees variant 1 or 2 at random (seeded).
// Whatever they saw is their TARGET; the other variant is the LURE at test.
function assignVariants(routine, rng) {
  const v = {};
  for (const s of routine.steps) {
    if (s.is_object_step) v[s.object_label] = (rng() < 0.5) ? 1 : 2;
  }
  return v;
}

// ===========================================================================
// initSubject — build the single source-of-truth subjectState.
//
//   subjectId : string/number used to seed all randomness for this subject.
//   subjIndex : integer that drives the counterbalancing (group + omission +
//               Block 2 test role). MUST increment per participant.
//   stimuli   : output of buildStimuli().
//   options.matchPositionHook : optional scramble constraint (see above).
// ===========================================================================
function initSubject(subjectId, subjIndex, stimuli, options) {
  options = options || {};
  const rng = makeRng(subjectId);  // variant stream only (condition-independent)
  const conditions = assignConditions(subjIndex, stimuli);
  const routineStates = {};

  for (const routine of stimuli.routines) {
    const omitted = pickOmission(subjIndex, routine);
    const shown = routine.steps.filter(s => s.step_num !== omitted);

    // Variants come from the main stream in a fixed per-routine order, so the
    // variant a subject sees never depends on the routine's condition.
    const variantSeen = assignVariants(routine, rng);

    const cond = conditions[routine.routine_id];
    let ordered;
    if (cond === 'ordered') {
      ordered = shown.slice().sort((a, b) => a.step_num - b.step_num);
    } else {
      // Scramble from an INDEPENDENT per-routine sub-seed so it never perturbs
      // the variant stream (keeps variants condition-independent).
      const srng = makeRng(String(subjectId) + ':scramble:' + routine.routine_id);
      ordered = scrambleWithinInstance(shown, srng, options.matchPositionHook || null);
    }

    const shown_order = ordered.map((s, i) => {
      const variant = s.is_object_step ? variantSeen[s.object_label] : 1;
      return {
        serial_pos: i + 1,
        step_num: s.step_num,
        is_object_step: s.is_object_step,
        object_label: s.object_label,
        variant_shown: variant,
        variant_desc: s.is_object_step ? s.variant_desc[variant] : null,
        image_file: imageFile(routine.routine_num, s.step_num, variant)
      };
    });

    routineStates[routine.routine_id] = {
      routine_id: routine.routine_id,
      routine_num: routine.routine_num,
      condition: cond,
      omitted_step: omitted,
      variant_seen: variantSeen,
      shown_order
    };
  }

  // Instance presentation order — drawn from an INDEPENDENT sub-seed AFTER the
  // main stream, so it never shifts variant/scramble draws (keeps them stable).
  const routineIds = stimuli.routines.map(r => r.routine_id); // routine_num order
  const instanceOrder = CONFIG.randomizeInstanceOrder
    ? seededShuffle(routineIds, String(subjectId) + ':order')
    : routineIds;

  return {
    subjectId: String(subjectId),
    subjIndex: subjIndex,
    design: CONFIG.design || 'within-subject',
    coverTask: CONFIG.coverTask,
    instance_order: instanceOrder,
    routines: routineStates
  };
}

// --- Block 1 correct answer (computed at runtime from the omission) --------
// Omitted step -> 'no' (schema-consistent lure); every shown step -> 'yes'.
function block1CorrectAnswer(subjectState, routine_id, step_num) {
  return subjectState.routines[routine_id].omitted_step === step_num ? 'no' : 'yes';
}

// --- Block 1 trial list (all 6 sub-events per routine) ---------------------
function buildBlock1Trials(subjectState, stimuli) {
  const trials = [];
  for (const routine of stimuli.routines) {
    for (const step of routine.steps) {
      trials.push({
        routine_id: routine.routine_id,
        routine_label: routine.routine_label,
        condition: subjectState.routines[routine.routine_id].condition,
        step_num: step.step_num,
        is_object_step: step.is_object_step,
        question_text: step.question_text,
        context_cue: step.context_cue,
        response_anchors: step.response_anchors,
        correct_answer: block1CorrectAnswer(subjectState, routine.routine_id, step.step_num),
        is_omitted_lure: subjectState.routines[routine.routine_id].omitted_step === step.step_num
      });
    }
  }
  return trials;
}

// ===========================================================================
// Block 2 builders
// ===========================================================================

// Build ONE Block 2 trial for the given test role. 'target' shows the variant
// the subject saw at encoding -> correct 'yes'; 'lure' shows the unseen variant
// -> correct 'no'.
function b2Trial(routine, step, subjectState, role) {
  const st = subjectState.routines[routine.routine_id];
  const targetVariant = st.variant_seen[step.object_label];
  const lureVariant = (targetVariant === 1) ? 2 : 1;
  const shownVariant = (role === 'target') ? targetVariant : lureVariant;
  return {
    routine_id: routine.routine_id,
    routine_label: routine.routine_label,
    routine_num: routine.routine_num,
    condition: st.condition,
    step_num: step.step_num,
    object_label: step.object_label,
    highlight_object: step.highlight_object,
    question_text: step.object_question_text,
    context_cue: step.context_cue,
    response_anchors: step.object_response_anchors,
    trial_variant: role,
    variant_shown: shownVariant,
    variant_desc: step.variant_desc[shownVariant],
    encoded_target_variant: targetVariant,
    image_file: imageFile(routine.routine_num, step.step_num, shownVariant),
    correct_answer: (role === 'target') ? 'yes' : 'no'
  };
}

// Stable ordered list of [routine, objectStep], by routine_num then step_num.
// Gives every tested object a fixed index j for counterbalancing.
function canonicalObjectList(stimuli) {
  const objs = [];
  for (const routine of stimuli.routines) {
    for (const step of routine.steps) {
      if (step.is_object_step) objs.push([routine, step]);
    }
  }
  return objs;
}

// One-per-object counterbalance (block2Design === 'one'): each object is tested
// with EITHER its target or its lure version this subject.
//   role(object j) = 'target' iff (j + k) is even, where k = floor(subjIndex/2).
// Using k (a WITHIN-GROUP subject counter) rather than subjIndex keeps the
// balance holding inside each group — not just overall — because group itself
// is subjIndex % 2. Deterministic: exactly 12 target + 12 lure per subject.
function assignTestRoles(subjectState, stimuli) {
  const k = Math.floor(subjectState.subjIndex / 2);
  const roles = {};
  canonicalObjectList(stimuli).forEach(([routine, step], j) => {
    roles[routine.routine_id + '|' + step.object_label] =
      ((j + k) % 2 === 0) ? 'target' : 'lure';
  });
  return roles;
}

// 'both' design: a target trial AND a lure trial for every object (48).
function buildBlock2Trials(subjectState, stimuli) {
  const trials = [];
  for (const routine of stimuli.routines) {
    for (const step of routine.steps) {
      if (!step.is_object_step) continue;
      trials.push(b2Trial(routine, step, subjectState, 'target'));
      trials.push(b2Trial(routine, step, subjectState, 'lure'));
    }
  }
  return trials;
}

// 'one' design: exactly one trial per object, role from assignTestRoles (24).
function buildBlock2TrialsOne(subjectState, stimuli) {
  const roles = assignTestRoles(subjectState, stimuli);
  const trials = [];
  for (const routine of stimuli.routines) {
    for (const step of routine.steps) {
      if (!step.is_object_step) continue;
      const role = roles[routine.routine_id + '|' + step.object_label];
      trials.push(b2Trial(routine, step, subjectState, role));
    }
  }
  return trials;
}

// ===========================================================================
// Order test (Block 3) — sequence reconstruction, one trial per routine.
// Each item carries its ACTUAL encoding position (true_pos) and its CANONICAL
// schema position (canonical_pos, rank by step_num). These coincide in an
// 'ordered' routine and dissociate in a 'scrambled' one — the basis of the
// tau_episode vs tau_schema contrast. `items` is in SCREEN order, shuffled from
// an independent sub-seed so spatial position never cues the answer.
// ===========================================================================
function buildOrderTestTrials(subjectState, stimuli) {
  const trials = [];
  for (const routine of stimuli.routines) {
    const st = subjectState.routines[routine.routine_id];
    const shown = st.shown_order;
    const canonRank = {};
    shown.slice().sort((a, b) => a.step_num - b.step_num)
         .forEach((s, i) => { canonRank[s.step_num] = i + 1; });
    const items = shown.map(s => ({
      step_num: s.step_num,
      image_file: s.image_file,
      true_pos: s.serial_pos,
      canonical_pos: canonRank[s.step_num],
      is_object_step: s.is_object_step,
      object_label: s.object_label
    }));
    trials.push({
      routine_id: routine.routine_id,
      routine_label: routine.routine_label,
      routine_num: routine.routine_num,
      condition: st.condition,
      items: seededShuffle(items, subjectState.subjectId + ':order_layout:' + routine.routine_id)
    });
  }
  return trials;
}

function orderedOrderTestTrials(subjectState, stimuli) {
  return seededShuffle(buildOrderTestTrials(subjectState, stimuli),
                       subjectState.subjectId + ':ordertest');
}

// --- 'both'-design order constraint ----------------------------------------
function sameObjectKey(t) { return t.routine_id + '|' + t.object_label; }

// Smallest gap between the two trials of any single object in this order.
function minSameObjectLag(order) {
  const pos = {};
  order.forEach((t, i) => {
    const k = sameObjectKey(t);
    (pos[k] = pos[k] || []).push(i);
  });
  return Math.min(...Object.values(pos).map(p => Math.abs(p[0] - p[1])));
}

// Put one trial of each object in the first half and the other in the second
// half, then shuffle each half independently. Separates every object's
// target/lure by ~half the block by construction.
function block2HalvesShuffle(trials, seedStr) {
  const byObj = {};
  for (const t of trials) {
    const k = sameObjectKey(t);
    (byObj[k] = byObj[k] || []).push(t);
  }
  const rng = makeRng(seedStr);
  const first = [], second = [];
  for (const key of Object.keys(byObj).sort()) {   // deterministic order before rng
    const pair = byObj[key];
    if (rng() < 0.5) { first.push(pair[0]); second.push(pair[1]); }
    else { first.push(pair[1]); second.push(pair[0]); }
  }
  for (const half of [first, second]) {
    for (let i = half.length - 1; i > 0; i--) {
      const j = Math.floor(rng() * (i + 1));
      [half[i], half[j]] = [half[j], half[i]];
    }
  }
  return first.concat(second);
}

// ===========================================================================
// Ordered (shuffled) test-block trial lists. Trial order within each block is
// randomized per subject, each from its own independent sub-seed so blocks are
// reproducible and mutually independent.
// ===========================================================================
function orderedBlock1Trials(subjectState, stimuli) {
  return seededShuffle(buildBlock1Trials(subjectState, stimuli),
                       subjectState.subjectId + ':block1');
}

function orderedBlock2Trials(subjectState, stimuli, minLag) {
  // 'one': one trial per object (24) -> plain seeded shuffle (no object appears
  // twice, so no separation constraint is needed).
  if ((CONFIG.block2Design || 'one') === 'one') {
    return seededShuffle(buildBlock2TrialsOne(subjectState, stimuli),
                         subjectState.subjectId + ':block2');
  }
  // 'both': 48 trials -> constrained shuffle keeping each object's target and
  // lure at least block2MinSameObjectLag apart.
  if (minLag == null) minLag = CONFIG.block2MinSameObjectLag;
  const trials = buildBlock2Trials(subjectState, stimuli);
  const base = subjectState.subjectId + ':block2';
  let order = null;
  for (let attempt = 0; attempt < 1000; attempt++) {
    order = block2HalvesShuffle(trials, base + ':' + attempt);
    if (minSameObjectLag(order) >= minLag) return order;
  }
  return order;  // best effort (unreachable for a feasible minLag)
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    makeRng, seededShuffle, assignGroup, pickOmission, scrambleWithinInstance,
    assignVariants, initSubject, block1CorrectAnswer,
    buildBlock1Trials, buildBlock2Trials, buildBlock2TrialsOne,
    canonicalObjectList, assignTestRoles, minSameObjectLag,
    orderedBlock1Trials, orderedBlock2Trials,
    buildOrderTestTrials, orderedOrderTestTrials
  };
}
