#!/bin/bash
#
# Campaign Portfolio Pacing Tool
# ===============================
#
# Analyzes campaign spend, impressions, and provides portfolio-level pacing intelligence
# Generates comprehensive rollup reports and creates actionable pacing dashboards
# Defaults to Tricoast Media LLC (account ID 17) with Eli Lilly campaigns if no parameters
#
# Usage: ./run_campaign_portfolio_pacing.sh [account_id] [advertiser_filter] [options]
# Examples:
#   ./run_campaign_portfolio_pacing.sh                                    # Account 17, Eli Lilly campaigns, publishes to Sheets (default)
#   ./run_campaign_portfolio_pacing.sh 17                                 # Account 17, Eli Lilly campaigns, publishes to Sheets
#   ./run_campaign_portfolio_pacing.sh 17 "Lilly"                        # Account 17, Eli Lilly campaigns, publishes to Sheets
#   ./run_campaign_portfolio_pacing.sh 17 "Lilly" --timezone UTC         # Override timezone to UTC
#   ./run_campaign_portfolio_pacing.sh 17 "Lilly" --campaign-start 2025-11-01 --campaign-end 2025-12-31 --campaign-budget 466000  # + Create pacing dashboard
#   ./run_campaign_portfolio_pacing.sh 9 "OtherBrand" --start-date 2025-11-01 --end-date 2025-11-15  # Custom date range
#   ./run_campaign_portfolio_pacing.sh 17 "Lilly" --no-publish-sheets    # Skip publishing to Sheets
#   ./run_campaign_portfolio_pacing.sh --extract-formulas "Portfolio DAILY"  # Extract formulas from specified worksheet
#
# Options:
#   --start-date YYYY-MM-DD    # Start date for analysis (default: all available data)
#   --end-date YYYY-MM-DD      # End date for analysis (default: all available data)
#   --timezone TZ              # Override timezone (e.g., "UTC", "PST", "America/Los_Angeles")
#   --publish-sheets           # Publish comprehensive rollups to Google Sheets (6 worksheets) - DEFAULT BEHAVIOR
#   --no-publish-sheets        # Skip publishing to Google Sheets
#   --campaign-start DATE      # Campaign start date (YYYY-MM-DD) for pacing calculations
#   --campaign-end DATE        # Campaign end date (YYYY-MM-DD) for pacing calculations
#   --campaign-budget AMOUNT   # Total campaign budget for pacing analysis
#   --extract-formulas SHEET   # Extract formulas and analyze user requirements from specified worksheet
#
# Default: ./run_campaign_portfolio_pacing.sh (uses account 17 with Eli Lilly, all available data, publishes to Sheets)

set -e  # Exit on any error

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PATH="../venv"
ENV_FILE="../.env"
REPORTS_DIR="../reports"

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
PUBLISH_SHEETS=true  # Default to publishing sheets
CREATE_SUMMARY=false
ADVANCED_DASHBOARD=false
EXTRACT_FORMULAS=false
EXTRACT_SHEET_NAME=""
TEST_SHEETS_DIR=""
START_DATE=""
END_DATE=""
TIMEZONE=""
ACCOUNT_ID=""
ADVERTISER_FILTER=""
CAMPAIGN_START=""
CAMPAIGN_END=""
CAMPAIGN_BUDGET=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --publish-sheets)
            PUBLISH_SHEETS=true
            shift
            ;;
        --no-publish-sheets)
            PUBLISH_SHEETS=false
            shift
            ;;
        --create-summary)
            CREATE_SUMMARY=true
            shift
            ;;
        --advanced-dashboard)
            ADVANCED_DASHBOARD=true
            shift
            ;;
        --extract-formulas)
            EXTRACT_FORMULAS=true
            EXTRACT_SHEET_NAME="$2"
            shift
            shift
            ;;
        --campaign-start)
            CAMPAIGN_START="$2"
            shift
            shift
            ;;
        --campaign-end)
            CAMPAIGN_END="$2"
            shift
            shift
            ;;
        --campaign-budget)
            CAMPAIGN_BUDGET="$2"
            shift
            shift
            ;;
        --test-sheets)
            TEST_SHEETS_DIR="$2"
            shift
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
            elif [ -z "$ADVERTISER_FILTER" ]; then
                ADVERTISER_FILTER="$1"
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

if [ -n "$ADVERTISER_FILTER" ]; then
    print_header "🔍 Comprehensive Campaign Analysis: $ACCOUNT_ID ($ADVERTISER_FILTER)"
