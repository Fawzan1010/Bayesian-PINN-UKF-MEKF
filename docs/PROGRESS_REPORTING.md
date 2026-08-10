# Modification report — progress reporting and `ablate-env` removal

Scope: console progress reporting across the repository, a seven-stage
pipeline driver, and removal of the obsolete `ablate-env` mode.
No algorithm, equation, numerical method, seed, dataset, hyperparameter,
loss, model, evaluation rule, filename or directory was changed.

---

## 1. Files modified

| File | Change |
|------|--------|
| `src/utils/progress.py` | **New.** All progress/reporting helpers. |
| `main.py` | Rewritten as a seven-stage driver; `ablate-env` removed. |
| `configs/default.yaml` | Removed `ablation.conditions`, `ablation.environment_trajectories`. |
| `requirements.txt` | Added `tqdm>=4.65`. |
| `src/dynamics/simulator.py` | Progress bars for trajectory generation, propagation, dataset writing. |
| `src/evaluation/pipeline.py` | Split-loading bar; step messages for synth and train. |
| `src/pinn/dataset.py` | Bar over residual-window construction. |
| `src/pinn/train.py` | Epoch bar with live loss; nested batch bars. |
| `src/models/train.py` | Same, plus sequence-window construction bar. |
| `src/evaluation/experiments.py` | Method/trajectory bars; runtime-repeat bar; opt-in timestep bars. |
| `src/evaluation/theory.py` | Bars for all four analyses; step messages. |
| `src/visualization/plots.py` | Figure-group progress with category labels. |
| `src/evaluation/storm_experiment.py` | Nested pairing/method/trajectory/timestep bars. |
| `src/evaluation/ablation.py` | Configuration/seed/method bars; **`ablate-env` code removed**. |
| `tests/test_ablation.py` | Removed the test covering the deleted `CONDITIONS` table. |
| `README.md`, `docs/CHANGES.md` | Documented the seven stages. |

---

## 2. `ablate-env` removal — complete

Deleted:

- `main.py`: the `ablate-env` argparse choice, the `{'ablate', 'ablate-env'}`
  branch, and the `run_environment_ablation` import.
- `src/evaluation/ablation.py`: `run_environment_ablation()`, the `CONDITIONS`
  truth/filter pairing table, `_plot_environment()` (its only caller), and the
  Tier A / Tier B framing in the module docstring.
- `configs/default.yaml`: the `conditions` and `environment_trajectories` keys.
- `tests/test_ablation.py`: `test_conditions_cover_the_meaningful_pairings`,
  which asserted on the deleted table.

A repository-wide search for `ablate-env`, `ablate_env`,
`run_environment_ablation`, `CONDITIONS`, `_plot_environment`,
`environment_trajectories` and `ablation_environment` returns **no matches**.
No duplicate or redundant implementation was left behind.

Normal ablation (`run_ablation`, Tier A) is untouched. Supported modes are
exactly: `synth`, `train`, `evaluate`, `plot`, `theory`, `storm`, `ablate`,
`all` — and no others.

---

## 3. Pipeline stages

| Stage | Mode | Reports |
|-------|------|---------|
| 1/7 | `synth`    | trajectories, propagation, noise, dataset writing |
| 2/7 | `train`    | epochs, mini-batches, per-epoch loss, per model |
| 3/7 | `evaluate` | methods, trajectories, runtime repeats |
| 4/7 | `theory`   | four analyses, trajectories, Jacobian/matrix loops |
| 5/7 | `plot`     | figure groups with category labels |
| 6/7 | `storm`    | pairings, methods, trajectories, timesteps |
| 7/7 | `ablate`   | configurations, seeds, training, methods, figures |

Program start prints a title banner with config path, mode and output
directory. Each stage prints a `Stage i/7` header and a
`Completed successfully. / Elapsed Time: HH:MM:SS` footer. The run ends with a
`PIPELINE COMPLETE` summary (stages completed, total runtime, output path).

**Behavioural note:** `--mode all` previously ran five stages
(synth → train → evaluate → plot → theory) and never storm or ablate. Per the
seven-stage specification it now runs all seven, which makes it substantially
slower. The execution order lives in the `STAGES` table at the top of
`main.py`; trimming it is a one-line edit.

Stage order is `theory` before `plot`, per the specification. This is safe:
`run_theory_analysis` only reads `outputs/predictions/` and writes
`theory_report.json`, which no plotting function consumes.

---

## 4. Progress bars added

Every bar uses one shared `bar_format` showing percentage, completed/total
iterations, elapsed time, ETA and rate.

