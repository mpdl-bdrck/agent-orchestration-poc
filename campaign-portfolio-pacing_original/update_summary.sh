#!/bin/bash
# Lightweight script to update only the Pacing dashboard

set -e  # Exit on any error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PATH="../venv"
ENV_FILE="../.env"

SPREADSHEET_ID="${SPREADSHEET_ID:-1syJFthysZXZKAyDiv-O-dDGawE7ZZqXyI08WmY4Pcoc}"
CAMPAIGN_START="${CAMPAIGN_START:-2025-11-01}"
CAMPAIGN_END="${CAMPAIGN_END:-2025-12-31}"
CAMPAIGN_BUDGET="${CAMPAIGN_BUDGET:-466000}"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --spreadsheet-id)
            SPREADSHEET_ID="$2"
            shift 2
            ;;
        --campaign-start)
            CAMPAIGN_START="$2"
            shift 2
            ;;
        --campaign-end)
            CAMPAIGN_END="$2"
            shift 2
            ;;
        --campaign-budget)
            CAMPAIGN_BUDGET="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Change to script directory
cd "$SCRIPT_DIR"

# Activate virtual environment
if [ -f "$VENV_PATH/bin/activate" ]; then
    echo "🔌 Activating virtual environment..."
    source "$VENV_PATH/bin/activate"
else
    echo "⚠️  Virtual environment not found at $VENV_PATH"
    exit 1
fi

# Load environment variables if .env exists
if [ -f "$ENV_FILE" ]; then
    echo "📋 Loading environment variables..."
    set -a  # Automatically export all variables
    source "$ENV_FILE"
    set +a
fi

# Run the update script
python3 update_summary_dashboard.py \
    --spreadsheet-id "$SPREADSHEET_ID" \
    --campaign-start "$CAMPAIGN_START" \
    --campaign-end "$CAMPAIGN_END" \
    --campaign-budget "$CAMPAIGN_BUDGET"

