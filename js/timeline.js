/**
 * timeline.js — builds the jsPsych timeline (display layer) for the online build.
 *
 * Everything about WHAT this subject sees is decided in randomization.js and read
 * from subjectState; this file only presents it and logs responses. Session
 * structure mirrors psychopy_exp/experiment.py exactly:
 *
 *   encoding (continuous 40-scene stream, rating after every scene but the first)
 *   → Block 1 (schema presence, text, 6-point)      — FIRST, before any scene is re-shown
 *   → Block 2 (specific / object variant, 6-point)
 *   → Block 3 (order test, click-to-order)          — LAST, its scenes reveal variants
 */

// --- rating trials ---------------------------------------------------------
// Ratings are collected with CLICKABLE BUTTONS, with number keys as a shortcut.
// Keyboard-only proved unreliable in the field: participants running a CJK IME can
// emit full-width digits ("１"), and non-US layouts (e.g. AZERTY) need Shift for the
// top row — in both cases event.key never equals "1" and the keypress silently does
// nothing. Buttons work regardless of keyboard or input method; the key handler below
// additionally normalises full-width digits back to ASCII.
let _kbHandler = null;

function bindDigitKeys(n) {
  _kbHandler = (e) => {
    const k = e.key.replace(/[０-９]/g,
                           (c) => String.fromCharCode(c.charCodeAt(0) - 0xFEE0));
    const v = parseInt(k, 10);
    if (Number.isInteger(v) && v >= 1 && v <= n) {
      const btns = document.querySelectorAll(".jspsych-btn");
      if (btns[v - 1]) btns[v - 1].click();
    }
  };
  document.addEventListener("keydown", _kbHandler);
}

function unbindDigitKeys() {
  if (_kbHandler) { document.removeEventListener("keydown", _kbHandler); _kbHandler = null; }
}

function ratingTrial({ stimulus, low, high, n, data, onFinish }) {
  return {
    type: jsPsychHtmlButtonResponse,
    stimulus,
    choices: Array.from({ length: n }, (_, i) => String(i + 1)),
    button_html: '<button class="jspsych-btn rate-btn">%choice%</button>',
    prompt: `<div class="anchors"><span>1 = ${low}</span><span>${n} = ${high}</span></div>
             <div class="hint">click a number, or press a number key</div>`,
    data,
    on_load: () => bindDigitKeys(n),
    on_finish: (d) => {
      unbindDigitKeys();
      // store the 1..n rating itself, never the 0-based button index
      d.response = d.response + 1;
      if (onFinish) onFinish(d);
    },
  };
}

function instructionScreen(html) {
  return {
    type: jsPsychHtmlKeyboardResponse,
    stimulus: `<div class="instr">${html}<p class="hint">Press SPACE to continue</p></div>`,
    choices: [" "],
  };
}

// ---------------------------------------------------------------------------
// Encoding — one continuous stream, no separator screens. Every scene is rated
// against the one immediately before it, INCLUDING across routine boundaries;
// only the very first scene of the whole stream is unrated.
// ---------------------------------------------------------------------------
function buildEncoding(state, stimuli) {
  const cover = CONFIG.coverTask;
  const cr = CONFIG.coverRating;
  const tl = [];

  tl.push(instructionScreen(`
    <h2>Welcome</h2>
    <p>You will watch a series of pictures showing a person going through
       everyday experiences.</p>
    <p>After each picture you will give a quick rating:</p>
    <p class="quote">"${cr.prompts[cover]}"</p>
    <p>${cr.instructionHint[cover]}</p>
    <p class="focus">${cr.focusNote}</p>`));

  // flatten to the presentation stream
  const stream = [];
  state.instance_order.forEach((rid, instPos) => {
    state.routines[rid].shown_order.forEach((scene) => stream.push({ instPos, rid, scene }));
  });

  let prev = null;
  stream.forEach((cur, gi) => {
    const { instPos, rid, scene } = cur;
    const isBoundary = prev !== null && prev.instPos !== instPos;
    const doRate = cover === "pleasantness" ? true : gi > 0;

    tl.push({
      type: jsPsychImageKeyboardResponse,
      stimulus: scene.image_file,
      choices: "NO_KEYS",
      trial_duration: CONFIG.scene.fixedMs,
      stimulus_height: 460,
      render_on_canvas: false,
      data: {
        phase: "encoding", instance_pos: instPos, condition: state.routines[rid].condition,
        routine_id: rid, step_num: scene.step_num,
        is_object_step: scene.is_object_step ? 1 : 0,
        object_label: scene.object_label || "",
        serial_pos_encoding: scene.serial_pos, global_scene_pos: gi,
        is_boundary_transition: doRate ? (isBoundary ? 1 : 0) : "",
        prev_routine_id: prev ? prev.rid : "", prev_step_num: prev ? prev.scene.step_num : "",
        omitted_step: state.routines[rid].omitted_step,
        variant_shown: scene.variant_shown, variant_desc: scene.variant_desc || "",
        viewing_time_ms: CONFIG.scene.fixedMs,
      },
    });

    if (doRate) {
      tl.push(ratingTrial({
        stimulus: `<div class="rate"><p class="q">${cr.prompts[cover]}</p></div>`,
        low: cr.anchors[cover].low, high: cr.anchors[cover].high, n: cr.max,
        data: {
          phase: "encoding_rating", condition: state.routines[rid].condition,
          routine_id: rid, step_num: scene.step_num, global_scene_pos: gi,
          is_boundary_transition: isBoundary ? 1 : 0,
        },
        onFinish: (d) => { d.cover_rating = d.response; d.cover_rt_ms = Math.round(d.rt); },
      }));
    }
    tl.push({ type: jsPsychHtmlKeyboardResponse, stimulus: "", choices: "NO_KEYS",
              trial_duration: CONFIG.interSceneBlankMs });
    prev = cur;
  });
  return tl;
}

