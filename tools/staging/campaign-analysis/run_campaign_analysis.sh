#!/bin/bash
#
# Campaign Analysis Tool Runner
# ============================
# 
# Simple runner script for the rebuilt campaign analysis tool.
# Reuses proven infrastructure from deal analysis tool.
# 
# Usage: ./run_campaign_analysis.sh <campaign_id>
# Example: ./run_campaign_analysis.sh 89
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

print_header "🔍 Campaign Analysis Tool: $CAMPAIGN_ID"

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
if ! python -c "import psycopg2, boto3, requests" 2>/dev/null; then
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
               "REDSHIFT_CLUSTER_ID" "REDSHIFT_DATABASE" 
               "BIDSWITCH_USERNAME" "BIDSWITCH_PASSWORD" "DSP_SEAT_ID")

for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        print_error "Required environment variable not set: $var"
        exit 1
    fi
done

print_success "Environment configuration validated"

# Step 4: Campaign Analysis Execution
print_step "🚀 Step 4: Campaign Analysis Execution"

echo "📊 Executing campaign analysis for campaign: $CAMPAIGN_ID"
echo ""

# Run the analysis
cd "$SCRIPT_DIR"
python src/campaign_analyzer.py "$CAMPAIGN_ID"

# Check if analysis completed successfully
if [ $? -eq 0 ]; then
    echo ""
    print_success "Campaign analysis completed successfully!"
    
    # Show generated files
    echo ""
    echo -e "${BLUE}📁 Generated Files:${NC}"
    echo ""
    
    # List analysis reports
    if ls ../reports/campaign_${CAMPAIGN_ID}_analysis.json 1> /dev/null 2>&1; then
        echo -e "${GREEN}📊 Campaign Analysis Report:${NC}"
        for file in ../reports/campaign_${CAMPAIGN_ID}_analysis.json; do
            if [ -f "$file" ]; then
                size=$(stat -f%z "$file" 2>/dev/null || stat -c%s "$file" 2>/dev/null)
                date=$(stat -f%Sm -t "%b %d %H:%M" "$file" 2>/dev/null || stat -c%y "$file" 2>/dev/null | cut -d' ' -f1-2)
                echo "   📊 $file (${size} bytes, $date)"
            fi
        done
    else
        print_error "No analysis reports found"
    fi
    
else
    print_error "Campaign analysis failed"
    exit 1
fi

echo ""
print_header "🎉 Campaign Analysis Complete!"
