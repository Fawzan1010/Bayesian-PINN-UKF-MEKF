#!/usr/bin/env bash
# Run the two ADDITIONAL storm epochs (Jun + Dec 2015) and archive all three.
# Reuses the already-trained pinn.pt / transformer.pt in outputs/models/ --
# NOTHING retrains and the rest of the pipeline (synth/train/evaluate/plot/
# ablate) is NOT touched. Only `--mode storm` runs.
set -euo pipefail
cd "$(dirname "$0")/.."          # -> project root

# 0. Preserve the existing 17 Mar 2015 run (the V8 result) if not already saved.
if [ -d outputs/storm ] && [ ! -d outputs/storm_2015-03-17 ]; then
  echo ">> archiving existing March run -> outputs/storm_2015-03-17"
  mv outputs/storm outputs/storm_2015-03-17
fi

# 1. June epoch
echo ">> June 2015 storm"
python main.py --mode storm --config configs/storm_june2015.yaml
rm -rf outputs/storm_2015-06-22 && mv outputs/storm outputs/storm_2015-06-22

# 2. December epoch
echo ">> December 2015 storm"
python main.py --mode storm --config configs/storm_dec2015.yaml
rm -rf outputs/storm_2015-12-20 && mv outputs/storm outputs/storm_2015-12-20

echo ">> done. archives:"
echo "   outputs/storm_2015-03-17  (Dst -234)"
echo "   outputs/storm_2015-06-22  (Dst -198)"
echo "   outputs/storm_2015-12-20  (Dst -166)"
