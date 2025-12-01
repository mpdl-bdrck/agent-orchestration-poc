#!/bin/bash
# Cleanup Chainlit-related databases and tables from PostgreSQL
# This removes all Chainlit persistence artifacts since we've disabled persistence

set -e

# Load environment variables
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Default to local PostgreSQL
POSTGRES_HOST="${POSTGRES_HOST:-localhost}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
POSTGRES_USER="${POSTGRES_USER:-$(whoami)}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-}"

# Get database connection details from DATABASE_URL if available
if [ -n "$DATABASE_URL" ]; then
    # Parse DATABASE_URL: postgresql://user:pass@host:port/dbname
    DB_URL_REGEX="postgresql://([^:]+):([^@]+)@([^:]+):([^/]+)/(.+)"
    if [[ $DATABASE_URL =~ $DB_URL_REGEX ]]; then
        POSTGRES_USER="${BASH_REMATCH[1]}"
        POSTGRES_PASSWORD="${BASH_REMATCH[2]}"
        POSTGRES_HOST="${BASH_REMATCH[3]}"
        POSTGRES_PORT="${BASH_REMATCH[4]}"
    fi
fi

echo "🗑️  Chainlit Database Cleanup"
echo "================================"
echo ""
echo "This will remove:"
echo "  1. chainlit_db database (dedicated Chainlit persistence - no longer used)"
echo "  2. knowledge_base database (if unused - verify first!)"
echo "  3. conversations table from bedrock_db (legacy table)"
echo ""
echo "Connection: postgresql://${POSTGRES_USER}@${POSTGRES_HOST}:${POSTGRES_PORT}"
echo ""

read -p "⚠️  Continue? (yes/no): " confirm
if [ "$confirm" != "yes" ]; then
    echo "❌ Cleanup cancelled"
    exit 0
fi

# Build psql connection string
if [ -n "$POSTGRES_PASSWORD" ]; then
    export PGPASSWORD="$POSTGRES_PASSWORD"
fi

PSQL_CMD="psql -h $POSTGRES_HOST -p $POSTGRES_PORT -U $POSTGRES_USER"

# 1. Drop chainlit_db database
echo ""
echo "1️⃣  Dropping chainlit_db database..."
$PSQL_CMD -d postgres -c "DROP DATABASE IF EXISTS chainlit_db;" 2>/dev/null || echo "   ⚠️  chainlit_db doesn't exist or already dropped"
echo "   ✅ chainlit_db removed"

# 2. Check if knowledge_base exists and is used
echo ""
echo "2️⃣  Checking knowledge_base database..."
KB_EXISTS=$($PSQL_CMD -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='knowledge_base';" 2>/dev/null || echo "0")

if [ "$KB_EXISTS" = "1" ]; then
    echo "   ⚠️  knowledge_base database exists"
    echo "   📊 Checking for active tables..."
    TABLE_COUNT=$($PSQL_CMD -d knowledge_base -tAc "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';" 2>/dev/null || echo "0")
    echo "   Found $TABLE_COUNT tables"
    
    if [ "$TABLE_COUNT" -gt 0 ]; then
        read -p "   ⚠️  knowledge_base has tables. Drop anyway? (yes/no): " drop_kb
        if [ "$drop_kb" = "yes" ]; then
            echo "   🗑️  Dropping knowledge_base..."
            $PSQL_CMD -d postgres -c "DROP DATABASE IF EXISTS knowledge_base;" 2>/dev/null || echo "   ⚠️  Failed to drop knowledge_base"
            echo "   ✅ knowledge_base removed"
        else
            echo "   ⏭️  Skipping knowledge_base (kept)"
        fi
    else
        echo "   🗑️  Dropping empty knowledge_base..."
        $PSQL_CMD -d postgres -c "DROP DATABASE IF EXISTS knowledge_base;" 2>/dev/null || echo "   ⚠️  Failed to drop knowledge_base"
        echo "   ✅ knowledge_base removed"
    fi
else
    echo "   ✅ knowledge_base doesn't exist"
fi

# 3. Drop conversations table from bedrock_db
echo ""
echo "3️⃣  Dropping conversations table from bedrock_db..."
$PSQL_CMD -d bedrock_db -c "DROP TABLE IF EXISTS conversations CASCADE;" 2>/dev/null || echo "   ⚠️  bedrock_db doesn't exist or conversations table already dropped"
echo "   ✅ conversations table removed from bedrock_db"

# Cleanup
unset PGPASSWORD

echo ""
echo "✅ Cleanup complete!"
echo ""
echo "📝 Note: Chainlit persistence is disabled in app.py"
echo "   If you want persistence in the future, consider SQLite (see CHAINLIT_DATABASE_AUDIT.md)"

