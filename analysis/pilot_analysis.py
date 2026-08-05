"""
pilot_analysis.py — the standing analysis for this experiment.

    python3 analysis/pilot_analysis.py <data_dir> [--items] [--pe] [--keep-all]

Sections
    1. data check + exclusions
    2. main effects (ordered vs scrambled), paired t over subjects
    3. --items  per-object difficulty for Block 2, with a reliability check
    4. --pe     memory as a function of the encoding rating

EXCLUSIONS are behavioural and independent of the condition contrast, so they
cannot manufacture an effect. Applied per block, not per person, because a
participant can disengage from one block and do the rest properly:

    whole subject   both blocks' median RT < 800 ms AND rating SD < 1.0
                    (did not read anything, did not use the scale)
    Block 1 only    Block 1 median RT < 800 ms   (48 text questions; 800 ms is
                    not enough to read one)
    Block 2 only    Block 2 median RT < 800 ms

Never exclude on d' itself — that is selecting on the dependent variable.

PRIMARY MEASURE — fixed 2026-08-04, at n = 13, before the confirmatory sample
----------------------------------------------------------------------------
Recognition (Blocks 1 and 2) is reported primarily as **d' at the >= 4 cutoff**.
AUC over the full 6-point scale is reported alongside as a robustness check, and
the criterion sweep (section 2b) is reported with it.

Recorded here because the two measures do not agree at this n, and the choice was
made while that was already visible — so it has to be stated rather than settled
later by whichever gives the better p-value:

    Block 1 condition effect   d' -0.47 (p .036)   AUC -0.061 (p .131)
    Block 2 condition effect   d' +0.37 (p .109)   AUC +0.029 (p .522)

Reasons for d' as primary: it is the standard measure in this literature, and the
criterion sweep shows the contrast keeps its sign at every cutoff from >=2 to >=6
(Block 1 -0.19 to -0.47, Block 2 +0.18 to +0.37), so it is not an artefact of one
criterion. Reason AUC must still be reported: it uses the whole scale and does not
depend on where the criterion sits, and it is the more conservative of the two here.

If the confirmatory sample splits the two measures again, report both and say so;
do not switch the primary after the fact.
"""

import argparse
import collections
import csv
import glob
import json
import math
import os
import statistics as st

MIN_RT = 800          # ms, below which a block is treated as not-read
MIN_RATING_SD = 1.0   # rating SD below which the scale was not used
EXPECTED = {"encoding": 40, "encoding_rating": 39, "block1": 48, "block2": 24, "order": 8}


