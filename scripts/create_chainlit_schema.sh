#!/bin/bash
# Script to create Chainlit database schema
# Usage: ./scripts/create_chainlit_schema.sh [database_name]
#
# WARNING: This script will DROP existing Chainlit tables and recreate them.
# All existing conversation history will be lost!

set -e

# Load .env file if it exists (from project root)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

if [ -f "$PROJECT_ROOT/.env" ]; then
    set -a  # Automatically export all variables
    source "$PROJECT_ROOT/.env"
    set +a  # Stop automatically exporting
    echo "✅ Loaded environment variables from .env"
fi

# Get database name from argument or use default
DB_NAME="${1:-knowledge_base}"

echo "⚠️  WARNING: This script will DROP existing Chainlit tables!"
echo "   All conversation history will be deleted."
echo ""
read -p "Continue? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Aborted."
    exit 1
fi

echo ""
echo "🔄 Dropping and recreating Chainlit schema..."

# Get database connection details from environment (now loaded from .env)
POSTGRES_HOST="${POSTGRES_HOST:-localhost}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
POSTGRES_USER="${POSTGRES_USER:-postgres}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-}"

# Check if DATABASE_URL is set (takes precedence)
if [ -n "$DATABASE_URL" ]; then
    echo "Using DATABASE_URL for connection..."
    # Extract database name from URL if not provided as argument
    if [ -z "$1" ]; then
        # Try to extract database name from DATABASE_URL
        DB_NAME=$(echo "$DATABASE_URL" | sed -n 's/.*\/\([^\/]*\)$/\1/p' | sed 's/?.*//')
        if [ -n "$DB_NAME" ]; then
            echo "Detected database name from DATABASE_URL: $DB_NAME"
        fi
    fi
    psql "$DATABASE_URL" -f scripts/create_chainlit_schema.sql
else
    # Use individual POSTGRES_* variables
    echo "Creating Chainlit schema in database: $DB_NAME"
    echo "Host: $POSTGRES_HOST:$POSTGRES_PORT"
    echo "User: $POSTGRES_USER"
    
    if [ -z "$POSTGRES_PASSWORD" ]; then
        echo "⚠️  Warning: POSTGRES_PASSWORD not set. You may be prompted for password."
    fi
    
    export PGPASSWORD="$POSTGRES_PASSWORD"
    psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$DB_NAME" -f scripts/create_chainlit_schema.sql
fi

echo ""
echo "✅ Chainlit database schema recreated successfully!"
echo "   - All datetime columns now use TIMESTAMPTZ (fixes asyncpg datetime errors)"
echo "   - Tables dropped and recreated with correct schema"
echo ""
echo "📋 Next steps:"
echo "   1. Restart Chainlit: chainlit run app.py -w"
echo "   2. Verify no datetime errors in console"
echo "   3. Check that avatars load correctly"

