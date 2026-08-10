#!/usr/bin/env python3
"""Regenerate the storm NEES-partitions figure (paper Fig. 17) with the
diverged arcs PROPERLY excluded. No simulation is rerun.

Root cause of the ~1e154 y-axis
-------------------------------
The original ``_plot_nees_partitions`` in ``src/visualization/plots.py``
filtered samples with ``np.isfinite`` only. A diverged filter yields a NEES
that is astronomically large but still *finite* (~1e154), so it passed the
finite check, entered the plotted trace, and blew up the y-axis -- while the
caption claimed the diverged channels were excluded. That mismatch is exactly
what the reviewer flagged.

Fix: mask samples whose NEES exceeds a physical cap. For 24 DoF the 97.5%
chi-square bound is ~39, so any value above ``--cap`` (default 1e4) is a
divergence, not a consistency error, and is dropped from BOTH the plotted
trace and the reported mean / coverage. The figure then shows the real,
in-family behaviour and the title records how much was excluded.

Reads the per-step NEES stored in each storm run's prediction .npz files, so
it works on runs you already have -- no ``--mode storm`` needed.

Usage
-----
  # one storm archive (defaults to the mismatched pairing, PINN+UKF+MEKF):
  python scripts/fix_fig17_nees.py outputs/storm_2015-06-22

  # all three at once:
  python scripts/fix_fig17_nees.py outputs/storm_2015-03-17 \
         outputs/storm_2015-06-22 outputs/storm_2015-12-20

  # options: --pairing matched  --method EKF  --cap 1e4  --logy
"""
from __future__ import annotations
import argparse
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats as st

PANELS = [("nees", 24, "Full state (24 DoF)"),
          ("nees_rot", 12, "Rotational (12 DoF)"),
          ("nees_trans", 12, "Translational (12 DoF)")]


def load_predictions(pairing_dir: Path) -> dict[str, dict]:
    out: dict[str, dict] = {}
    pred_dir = pairing_dir / "predictions"
    for f in sorted(pred_dir.glob("*.npz")):
        d = np.load(f, allow_pickle=True)
        out[str(d["method"])] = {k: d[k] for k in d.files}
    return out


def plot_one(storm_dir: Path, pairing: str, method: str, cap: float, logy: bool) -> Path | None:
    pairing_dir = storm_dir / pairing
    preds = load_predictions(pairing_dir)
    if not preds:
        print(f"  [skip] no predictions in {pairing_dir}")
        return None
    pred = preds.get(method) or next(iter(preds.values()))
    used = method if method in preds else next(iter(preds))
    t = np.asarray(pred["time"], dtype=float)

    avail = [(k, dof, lbl) for k, dof, lbl in PANELS if k in pred]
    fig, axes = plt.subplots(len(avail), 1, figsize=(9, 3.0 * len(avail)), sharex=True)
    axes = np.atleast_1d(axes)
    for ax, (key, dof, title) in zip(axes, avail):
        v = np.asarray(pred[key], dtype=float)
        tt = t[: v.size]
        # --- the fix: diverged = non-finite OR beyond the physical cap ---
        good = np.isfinite(v) & (np.abs(v) <= cap)
        excl = int((~good).sum())
        lo, hi = st.chi2.ppf([0.025, 0.975], dof)
        vplot = np.where(good, v, np.nan)          # break the line over diverged arcs
        ax.plot(tt, vplot, lw=0.8, label="NEES (diverged arcs excluded)")
        ax.axhline(dof, color="k", ls="-", lw=0.9, label="expected (= DoF)")
        ax.axhline(hi, color="r", ls="--", lw=0.9, label="95% bounds")
        ax.axhline(lo, color="r", ls="--", lw=0.9)
        kept = v[good]
        if kept.size:
            inside = float(np.mean((kept >= lo) & (kept <= hi)))
            # keep the y-axis on the physical range, not the overflow
            top = max(float(np.nanmax(kept)) * 1.1, hi * 1.5)
            if logy:
                ax.set_yscale("log"); ax.set_ylim(max(lo * 0.5, 1e-1), top)
            else:
                ax.set_ylim(0.0, top)
            ax.set_title(f"{title} - mean {kept.mean():.1f}, {inside:.0%} within bounds"
                         f"  ({excl} diverged samples excluded)", fontsize=10)
        ax.set_ylabel("NEES"); ax.grid(True, alpha=0.3)
    axes[0].legend(fontsize=8, loc="upper right")
    axes[-1].set_xlabel("Time [s]")
    out = pairing_dir.parent / "figures" / f"storm_nees_partitions_{pairing}_fixed.pdf"
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout(); fig.savefig(out, bbox_inches="tight"); plt.close(fig)
    print(f"  [ok] {storm_dir.name}/{pairing} [{used}] -> {out.name}")
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("storm_dirs", nargs="+", type=Path)
    ap.add_argument("--pairing", default="mismatched")
    ap.add_argument("--method", default="PINN+UKF+MEKF")
    ap.add_argument("--cap", type=float, default=1e4,
                    help="NEES above this is treated as a divergence (default 1e4).")
    ap.add_argument("--logy", action="store_true")
    a = ap.parse_args()
    for sd in a.storm_dirs:
        print(f"{sd}:")
        plot_one(sd, a.pairing, a.method, a.cap, a.logy)


if __name__ == "__main__":
    main()