# --- statistics -------------------------------------------------------------
def probit(p, n):
    """Inverse normal CDF with a loglinear correction, so d' stays finite."""
    p = (p * n + 0.5) / (n + 1)
    a = [-39.69683028665376, 220.9460984245205, -275.9285104469687,
         138.3577518672690, -30.66479806614716, 2.506628277459239]
    b = [-54.47609879822406, 161.5858368580409, -155.6989798598866,
         66.80131188771972, -13.28068155288572]
    q = p - 0.5
    r = q * q
    return ((((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q /
            (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1))


def dprime(hits, fas):
    return probit(st.mean(hits), len(hits)) - probit(st.mean(fas), len(fas))


def auc(targets, lures):
    """Mann-Whitney AUC over the full rating scale: the probability that a random
    target is rated above a random lure (ties 0.5). Unlike d' at a fixed cutoff it
    uses every response level and does not depend on where the criterion sits."""
    if not targets or not lures:
        return None
    s = sum(1 if a > b else (0.5 if a == b else 0) for a in targets for b in lures)
    return s / (len(targets) * len(lures))


def _betacf(a, b, x):
    MAXIT, EPS, FPMIN = 300, 3e-16, 1e-300
    qab, qap, qam = a + b, a + 1, a - 1
    c, d = 1.0, 1 - qab * x / qap
    d = FPMIN if abs(d) < FPMIN else d
    d = 1 / d
    h = d
    for m in range(1, MAXIT + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1 + aa * d; d = FPMIN if abs(d) < FPMIN else d
        c = 1 + aa / c; c = FPMIN if abs(c) < FPMIN else c
        d = 1 / d; h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1 + aa * d; d = FPMIN if abs(d) < FPMIN else d
        c = 1 + aa / c; c = FPMIN if abs(c) < FPMIN else c
        d = 1 / d; de = d * c; h *= de
        if abs(de - 1) < EPS:
            break
    return h


def _betai(a, b, x):
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    lb = (math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
          + a * math.log(x) + b * math.log(1 - x))
    bt = math.exp(lb)
    return bt * _betacf(a, b, x) / a if x < (a + 1) / (a + b + 2) \
        else 1 - bt * _betacf(b, a, 1 - x) / b


def paired_t(diffs):
    """mean, t, two-tailed p, n  for a one-sample t on paired differences."""
    n = len(diffs)
    if n < 2:
        return float("nan"), float("nan"), float("nan"), n
    m, sd = st.mean(diffs), st.stdev(diffs)
    if sd == 0:
        return m, float("inf"), 0.0, n
    t = m / (sd / math.sqrt(n))
    df = n - 1
    p = _betai(df / 2, 0.5, df / (df + t * t))
    return m, t, p, n


def kendall_tau(x, y):
    n = len(x)
    con = dis = 0
    for i in range(n):
        for j in range(i + 1, n):
            s = (x[i] - x[j]) * (y[i] - y[j])
            con += s > 0
            dis += s < 0
    return (con - dis) / (n * (n - 1) / 2)


def stars(p):
    return " ***" if p < .001 else (" **" if p < .01 else (" *" if p < .05 else ""))


# --- loading ----------------------------------------------------------------
def load(path):
    """One participant -> summary dict + the raw trial lists later sections need."""
    rows = list(csv.DictReader(open(path)))
    r0 = rows[0]
    s = {"sid": r0["subject_id"], "idx": int(r0["subj_index"]),
         "src": r0.get("subj_index_source", "?"), "n_rows": len(rows),
         "minutes": max(int(r["time_elapsed"]) for r in rows) / 60000,
         "phases": collections.Counter(r.get("phase", "") for r in rows)}
    s["complete"] = all(s["phases"].get(k) == v for k, v in EXPECTED.items())

    med = lambda ph: st.median([int(r["rt"]) for r in rows if r.get("phase") == ph] or [0])
    s["rt_b1"], s["rt_b2"] = med("block1"), med("block2")

    ratings = collections.defaultdict(list)
    boundary = []
    pe = {}
    for x in rows:
        if x.get("phase") == "encoding_rating":
            v = int(x["response"])
            (boundary if x.get("is_boundary_transition") == "1"
             else ratings[x["condition"]]).append(v)
            pe[(x["routine_id"], x["step_num"])] = (
                v, x.get("is_boundary_transition") == "1", x["condition"])
    s["pe"] = pe
    s["rating_sd"] = st.stdev([v for vs in ratings.values() for v in vs] + boundary)
    s["rate_ordered"] = st.mean(ratings["ordered"])
    s["rate_scrambled"] = st.mean(ratings["scrambled"])
    s["rate_boundary"] = st.mean(boundary)

    s["trials"] = {"block1": [], "block2": []}
    for ph, key in (("block1", "b1"), ("block2", "b2")):
        acc = collections.defaultdict(lambda: {"h": [], "f": []})
        for x in rows:
            if x.get("phase") != ph:
                continue
            said_yes = int(x["response"]) >= 4
            acc[x["condition"]]["h" if x["correct_answer"] == "yes" else "f"].append(said_yes)
            s["trials"][ph].append({
                "routine_id": x["routine_id"], "step_num": x["step_num"],
                "object_label": x.get("object_label", ""), "condition": x["condition"],
                "is_target": x["correct_answer"] == "yes",
                "resp": int(x["response"]), "said_yes": said_yes,
            })
        for c in ("ordered", "scrambled"):
            s[f"{key}_{c}"] = dprime(acc[c]["h"], acc[c]["f"])
        # AUC over the full scale, same split
        by_cond = collections.defaultdict(lambda: {"t": [], "l": []})
        for tr in s["trials"][ph]:
            by_cond[tr["condition"]]["t" if tr["is_target"] else "l"].append(tr["resp"])
        for c in ("ordered", "scrambled"):
            s[f"{key}auc_{c}"] = auc(by_cond[c]["t"], by_cond[c]["l"])

    order = collections.defaultdict(lambda: {"e": [], "s": []})
    for x in rows:
        if x.get("phase") != "order":
            continue
        clicks = json.loads(x["click_order"])
        true_pos = json.loads(x["items_true_pos"])
        canon = json.loads(x["items_canonical_pos"])
        assigned = [0] * len(clicks)
        for pos, slot in enumerate(clicks):
            assigned[slot] = pos + 1
        order[x["condition"]]["e"].append(kendall_tau(assigned, true_pos))
        order[x["condition"]]["s"].append(kendall_tau(assigned, canon))
    for c in ("ordered", "scrambled"):
        s[f"tau_epi_{c}"] = st.mean(order[c]["e"])
        s[f"tau_sch_{c}"] = st.mean(order[c]["s"])
    return s


def classify(s):
    """Which blocks to drop for this participant, and why."""
    drop, why = set(), []
    if s["rt_b1"] < MIN_RT and s["rt_b2"] < MIN_RT and s["rating_sd"] < MIN_RATING_SD:
        drop |= {"block1", "block2", "order", "rating"}
        why.append("whole subject: no block read, scale unused")
    else:
        if s["rt_b1"] < MIN_RT:
            drop.add("block1"); why.append("Block 1 RT")
        if s["rt_b2"] < MIN_RT:
            drop.add("block2"); why.append("Block 2 RT")
    if not s["complete"]:
        drop |= {"block1", "block2", "order", "rating"}
        why.append("incomplete")
    return drop, "; ".join(why)


# --- sections ---------------------------------------------------------------
def section_check(subs):
    print("=" * 96)
    print("1. DATA CHECK AND EXCLUSIONS")
    print("=" * 96)
    print("%-5s %-8s %6s %6s | %7s %7s %8s | %8s %s"
          % ("idx", "sid", "rows", "min", "B1 RT", "B2 RT", "rateSD", "complete", "dropped"))
    print("-" * 96)
    for s in subs:
        print("%-5d %-8s %6d %6.1f | %7.0f %7.0f %8.2f | %8s %s"
              % (s["idx"], s["sid"], s["n_rows"], s["minutes"], s["rt_b1"], s["rt_b2"],
                 s["rating_sd"], "yes" if s["complete"] else "NO", s["why"] or "—"))
    idxs = sorted(x["idx"] for x in subs)
    missing = [i for i in range(min(idxs), max(idxs) + 1) if i not in idxs]
    print("\nsubj_index present: %s" % idxs)
    print("missing (drop-outs / lost): %s" % (missing or "none"))
    bad_src = [s["sid"] for s in subs if s["src"] != "datapipe"]
    print("counterbalance source: %s"
          % ("all datapipe" if not bad_src else "NOT datapipe -> %s" % bad_src))


def section_main(subs):
    print("\n" + "=" * 96)
    print("2. MAIN EFFECTS — ordered vs scrambled, paired over participants")
    print("=" * 96)
    # Both d' and AUC are reported for every recognition measure, deliberately.
    # d' uses one cutoff (>=4) and so can pick up an effect that lives only at that
    # criterion; AUC uses the whole 6-point scale and cannot. Where the two disagree,
    # that disagreement is itself the finding — see the criterion sweep below.
    rows = [
        ("encoding rating (within-routine)", "rate_ordered", "rate_scrambled", "rating"),
        (None, None, None, None),
        ("Block 1  schema   d'", "b1_ordered", "b1_scrambled", "block1"),
        ("Block 1  schema   AUC", "b1auc_ordered", "b1auc_scrambled", "block1"),
        ("Block 2  specific d'", "b2_ordered", "b2_scrambled", "block2"),
        ("Block 2  specific AUC", "b2auc_ordered", "b2auc_scrambled", "block2"),
        (None, None, None, None),
        ("Block 3 tau_episode", "tau_epi_ordered", "tau_epi_scrambled", "order"),
        ("Block 3 tau_schema", "tau_sch_ordered", "tau_sch_scrambled", "order"),
    ]
    print("%-34s %8s %10s %8s %7s %9s %8s"
          % ("", "ordered", "scrambled", "diff", "t", "p", "same dir"))
    print("-" * 96)
    for label, a, b, block in rows:
        if label is None:
            print()
            continue
        keep = [s for s in subs if block not in s["drop"]]
        diffs = [s[a] - s[b] for s in keep]
        m, t, p, n = paired_t(diffs)
        print("%-34s %8.2f %10.2f %+8.2f %7.2f %9.4f %5d/%-2d%s"
              % (label, st.mean([s[a] for s in keep]), st.mean([s[b] for s in keep]),
                 m, t, p, sum(1 for d in diffs if d > 0), n, stars(p)))

    keep = [s for s in subs if "rating" not in s["drop"]]
    within = [(s["rate_ordered"] + s["rate_scrambled"]) / 2 for s in keep]
    bnd = [s["rate_boundary"] for s in keep]
    m, t, p, n = paired_t([b - w for b, w in zip(bnd, within)])
    print("\n%-34s %8.2f %10.2f %+8.2f %7.2f %9.4f %5d/%-2d%s"
          % ("boundary vs within-routine rating", st.mean(bnd), st.mean(within),
             m, t, p, sum(1 for b, w in zip(bnd, within) if b < w), n, stars(p)))


def section_criterion(subs):
    """d' for the condition contrast at every possible cutoff.

    d' is normally criterion-free, but only if the equal-variance Gaussian model
    holds; computed from one cutoff on a 6-point scale it can still pick up an
    effect that lives at that cutoff alone. If the contrast only appears at >=4 it
    is a property of where people put their "yes", not of how well they discriminate
    — which is what AUC, using the whole scale, would then correctly report as null.
    """
    print("\n" + "=" * 96)
    print("2b. CRITERION SWEEP — is the d' effect specific to the >=4 cutoff?")
    print("=" * 96)
    print("%-22s %s" % ("", "  ".join("  >=%d" % c for c in (2, 3, 4, 5, 6))))
    print("-" * 96)
    for block, label in (("block1", "Block 1 diff"), ("block2", "Block 2 diff")):
        keep = [s for s in subs if block not in s["drop"]]
        cells = []
        for cut in (2, 3, 4, 5, 6):
            diffs = []
            for s in keep:
                per = {}
                acc = collections.defaultdict(lambda: {"t": [], "l": []})
                for tr in s["trials"][block]:
                    acc[tr["condition"]]["t" if tr["is_target"] else "l"].append(tr["resp"])
                for c in ("ordered", "scrambled"):
                    per[c] = dprime([r >= cut for r in acc[c]["t"]],
                                    [r >= cut for r in acc[c]["l"]])
                diffs.append(per["ordered"] - per["scrambled"])
            m, t, p, n = paired_t(diffs)
            cells.append("%+.2f%s" % (m, "*" if p < .05 else " "))
        print("%-22s %s" % (label + " (d')", "  ".join("%6s" % c for c in cells)))
    print("\n  * = p < .05 at that cutoff. An effect that appears at only one cutoff is")
    print("    criterion-localised and should not be reported as a discrimination effect.")


def section_items(subs):
    """Per-object difficulty for Block 2, plus a split-half reliability check.

    The reliability number is the point of this section: with ~6 targets and ~6
    lures per object, an item's observed d' is mostly sampling noise, and ranking
    items by it then trimming the ends capitalises on exactly that noise.
    """
    print("\n" + "=" * 96)
    print("3. BLOCK 2 — per-object difficulty")
    print("=" * 96)
    keep = [s for s in subs if "block2" not in s["drop"]]
    items = collections.defaultdict(lambda: {"t": [], "f": []})
    by_sub = collections.defaultdict(lambda: collections.defaultdict(lambda: {"t": [], "f": []}))
    for s in keep:
        for tr in s["trials"]["block2"]:
            k = (tr["routine_id"], tr["object_label"])
            items[k]["t" if tr["is_target"] else "f"].append(tr["said_yes"])
            by_sub[s["sid"]][k]["t" if tr["is_target"] else "f"].append(tr["said_yes"])

    res = []
    for k, v in items.items():
        if v["t"] and v["f"]:
            res.append((dprime(v["t"], v["f"]), k, st.mean(v["t"]), st.mean(v["f"]),
                        len(v["t"]), len(v["f"])))
    res.sort()
    print("%-11s %-22s %4s %4s %7s %7s %8s" % ("routine", "object", "nT", "nL", "hit", "FA", "d'"))
    print("-" * 70)
    for d, k, hr, fr, nt, nl in res:
        tag = "  <- hard" if d <= 0.3 else ("  <- easy" if d >= 1.8 else "")
        print("%-11s %-22s %4d %4d %7.2f %7.2f %8.2f%s" % (k[0], k[1], nt, nl, hr, fr, d, tag))
    ds = [r[0] for r in res]
    print("\nd' across objects: median %.2f, range %.2f to %.2f" % (st.median(ds), min(ds), max(ds)))
    print("  at or below chance (d' <= 0): %d/%d      at ceiling (d' >= 1.8): %d/%d"
          % (sum(1 for d in ds if d <= 0), len(ds), sum(1 for d in ds if d >= 1.8), len(ds)))

    # split-half reliability of item difficulty, over participants
    sids = [s["sid"] for s in keep]
    cors = []
    for rep in range(200):
        idx = (rep * 7919) % (1 << 30)
        half = set()
        for i, sid in enumerate(sids):
            if (idx >> (i % 30)) & 1:
                half.add(sid)
        if not (2 <= len(half) <= len(sids) - 2):
            half = set(sids[: len(sids) // 2])
        a, b = [], []
        for k in items:
            va = {"t": [], "f": []}
            vb = {"t": [], "f": []}
            for sid in sids:
                tgt = (va if sid in half else vb)
                tgt["t"] += by_sub[sid][k]["t"]
                tgt["f"] += by_sub[sid][k]["f"]
            if va["t"] and va["f"] and vb["t"] and vb["f"]:
                a.append(dprime(va["t"], va["f"]))
                b.append(dprime(vb["t"], vb["f"]))
        if len(a) < 8:
            continue
        ma, mb = st.mean(a), st.mean(b)
        num = sum((x - ma) * (y - mb) for x, y in zip(a, b))
        den = math.sqrt(sum((x - ma) ** 2 for x in a) * sum((y - mb) ** 2 for y in b))
        if den:
            cors.append(num / den)
    if cors:
        r = st.mean(cors)
        full = 2 * r / (1 + r) if r > -1 else float("nan")
        print("\nsplit-half reliability of item difficulty: r = %+.3f (Spearman-Brown %+.3f)" % (r, full))
        print("  -> about %.0f%% of the spread across objects is real; the rest is sampling noise."
              % (100 * max(full, 0)))
        print("  Trimming items by observed d' is therefore mostly trimming noise.")

    # what trimming does to the condition contrast
    print("\neffect of trimming objects, on the ordered-vs-scrambled contrast:")

    def contrast(drop):
        diffs = []
        for s in keep:
            per = {}
            for c in ("ordered", "scrambled"):
                t = [tr["said_yes"] for tr in s["trials"]["block2"]
                     if tr["condition"] == c and tr["is_target"]
                     and (tr["routine_id"], tr["object_label"]) not in drop]
                f = [tr["said_yes"] for tr in s["trials"]["block2"]
                     if tr["condition"] == c and not tr["is_target"]
                     and (tr["routine_id"], tr["object_label"]) not in drop]
                per[c] = dprime(t, f) if t and f else None
            if per["ordered"] is not None and per["scrambled"] is not None:
                diffs.append(per["ordered"] - per["scrambled"])
        return paired_t(diffs), sum(1 for d in diffs if d > 0)

    def show(lab, drop):
        (m, t, p, n), same = contrast(drop)
        print("  %-20s diff %+.2f  t %5.2f  p %.4f  same dir %d/%d"
              % (lab, m, t, p, same, n))

    show("all 24 objects", set())
    order_hard = [r[1] for r in res]                 # ascending d'
    order_easy = [r[1] for r in reversed(res)]       # descending d'
    for n_drop in (3, 6):
        show("drop %d hardest" % n_drop, set(order_hard[:n_drop]))
    for n_drop in (3, 6):
        show("drop %d easiest" % n_drop, set(order_easy[:n_drop]))
    show("drop 3 hardest + 3 easiest", set(order_hard[:3]) | set(order_easy[:3]))


def section_pe(subs):
    """Memory against the encoding rating. Low rating = high prediction error."""
    print("\n" + "=" * 96)
    print("4. MEMORY vs ENCODING RATING  (rating 1 = highest PE, 6 = lowest)")
    print("=" * 96)
    for block, label in (("block2", "Block 2 (specific)"), ("block1", "Block 1 (schema)")):
        keep = [s for s in subs if block not in s["drop"]]
        print("\n%s" % label)
        if block == "block1":
            print("  note: the Block 1 lure is the omitted sub-event, which was never shown and")
            print("        so has no rating. Only hit rate can be split by PE here.")
        pooled = collections.defaultdict(lambda: {"t": [], "f": []})
        for s in keep:
            for tr in s["trials"][block]:
                k = (tr["routine_id"], tr["step_num"])
                if k not in s["pe"]:
                    continue
                rating = s["pe"][k][0]
                b = 1 if rating <= 3 else (2 if rating <= 5 else 3)
                pooled[b]["t" if tr["is_target"] else "f"].append(tr["said_yes"])
        names = {1: "rating 1-3 (high PE)", 2: "rating 4-5 (mid)", 3: "rating 6 (low PE)"}
        for b in (1, 2, 3):
            v = pooled[b]
            if len(v["t"]) < 4:
                continue
            if len(v["f"]) >= 4:
                print("  %-22s hit %.2f (n=%3d)  FA %.2f (n=%3d)  d' %+.2f"
                      % (names[b], st.mean(v["t"]), len(v["t"]),
                         st.mean(v["f"]), len(v["f"]), dprime(v["t"], v["f"])))
            else:
                print("  %-22s hit %.2f (n=%3d)  (too few lures to form d')"
                      % (names[b], st.mean(v["t"]), len(v["t"])))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("data_dir", nargs="?", default="data")
    ap.add_argument("--items", action="store_true", help="per-object Block 2 analysis")
    ap.add_argument("--pe", action="store_true", help="memory vs encoding rating")
    ap.add_argument("--keep-all", action="store_true", help="skip all exclusions")
    ap.add_argument("--drop-items-below", type=float, default=None, metavar="D",
                    help="drop Block 2 objects whose pooled d' is below D "
                         "(caveat: item difficulty is only ~12%% reliable at this N, "
                         "so this trims mostly noise)")
    args = ap.parse_args()

    files = sorted(glob.glob(os.path.join(args.data_dir, "sub-*.csv")),
                   key=lambda f: int(os.path.basename(f).split("_")[0][4:]))
    if not files:
        raise SystemExit("no sub-*.csv in %s" % args.data_dir)
    subs = [load(f) for f in files]
    for s in subs:
        s["drop"], s["why"] = (set(), "") if args.keep_all else classify(s)

    if args.drop_items_below is not None:
        pool = collections.defaultdict(lambda: {"t": [], "f": []})
        for s in subs:
            if "block2" in s["drop"]:
                continue
            for tr in s["trials"]["block2"]:
                k = (tr["routine_id"], tr["object_label"])
                pool[k]["t" if tr["is_target"] else "f"].append(tr["said_yes"])
        dropped = {k for k, v in pool.items()
                   if v["t"] and v["f"] and dprime(v["t"], v["f"]) < args.drop_items_below}
        for s in subs:
            s["trials"]["block2"] = [
                tr for tr in s["trials"]["block2"]
                if (tr["routine_id"], tr["object_label"]) not in dropped]
            acc = collections.defaultdict(lambda: {"h": [], "f": []})
            for tr in s["trials"]["block2"]:
                acc[tr["condition"]]["h" if tr["is_target"] else "f"].append(tr["said_yes"])
            for c in ("ordered", "scrambled"):
                h, f = acc[c]["h"], acc[c]["f"]
                s[f"b2_{c}"] = dprime(h, f) if h and f else float("nan")
        print("Dropped %d Block 2 objects with pooled d' < %.2f:" % (len(dropped), args.drop_items_below))
        for k in sorted(dropped):
            print("    %s / %s" % k)
        print("Item difficulty is ~12%% reliable at this N, so most of what this "
              "removes is sampling noise.\n")

    section_check(subs)
    section_main(subs)
    section_criterion(subs)
    if args.items:
        section_items(subs)
    if args.pe:
        section_pe(subs)
    print()


if __name__ == "__main__":
    main()
