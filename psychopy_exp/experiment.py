# ===========================================================================
# experiment.py — PsychoPy Coder timeline for the schema x episodic-memory study.
#
# Run this from PsychoPy Standalone (the Coder "Run" button) or:
#   /path/to/psychopy-python experiment.py
# The display layer cannot be exercised without psychopy installed; the
# randomization/logic layer it depends on is validated separately by
# verify_logic.py (run with a plain python3).
#
# All per-subject randomness comes from experiment_logic.init_subject — this
# file only DISPLAYS what that single source of truth decided, and logs one row
# per trial in long format.
# ===========================================================================

import os
import sys
import csv
import datetime

from psychopy import visual, core, event, gui, data  # noqa: E402

# make sibling modules importable regardless of cwd
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

from config import CONFIG  # noqa: E402
import experiment_logic as L  # noqa: E402

REPO_ROOT = L.REPO_ROOT


def asset(rel_path):
    """Resolve a repo-root-relative asset path to an absolute path."""
    return os.path.join(REPO_ROOT, rel_path)


# ---------------------------------------------------------------------------
# 1. Subject dialog + logic init
# ---------------------------------------------------------------------------
# NOTE: everything the participant can see must stay neutral — encoding is
# incidental and the memory test is a surprise (spec §1/§4). The dialog is filled
# in with the participant in the room, so its title and tips must not mention
# memory, schema, conditions, or order. (What the index actually drives is
# documented in README.md, not here.)
dlg_info = {"subject_index": 0}
dlg = gui.DlgFromDict(
    dlg_info,
    title="Everyday Experiences",
    order=["subject_index"],
    tip={"subject_index": "integer; MUST increment for every participant (0, 1, 2, …)"},
)
if not dlg.OK:
    core.quit()

subj_index = int(dlg_info["subject_index"])
# subject_id seeds all randomness. Keep it aligned with the index so the
# counterbalancing and the seeded draws refer to the same subject.
subject_id = str(subj_index)

STIM = L.build_stimuli()
STATE = L.init_subject(subject_id, subj_index, STIM)

# routine_id -> routine dict, for quick lookup of ordered scenes / labels
ROUTINE_BY_ID = {r["routine_id"]: r for r in STIM["routines"]}


# ---------------------------------------------------------------------------
# 2. Data logging — one row per trial, long format
# ---------------------------------------------------------------------------
FIELDNAMES = [
    "subject_id", "subj_index", "design", "condition", "cover_task", "is_demo",
    "phase", "block", "instance_pos",
    "routine_id", "routine_label", "routine_num",
    "step_num", "is_object_step", "object_label",
    "canonical_pos", "order_click_pos", "order_slot",
    "serial_pos_encoding", "global_scene_pos", "is_boundary_transition",
    "prev_routine_id", "prev_step_num",
    "omitted_step", "is_omitted_lure",
    "variant_shown", "variant_desc", "encoded_target_variant", "trial_variant",
    "viewing_time_ms", "cover_rating", "cover_rt_ms",
    "response", "correct_answer", "rt_ms", "timestamp",
]

IS_DEMO = bool(CONFIG.get("demo_routines"))

data_dir = asset(CONFIG["paths"]["data_dir"])
os.makedirs(data_dir, exist_ok=True)
_stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
# Demo runs get a distinct prefix so they can never be mistaken for real data.
data_path = os.path.join(data_dir, "%ssub-%s_%s.csv"
                         % ("demo_" if IS_DEMO else "", subj_index, _stamp))
_data_file = open(data_path, "w", newline="", encoding="utf-8")
_writer = csv.DictWriter(_data_file, fieldnames=FIELDNAMES)
_writer.writeheader()


def log_row(**kwargs):
    row = {k: "" for k in FIELDNAMES}
    row["subject_id"] = STATE["subject_id"]
    row["subj_index"] = STATE["subj_index"]
    row["design"] = STATE["design"]
    # 'condition' (ordered/scrambled) is per-routine, so each caller passes it via
    # kwargs (row.update below); left blank on any row without a routine.
    row["cover_task"] = STATE["cover_task"]
    row["is_demo"] = int(IS_DEMO)
    row["timestamp"] = datetime.datetime.now().isoformat(timespec="milliseconds")
    row.update(kwargs)
    _writer.writerow(row)
    _data_file.flush()  # persist after every trial (crash-resilient)


