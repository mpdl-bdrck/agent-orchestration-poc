#!/bin/bash
#
# Simple Google Sheets Publisher for Existing CSVs
# =================================================
#
# Publishes existing rollup CSV files to Google Sheets
#
# Usage: ./publish_sheets.sh /path/to/rollups/directory
# Example: ./publish_sheets.sh ../reports/rollups/17_20251118_221746

set -e  # Exit on any error

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PATH="../venv"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_header() {
    echo -e "${BLUE}$1${NC}"
    echo "================================================="
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check arguments
if [ "$#" -ne 1 ]; then
    print_error "Missing rollups directory path"
    echo "Usage: ./publish_sheets.sh /path/to/rollups/directory"
    echo "Example: ./publish_sheets.sh ../reports/rollups/17_20251118_221746"
    exit 1
fi

ROLLUPS_DIR="$1"

if [ ! -d "$ROLLUPS_DIR" ]; then
    print_error "Directory not found: $ROLLUPS_DIR"
    exit 1
fi

print_header "🚀 Google Sheets CSV Publisher"
echo "📂 Rollups directory: $ROLLUPS_DIR"
echo ""

# Step 1: Activate virtual environment
echo "🔌 Activating virtual environment..."
if [ ! -d "$VENV_PATH" ]; then
    print_error "Virtual environment not found at $VENV_PATH"
    exit 1
fi

cd "$SCRIPT_DIR"
source "$VENV_PATH/bin/activate"
print_success "Virtual environment activated"

# Step 2: Run the publishing script
echo ""
echo "📊 Publishing CSVs to Google Sheets..."
echo ""

python publish_csvs_to_sheets.py "$ROLLUPS_DIR"

RESULT=$?

if [ $RESULT -eq 0 ]; then
    echo ""
    print_success "Publishing complete!"
else
    echo ""
    print_error "Publishing failed"
    exit 1
fi

