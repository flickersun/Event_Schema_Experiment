# Schema & Episodic Memory — Behavioral Experiment Spec

Goal (single claim to test):
> With a schema, the schema supplies the predictable (schema) dimension, so episodic memory
> can focus on the specific dimension with less interference. BOTH dimensions are remembered
> better — the schema dimension more via FAMILIARITY, the specific dimension more via RECOLLECTION.

Not testing U-shape here (stays in the model + discussion). No violations (they would create
new event boundaries). Dimension dissociation only.

> **⚠ This spec is the original design document and has not been revised.** The built
> experiment deliberately diverges from it in several places — most notably: no instance
> separator (§1), consistency instead of pleasantness rating (§4), a 6-point encoding
> scale (§4), Block 2 reduced to 24 trials with one version per object (§5), and no
> highlight box (§5). See **`IMPLEMENTATION_NOTES.md`** for the full decision log,
> the deviations and their rationale, and the resolved §9 open items.

---

## 1. Design

- **Between-subject**, pre-learned schemas (no learning phase).
  - **Schema group**: each routine's scenes shown in the correct (predictable) order.
  - **No-schema group**: same scenes, order scrambled **within each instance** (unpredictable).
  - Both groups see identical scenes; the only difference is order predictability.
- **Scramble is within-instance, never across instances.** Cross-instance scrambling would
  destroy "which experience" as a unit — both test blocks depend on it — and would make the two
  groups do different tasks (the scrambled group doing pure item recognition over a jumble).
- **Explicit instance separator** between routines (a brief blank/"a new experience" screen), so
  the scrambled group also knows where instance boundaries are (the schema group gets this free
  from the coherent flow). Same separator for both groups.
- **8 instances**, each a *different* pre-learned routine (not repeats of one routine).
  Different routines are naturally distinguishable → test can bind "which experience".
- Same protagonist (short dark hair, green sweater) across all routines; only setting changes.
- Each routine = **6 sub-events** (rigid order). Present **5 of 6** (omit 1).
  - The omitted sub-event = schema-consistent lure at test → schema-based false memory.
- **~3 of the presented sub-events carry an OBJECT** (specific dimension); a couple of
  object-poor routines (e.g. Laundromat) carry 2. Total ≈ 22–24 objects.
- Encoding is **incidental**; memory test is a **surprise**.
- Cover task at encoding: see §4.
- **Object serial-position confound:** scrambling moves object-bearing scenes to different serial
  positions, and position affects memory. Fix at implementation: constrain the scramble so
  object-bearing scenes occupy matched serial positions in both groups.

## 2. The two dimensions

- **Schema dimension** = sub-event identity / whether that step occurred in that experience.
  Supported by schema reconstruction → predicted to run on **familiarity**, and to produce
  false alarms to the omitted (schema-consistent) step.
- **Specific dimension** = **which variant** of the object appeared this time.
  Idiosyncratic and unpredictable by the schema → predicted to run on **recollection**.

Note on orthogonality: the object's *category* is schema-related (a restaurant serves a dish),
but *which variant this time* is random and unpredictable → clean specific dimension.

## 3. Object variants (target + lure)

Each object slot has 2 variants. At encoding one variant appears (random per subject) = TARGET.
At test the other variant = LURE.

**Variant similarity rule (important):** same category, **clearly distinguishable but not
cross-category**. E.g., two clearly different dogs — NOT dog vs cat (too easy, solvable by gist)
and NOT two near-identical dogs (floor). Target ~60–85% accuracy; calibrate at pilot.

**Object salience rule:** clearly visible but not the sole focus of the frame.
Too salient → ceiling (no room for a group difference); too subtle → floor.

**Object isolation:** each object appears clearly in exactly ONE scene (no carryover to later
scenes of the same instance), so encoding is localized to that scene.

---

## 4. Encoding

Incidental cover task, one rating per scene. Two options on the table:

**(current) Expectedness rating** — "How well does this step fit what you'd expect next?" slider
0–100, PE = 100 − rating. Doubles as a manipulation check (scrambled group should rate steps as
less expected).

