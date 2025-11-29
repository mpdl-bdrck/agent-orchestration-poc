#!/bin/bash
# Agentic CRAG Launchpad - Knowledge Base Ingestion Launcher
# This script activates the virtual environment and runs ingestion

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

# Default values
KB_PATH="./knowledge-base"
CONTEXT_ID="bedrock_kb"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --kb-path)
            KB_PATH="$2"
            shift 2
            ;;
        --context-id)
            CONTEXT_ID="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: ./ingest.sh [--kb-path PATH] [--context-id ID]"
            exit 1
            ;;
    esac
done

# Run ingestion
echo "📥 Ingesting knowledge base..."
echo "   Path: $KB_PATH"
echo "   Context ID: $CONTEXT_ID"
echo ""
python -m src.ingestion.ingest --kb-path "$KB_PATH" --context-id "$CONTEXT_ID"