else
    print_header "🔍 Comprehensive Campaign Analysis: $ACCOUNT_ID (Eli Lilly)"
fi

if [ -n "$START_DATE" ] || [ -n "$END_DATE" ]; then
    echo "📅 Date Range: ${START_DATE:-2025-11-01} to ${END_DATE:-Today}"
else
    echo "📅 Date Range: All available data (no date filter)"
fi

if [ -n "$TIMEZONE" ]; then
    echo "🌍 Timezone override: $TIMEZONE"
fi

if [ "$PUBLISH_SHEETS" = true ]; then
    echo "📊 Google Sheets publishing: ENABLED (6 worksheets) [DEFAULT]"
    if [ "$CREATE_SUMMARY" = true ]; then
        echo "📈 Summary dashboard creation: ENABLED (33+ live formulas)"
        if [ "$ADVANCED_DASHBOARD" = true ]; then
            echo "🧠 Advanced dashboard creation: ENABLED (trend analysis, risk assessment, forecasting)"
        else
            echo "🧠 Advanced dashboard creation: DISABLED"
        fi
    else
        echo "📈 Summary dashboard creation: DISABLED"
    fi
else
    echo "📊 Google Sheets publishing: DISABLED"
fi

if [ -n "$TEST_SHEETS_DIR" ]; then
    print_header "🧪 Google Sheets Test Publishing: $TEST_SHEETS_DIR"
    echo "📊 Publishing existing rollup CSVs to Google Sheets (6 worksheets)"
fi

if [ "$EXTRACT_FORMULAS" = true ]; then
    print_header "🔍 Formula Extraction: $EXTRACT_SHEET_NAME"
    echo "📝 Extracting formulas and analyzing user requirements from worksheet"
fi

if [ -n "$CAMPAIGN_START" ] || [ -n "$CAMPAIGN_END" ] || [ -n "$CAMPAIGN_BUDGET" ]; then
    print_header "📊 Campaign Pacing Configuration"
    if [ -n "$CAMPAIGN_START" ]; then
        echo "📅 Start Date: $CAMPAIGN_START"
    fi
    if [ -n "$CAMPAIGN_END" ]; then
        echo "📅 End Date: $CAMPAIGN_END"
    fi
    if [ -n "$CAMPAIGN_BUDGET" ]; then
        echo "💰 Budget: $CAMPAIGN_BUDGET"
    fi
    echo "🎯 Pacing dashboard will be created/updated"
fi

# Validate arguments
if [ "$CREATE_SUMMARY" = true ] && [ "$PUBLISH_SHEETS" = false ]; then
    print_error "--create-summary requires --publish-sheets to be enabled (or use default behavior)"
    exit 1
fi

if [ "$ADVANCED_DASHBOARD" = true ] && [ "$CREATE_SUMMARY" = false ]; then
    print_error "--advanced-dashboard requires --create-summary to be enabled"
    exit 1
fi

if [ "$EXTRACT_FORMULAS" = true ] && [ -z "$EXTRACT_SHEET_NAME" ]; then
    print_error "--extract-formulas requires a worksheet name as argument"
    exit 1
fi

# Step 0: Clean Reports Folder (skip if testing sheets)
if [ -z "$TEST_SHEETS_DIR" ]; then
print_step "🧹 Step 0: Cleaning Reports Folder"

REPORTS_PATH="$SCRIPT_DIR/$REPORTS_DIR"

if [ -d "$REPORTS_PATH" ]; then
    # Count analysis report files before deletion
    file_count=$(find "$REPORTS_PATH" -type f \( -name "account_*_campaigns_*.csv" -o -name "account_*_line_items_*.json" -o -name "account_*_line_items_*.csv" \) 2>/dev/null | wc -l | tr -d ' ')

    if [ "$file_count" -gt 0 ]; then
        echo "🗑️  Removing $file_count existing analysis report file(s)..."
        find "$REPORTS_PATH" -type f \( -name "account_*_campaigns_*.csv" -o -name "account_*_line_items_*.json" -o -name "account_*_line_items_*.csv" \) -delete
        print_success "Reports folder cleaned ($file_count file(s) removed)"
    else
        echo "📁 No analysis reports to clean"
        print_success "Reports folder ready"
    fi
else
    echo "📁 Creating reports directory..."
    mkdir -p "$REPORTS_PATH"
    print_success "Reports directory created"
    fi
fi

# Step 1: Check AWS SSO Authentication (skip if testing sheets)
if [ -z "$TEST_SHEETS_DIR" ]; then
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
fi

