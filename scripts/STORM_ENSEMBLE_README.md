# Storm ensemble + Figure 17 fix — what to run

Everything here reuses your already-trained `outputs/models/pinn.pt` and
`transformer.pt`. **Nothing retrains.** Only `--mode storm` runs; the
synth/train/evaluate/plot/ablate stages are untouched.

## The three storm epochs (all in your existing `omni2_2015.dat`)

| Epoch | Config | Window (UTC) | Dst min | ap climb |
|------|--------|--------------|---------|----------|
| 17 Mar 2015 (V8) | `configs/default.yaml` | 09:00–15:00 | −234 nT | 56→179 |
| 22–23 Jun 2015 | `configs/storm_june2015.yaml` | 22:00–04:00 | −198 nT | 56→179 |
| 20 Dec 2015 | `configs/storm_dec2015.yaml` | 17:00–23:00 | −166 nT | 94→111 |

No new OMNI download — the 2015 file already spans all three.

## Step 1 — permanently fix Figure 17 *before* running (item 2)

Edit `src/visualization/plots.py`, function `_plot_nees_partitions`. Replace:

```python
        finite = v[np.isfinite(v)]
        if finite.size:
            inside = float(np.mean((finite >= lo) & (finite <= hi)))
            ax.plot(t[: v.size], v, lw=0.8, label="NEES")
```

with a version that treats a diverged (huge-but-finite) NEES as excluded and
bounds the axis. The minimal change is the mask + the plotted array + ylim:

```python
        CAP = 1e4  # 97.5% chi2 bound for 24 DoF is ~39; >1e4 is divergence
        good = np.isfinite(v) & (np.abs(v) <= CAP)
        vplot = np.where(good, v, np.nan)      # break the line over diverged arcs
        ax.plot(t[: v.size], vplot, lw=0.8, label="NEES")
        finite = v[good]
        if finite.size:
            inside = float(np.mean((finite >= lo) & (finite <= hi)))
            ax.set_ylim(0.0, max(float(finite.max()) * 1.1, hi * 1.5))
```

(The original bug: `np.isfinite` alone lets ~1e154 through, so it entered the
trace and the y-axis while the caption said diverged channels were excluded.)

## Step 2 — run the two new epochs and archive all three

```bash
bash scripts/run_storm_epochs.sh
```

Produces `outputs/storm_2015-03-17`, `outputs/storm_2015-06-22`,
`outputs/storm_2015-12-20`.

## Step 3 — pool them into one transfer-study table (item 7)

```bash
python scripts/aggregate_storms.py           # globs outputs/storm_2015-*
```

Writes `outputs/storm_ensemble/transfer_ensemble_summary.csv` (per method,
mean ± std across the 3 storms) and prints a Markdown table. It ranks by
`|NEES_norm − 1|` — distance from the ideal 1.0 — which is the **item-1**
correction applied ensemble-wide (a NEES far below 1 is over-conservative, not
"best").

## Optional — regenerate Fig 17 for runs you already have, no rerun

If you don't want to re-run storm at all to fix the figure, rebuild it straight
from stored predictions:

```bash
python scripts/fix_fig17_nees.py outputs/storm_2015-03-17 \
       outputs/storm_2015-06-22 outputs/storm_2015-12-20
```

## Map to the professor's list

- **2 (Fig 17 overflow):** Step 1 patch, or `fix_fig17_nees.py`.
- **7 (more storm epochs):** Steps 2–3 (June + December added → 3 total).
- **1 (NEES "best-calibrated"):** `aggregate_storms.py` ranks by distance from 1.
- **3, 5, 6:** paper-text / table edits — no code.
- **4 (NIS accounting):** from `results.json` the numbers are fixed, not
  ambiguous: measurement vector nz = **20** nominal (18 + range/Doppler); the
  *effective* `nis_dof` = **19.2** (mean innovation size after measurement
  gating). Raw `nis_mean` ~ **31.4**, so `nis_normalized` ~ **1.64**. State
  nz = 20 / effective 19.2 once, then make Fig 11 (normalized), Table V (raw)
  and the text agree. Raw NIS ~31 is **not** "close to nominal": nominal for
  the raw statistic is 19.2, i.e. ~64% over-dispersed (normalized 1.64).
