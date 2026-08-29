#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# TOS Automation — Run Script
# Usage:
#   ./run.sh          → runs both iterations sequentially
#   ./run.sh iter1    → runs Iteration 1 only (UPI ID)
#   ./run.sh iter2    → runs Iteration 2 only (QR Upload)
#   ./run.sh setup    → install dependencies only
# ─────────────────────────────────────────────────────────────

set -e

ITER=${1:-"all"}

echo "======================================================"
echo "  TOS Automation Framework"
echo "  Mode: $ITER"
echo "======================================================"

# Install dependencies
if [ "$ITER" = "setup" ]; then
    pip install -r requirements.txt
    echo "Dependencies installed."
    exit 0
fi

# Validate Appium is running
check_appium() {
    local port=$1
    local name=$2
    if ! curl -s "http://localhost:$port/status" > /dev/null 2>&1; then
        echo "ERROR: Appium ($name) not running on port $port"
        echo "Start with: appium --port $port"
        exit 1
    fi
    echo "✅ Appium $name: OK (port $port)"
}

check_appium 4723 "User"
check_appium 4724 "Approver"

# Run tests
case $ITER in
    "iter1")
        echo "Running Iteration 1 — UPI ID Flow"
        pytest tests/iteration_1/ -v --alluredir=reports/allure-results/
        ;;
    "iter2")
        echo "Running Iteration 2 — QR Upload Flow"
        pytest tests/iteration_2/ -v --alluredir=reports/allure-results/
        ;;
    "all")
        echo "Running all iterations sequentially..."
        # Iteration 1 first — state must exist before Iteration 2
        pytest tests/iteration_1/ tests/iteration_2/ \
               -v \
               --alluredir=reports/allure-results/ \
               --html=reports/report.html
        ;;
    *)
        echo "Unknown option: $ITER"
        exit 1
        ;;
esac

echo ""
echo "======================================================"
echo "  Run complete. Report: reports/report.html"
echo "======================================================"
