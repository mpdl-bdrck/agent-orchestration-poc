#!/bin/bash
#
# Client Billing Analysis Tool
# ============================
#
# Generates client billing reports from campaign data with deal/marketplace split
# Creates comprehensive billing rollups and publishes to Google Sheets
# Defaults to Tricoast Media LLC (account ID 17) if no account specified
#
# Usage: ./run_client_billing.sh [account_id] [options]
# Examples:
#   ./run_client_billing.sh                                    # Account 17, Nov 1st to today (defaults, PST timezone)
#   ./run_client_billing.sh 17                                 # Account 17, Nov 1st to today (PST timezone)
#   ./run_client_billing.sh 17 --publish-sheets               # + Publish to Google Sheets
#   ./run_client_billing.sh 17 --start-date 2025-11-01 --end-date 2025-11-15  # Custom date range
#   ./run_client_billing.sh 17 --start-date 2025-11-01 --end-date 2025-11-30 --timezone UTC --publish-sheets  # Override to UTC
#
# Options:
#   --start-date YYYY-MM-DD    # Start date for analysis (default: 2025-11-01)
#   --end-date YYYY-MM-DD      # End date for analysis (default: today)
#   --timezone TZ              # Override timezone (e.g., "UTC", "PST", "America/Los_Angeles")
#   --publish-sheets           # Publish billing data to Google Sheets
#
# Default: ./run_client_billing.sh (uses account 17, Nov 1st to today, no Sheets publishing)
# Timezone: Uses client config default (PST for Tricoast) unless --timezone is specified

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

print_step() {
    echo -e "\n${YELLOW}$1${NC}"
    echo "================================="
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Parse command line arguments
PUBLISH_SHEETS=false
START_DATE=""
END_DATE=""
TIMEZONE=""
ACCOUNT_ID=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --publish-sheets)
            PUBLISH_SHEETS=true
            shift
            ;;
        --start-date)
            START_DATE="$2"
            shift
            shift
            ;;
        --end-date)
            END_DATE="$2"
            shift
            shift
            ;;
        --timezone)
            TIMEZONE="$2"
            shift
            shift
            ;;
        *)
            if [ -z "$ACCOUNT_ID" ]; then
                ACCOUNT_ID="$1"
            fi
            shift
            ;;
    esac
done

# Set defaults if not provided
ACCOUNT_ID="${ACCOUNT_ID:-17}"  # Default to Tricoast Media LLC

# Validate account ID is numeric
if ! [[ "$ACCOUNT_ID" =~ ^[0-9]+$ ]]; then
    print_error "Account ID must be numeric. Got: $ACCOUNT_ID"
    exit 1
fi

print_header "💰 Client Billing Analysis: Account $ACCOUNT_ID"

if [ -n "$START_DATE" ] || [ -n "$END_DATE" ]; then
    echo "📅 Date Range: ${START_DATE:-2025-11-01} to ${END_DATE:-Today}"
else
    echo "📅 Date Range: 2025-11-01 to Today (default)"
fi

if [ "$PUBLISH_SHEETS" = true ]; then
    echo "📊 Google Sheets publishing: ENABLED"
else
    echo "📊 Google Sheets publishing: DISABLED"
fi

if [ -n "$TIMEZONE" ]; then
    echo "🌍 Timezone override: $TIMEZONE"
fi

# Step 1: Check AWS SSO Authentication
print_step "🔐 Step 1: AWS SSO Authentication"
echo "Checking AWS SSO login status..."

if aws sts get-caller-identity --profile bedrock &> /dev/null; then
    print_success "AWS SSO authentication successful"
else
    echo "🔑 AWS SSO login required..."
    echo "Running: aws sso login --profile bedrock"
    aws sso login --profile bedrock

    # Verify login was successful
    if ! aws sts get-caller-identity --profile bedrock &> /dev/null; then
        print_error "AWS SSO authentication failed"
        exit 1
    fi
    print_success "AWS SSO authentication successful"
fi

# Step 2: Python Environment Setup
print_step "🐍 Step 2: Python Environment Setup"

# Check if virtual environment exists
if [ ! -d "$VENV_PATH" ]; then
    print_error "Virtual environment not found at $VENV_PATH"
    echo "Please set up the virtual environment first"
    exit 1
fi

echo "🔌 Activating virtual environment ($VENV_PATH)..."
source "$VENV_PATH/bin/activate"

echo "📦 Checking required packages..."
if ! python -c "import psycopg2, boto3, requests, pandas, pytz" 2>/dev/null; then
    print_error "Required packages not installed in virtual environment"
    echo "Please run from tools/ directory:"
    echo "  source venv/bin/activate"
    echo "  pip install -r requirements.txt"
    exit 1
fi

print_success "Python environment ready"

# Step 3: Environment Configuration
print_step "🔧 Step 3: Environment Configuration"

echo "📋 Loading environment variables from $ENV_FILE..."
if [ ! -f "$ENV_FILE" ]; then
    print_error "Environment file not found: $ENV_FILE"
    exit 1
fi

# Load environment variables
set -a  # Automatically export all variables
source "$ENV_FILE"
set +a

print_success "Environment variables loaded"

echo "🔍 Validating environment configuration..."
required_vars=("POSTGRES_HOST" "POSTGRES_DB" "POSTGRES_USER" "POSTGRES_PASSWORD"
               "REDSHIFT_CLUSTER_ID" "REDSHIFT_DATABASE")

for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        print_error "Required environment variable not set: $var"
        exit 1
    fi
done

print_success "Environment configuration validated"

# Step 4: Run Client Billing Analysis
print_step "🚀 Step 4: Running Client Billing Analysis"

echo "💰 Executing billing analysis for account: $ACCOUNT_ID"
echo ""

# Run the analysis
cd "$SCRIPT_DIR"
cmd="python -m src.client_billing_analysis --account-id $ACCOUNT_ID"

if [ -n "$START_DATE" ]; then
    cmd="$cmd --start-date $START_DATE"
fi

if [ -n "$END_DATE" ]; then
    cmd="$cmd --end-date $END_DATE"
fi

if [ -n "$TIMEZONE" ]; then
    cmd="$cmd --timezone $TIMEZONE"
fi

if [ "$PUBLISH_SHEETS" = true ]; then
    cmd="$cmd --publish-sheets"
fi

echo "🔍 Running: $cmd"
echo ""
$cmd

# Check if analysis completed successfully
if [ $? -eq 0 ]; then
    echo ""
    print_success "Billing analysis completed successfully!"

    # Show generated files if any
    echo ""
    echo -e "${BLUE}📁 Analysis Complete:${NC}"
    echo -e "${GREEN}💰 Billing rollup generated for account $ACCOUNT_ID${NC}"

else
    print_error "Billing analysis failed"
    exit 1
fi

echo ""
print_header "🎉 Client Billing Analysis Complete!"

