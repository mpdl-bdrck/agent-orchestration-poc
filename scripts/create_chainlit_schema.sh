#!/bin/bash
# Script to create Chainlit database schema
# Usage: ./scripts/create_chainlit_schema.sh [database_name]

set -e

# Get database name from argument or use default
DB_NAME="${1:-knowledge_base}"

# Get database connection details from environment
POSTGRES_HOST="${POSTGRES_HOST:-localhost}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
POSTGRES_USER="${POSTGRES_USER:-postgres}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-}"

# Check if DATABASE_URL is set (takes precedence)
if [ -n "$DATABASE_URL" ]; then
    echo "Using DATABASE_URL for connection..."
    PGPASSWORD="${POSTGRES_PASSWORD}" psql "$DATABASE_URL" -f scripts/create_chainlit_schema.sql
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

echo "✅ Chainlit schema created successfully!"