**(recommended, Charan's suggestion) Pleasantness rating** — neutral 1–7. Reasons to prefer it now
that U-shape is dropped and the rating is no longer an IV:
- Expectedness makes the schema dimension an explicit task and gives the two groups systematically
  different task experiences (the scrambled group evaluating "this is wrong" every trial, which
  can trigger compensatory strategies and demand characteristics).
- Pleasantness is neutral to both groups, doesn't reveal the manipulation, and still ensures deep
  semantic processing (levels-of-processing).
- The lost manipulation check can be recovered with a **post-test** order-plausibility question
  (after the memory test, so it can't contaminate encoding), viewing time, or a separate norming
  sample.

Also collect, at the very end: a **per-routine familiarity rating** (1–7, "how familiar is this
kind of place/experience to you?") — for pilot screening / as a covariate, since schema can come
from cultural knowledge, not only personal experience.

Note: since U-shape is dropped, the encoding rating is a manipulation check, not the main IV.

---

## 5. Test (surprise), two blocks

**Order: Block 1 first** — showing scenes first would reveal which sub-events occurred and
contaminate the schema-dimension presence judgments.

### Block 1 — Schema dimension (TEXT, includes the omitted step)
Text only, so the omitted step (which has no scene) is tested the same way as the others.

```
Context cue: "In the MOVIE THEATRE experience..."
"Was there a 'buying a snack' step?"
→ 1 (definitely not) ... 6 (definitely yes)
```
- Targets: the 5 presented sub-events. Lure: the 1 omitted sub-event.
- 8 instances × 6 = **48 trials**.
- Key measure: **false alarms to the omitted step** = schema-based filling (familiarity).
- Confidence → ROC → dual-process (predict: high familiarity, low recollection).

### Block 2 — Specific dimension (SCENE shown, keeps context)
The scene is shown (context preserved), with the object highlighted; the displayed scene is
either the target-object version or the lure-object version.

```
Show scene (target-object version OR lure-object version), object highlighted/boxed
"Is THIS the one you saw in that experience?"
→ 1 (definitely not) ... 6 (definitely yes)
```
- 24 objects × 2 (target + lure versions) = **48 trials**.
- Instruction must direct judgment to the highlighted object, not the whole scene/gist.
- Confidence → ROC → dual-process (predict: high recollection).

**Total ≈ 96 test trials (~15 min).** These per-class counts (48 targets / 48 lures) are near
the lower bound for stable confidence-ROC fitting — do not cut objects further.

**Caveat to record.** The lure variant never appears anywhere in the experiment, so in principle
a subject can answer from item familiarity alone ("does this picture look familiar?") without
retrieving the restaurant episode. Similar lures + a context-bound question ("is this the cake
you ate that time?") push toward a source judgment, but "the specific dimension runs on
recollection" is therefore an **empirical question the ROC measures**, not something the design
guarantees. A familiarity component in the specific dimension would be an honest finding.

### Predictions
| | Schema group | No-schema group |
|---|---|---|
| Schema dim (presence) | **higher d′** (better discrimination of presented vs omitted) | lower d′ |
| Specific dim (object variant) | **better** ← core novel claim; high recollection | worse (more interference) |
| Dimension character | schema dim runs more on **familiarity**, specific dim more on **recollection** (both groups) |

**Note on false alarms to the omitted step.** High false alarms to the omitted (schema-consistent)
step are a property of the **schema dimension itself** (schema filling), and BOTH groups have the
pre-learned schema, so both can fill — this is *not* expected to be a schema-group advantage.
The schema group's advantage should show up as **higher d′**, not as more false alarms. (Earlier
drafts predicted "more false alarms in the schema group"; that was likely wrong.)

---

## 6. The 8 routines (6 sub-events each; **[OBJ: target / lure]**)

Final set: Restaurant, Movie theatre, Doctor visit, Airport, Metro commute, Hotel, Laundromat, Gym.
Selection principles that survived: rigid (or at least non-trivial) step order; one distinct
location/action per step where possible; objects that are natural to the scene but whose *variant
this time* is unpredictable; target and lure matched in visual weight; each tested object clearly
visible in exactly one scene (isolation), with looser isolation tolerated when an item logically
persists (umbrella, suitcase) as long as its *identifying detail* appears in only one frame.

### 1. Restaurant
1. Sit down
2. Read the menu   **[OBJ: bread — croissant / bagel]**
3. Order to the waiter
4. Food is served   **[OBJ: cake A / cake B — two clearly different cakes]**
   (e.g. chocolate-curl cake vs strawberry-topped cake — same category, not cake vs pasta)
5. Eating   **[OBJ: drink — orange juice / cola]**
6. Pay and leave
> Foods have less controllable variants — revisit at pilot.

### 2. Movie theatre
1. Arrive at the cinema
2. Buy a ticket
3. Buy a snack   **[OBJ: hot dog / taco]**
4. Enter the hall (ticket check)
5. Sit down   **[OBJ: neighbouring viewer's clothing — red sweater / blue jacket]**
   - Same neighbour (same face/hair) in both versions; only the clothing differs.
   - Compose so both people are clearly visible.
6. Watch the movie   **[OBJ: what's on the screen — dog A / dog B, two clearly different dogs]**
   - Screen = plain glowing screen, a simple original flat-vector dog, no text.

### 3. Doctor visit
*One distinct location per step.*
1. Arrive at the clinic — outside, street (back view toward entrance; not pushing the door — clips)
2. Check in — front desk (filling a form on a clipboard)
3. Waiting room   **[OBJ: magazine A / magazine B — cover clearly different]**
4. Blood pressure check — corridor nook (cuff on arm, nurse with bulb pump)
5. Doctor examines — exam room (stethoscope on chest)
   **[OBJ: wall anatomy chart — full-body MUSCLE chart / full-body SKELETON chart]**
6. Pharmacy window   **[OBJ: pill bottle A / pill bottle B — cap colour + bottle shape differ]**
> "Registration" isn't self-evident from the image; that's fine — Block 1 asks in text and there's
> no competing counter step. Chart is the one non-handled object; watch its hit rate (may ceiling).

### 4. Airport departure
1. Check in / drop bag   **[OBJ: hard-shell suitcase / duffel bag]**
2. Security screening
3. Wait at the gate   **[OBJ: headphones — orange over-ear / dark-purple over-ear, same size]**
   (revised from earbuds: target and lure must have matched visual weight)
4. Boarding scan
5. Standing at the aircraft door (end of the jet bridge — round doorframe + cabin crew)
6. Buckle seatbelt   **[OBJ: neck pillow — yellow U-shape / dark-purple square]**
> Drink was rejected at the gate (collides with the restaurant drink) → headphones.
> "Overhead bin" replaced by the aircraft-door scene (illogical to stow after checking a bag).

### 5. Metro commute
1. Station entrance — rainy street, down-stairway   **[OBJ: umbrella — deep red / deep blue]**
   - Umbrella's identifying detail shows only here; from Scene 2 on it's "in the bag", not shown.
2. Ticket machine (buying a ticket)
3. Down the escalator to the platform (direction readable — platform visible below)
4. Platform, waiting   **[OBJ: cup — white paper cup w/ sleeve / dark-green steel tumbler]**
5. In the carriage, seated   **[OBJ: book — red hardcover / cream paperback]**
6. Getting off onto the platform (a *different* station; open carriage door + platform)
> Fare gates were dropped (hard to draw; entry/exit direction ambiguous) → escalator.

### 6. Hotel check-in
1. Arrive at the entrance   **[OBJ: suitcase — deep-red grooved hard-shell / deep-blue smooth hard-shell]**
   - Full suitcase shown here only; Scenes 2–5 use a tight/upper-body crop showing just the
     pull-handle, so the identifying detail (body/colour) appears in one frame only.
2. Front desk check-in (upper-body crop, only the handle visible)
3. Elevator up   **[OBJ: another passenger's clothing — orange coat / beige cardigan; same person]**
4. Walk the corridor to the room
5. Unlock the room door (key card on the reader)
6. Settle in the room   **[OBJ: on the bed — coral folded towel / teal rolled towel]**
   - Towel placed front-and-centre, contrasting colour, room otherwise simple, to be salient.

### 7. Laundromat
1. Enter carrying dirty laundry (at the doorway, arms full of rumpled clothes)
2. Load the washer   **[OBJ: a hoodie — bright red / mustard checked shirt]**
3. Add detergent (holding the bottle to pour)   **[OBJ: blue plastic jug / green round jug]**
4. Sit and wait (on a bench, machine running)
5. Fold laundry (folding a towel in hand)   **[OBJ: orange-white striped towel / blue-green striped towel]**
6. Hang clothes (on a rack) — no object
> Washer-vs-dryer confusion led to dropping the dryer. Order is looser here (fold vs hang aren't
> ordered) — accepted, since not testing U-shape; the wash→handle chain still anchors it.
> Effectively 3 objects.

### 8. Gym
*Scenes 1–2 in the green sweater; Scenes 3–6 in a grey tee + black shorts (face/hair unchanged).*
1. Front-desk scan-in
2. Locker room, changing   **[OBJ: gym bag — bright blue holdall / grey-red-stripe backpack]**
3. Mat warm-up / stretch
4. Treadmill   **[OBJ: water bottle — bright green / clear with blue cap]**
5. Dumbbells (bicep curls)
6. Leaving   **[OBJ: towel over the shoulder — dark purple / yellow-black checked]**
> Weakest schema of the set: warm-up / treadmill / dumbbells are interchangeable in order.
> Accepted (individual weak instance dilutes but doesn't break the group contrast).

**Cross-routine notes:**
- Two instances (Laundromat, and any where a slot proved too weak) may end with ~2 objects rather
  than 3; total ≈ 22–23 objects, still ≈46 target + 46 lure test trials (ROC floor).
- Variant-pair difficulty is uneven (some cross-category = easier); equalise at pilot.
- Object serial position is confounded between groups (scrambling moves object scenes to other
  positions). Fix at implementation: constrain scrambling so object scenes keep matched serial
  positions across groups.

---

## 7. Generation

Style (identical for every image):
> "flat vector illustration, simple clean shapes, muted pastel palette, soft even lighting,
> minimal background, eye-level view, no text, no words, uncluttered composition"
+ 4:3, protagonist locked, setting locked within a routine.

Workflow (validated on the restaurant):
1. Generate an **anchor** for the routine (protagonist + setting); curate from several.
2. Generate each sub-event from the anchor: "same person, same place, same style, now [action]".
   One image at a time — batching breaks consistency.
3. For each object scene, generate the **target version**, then the **lure version**:
   "identical scene, identical everything, only [object] changed to [lure variant]".
4. Check every image: object isolation (no carryover), no text, object clearly visible.

Counts: 8 routines × 6 = 48 base scenes (but only 5/6 are ever shown, so the omitted step's scene
need not be generated for encoding — only its text is needed for Block 1). Object scenes need a
target + a lure version. ≈ 22–24 objects × 2 ≈ 44–48 object images. Plan on ~60–70 images total.

---

## 8. Numbers & piloting

- Encoding: 8 instances × 5 presented scenes = **40 scenes** (~10–15 min).
- Test: ~94–96 trials (~15 min). Session ≈ 40 min.
- Pilot 10–15 people first, to check:
  1. **Object memory is not at floor/ceiling** (target hit rate ~60–85%).
  2. **False alarms to the omitted step** appear (schema filling present).
  3. Manipulation works: scrambled group rates steps as less predictable (post-test or norming).
  4. Timing and fatigue acceptable.
  5. **Per-routine familiarity** — flag routines (metro, gym, laundromat) that some subjects don't
     know; use as covariate or exclusion.
- Then ~30–40 per group × 2 groups (≈60–80 total), refined by pilot effect sizes.

## 9. Open items
- Encoding cover task: **pleasantness (recommended) vs expectedness** — decide (see §4).
- Do we generate the omitted step's scene at all? Only needed if the omitted step is
  counterbalanced across subjects (then every step can be shown to some subjects → generate all 6).
  If the omitted step is fixed per routine, 5 scenes per routine suffice.
- Restaurant objects are foods (variant differences less controllable) — revisit at pilot.
- Equalise variant-pair difficulty across routines (some pairs are cross-category = easier).
- Counterbalance which sub-event is omitted per instance (interacts with the point above).
- Constrain scramble for matched object serial positions across groups (see §1).
- Whether to add a per-object item at position 1 to probe boundary memory — decided **no**
  (only ~8 data points, underpowered; it's a different experiment).
