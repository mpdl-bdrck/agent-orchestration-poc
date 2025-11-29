#!/bin/bash
#
# Weekly Budget Forecast Tool
# ===========================
#
# Generates 12-week budget forecast reports (6 weeks past + 6 weeks future)
# showing weekly spend, budget allocation, and forecasted spend.
# Analyzes ALL campaigns across ALL accounts by default.
#
# Usage: ./run_weekly_budget_forecast.sh [account_id] [advertiser_filter]
# Examples:
#   ./run_weekly_budget_forecast.sh                                    # ALL campaigns across ALL accounts
#   ./run_weekly_budget_forecast.sh 17                                 # Account 17 campaigns only
#   ./run_weekly_budget_forecast.sh 17 "Lilly"                        # Account 17, Eli Lilly campaigns
#
# Options:
#   --account-id ID           # Optional account ID filter
#   --advertiser-filter NAME  # Optional advertiser filter (e.g., "Lilly")

set -e  # Exit on any error

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PATH="../venv"
ENV_FILE="../.env"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
print_header() {
    echo -e "${BLUE}$1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

# Parse arguments
ACCOUNT_ID=""
ADVERTISER_FILTER=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --account-id)
            ACCOUNT_ID="$2"
            shift
            shift
            ;;
        --advertiser-filter)
            ADVERTISER_FILTER="$2"
            shift
            shift
            ;;
        *)
            # Positional arguments: account_id, advertiser_filter
            if [ -z "$ACCOUNT_ID" ]; then
                ACCOUNT_ID="$1"
            elif [ -z "$ADVERTISER_FILTER" ]; then
                ADVERTISER_FILTER="$1"
            fi
            shift
            ;;
    esac
done

# Change to script directory
cd "$SCRIPT_DIR"

# Check for virtual environment
if [ -d "$VENV_PATH" ]; then
    print_header "Activating virtual environment..."
    source "$VENV_PATH/bin/activate"
else
    print_error "Virtual environment not found at $VENV_PATH"
    print_error "Please create a virtual environment first: python3 -m venv ../venv"
    exit 1
fi

# Load environment variables if .env exists
if [ -f "$ENV_FILE" ]; then
    print_header "Loading environment variables..."
    set -a
    source "$ENV_FILE"
    set +a
fi

# Build Python command
PYTHON_CMD="python3 src/weekly_budget_forecast_analysis.py"

if [ -n "$ACCOUNT_ID" ]; then
    PYTHON_CMD="$PYTHON_CMD --account-id $ACCOUNT_ID"
fi

if [ -n "$ADVERTISER_FILTER" ]; then
    PYTHON_CMD="$PYTHON_CMD --advertiser-filter \"$ADVERTISER_FILTER\""
fi

# Run the analysis
print_header "Running Weekly Budget Forecast Analysis..."
echo ""

eval $PYTHON_CMD

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    print_success "Weekly budget forecast completed successfully!"
else
    print_error "Weekly budget forecast failed with exit code $EXIT_CODE"
fi

exit $EXIT_CODE

