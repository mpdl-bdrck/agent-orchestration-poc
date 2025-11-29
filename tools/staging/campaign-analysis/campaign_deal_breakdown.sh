#!/bin/bash
#
# Campaign Deal Breakdown Script
# =============================
# 
# Analyzes the complex relationships between campaigns, line items, 
# curation packages, and deals to explain duplication in campaign analysis.
# 
# Usage: ./campaign_deal_breakdown.sh <campaign_id>
# Example: ./campaign_deal_breakdown.sh 89
#

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
    echo "================================================="
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Validate input
if [ $# -ne 1 ]; then
    echo "Usage: $0 <campaign_id>"
    echo "Example: $0 89"
    exit 1
fi

CAMPAIGN_ID="$1"

# Validate campaign ID is numeric
if ! [[ "$CAMPAIGN_ID" =~ ^[0-9]+$ ]]; then
    print_error "Campaign ID must be numeric. Got: $CAMPAIGN_ID"
    exit 1
fi

print_header "🔍 Campaign Deal Breakdown: $CAMPAIGN_ID"

# Check if virtual environment exists
if [ ! -d "$VENV_PATH" ]; then
    print_error "Virtual environment not found at $VENV_PATH"
    exit 1
fi

echo "🔌 Activating virtual environment..."
source "$VENV_PATH/bin/activate"

echo "📦 Checking required packages..."
if ! python -c "import psycopg2, boto3, requests" 2>/dev/null; then
    print_error "Required packages not installed in virtual environment"
    echo "Please run from tools/ directory:"
    echo "  source venv/bin/activate"
    echo "  pip install -r requirements.txt"
    exit 1
fi

# Check environment file
if [ ! -f "$ENV_FILE" ]; then
    print_error "Environment file not found: $ENV_FILE"
    exit 1
fi

# Load environment variables
set -a  # Automatically export all variables
source "$ENV_FILE"
set +a

print_success "Environment loaded"

# Run the analysis
cd "$SCRIPT_DIR"
python src/campaign_deal_breakdown.py "$CAMPAIGN_ID"

# Check if analysis completed successfully
if [ $? -eq 0 ]; then
    echo ""
    print_success "Campaign deal breakdown completed!"
    
    # Show generated files
    echo ""
    echo -e "${BLUE}📁 Generated Files:${NC}"
    
    if ls ../reports/campaign_${CAMPAIGN_ID}_deal_breakdown.json 1> /dev/null 2>&1; then
        echo -e "${GREEN}📊 Deal Breakdown Report:${NC}"
        for file in ../reports/campaign_${CAMPAIGN_ID}_deal_breakdown.json; do
            if [ -f "$file" ]; then
                size=$(stat -f%z "$file" 2>/dev/null || stat -c%s "$file" 2>/dev/null)
                date=$(stat -f%Sm -t "%b %d %H:%M" "$file" 2>/dev/null || stat -c%y "$file" 2>/dev/null | cut -d' ' -f1-2)
                echo "   📊 $file (${size} bytes, $date)"
            fi
        done
    fi
else
    print_error "Campaign deal breakdown failed"
    exit 1
fi
