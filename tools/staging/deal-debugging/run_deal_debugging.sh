#!/bin/bash

# BidSwitch Deal Debugging Tool - Simplified
# ===========================================
#
# Debugs a specific BidSwitch deal ID.
# Simplified version focused only on deal debugging.
#
# Usage: ./run_deal_debugging.sh <deal_id>
# Example: ./run_deal_debugging.sh 549644393850112493

set -e  # Exit on any error

# Check if deal ID is provided
if [ $# -eq 0 ]; then
    echo "❌ Usage: ./run_deal_debugging.sh <deal_id>"
    echo "   Example: ./run_deal_debugging.sh 549644393850112493"
    exit 1
fi

DEAL_ID="$1"

echo "🔍 BidSwitch Deal Debugging: $DEAL_ID"
echo "================================================="
echo ""

# Step 1: AWS SSO Authentication
echo "🔐 Step 1: AWS SSO Authentication"
echo "================================="
echo "Checking AWS SSO login status..."

# Check if AWS CLI is available
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI not found. Please install AWS CLI first:"
    echo "   https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html"
    exit 1
fi

# Check AWS SSO login status
if ! aws sts get-caller-identity --profile bedrock &> /dev/null; then
    echo "🔑 AWS SSO login required..."
    echo "Running: aws sso login --profile bedrock"
    aws sso login --profile bedrock
    
    # Verify login was successful
    if ! aws sts get-caller-identity --profile bedrock &> /dev/null; then
        echo "❌ AWS SSO login failed. Please check your configuration."
        exit 1
    fi
    echo "✅ AWS SSO authentication successful"
fi

echo "✅ AWS SSO authentication successful"

# Step 2: Virtual Environment Setup
echo ""
echo "🐍 Step 2: Python Environment Setup"
echo "==================================="

# Check if virtual environment exists (in tools root)
if [ ! -d "../venv" ]; then
    echo "❌ Virtual environment not found in tools/ directory."
    echo "Please run 'python3 -m venv venv' from tools/ directory first."
    exit 1
fi

# Activate virtual environment from tools root
echo "🔌 Activating virtual environment (../venv)..."
source ../venv/bin/activate

# Check if required packages are installed
echo "📦 Checking required packages..."
if ! python3 -c "import requests, psycopg2, boto3" &> /dev/null; then
    echo "❌ Required packages not installed in virtual environment"
    echo "Please run from tools/ directory:"
    echo "  source venv/bin/activate"
    echo "  pip install -r requirements.txt"
    exit 1
fi

echo "✅ Python environment ready"

# Step 3: Environment Variables
echo ""
echo "🔧 Step 3: Environment Configuration"
echo "===================================="

# Load environment variables from tools root
if [ -f "../.env" ]; then
    echo "📋 Loading environment variables from ../.env..."
    export $(grep -v '^#' ../.env | xargs)
    echo "✅ Environment variables loaded"
else
    echo "❌ .env file not found in tools/ directory."
    exit 1
fi

# Check critical environment variables
echo "🔍 Validating environment configuration..."
if [ -z "$BIDSWITCH_USERNAME" ] || [ -z "$BIDSWITCH_PASSWORD" ]; then
    echo "❌ Missing BidSwitch credentials"
    echo "   Please ensure BIDSWITCH_USERNAME and BIDSWITCH_PASSWORD are set in .env"
    exit 1
fi

echo "✅ Environment configuration validated"

# Step 4: Deal Debugging Execution
echo ""
echo "🚀 Step 4: Deal Debugging Execution"
echo "===================================="

# Create reports directory if it doesn't exist
mkdir -p reports

# Run the deal debugger
echo "📊 Executing enhanced deal debugging for deal: $DEAL_ID"
echo ""
python3 src/deal_debugger.py "$DEAL_ID"

# Check if debugging was successful
if [ $? -eq 0 ]; then
    echo ""
    echo "🎉 Deal Debugging Complete!"
    echo "================================================="
    echo ""
    echo "📁 Generated Files:"
    echo ""
    echo "📊 Deal Debugging Report:"
    ls -la ../reports/deal_${DEAL_ID}_analysis.json 2>/dev/null | awk '{print "   🔍 " $9 " (" $5 " bytes, " $6 " " $7 " " $8 ")"}'
    echo ""
else
    echo ""
    echo "❌ Debugging failed. Check the error messages above."
    echo ""
    echo "🔧 Troubleshooting tips:"
    echo "   1. Ensure AWS SSO login is active: aws sts get-caller-identity --profile bedrock"
    echo "   2. Check .env file has BidSwitch credentials"
    echo "   3. Verify deal ID is correct"
    echo "   4. Check BidSwitch API connectivity"
    echo ""
    exit 1
fi