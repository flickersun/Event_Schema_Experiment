// ===========================================================================
// parseStimuli.js — build the routine/step/object model from the two test CSVs.
//
// Single source of truth: the model is DERIVED from test_block1_schema.csv and
// test_block2_specific.csv rather than hand-typed, so it cannot silently drift
// away from the stimulus files. Nothing here is random.
// ===========================================================================

// routine_id -> routine number used in the image filenames.
// IMPORTANT: this ordering must match the scene_<N>_<step>_<variant>.png
// numbering of the files in schema_stimuli/. Verified against the assets:
//   1 restaurant, 2 movie, 3 clinic, 4 airport,
//   5 metro, 6 hotel, 7 laundromat, 8 gym.
const ROUTINE_NUM = {
  restaurant: 1, movie: 2, clinic: 3, airport: 4,
  metro: 5, hotel: 6, laundromat: 7, gym: 8
};

// Minimal RFC-4180-ish CSV parser: handles quoted fields and embedded commas.
// Returns an array of objects keyed by the header row.
function parseCsv(text) {
  const rows = [];
  let field = '';
  let record = [];
  let inQuotes = false;
  const s = text.replace(/\r\n/g, '\n').replace(/\r/g, '\n');

  for (let i = 0; i < s.length; i++) {
    const c = s[i];
    if (inQuotes) {
      if (c === '"') {
        if (s[i + 1] === '"') { field += '"'; i++; }  // escaped quote
        else inQuotes = false;
      } else field += c;
    } else {
      if (c === '"') inQuotes = true;
      else if (c === ',') { record.push(field); field = ''; }
      else if (c === '\n') { record.push(field); rows.push(record); field = ''; record = []; }
      else field += c;
    }
  }
  // flush trailing field/record (file may not end with newline)
  if (field.length > 0 || record.length > 0) { record.push(field); rows.push(record); }

  const header = rows.shift().map(h => h.trim());
  return rows
    .filter(r => r.length === header.length && r.some(v => v.trim() !== ''))
    .map(r => {
      const o = {};
      header.forEach((h, idx) => { o[h] = r[idx]; });
      return o;
    });
}

// Image path for a specific scene variant. Extension comes from config so the
// web build can point at the compressed JPEGs while PsychoPy keeps the PNGs.
function imageFile(routineNum, stepNum, variant) {
  return CONFIG.paths.images + 'scene_' + routineNum + '_' + stepNum + '_' + variant +
         (CONFIG.paths.imageExt || '.png');
}

// Build the full stimulus model from the two CSV texts.
// Returns { routines: [ { routine_id, routine_label, routine_num, steps:[...] } ] }
//
// restrictRoutines: array of routine_ids to keep (demo mode), or null for the
// full 8-routine experiment. Defaults to CONFIG.demoRoutines; pass null
// explicitly to force the full set regardless of config.
function buildStimuli(block1Text, block2Text, restrictRoutines) {
  if (restrictRoutines === undefined) restrictRoutines = CONFIG.demoRoutines;
  const b1 = parseCsv(block1Text);
  const b2 = parseCsv(block2Text);

  // --- index Block 2 object rows by routine_id + step_num ------------------
  // Each object slot has a 'target' row and a 'lure' row. We map:
  //   physical variant 1  <-  the 'target' row's description
  //   physical variant 2  <-  the 'lure'   row's description
  // AUDITED: all 48 object images were visually checked against the CSV and the
  // descriptions corrected so this holds (see test_files_README.md). It only
  // ever affected the shown_variant_desc bookkeeping label — NOT correctness,
  // because target/lure roles are assigned per subject at random regardless.
  const objByKey = {};
  for (const r of b2) {
    const key = r.routine_id + '_' + r.step_num;
    if (!objByKey[key]) {
      objByKey[key] = {
        object_label: r.object_label,
        highlight_object: r.highlight_object,
        object_question_text: r.question_text,
        object_context_cue: r.context_cue,
        response_anchors: r.response_anchors,
        variant_desc: {}
      };
    }
    if (r.trial_variant === 'target') objByKey[key].variant_desc[1] = r.shown_variant_desc;
    else if (r.trial_variant === 'lure') objByKey[key].variant_desc[2] = r.shown_variant_desc;
  }

  // --- build routines from Block 1 (has all 6 canonical steps in order) ----
  const routinesMap = {};
  for (const r of b1) {
    const rid = r.routine_id;
    if (!routinesMap[rid]) {
      routinesMap[rid] = {
        routine_id: rid,
        routine_label: r.routine_label,
        routine_num: ROUTINE_NUM[rid],
        steps: []
      };
    }
    const stepNum = parseInt(r.step_num, 10);
    const isObj = r.is_object_step === '1';
    const key = rid + '_' + stepNum;
    const obj = isObj ? objByKey[key] : null;

    routinesMap[rid].steps.push({
      step_num: stepNum,
      is_object_step: isObj,
      // Block 1 (schema-dimension, text) content:
      question_text: r.question_text,
      context_cue: r.context_cue,
      response_anchors: r.response_anchors,
      default_omitted_step: r.default_omitted_step === '1',  // NOT used (counterbalanced), kept for reference
      // Block 2 (specific-dimension, image) object content (null if non-object):
      object_label: obj ? obj.object_label : null,
      highlight_object: obj ? obj.highlight_object : null,
      object_question_text: obj ? obj.object_question_text : null,
      object_response_anchors: obj ? obj.response_anchors : null,
      variant_desc: obj ? obj.variant_desc : null,
      // available image variants: object steps have {1,2}, others just {1}
      variants: isObj ? [1, 2] : [1]
    });
  }

  let routines = Object.values(routinesMap);
  routines.forEach(rt => rt.steps.sort((a, b) => a.step_num - b.step_num));
  routines.sort((a, b) => a.routine_num - b.routine_num);

  // --- demo mode: keep only the requested routines -------------------------
  if (restrictRoutines && restrictRoutines.length) {
    const known = new Set(routines.map(r => r.routine_id));
    const unknown = restrictRoutines.filter(r => !known.has(r));
    if (unknown.length) {
      throw new Error('demoRoutines contains unknown routine_id(s): ' + unknown.join(', ') +
                      '. Valid ids: ' + [...known].join(', '));
    }
    const keep = new Set(restrictRoutines);
    routines = routines.filter(r => keep.has(r.routine_id));
  }

  return { routines };
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = { buildStimuli, parseCsv, imageFile, ROUTINE_NUM };
}
