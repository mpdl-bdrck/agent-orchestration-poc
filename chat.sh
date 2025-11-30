#!/bin/bash
# Agent Orchestration POC - CLI Chat Launcher
# This script activates the virtual environment and starts the CLI chat

# Clear terminal
clear

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Activate virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "❌ Error: Virtual environment not found!"
    echo "   Run: python3 -m venv venv"
    exit 1
fi

# Check if context-id is provided as argument
if [ -z "$1" ]; then
    # Default to bedrock_kb if no argument provided
    CONTEXT_ID="bedrock_kb"
    echo "ℹ️  No context-id provided, using default: $CONTEXT_ID"
else
    CONTEXT_ID="$1"
fi

# AWS Authentication Check
echo "🔐 Checking AWS SSO authentication..."
if aws sts get-caller-identity --profile bedrock &> /dev/null; then
    echo "✅ AWS SSO authentication successful"
else
    echo "⚠️  AWS SSO login required for portfolio analysis tools"
    echo "🔑 Running: aws sso login --profile bedrock"
    aws sso login --profile bedrock

    # Verify login was successful
    if ! aws sts get-caller-identity --profile bedrock &> /dev/null; then
        echo "❌ AWS SSO authentication failed"
        echo "ℹ️  Portfolio analysis tools may not work properly"
        echo "ℹ️  You can still use the chat interface for other queries"
    else
        echo "✅ AWS SSO authentication successful"
    fi
fi

echo ""

# Enable Guardian tools by default
export GUARDIAN_TOOLS_ENABLED=true

# Start the CLI chat
echo "🚀 Starting Agent Orchestration POC CLI..."
echo "📚 Context Knowledge Base: $CONTEXT_ID"
echo ""
python -m src.interface.cli.main --context-id "$CONTEXT_ID"