// ---------------------------------------------------------------------------
// Block 1 — schema dimension, text only. Runs FIRST: showing scenes beforehand
// would reveal which sub-events occurred.
// ---------------------------------------------------------------------------
function buildBlock1(state, stimuli) {
  const n = CONFIG.confidence.max;
  const tl = [instructionScreen(`
    <h2>Memory test</h2>
    <p>This part is a surprise.</p>
    <p>For each experience you will be asked whether a particular step was part of it.
       Answer with your confidence.</p>
    <p class="quote">1 = definitely NO &nbsp;…&nbsp; ${n} = definitely YES</p>
    <p>There are no pictures in this part.</p>`)];

  orderedBlock1Trials(state, stimuli).forEach((t) => {
    tl.push(ratingTrial({
      stimulus: `<div class="rate"><p class="cue">${t.context_cue}</p>
                 <p class="q">${t.question_text}</p></div>`,
      low: "definitely NO", high: "definitely YES", n,
      data: {
        phase: "block1", block: 1, condition: t.condition,
        routine_id: t.routine_id, step_num: t.step_num,
        is_object_step: t.is_object_step ? 1 : 0,
        omitted_step: state.routines[t.routine_id].omitted_step,
        is_omitted_lure: t.is_omitted_lure ? 1 : 0,
        correct_answer: t.correct_answer,
      },
      onFinish: (d) => { d.rt_ms = Math.round(d.rt); },
    }));
    tl.push({ type: jsPsychHtmlKeyboardResponse, stimulus: "", choices: "NO_KEYS",
              trial_duration: 250 });
  });
  return tl;
}

// ---------------------------------------------------------------------------
// Block 2 — specific dimension. Scene shown; the question names the object.
// ---------------------------------------------------------------------------
function buildBlock2(state, stimuli) {
  const n = CONFIG.confidence.max;
  const tl = [instructionScreen(`
    <h2>Next part</h2>
    <p>You will see a picture from an experience and be asked whether a specific
       object in it is the one that was actually there.</p>
    <p>Focus on the object named in the question.</p>
    <p class="quote">1 = definitely NOT the one &nbsp;…&nbsp; ${n} = definitely the one</p>`)];

  orderedBlock2Trials(state, stimuli).forEach((t) => {
    tl.push(ratingTrial({
      stimulus: `<div class="rate">
                   <img class="probe" src="${t.image_file}">
                   <p class="cue">${t.context_cue}</p>
                   <p class="q">${t.question_text}</p></div>`,
      low: "definitely NOT the one", high: "definitely the one", n,
      data: {
        phase: "block2", block: 2, condition: t.condition,
        routine_id: t.routine_id, step_num: t.step_num, is_object_step: 1,
        object_label: t.object_label, trial_variant: t.trial_variant,
        variant_shown: t.variant_shown, variant_desc: t.variant_desc,
        encoded_target_variant: t.encoded_target_variant,
        correct_answer: t.correct_answer,
      },
      onFinish: (d) => { d.rt_ms = Math.round(d.rt); },
    }));
    tl.push({ type: jsPsychHtmlKeyboardResponse, stimulus: "", choices: "NO_KEYS",
              trial_duration: 250 });
  });
  return tl;
}

// ---------------------------------------------------------------------------
// Block 3 — order test. Runs LAST: its scenes reveal the encoded object variants,
// so it must not precede Block 2. Block 2 first is safe because its trial order
// is randomized and therefore carries no information about the encoding order.
// ---------------------------------------------------------------------------
function buildBlock3(state, stimuli) {
  const tl = [instructionScreen(`
    <h2>Last part</h2>
    <p>For each experience you will see its pictures all at once, in a mixed-up
       order.</p>
    <p>Click them in the order they actually happened — first click the one that
       came first, and so on.</p>
    <p>Backspace undoes your last click.</p>`)];

  orderedOrderTestTrials(state, stimuli).forEach((t) => {
    tl.push({
      type: jsPsychClickOrder,
      stimuli: t.items.map((it) => it.image_file),
      prompt: `In the ${t.routine_label} experience — click the pictures in the order they happened.`,
      hint: "backspace = undo",
      assigned_opacity: CONFIG.orderTest.assignedOpacity,
      data: {
        phase: "order", block: 3, condition: t.condition, routine_id: t.routine_id,
        // parallel arrays in SCREEN order, so click_order indexes straight into them
        items_step_num: t.items.map((it) => it.step_num),
        items_true_pos: t.items.map((it) => it.true_pos),
        items_canonical_pos: t.items.map((it) => it.canonical_pos),
      },
    });
  });
  return tl;
}

// ---------------------------------------------------------------------------
function buildTimeline(state, stimuli) {
  const imgs = new Set();
  state.instance_order.forEach((rid) =>
    state.routines[rid].shown_order.forEach((s) => imgs.add(s.image_file)));
  orderedBlock2Trials(state, stimuli).forEach((t) => imgs.add(t.image_file));

  return [
    { type: jsPsychPreload, images: Array.from(imgs), message: "Loading…", show_progress_bar: true },
    ...buildEncoding(state, stimuli),
    ...buildBlock1(state, stimuli),
    ...buildBlock2(state, stimuli),
    ...(CONFIG.orderTest.enabled ? buildBlock3(state, stimuli) : []),
  ];
}
