#!/bin/bash

# Ocean Shipping GA Optimization Runner
# Usage: ./run.sh [version] [show_plot]
# version: quick, medium, standard, full (default: quick)
# show_plot: true, false (default: true)

VERSION=${1:-quick}
SHOW_PLOT=${2:-true}

# Run the Python script
python3 run.py "$VERSION" "$SHOW_PLOT"