# ---------------------------------------------------------------------------
# 3. Window + reusable stimuli/helpers
# ---------------------------------------------------------------------------
win = visual.Window(fullscr=True, color="white", units="height", allowGUI=False)

TXT = dict(color="black", wrapWidth=1.4, height=0.045, font="Arial")
_msg = visual.TextStim(win, text="", **TXT)
# Scenes are 4:3 (spec §7). Fixed display box at height 0.8 -> width 0.8*4/3.
_img = visual.ImageStim(win, image=None, size=(0.8 * 4.0 / 3.0, 0.8), pos=(0, 0.06))


def _quit():
    try:
        _data_file.close()
    finally:
        win.close()
        core.quit()


def _check_escape(keys):
    if keys and "escape" in keys:
        _quit()


def show_message(text, duration=None, keys=("space",)):
    """Show centered text. If duration given, wait that long; else wait for a key."""
    _msg.text = text
    _msg.draw()
    win.flip()
    if duration is not None:
        core.wait(duration)
    else:
        k = event.waitKeys(keyList=list(keys) + ["escape"])
        _check_escape(k)


def blank(duration):
    win.flip()
    core.wait(duration)


def likert(prompt, low_label, high_label, n_points, top_y=0.30):
    """Draw a prompt + an n-point scale; collect a keypress 1..n. Returns
    (response_int, rt_seconds)."""
    q = visual.TextStim(win, text=prompt, color="black", wrapWidth=1.5,
                        height=0.05, pos=(0, top_y), font="Arial")
    # scale row: numbers with end anchors
    nums = "    ".join(str(i) for i in range(1, n_points + 1))
    scale = visual.TextStim(win, text=nums, color="black", height=0.06,
                            pos=(0, -0.05), font="Arial")
    low = visual.TextStim(win, text="1 = " + low_label, color="black", height=0.038,
                          pos=(-0.45, -0.16), font="Arial")
    high = visual.TextStim(win, text="%d = %s" % (n_points, high_label), color="black",
                           height=0.038, pos=(0.45, -0.16), font="Arial")
    hint = visual.TextStim(win, text="press a number key", color="grey", height=0.03,
                           pos=(0, -0.30), font="Arial")
    for s in (q, scale, low, high, hint):
        s.draw()
    win.flip()

    valid = [str(i) for i in range(1, n_points + 1)]
    clock = core.Clock()
    keys = event.waitKeys(keyList=valid + ["escape"], timeStamped=clock)
    _check_escape([k for k, _ in keys])
    key, rt = keys[0]
    return int(key), rt


def likert_over_image(image_path, prompt, low_label, high_label, n_points):
    """Block 2: show the scene image with the question + scale beneath it."""
    _img.image = image_path
    _img.pos = (0, 0.28)
    _img.size = (0.55 * 4.0 / 3.0, 0.55)
    _img.draw()
    q = visual.TextStim(win, text=prompt, color="black", wrapWidth=1.5, height=0.045,
                        pos=(0, -0.12), font="Arial")
    nums = "    ".join(str(i) for i in range(1, n_points + 1))
    scale = visual.TextStim(win, text=nums, color="black", height=0.055, pos=(0, -0.24), font="Arial")
    low = visual.TextStim(win, text="1 = " + low_label, color="black", height=0.033,
                          pos=(-0.5, -0.33), font="Arial")
    high = visual.TextStim(win, text="%d = %s" % (n_points, high_label), color="black",
                           height=0.033, pos=(0.5, -0.33), font="Arial")
    for s in (q, scale, low, high):
        s.draw()
    win.flip()
    valid = [str(i) for i in range(1, n_points + 1)]
    clock = core.Clock()
    keys = event.waitKeys(keyList=valid + ["escape"], timeStamped=clock)
    _check_escape([k for k, _ in keys])
    key, rt = keys[0]
    return int(key), rt


