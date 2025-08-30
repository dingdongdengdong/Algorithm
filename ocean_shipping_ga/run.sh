#!/bin/bash

# Ocean Shipping GA Optimization Runner
# Usage: ./run.sh [version] [show_plot] [save_report] [advanced_features]
# version: quick, medium, standard, full (default: quick)
# show_plot: true, false (default: true)
# save_report: true, false (default: true)
# advanced_features: true, false (default: false)

VERSION=${1:-quick}
SHOW_PLOT=${2:-true}
SAVE_REPORT=${3:-true}
ADVANCED_FEATURES=${4:-false}

echo "Ocean Shipping GA 실행 옵션:"
echo "  버전: $VERSION"
echo "  시각화: $SHOW_PLOT"
echo "  보고서 저장: $SAVE_REPORT"
echo "  고급 기능: $ADVANCED_FEATURES"
echo ""

# Run the Python script
python3 run.py "$VERSION" "$SHOW_PLOT" "$SAVE_REPORT" "$ADVANCED_FEATURES"