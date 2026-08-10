#!/usr/bin/env python3
"""Combine the per-storm results into one multi-storm transfer-study table.

Running ``--mode storm`` three times leaves three separate result folders,
each overwriting ``outputs/storm``. The runner archives them as
``outputs/storm_2015-03-17``, ``_2015-06-22`` and ``_2015-12-20``. This script
pools their per-trial metrics into the single ensemble table the paper needs
so the transfer study rests on three storms rather than one.

Outputs (in outputs/storm_ensemble/):
  transfer_pooled_trials.csv     every trial from every storm, tagged
  transfer_ensemble_summary.csv  per method: mean +/- std over pooled trials
                                  for the key accuracy channels and the NEES /
                                  NIS calibration ratios, plus |NEES_norm - 1|
                                  so methods can be ranked by DISTANCE FROM the
                                  ideal of 1 (the item-1 correction), not by
                                  smallest NEES.
Also prints a Markdown table you can paste while drafting.

Usage:
  python scripts/aggregate_storms.py                 # auto-globs outputs/storm_2015-*
  python scripts/aggregate_storms.py --pairing mismatched
  python scripts/aggregate_storms.py outputs/storm_2015-03-17 outputs/storm_2015-06-22 ...
"""
from __future__ import annotations
import argparse, glob
from pathlib import Path
import numpy as np
import pandas as pd

KEY = ["attitude_geodesic_rmse", "position_rmse", "velocity_rmse", "angular_rate_rmse"]
CALIB = ["nees_normalized", "nees_rot_normalized", "nees_trans_normalized", "nis_normalized"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("storm_dirs", nargs="*", type=Path)
    ap.add_argument("--pairing", default="mismatched",
                    help="which truth/filter pairing to pool (default mismatched).")
    ap.add_argument("--out", type=Path, default=Path("outputs/storm_ensemble"))
    a = ap.parse_args()

    dirs = a.storm_dirs or [Path(p) for p in sorted(glob.glob("outputs/storm_2015-*"))]
    frames = []
    for sd in dirs:
        f = sd / "tables" / "storm_metrics_per_trial.csv"
        if not f.exists():
            print(f"  [skip] {f} not found"); continue
        df = pd.read_csv(f)
        df["storm"] = sd.name
        frames.append(df)
    if not frames:
        raise SystemExit("No storm_metrics_per_trial.csv found. Run the storms first.")

    alldf = pd.concat(frames, ignore_index=True)
    pooled = alldf[alldf["pairing"] == a.pairing].copy()
    a.out.mkdir(parents=True, exist_ok=True)
    pooled.to_csv(a.out / "transfer_pooled_trials.csv", index=False)

    have_key = [c for c in KEY if c in pooled.columns]
    have_cal = [c for c in CALIB if c in pooled.columns]
    g = pooled.groupby("method")
    summary = pd.DataFrame(index=sorted(pooled["method"].unique()))
    summary["n_storms"] = g["storm"].nunique()
    summary["n_trials"] = g.size()
    for c in have_key + have_cal:
        summary[f"{c}_mean"] = g[c].mean()
        summary[f"{c}_std"] = g[c].std(ddof=1)
    # Item-1 correction: closeness of the full-state NEES ratio to the ideal 1.
    if "nees_normalized_mean" in summary.columns:
        summary["nees_norm_dist_from_1"] = (summary["nees_normalized_mean"] - 1.0).abs()
        summary["calibration_rank"] = summary["nees_norm_dist_from_1"].rank(method="min")
    summary = summary.reset_index().rename(columns={"index": "method"})
    summary.to_csv(a.out / "transfer_ensemble_summary.csv", index=False)

    print(f"\nPooled {len(dirs)} storms, pairing='{a.pairing}', "
          f"{summary['n_trials'].sum()} trials total -> {a.out}\n")
    show = ["method", "n_storms", "n_trials"]
    show += [f"{c}_mean" for c in have_key if f"{c}_mean" in summary.columns]
    if "nees_normalized_mean" in summary.columns:
        show += ["nees_normalized_mean", "nees_norm_dist_from_1", "calibration_rank"]
    with pd.option_context("display.float_format", lambda v: f"{v:.3f}"):
        print(summary[show].to_markdown(index=False))
    if "nees_normalized_mean" in summary.columns:
        print("\nNote: rank by nees_norm_dist_from_1 (closeness to the ideal 1.0),"
              "\nNOT by smallest NEES -- a NEES far below 1 is over-conservative,"
              "\nnot better calibrated. This is the item-1 fix, ensemble-wide.")


if __name__ == "__main__":
    main()