def click_to_order(image_paths, prompt):
    """Show the images side by side and have the subject click them in the order
    they think they occurred. Returns (click_order, rts) where click_order is a
    list of indices into image_paths in the order clicked, and rts are seconds
    from trial onset. Backspace undoes the last click; SPACE confirms once all
    images are assigned."""
    n = len(image_paths)
    img_w, gap = 0.28, 0.03
    img_h = img_w * 3.0 / 4.0
    x0 = -(n * img_w + (n - 1) * gap) / 2.0 + img_w / 2.0
    xs = [x0 + i * (img_w + gap) for i in range(n)]

    stims = [visual.ImageStim(win, image=image_paths[i], size=(img_w, img_h),
                              pos=(xs[i], -0.02)) for i in range(n)]
    # position badge drawn over an image once it has been assigned
    badges = [visual.TextStim(win, text="", color="white", height=0.075, bold=True,
                              pos=(xs[i], -0.02), font="Arial") for i in range(n)]
    badge_bgs = [visual.Circle(win, radius=0.055, fillColor="black", lineColor="white",
                               lineWidth=2, pos=(xs[i], -0.02)) for i in range(n)]
    q = visual.TextStim(win, text=prompt, color="black", wrapWidth=1.6, height=0.045,
                        pos=(0, 0.30), font="Arial")
    hint = visual.TextStim(win, text="", color="grey", height=0.032, pos=(0, -0.30),
                           font="Arial")

    mouse = event.Mouse(win=win)
    mouse.clickReset()
    assigned = []           # indices into stims, in click order
    rts = []
    clock = core.Clock()
    was_down = True         # ignore a button still held from the previous screen

    while True:
        for s in (q,):
            s.draw()
        for i, s in enumerate(stims):
            s.opacity = CONFIG["order_test"]["assigned_opacity"] if i in assigned else 1.0
            s.draw()
        for pos, idx in enumerate(assigned):
            badge_bgs[idx].draw()
            badges[idx].text = str(pos + 1)
            badges[idx].draw()
        hint.text = ("all placed — press SPACE to confirm   (backspace = undo)"
                     if len(assigned) == n else
                     "click the pictures in order   (backspace = undo)")
        hint.draw()
        win.flip()

        keys = event.getKeys(keyList=["escape", "backspace", "space"])
        _check_escape(keys)
        if "backspace" in keys and assigned:
            assigned.pop()
            rts.pop()
        if "space" in keys and len(assigned) == n:
            return assigned, rts

        pressed = mouse.getPressed()[0]
        if pressed and not was_down:          # rising edge = one click
            for i, s in enumerate(stims):
                if i not in assigned and s.contains(mouse):
                    assigned.append(i)
                    rts.append(clock.getTime())
                    break
        was_down = pressed


# ---------------------------------------------------------------------------
# 4. Encoding phase
# ---------------------------------------------------------------------------
def _present_scene(image_path, scene_cfg):
    """Show one scene; return viewing time in ms."""
    _img.image = image_path
    _img.pos = (0, 0.06)
    _img.size = (0.8 * 4.0 / 3.0, 0.8)
    clock = core.Clock()
    if scene_cfg["mode"] == "fixed":
        _img.draw()
        win.flip()
        core.wait(scene_cfg["fixed_ms"] / 1000.0)
        return scene_cfg["fixed_ms"]
    # self_paced: locked for min_ms, auto-advance at max_ms
    _img.draw()
    win.flip()
    core.wait(scene_cfg["min_ms"] / 1000.0)
    k = event.waitKeys(maxWait=(scene_cfg["max_ms"] - scene_cfg["min_ms"]) / 1000.0,
                       keyList=["space", "escape"], timeStamped=clock)
    _check_escape([kk for kk, _ in k] if k else [])
    return (k[0][1] * 1000.0) if k else scene_cfg["max_ms"]


