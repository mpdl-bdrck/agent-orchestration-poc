#!/bin/bash
# BidSwitch Active Deals Lister
# Usage: ./list_active_deals.sh [--save-file filename.json]

echo "🔍 BidSwitch Active Deals Discovery"
echo "==================================================="

# 1. Perform AWS SSO login (if needed)
echo "🔐 Checking AWS SSO login status..."
if ! aws sts get-caller-identity --profile bedrock > /dev/null 2>&1; then
    echo "🔑 AWS SSO login required..."
    echo "Running: aws sso login --profile bedrock"
    aws sso login --profile bedrock
    if ! aws sts get-caller-identity --profile bedrock > /dev/null 2>&1; then
        echo "❌ AWS SSO login failed. Please ensure your AWS CLI is configured for SSO."
        exit 1
    fi
fi
echo "✅ AWS SSO authentication successful"

# Navigate to the script's directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

# 2. Activate virtual environment
echo "🐍 Activating virtual environment..."
if [ ! -d "../venv" ]; then
    echo "❌ Virtual environment '../venv' not found. Please run setup first."
    exit 1
else
    source ../venv/bin/activate
fi

# Check packages are installed
echo "📦 Checking required packages..."
if ! python -c "import requests, psycopg2, boto3" 2>/dev/null; then
    echo "❌ Required packages not installed in virtual environment"
    echo "Please run from tools/ directory:"
    echo "  source venv/bin/activate"
    echo "  pip install -r requirements.txt"
    exit 1
fi
echo "✅ Virtual environment active"

# 3. Load environment variables
echo "🔧 Loading environment variables..."
if [ -f "../.env" ]; then
    echo "📋 Loading environment variables from ../.env..."
    export $(grep -v '^#' ../.env | xargs)
    echo "✅ Environment variables loaded"
else
    echo "❌ No .env file found in tools/ directory"
    echo "   Please ensure DSP_SEAT_ID and BidSwitch credentials are configured"
    exit 1
fi

# 4. Run the active deals lister
echo "🚀 Fetching active deals from BidSwitch..."
python list_active_deals.py "$@"

# Check if listing was successful
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Active deals listing completed successfully!"
    echo "📁 Check the ../reports/ directory for the generated JSON file."
    echo ""
    echo "Latest reports:"
    ls -la ../reports/active_deals_*.json | tail -3
else
    echo ""
    echo "❌ Active deals listing failed. Check the error messages above."
    exit 1
fi
