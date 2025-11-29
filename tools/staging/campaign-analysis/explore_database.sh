#!/bin/bash

# Database Explorer Script
# Uses the same authentication as campaign analysis

set -e

echo "🔍 Database Spend Explorer"
echo "================================================="

# Step 1: Check AWS SSO
echo "🔐 Step 1: AWS SSO Authentication"
echo "================================="
echo "Checking AWS SSO login status..."

if aws sts get-caller-identity --profile bedrock >/dev/null 2>&1; then
    echo "✅ AWS SSO authentication successful"
else
    echo "🔑 AWS SSO login required..."
    echo "Running: aws sso login --profile bedrock"
    aws sso login --profile bedrock
    
    # Verify login was successful
    if ! aws sts get-caller-identity --profile bedrock >/dev/null 2>&1; then
        echo "❌ AWS SSO authentication failed"
        exit 1
    fi
    echo "✅ AWS SSO authentication successful"
fi

# Step 2: Python Environment
echo ""
echo "🐍 Step 2: Python Environment Setup"
echo "================================="
echo "🔌 Activating virtual environment (../venv)..."
source ../venv/bin/activate

echo "📦 Checking required packages..."
if ! python -c "import psycopg2, boto3" 2>/dev/null; then
    echo "❌ Required packages not installed in virtual environment"
    echo "Please run from tools/ directory:"
    echo "  source venv/bin/activate"
    echo "  pip install -r requirements.txt"
    exit 1
fi
echo "✅ Python environment ready"

# Step 3: Environment Configuration
echo ""
echo "🔧 Step 3: Environment Configuration"
echo "================================="
echo "📋 Loading environment variables from ../.env..."
if [ -f "../.env" ]; then
    source ../.env
    echo "✅ Environment variables loaded"
else
    echo "❌ .env file not found"
    exit 1
fi

echo "🔍 Validating environment configuration..."
if [ -z "$POSTGRES_HOST" ] || [ -z "$REDSHIFT_CLUSTER_ID" ]; then
    echo "❌ Missing required environment variables"
    exit 1
fi
echo "✅ Environment configuration validated"

# Step 4: Run Database Exploration
echo ""
echo "🚀 Step 4: Database Exploration"
echo "================================="
echo "🔍 Exploring database schema and spend calculations..."

python simple_spend_explorer.py

echo ""
echo "✅ Database exploration completed!"
