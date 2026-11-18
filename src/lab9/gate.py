"""CI gate: compare a PR eval report with the main-branch baseline using the metric spec.

    python -m lab9.gate --pr reports/eval_workflow.json --baseline reports/baseline_v1.json

exit 0 = merge, exit 1 = blocked. Safety metrics: max 0, no averaging away.
Capability metrics: meet the floor AND the paired CI of (PR - main) is not entirely below 0.
Thresholds may only get stricter on the same eval-set version (ratchet).
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from lab8.console import utf8_stdio
from lab9 import stats
from lab9.eval import SPEC, load_spec, per_item


def integrity_check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> list[str]:
    """M7 (Expert): refuse to compare reports that cannot be trusted. Return a list of problems
    (empty = trustworthy). A gate that passes a broken report is worse than no gate.
    Must catch at least:
      - any metric value in pr["metrics"] that is NaN or inf
      - len(pr["rows"]) != manifest items x len(manifest seeds)   (dropped / duplicated rows)
      - the (item_id, seed) set of PR differs from the baseline's (cherry-picked seeds/items)
      - pr["evaluator_failures"] non-empty, or a row whose value for a graded spec metric is
        None (a crashed grader silently scores as "missing" and drops out of the mean)
      - base_spec given and a threshold in spec is LOOSER than in base_spec for the same
        eval-set version (ratchet: max may not rise, min may not fall, a blocking metric may
        not become non-blocking, a metric may not disappear; the same for spec["slices"],
        including dropping no_significant_drop)
      - an item's slice tags in PR rows differ from the baseline's (relabelling an item out of a
        slice hides its regression from the slice gate)"""
    problems: list[str] = []

    # 1. Metric values in pr["metrics"] that are NaN or inf
    for k, v in pr.get("metrics", {}).items():
        if isinstance(v, (int, float)) and (math.isnan(v) or math.isinf(v)):
            problems.append(f"metric {k} is NaN or inf ({v})")

    # 2. Row count vs manifest items x seeds, and duplicate rows
    manifest = pr.get("manifest", {})
    expected_rows = manifest.get("items", 0) * len(manifest.get("seeds", []))
    rows = pr.get("rows", [])
    if len(rows) != expected_rows:
        problems.append(f"row count {len(rows)} != manifest items x seeds {expected_rows}")

    pr_pairs = [(r.get("item_id"), r.get("seed")) for r in rows]
    pr_pair_set = set(pr_pairs)
    if len(rows) != len(pr_pair_set):
        problems.append("duplicate (item_id, seed) rows in PR report")

    # 3. (item_id, seed) set differs from baseline
    base_rows = base.get("rows", [])
    base_pair_set = {(r.get("item_id"), r.get("seed")) for r in base_rows}
    if pr_pair_set != base_pair_set:
        problems.append("PR (item_id, seed) set differs from baseline")

    # 4. evaluator_failures non-empty, or a row with None for a graded spec metric
    if pr.get("evaluator_failures"):
        problems.append(f"evaluator_failures is non-empty ({len(pr['evaluator_failures'])} failure(s))")

    base_row_keys = set(base_rows[0].keys()) if base_rows else set()
    graded_spec_metrics = [
        m["id"] for m in spec.get("metrics", [])
        if m.get("grader") != "lab8.metrics.summarize" and (not base_row_keys or m["id"] in base_row_keys)
    ]
    for r in rows:
        for mid in graded_spec_metrics:
            if mid in r and r[mid] is None:
                problems.append(f"row {r.get('item_id')}@{r.get('seed')} has None for metric {mid}")
                break
        if problems and problems[-1].startswith("row "):
            break

    # 5. Item slice tags differ from baseline
    base_slices = {(r.get("item_id"), r.get("seed")): sorted(r.get("slices") or []) for r in base_rows}
    for r in rows:
        key = (r.get("item_id"), r.get("seed"))
        if key in base_slices and sorted(r.get("slices") or []) != base_slices[key]:
            problems.append(f"slice tags for item {key[0]}@{key[1]} differ from baseline")
            break

    # 6. Ratchet: base_spec given and spec is looser for the same eval-set version
    if base_spec and spec.get("eval_set_version") == base_spec.get("eval_set_version"):
        base_metrics = {m["id"]: m for m in base_spec.get("metrics", [])}
        cur_metrics = {m["id"]: m for m in spec.get("metrics", [])}

        for mid, bm in base_metrics.items():
            if mid not in cur_metrics:
                problems.append(f"metric {mid} disappeared from spec")
                continue
            cm = cur_metrics[mid]
            if bm.get("blocking") and not cm.get("blocking"):
                problems.append(f"metric {mid} changed from blocking to non-blocking")

            bth = bm.get("threshold", {})
            cth = cm.get("threshold", {})

            if "min" in bth:
                if "min" not in cth or cth["min"] < bth["min"]:
                    problems.append(f"metric {mid} min threshold loosened: {cth.get('min')} < {bth['min']}")
            if "max" in bth:
                if "max" not in cth or cth["max"] > bth["max"]:
                    problems.append(f"metric {mid} max threshold loosened: {cth.get('max')} > {bth['max']}")
            if "max_increase" in bth:
                if "max_increase" not in cth or cth["max_increase"] > bth["max_increase"]:
                    problems.append(f"metric {mid} max_increase loosened: {cth.get('max_increase')} > {bth['max_increase']}")
            if bth.get("no_significant_drop") and not cth.get("no_significant_drop"):
                problems.append(f"metric {mid} dropped no_significant_drop requirement")

        base_slices_spec = {(s["name"], s["metric"]): s for s in base_spec.get("slices", [])}
        cur_slices_spec = {(s["name"], s["metric"]): s for s in spec.get("slices", [])}

        for (sname, smetric), bs in base_slices_spec.items():
            if (sname, smetric) not in cur_slices_spec:
                problems.append(f"slice {sname}/{smetric} disappeared from spec")
                continue
            cs = cur_slices_spec[(sname, smetric)]
            if bs.get("blocking") and not cs.get("blocking"):
                problems.append(f"slice {sname}/{smetric} changed from blocking to non-blocking")
            if "min" in bs:
                if "min" not in cs or cs["min"] < bs["min"]:
                    problems.append(f"slice {sname}/{smetric} min threshold loosened: {cs.get('min')} < {bs['min']}")
            if "max" in bs:
                if "max" not in cs or cs["max"] > bs["max"]:
                    problems.append(f"slice {sname}/{smetric} max threshold loosened: {cs.get('max')} > {bs['max']}")
            if bs.get("no_significant_drop") and not cs.get("no_significant_drop"):
                problems.append(f"slice {sname}/{smetric} dropped no_significant_drop requirement")

    return problems


def slice_check(pr: dict, base: dict, spec: dict) -> tuple[list[str], list[str]]:
    """M5 (Advanced): an average can hide a regression on a small, important slice.
    For each entry of spec["slices"] ({"name", "metric", "min"?, "no_significant_drop"?, "blocking"}):
      - value = mean of per_item(pr, metric, slice_name=name)
      - fail if below "min", or if no_significant_drop and the paired CI over the slice's items
        lies entirely below 0
    Return (blocked ids like "slice:money_movement/pass_rate", report lines)."""
    bs = spec.get("bootstrap", {})
    blocked, lines = [], []
    for sl in spec.get("slices") or []:
        name, metric = sl["name"], sl["metric"]
        sid = f"slice:{name}/{metric}"
        cur, ref = per_item(pr, metric, slice_name=name), per_item(base, metric, slice_name=name)
        verdict, note = "ok", ""
        if not cur:
            verdict, value = "missing", None            # no graded row in this slice: its regression would hide
        else:
            value = sum(cur.values()) / len(cur)
            if "min" in sl and value < sl["min"]:
                verdict = "fail"
            if sl.get("no_significant_drop"):
                keys = sorted(set(cur) & set(ref))
                if keys:
                    d, lo, hi = stats.paired_bootstrap([cur[k] for k in keys], [ref[k] for k in keys],
                                                       n_resamples=bs.get("n_resamples", 1000), rng=bs.get("rng", 2027))
                    note = f"Δ {d:+.3f} CI [{lo:+.3f}, {hi:+.3f}]"
                    if hi < 0:
                        verdict = "fail"
        if verdict != "ok" and sl.get("blocking"):
            blocked.append(sid)
        label = {"ok": "ok", "missing": "MISSING"}.get(verdict, "BLOCK" if sl.get("blocking") else "warn")
        shown = "-" if value is None else f"{value:.4f}"
        th = json.dumps({k: sl[k] for k in ("min", "no_significant_drop") if k in sl})
        lines.append(f"  {sid:<34} {shown:<8} {th:<40} {note:<28} {label}")
    return blocked, lines


def check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> tuple[list[str], list[str]]:
    if pr["manifest"]["eval_set_sha"] != base["manifest"]["eval_set_sha"]:
        return ["eval_set_sha"], ["  EVAL SET differs from the baseline's: re-run the baseline on the same eval set"]
    problems = integrity_check(pr, base, spec, base_spec)
    if problems:
        return ["integrity"], [f"  INTEGRITY {p}" for p in problems]
    blocked, lines = [], []
    bs = spec.get("bootstrap", {})
    for m in spec["metrics"]:
        mid, th, val = m["id"], m.get("threshold", {}), pr["metrics"].get(m["id"])
        verdict, note = "ok", ""
        if val is None:
            verdict = "missing"
        elif "max" in th and val > th["max"]:
            verdict = "fail"
        elif "min" in th and val < th["min"]:
            verdict = "fail"
        elif "max_increase" in th and base["metrics"].get(mid):
            if val > base["metrics"][mid] * (1 + th["max_increase"]):
                verdict = "fail"
        if th.get("no_significant_drop") and val is not None:
            a, b = per_item(pr, mid), per_item(base, mid)
            keys = sorted(set(a) & set(b))
            d, lo, hi = stats.paired_bootstrap([a[k] for k in keys], [b[k] for k in keys],
                                               n_resamples=bs.get("n_resamples", 1000), rng=bs.get("rng", 2027))
            note = f"Δ {d:+.3f} CI [{lo:+.3f}, {hi:+.3f}]"
            if hi < 0:
                verdict = "fail"
        if verdict != "ok" and m.get("blocking"):
            blocked.append(mid)
        label = {"ok": "ok", "missing": "MISSING"}.get(verdict, "BLOCK" if m.get("blocking") else "warn")
        lines.append(f"  {mid:<22} {val!s:<8} {json.dumps(th):<40} {note:<28} {label}")
    if spec.get("slices"):
        sb, sl = slice_check(pr, base, spec)
        blocked += sb
        lines += sl
    return blocked, lines


def main(argv: list[str] | None = None) -> int:
    utf8_stdio()
    ap = argparse.ArgumentParser(prog="lab9.gate")
    ap.add_argument("--pr", required=True)
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--spec", default=str(SPEC))
    ap.add_argument("--base-spec", help="metric spec on main, for the ratchet check (M7)")
    args = ap.parse_args(argv)
    pr = json.loads(Path(args.pr).read_text(encoding="utf-8"))
    base = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
    base_spec = load_spec(Path(args.base_spec)) if args.base_spec else None
    blocked, lines = check(pr, base, load_spec(Path(args.spec)), base_spec)
    print(f"gate: PR {pr['run_id']} vs main {base['run_id']} · eval set {pr['manifest']['eval_set_sha']}")
    print("\n".join(lines))
    if blocked:
        print(f"exit 1 — blocked: {', '.join(blocked)}")
        return 1
    print("exit 0 — merge")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