# Step 2: Python Environment Setup (skip if testing sheets)
if [ -z "$TEST_SHEETS_DIR" ]; then
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
if ! python -c "import psycopg2, boto3, requests" 2>/dev/null; then
    print_error "Required packages not installed in virtual environment"
    echo "Please run from tools/ directory:"
    echo "  source venv/bin/activate"
    echo "  pip install -r requirements.txt"
    exit 1
fi

print_success "Python environment ready"
fi

# Step 3: Environment Configuration (skip if testing sheets)
if [ -z "$TEST_SHEETS_DIR" ]; then
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
fi

# Step 4: Run Formula Extraction, Test Sheets Publishing, or Campaign Analysis
if [ "$EXTRACT_FORMULAS" = true ]; then
    print_step "🚀 Step 4: Running Formula Extraction"

    echo "📝 Extracting formulas from worksheet: $EXTRACT_SHEET_NAME"
    echo ""

    # Run the formula extraction
    cd "$SCRIPT_DIR"
    cmd="python extract_portfolio_formulas.py \"$EXTRACT_SHEET_NAME\""
elif [ -n "$TEST_SHEETS_DIR" ]; then
    print_step "🚀 Step 4: Running Google Sheets Test Publishing"

    echo "📊 Publishing existing rollup CSVs from: $TEST_SHEETS_DIR"
    echo ""

    # Run the test publishing script
    cd "$SCRIPT_DIR"
    cmd="python publish_csvs_to_sheets.py \"$TEST_SHEETS_DIR\""
else
    print_step "🚀 Step 4: Running Campaign Spend Analysis"

echo "📊 Executing spend analysis for account: $ACCOUNT_ID"
echo ""

# Run the analysis
cd "$SCRIPT_DIR"
    cmd="python -m src.campaign_spend_analysis --account-id $ACCOUNT_ID"

if [ -n "$ADVERTISER_FILTER" ]; then
        cmd="$cmd --advertiser-filter $ADVERTISER_FILTER"
    fi

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

    if [ "$CREATE_SUMMARY" = true ]; then
        cmd="$cmd --create-summary"
    fi

    if [ "$ADVANCED_DASHBOARD" = true ]; then
        cmd="$cmd --advanced-dashboard"
    fi

    # Always pass campaign parameters if provided (they enable pacing dashboard)
    if [ -n "$CAMPAIGN_START" ]; then
        cmd="$cmd --campaign-start $CAMPAIGN_START"
    fi

    if [ -n "$CAMPAIGN_END" ]; then
        cmd="$cmd --campaign-end $CAMPAIGN_END"
    fi

    if [ -n "$CAMPAIGN_BUDGET" ]; then
        cmd="$cmd --campaign-budget $CAMPAIGN_BUDGET"
    fi
fi

echo "🔍 Running: $cmd"
echo ""
$cmd

# Check if analysis completed successfully
if [ $? -eq 0 ]; then
    echo ""
    print_success "Analysis completed successfully!"

    # Show generated CSV files
    echo ""
    echo -e "${BLUE}📁 Generated Files:${NC}"
    echo ""

    # Show rollup CSV reports (flat structure in reports/)
    rollup_files=(
        "../reports/line_items_daily.csv"
        "../reports/line_items_total.csv"
        "../reports/campaigns_daily.csv"
        "../reports/campaigns_total.csv"
        "../reports/portfolio_daily.csv"
        "../reports/portfolio_total.csv"
    )
    
    found_files=0
    for file in "${rollup_files[@]}"; do
        if [ -f "$file" ]; then
            found_files=$((found_files + 1))
        fi
    done
    
    if [ $found_files -gt 0 ]; then
        echo -e "${GREEN}📊 Rollup CSV Reports:${NC}"
        for file in "${rollup_files[@]}"; do
            if [ -f "$file" ]; then
                filename=$(basename "$file")
                size=$(stat -f%z "$file" 2>/dev/null || stat -c%s "$file" 2>/dev/null)
                date=$(stat -f%Sm -t "%b %d %H:%M" "$file" 2>/dev/null || stat -c%y "$file" 2>/dev/null | cut -d' ' -f1-2)
                echo "   📊 $filename (${size} bytes, $date)"
            fi
        done
    else
        print_error "No CSV reports found"
    fi

else
    print_error "Analysis failed"
    exit 1
fi

echo ""
print_header "🎉 Campaign Spend Analysis Complete!"

