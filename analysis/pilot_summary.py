"""
pilot_summary.py — within-subject summary of the ordered vs scrambled contrast.

    python3 analysis/pilot_summary.py <data_dir>

Reports, per participant and per condition:
  * the encoding "follow from" rating (manipulation check), split by whether the
    transition crossed a routine boundary
  * Block 1 (schema dimension): hits to presented steps, false alarms to the
    omitted step, and d'
  * Block 2 (specific dimension): hits to targets, false alarms to lures, and d'
  * Block 3 (order): Kendall's tau of the reconstruction against the ACTUAL
    presented order (tau_episode) and against the CANONICAL schema order
    (tau_schema). These coincide in ordered routines and dissociate in scrambled
    ones, so the gap indexes schema intrusion.

A 6-point confidence response is dichotomised at >= 4 for hit/FA rates; the mean
confidence is reported alongside because it uses the full scale.
"""

import csv
import json
import math
import os
import sys
from collections import defaultdict


def z(p, n):
    """Inverse normal CDF with a loglinear correction for 0/1 rates."""
    p = (p * n + 0.5) / (n + 1)                      # keep d' finite
    # Acklam's rational approximation to the probit
    a = [-39.69683028665376, 220.9460984245205, -275.9285104469687,
         138.3577518672690, -30.66479806614716, 2.506628277459239]
    b = [-54.47609879822406, 161.5858368580409, -155.6989798598866,
         66.80131188771972, -13.28068155288572]
    c = [-0.007784894002430293, -0.3223964580411365, -2.400758277161838,
         -2.549732539343734, 4.374664141464968, 2.938163982698783]
    d = [0.007784695709041462, 0.3224671290700398, 2.445134137142996,
         3.754408661907416]
    pl, ph = 0.02425, 1 - 0.02425
    if p < pl:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / \
               ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    if p > ph:
        q = math.sqrt(-2 * math.log(1 - p))
        return -(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / \
                ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    q, r = p - 0.5, (p - 0.5) ** 2
    return (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q / \
           (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1)


def kendall_tau(x, y):
    n = len(x)
    con = dis = 0
    for i in range(n):
        for j in range(i + 1, n):
            s = (x[i] - x[j]) * (y[i] - y[j])
            if s > 0:
                con += 1
            elif s < 0:
                dis += 1
    tot = n * (n - 1) / 2
    return (con - dis) / tot if tot else float("nan")


def mean(v):
    return sum(v) / len(v) if v else float("nan")


def fmt(x, nd=2):
    return "  n/a" if x != x else f"{x:>5.{nd}f}"


def analyse(path):
    rows = list(csv.DictReader(open(path)))
    sid = rows[0]["subject_id"]
    idx = rows[0]["subj_index"]
    src = rows[0].get("subj_index_source", "?")
    out = {"sid": sid, "idx": idx, "src": src}

    # --- manipulation check: encoding rating -------------------------------
    rate = defaultdict(list)          # (condition, is_boundary) -> ratings
    for r in rows:
        if r.get("phase") != "encoding_rating":
            continue
        c = r["condition"]
        b = r.get("is_boundary_transition") == "1"
        rate[(c, b)].append(int(r["response"]))
    out["rating"] = {k: (mean(v), len(v)) for k, v in rate.items()}

    # --- Block 1 and Block 2: hits / false alarms --------------------------
    for phase, key in (("block1", "b1"), ("block2", "b2")):
        acc = defaultdict(lambda: {"hit": [], "fa": []})
        for r in rows:
            if r.get("phase") != phase:
                continue
            resp = int(r["response"])
            bucket = "hit" if r["correct_answer"] == "yes" else "fa"
            acc[r["condition"]][bucket].append(resp)
        res = {}
        for cond, d in acc.items():
            h, f = d["hit"], d["fa"]
            hr = mean([1 if x >= 4 else 0 for x in h])
            fr = mean([1 if x >= 4 else 0 for x in f])
            res[cond] = {
                "hit_rate": hr, "fa_rate": fr, "n_hit": len(h), "n_fa": len(f),
                "hit_conf": mean(h), "fa_conf": mean(f),
                "dprime": (z(hr, len(h)) - z(fr, len(f))) if h and f else float("nan"),
            }
        out[key] = res

    # --- Block 3: order reconstruction -------------------------------------
    order = defaultdict(lambda: {"epi": [], "sch": []})
    for r in rows:
        if r.get("phase") != "order":
            continue
        clicks = json.loads(r["click_order"])              # screen slots, in click order
        true_pos = json.loads(r["items_true_pos"])
        canon_pos = json.loads(r["items_canonical_pos"])
        assigned = [0] * len(clicks)
        for pos, slot in enumerate(clicks):
            assigned[slot] = pos + 1                       # position the subject gave
        order[r["condition"]]["epi"].append(kendall_tau(assigned, true_pos))
        order[r["condition"]]["sch"].append(kendall_tau(assigned, canon_pos))
    out["b3"] = {c: {"tau_episode": mean(d["epi"]), "tau_schema": mean(d["sch"]),
                     "n": len(d["epi"])} for c, d in order.items()}
    return out


def main(data_dir):
    files = sorted(f for f in os.listdir(data_dir)
                   if f.startswith("sub-") and f.endswith(".csv"))
    if not files:
        sys.exit(f"no sub-*.csv in {data_dir}")
    subs = [analyse(os.path.join(data_dir, f)) for f in files]

    print(f"\n{len(subs)} participant(s): " +
          ", ".join(f"{s['sid']} (idx {s['idx']}, {s['src']})" for s in subs))
    print("\nN IS FAR TOO SMALL FOR INFERENCE — these are descriptive only.\n")

    print("=" * 74)
    print("ENCODING RATING  'how well does this follow from the one before it?' (1-6)")
    print("=" * 74)
    print(f"{'subject':>10} | {'ordered':>18} | {'scrambled':>18} | {'boundary':>10}")
    print(f"{'':>10} | {'within-routine':>18} | {'within-routine':>18} | {'':>10}")
    print("-" * 74)
    for s in subs:
        o = s["rating"].get(("ordered", False), (float("nan"), 0))
        c = s["rating"].get(("scrambled", False), (float("nan"), 0))
        bo = s["rating"].get(("ordered", True), (float("nan"), 0))
        bc = s["rating"].get(("scrambled", True), (float("nan"), 0))
        bnd = mean([bo[0]] * bo[1] + [bc[0]] * bc[1]) if (bo[1] + bc[1]) else float("nan")
        print(f"{s['sid']:>10} | {fmt(o[0])} (n={o[1]:>2})      | "
              f"{fmt(c[0])} (n={c[1]:>2})      | {fmt(bnd)}")

    for key, title, note in (
        ("b1", "BLOCK 1 — schema dimension (was this step present?)",
         "hits = the 5 presented steps; false alarms = the 1 omitted step"),
        ("b2", "BLOCK 2 — specific dimension (is this the object you saw?)",
         "hits = target version; false alarms = lure version"),
    ):
        print("\n" + "=" * 74)
        print(title)
        print(note)
        print("=" * 74)
        print(f"{'subject':>10} | {'condition':>10} | {'hit':>6} {'FA':>6} {'d-prime':>8} | "
              f"{'conf(hit)':>9} {'conf(FA)':>9}")
        print("-" * 74)
        for s in subs:
            for cond in ("ordered", "scrambled"):
                d = s[key].get(cond)
                if not d:
                    continue
                print(f"{s['sid']:>10} | {cond:>10} | {fmt(d['hit_rate'])} {fmt(d['fa_rate'])} "
                      f"{fmt(d['dprime'])} | {fmt(d['hit_conf'])}    {fmt(d['fa_conf'])}")

    print("\n" + "=" * 74)
    print("BLOCK 3 — order reconstruction (Kendall's tau, -1..1)")
    print("tau_episode = vs the order actually shown; tau_schema = vs canonical order")
    print("=" * 74)
    print(f"{'subject':>10} | {'condition':>10} | {'tau_episode':>12} {'tau_schema':>12}")
    print("-" * 74)
    for s in subs:
        for cond in ("ordered", "scrambled"):
            d = s["b3"].get(cond)
            if not d:
                continue
            print(f"{s['sid']:>10} | {cond:>10} | {fmt(d['tau_episode'])}        "
                  f"{fmt(d['tau_schema'])}")
    print()


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "data")