def run_encoding():
    cover = STATE["cover_task"]
    anchors = CONFIG["cover_rating"]["anchors"][cover]
    prompt = CONFIG["cover_rating"]["prompts"][cover]
    hint = CONFIG["cover_rating"]["instruction_hint"][cover]
    r_max = CONFIG["cover_rating"]["max"]  # r_min assumed 1

    focus = CONFIG["cover_rating"]["focus_note"]
    show_message(
        "Welcome.\n\nYou will watch a series of pictures showing a person going through "
        "everyday experiences.\n\n"
        "After each picture you will give a quick rating:\n"
        '"%s"\n\n%s\n\n%s\n\nPress SPACE to begin.' % (prompt, hint, focus))
    scene_cfg = CONFIG["scene"]
    use_sep = CONFIG["use_instance_separator"]
    sep = CONFIG["instance_separator"]
    isi = CONFIG.get("inter_scene_blank_ms", 300) / 1000.0

    # Flatten all shown scenes into one presentation stream (instance order).
    stream = []
    for inst_pos, rid in enumerate(STATE["instance_order"]):
        for scene in STATE["routines"][rid]["shown_order"]:
            stream.append((inst_pos, rid, scene))

    prev = None  # (inst_pos, rid, scene) of the previously shown scene
    for gi, (inst_pos, rid, scene) in enumerate(stream):
        rstate = STATE["routines"][rid]
        rmeta = ROUTINE_BY_ID[rid]
        is_boundary = (prev is not None) and (prev[0] != inst_pos)

        # optional separator BEFORE the first scene of a new instance (legacy design)
        if use_sep and scene["serial_pos"] == 1:
            show_message(sep["message"], duration=sep["message_ms"] / 1000.0)
            blank(sep["blank_ms"] / 1000.0)

        viewing_ms = _present_scene(asset(scene["image_file"]), scene_cfg)

        # --- cover-task rating ---
        # Continuous design (no separator): rate every scene vs the immediately
        # preceding one, INCLUDING across boundaries; only the very first scene of
        # the whole stream is unrated. Legacy separator design: skip the first
        # scene of each instance. Pleasantness: rate every scene regardless.
        if cover == "pleasantness":
            do_rate = True
        elif use_sep:
            do_rate = scene["serial_pos"] != 1
        else:
            do_rate = gi > 0  # skip only the global first scene
        cover_rating = ""
        cover_rt = ""
        if do_rate:
            cover_rating, rt = likert(prompt, anchors["low"], anchors["high"], r_max)
            cover_rt = round(rt * 1000.0)

        log_row(
            phase="encoding", instance_pos=inst_pos, condition=rstate["condition"],
            routine_id=rid, routine_label=rmeta["routine_label"], routine_num=rmeta["routine_num"],
            step_num=scene["step_num"], is_object_step=int(scene["is_object_step"]),
            object_label=scene["object_label"] or "",
            serial_pos_encoding=scene["serial_pos"], global_scene_pos=gi,
            is_boundary_transition=(int(is_boundary) if do_rate else ""),
            prev_routine_id=(prev[1] if prev else ""),
            prev_step_num=(prev[2]["step_num"] if prev else ""),
            omitted_step=rstate["omitted_step"],
            variant_shown=scene["variant_shown"], variant_desc=scene["variant_desc"] or "",
            viewing_time_ms=round(viewing_ms), cover_rating=cover_rating, cover_rt_ms=cover_rt,
        )
        blank(isi)
        prev = (inst_pos, rid, scene)


# ---------------------------------------------------------------------------
# 5. Block 1 — schema dimension (TEXT, presence judgment) — runs FIRST
# ---------------------------------------------------------------------------
def run_block1():
    show_message(
        "Now a memory test (this part is a surprise).\n\n"
        "For each experience you will be asked whether a particular step was part of it.\n"
        "Answer with your confidence:\n"
        "1 = definitely NO   …   6 = definitely YES.\n\n"
        "There are no pictures in this part.\n\nPress SPACE to begin.")

    trials = L.ordered_block1_trials(STATE, STIM)
    for t in trials:
        prompt = "%s\n\n%s" % (t["context_cue"], t["question_text"])
        resp, rt = likert(prompt, "definitely NO", "definitely YES",
                          CONFIG["confidence"]["max"])
        log_row(
            phase="block1", block=1, condition=t["condition"],
            routine_id=t["routine_id"], routine_label=t["routine_label"],
            step_num=t["step_num"], is_object_step=int(t["is_object_step"]),
            omitted_step=STATE["routines"][t["routine_id"]]["omitted_step"],
            is_omitted_lure=int(t["is_omitted_lure"]),
            response=resp, correct_answer=t["correct_answer"], rt_ms=round(rt * 1000.0),
        )
        blank(0.25)