**Data generation** — trajectories per split; propagation timesteps (sensor
noise is generated inside this loop); dataset file writing.
**Training** — PINN and Transformer epoch bars carrying `Epoch i/N` and live
train/val/best loss, with nested per-batch bars; dataset-window construction.
**Evaluation** — `Method i/11` bar; per-method trajectory bar; runtime-repeat bar.
**Theory** — trajectories, start points, Jacobian/matrix-product blocks,
per-method passes for consistency, bounded-error fit and Lyapunov drift.
**Plotting** — `Generating figure group i of N` with category labels
(Time series, Comparison, Publication, Distribution, Per-scenario,
Innovations, Consistency), plus nested bars for box plots, CI bars,
per-scenario figures and innovation traces.
**Storm** — pairings, `Method i/11`, trajectories, per-timestep bars, OMNI
sampling, ranking/significance/degradation tables.
**Ablation** — `Configuration i/N [axis=value] seed j/k`, per-config PINN
training, methods, trajectories, runtime repeats, figure axes.

### Deliberate restraint

- **Timed regions carry zero bar overhead.** Per-timestep bars in the three
  estimator runners are opt-in (`show_progress=False` default). The runtime
  benchmark and the ablation runtime pass never enable them, and their bars sit
  on the outer repeat loop, outside every `perf_counter` window.
- **Tiny loops are not wrapped.** `PROGRESS_MIN_STEPS = 1000` suppresses
  per-timestep bars below that length, so the sub-second 240-step benchmark
  horizon stays clean while the multi-thousand-step storm arcs report properly.
- **No per-iteration `print`.** Existing prints were kept or moved to
  `tqdm.write` so they do not corrupt a live bar.
- Bars are written to **stderr**, so stdout and every saved artifact are
  unaffected.

---

## 5. Error handling

Exceptions are never suppressed. Each stage runs inside a context manager that,
on failure, prints `FAILED during Stage i/7: <NAME>` plus elapsed time, then
re-raises the original exception with its traceback intact.

---

## 6. Verification — numerical results unchanged

The unmodified project and the modified project were run end to end from the
same reduced config on the same machine, and their outputs compared by SHA-256.

**42 of 42 deterministic scientific artifacts are bit-identical**, including:

- `data/{train,val,test}.npz`
- `models/pinn.pt`, `models/transformer.pt`
- all 11 `predictions/*.npz` and all 11 `storm/mismatched/predictions/*.npz`
- `tables/metrics_summary.{csv,tex}`, `metrics_per_trial.csv`,
  `metrics_per_scenario.csv`, `metric_rankings.{csv,tex}`
- `results.json`, `theory_report.json`, `storm/storm_report.json`
- `storm/tables/storm_{metrics_per_trial,metrics_summary,rankings}_*.csv`
- `tables/ablation_results.csv` and all six retrained ablation checkpoints

Remaining differences are non-deterministic or environment fields only:

| Artifact | Sole difference |
|----------|-----------------|
| 42 of 46 PDFs | embedded PDF creation timestamp; byte-identical once stripped |
| 4 runtime PDFs | plot measured wall-clock runtime |
| `metadata.json` | the `output_dir` path (differs because the two runs wrote to different directories) |
| `*_training_log.json` | `training_wall_time_s` |
| `runtime_breakdown.{csv,tex}`, `runtime_repeats.csv` | measured timing and memory columns |

Also verified: all modules import cleanly; `python -m compileall` passes;
`--mode ablate-env` is rejected by argparse; the test suite passes (72 tests,
down from 73 solely because of the deleted `CONDITIONS` test).

### One regression found and fixed during verification

The first implementation imported `from tqdm.auto import tqdm`. The `auto`
variant pulls in notebook/ipywidgets machinery that **perturbs the global torch
RNG stream**, which reshuffled `DataLoader` batch order and changed the trained
weights and every downstream learned-method result. This was caught by the
A/B comparison, isolated by bisection, and fixed by importing the plain console
`tqdm`. A comment in `src/utils/progress.py` records why `tqdm.auto` must not
be reintroduced. All results above are from the fixed version.

---

## 7. Pre-existing issue (not introduced, not fixed)

`--mode ablate` crashes at `src/evaluation/ablation.py:264`:

```
IndexError: Column(s) [...] already selected
```

from `df.groupby([...])[METRIC_COLUMNS].agg(["mean", "std"])` under current
pandas. **This reproduces identically in the unmodified project at the same
line**, so it is pre-existing and unrelated to these changes. It was left alone
because fixing it would mean changing code outside the requested scope. Note
that `ablation_results.csv` is written before the crash; `ablation_summary.csv`
and the ablation figures are not.