# ---------------------------------------------------------------------------
# 6. Block 2 — specific dimension (SCENE shown, source judgment) — runs SECOND
# ---------------------------------------------------------------------------
def run_block2():
    show_message(
        "Last part.\n\n"
        "You will see a picture from an experience and be asked whether a specific object "
        "in it is the one that was actually there.\n"
        "Focus on the object named in the question.\n"
        "1 = definitely NOT the one   …   6 = definitely the one.\n\n"
        "Press SPACE to begin.")

    trials = L.ordered_block2_trials(STATE, STIM)
    for t in trials:
        rstate = STATE["routines"][t["routine_id"]]
        prompt = "%s\n\n%s" % (t["context_cue"], t["question_text"])
        resp, rt = likert_over_image(asset(t["image_file"]), prompt,
                                     "definitely NOT the one", "definitely the one",
                                     CONFIG["confidence"]["max"])
        log_row(
            phase="block2", block=2, condition=t["condition"],
            routine_id=t["routine_id"], routine_label=t["routine_label"], routine_num=t["routine_num"],
            step_num=t["step_num"], is_object_step=1, object_label=t["object_label"],
            variant_shown=t["variant_shown"], variant_desc=t["variant_desc"],
            encoded_target_variant=rstate["variant_seen"][t["object_label"]],
            trial_variant=t["trial_variant"],
            response=resp, correct_answer=t["correct_answer"], rt_ms=round(rt * 1000.0),
        )
        blank(0.25)


# ---------------------------------------------------------------------------
# 7. Block 3 — order test (sequence reconstruction) — runs LAST
# ---------------------------------------------------------------------------
def run_order_test():
    show_message(
        "One last part.\n\n"
        "For each experience you will see its pictures all at once, in a shuffled "
        "arrangement.\n"
        "Click them in the order they actually happened — first click the one that came "
        "first, and so on.\n\n"
        "Backspace undoes your last click.\n\nPress SPACE to begin.")

    trials = L.ordered_order_test_trials(STATE, STIM)
    for t in trials:
        items = t["items"]
        paths = [asset(it["image_file"]) for it in items]
        prompt = ("In the %s experience — click the pictures in the order they happened."
                  % t["routine_label"])
        click_order, rts = click_to_order(paths, prompt)

        # one row per placement: which scene was put in which position
        for click_i, item_idx in enumerate(click_order):
            it = items[item_idx]
            log_row(
                phase="order", block=3, condition=t["condition"],
                routine_id=t["routine_id"], routine_label=t["routine_label"],
                routine_num=t["routine_num"],
                step_num=it["step_num"], is_object_step=int(it["is_object_step"]),
                object_label=it["object_label"] or "",
                serial_pos_encoding=it["true_pos"],      # ACTUAL encoding position
                canonical_pos=it["canonical_pos"],       # canonical schema position
                order_click_pos=click_i + 1,             # position the subject assigned
                order_slot=item_idx + 1,                 # where it sat on screen
                rt_ms=round(rts[click_i] * 1000.0),
            )
        blank(0.3)


# ---------------------------------------------------------------------------
# 8. Run
# ---------------------------------------------------------------------------
try:
    run_encoding()
    run_block1()   # Block 1 FIRST (spec §5): scenes must not be shown before it
    run_block2()
    # Block 3 LAST: its scenes reveal the encoded object variants, so it must not
    # precede Block 2. Block 2 first is safe — its trial order is randomized and
    # therefore carries no information about the encoding order.
    if CONFIG["order_test"]["enabled"]:
        run_order_test()
    show_message("That's the end. Thank you!\n\nPress SPACE to finish.")
finally:
    _data_file.close()

win.close()
core.quit()
