#!/bin/bash
# Initialize dedicated Chainlit database with proper schema
# Usage: ./scripts/init_chainlit_db.sh
#
# This script creates a dedicated 'chainlit_db' database separate from
# the knowledge_base to prevent schema conflicts and datetime casting errors.
#
# REQUIREMENTS:
# - Local PostgreSQL running on localhost:5432
# - PostgreSQL user with CREATE DATABASE permissions (default: postgres)
# - Check PostgreSQL is running: pg_isready

set -e

# Load .env file
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

if [ -f "$PROJECT_ROOT/.env" ]; then
    set -a
    source "$PROJECT_ROOT/.env"
    set +a
    echo "✅ Loaded environment variables from .env"
fi

# Get connection details from .env (may have remote settings)
ORIGINAL_POSTGRES_HOST="${POSTGRES_HOST:-localhost}"
ORIGINAL_POSTGRES_USER="${POSTGRES_USER:-postgres}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-}"
DB_NAME="${CHAINLIT_DB_NAME:-chainlit_db}"

# Detect local PostgreSQL default user (macOS uses current username, Linux uses postgres)
LOCAL_DEFAULT_USER="${USER:-$(whoami)}"

# CRITICAL: Force localhost for Chainlit database (ignore any remote settings from .env)
# Chainlit uses local PostgreSQL only - override any AWS/remote settings
if [ "$ORIGINAL_POSTGRES_HOST" != "localhost" ] && [ "$ORIGINAL_POSTGRES_HOST" != "127.0.0.1" ]; then
    echo "⚠️  Overriding POSTGRES_HOST=$ORIGINAL_POSTGRES_HOST → localhost (Chainlit uses local PostgreSQL only)"
    POSTGRES_HOST="localhost"
    # Use current user for macOS PostgreSQL (unless CHAINLIT_POSTGRES_USER is explicitly set)
    if [ -z "$CHAINLIT_POSTGRES_USER" ]; then
        if [ "$ORIGINAL_POSTGRES_USER" != "$LOCAL_DEFAULT_USER" ]; then
            echo "⚠️  Overriding POSTGRES_USER=$ORIGINAL_POSTGRES_USER → $LOCAL_DEFAULT_USER (local PostgreSQL default)"
        fi
        POSTGRES_USER="$LOCAL_DEFAULT_USER"
    else
        POSTGRES_USER="$CHAINLIT_POSTGRES_USER"
    fi
else
    # Already localhost, use settings as-is but default to current user
    POSTGRES_HOST="${ORIGINAL_POSTGRES_HOST}"
    POSTGRES_USER="${CHAINLIT_POSTGRES_USER:-${ORIGINAL_POSTGRES_USER:-$LOCAL_DEFAULT_USER}}"
fi

# Warn if connecting to remote host (should be localhost for local dev)
if [ "$POSTGRES_HOST" != "localhost" ] && [ "$POSTGRES_HOST" != "127.0.0.1" ]; then
    echo "⚠️  WARNING: Connecting to remote host: $POSTGRES_HOST"
    echo "   This script is designed for local PostgreSQL. For remote databases,"
    echo "   ensure the database exists and you have proper permissions."
else
    # Check if local PostgreSQL is running
    if ! pg_isready -h localhost -p "$POSTGRES_PORT" >/dev/null 2>&1; then
        echo "❌ ERROR: Local PostgreSQL is not running on localhost:$POSTGRES_PORT"
        echo ""
        echo "   Start PostgreSQL:"
        echo "   - macOS (Homebrew): brew services start postgresql@14"
        echo "   - Linux (systemd): sudo systemctl start postgresql"
        echo "   - Docker: docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=password postgres"
        echo ""
        echo "   Then check: pg_isready"
        exit 1
    fi
fi

echo "🚀 Initializing Chainlit database: $DB_NAME"
echo "   Host: $POSTGRES_HOST:$POSTGRES_PORT"
echo "   User: $POSTGRES_USER"
echo ""

# Export password for psql
export PGPASSWORD="$POSTGRES_PASSWORD"

# Step 1: Create database if it doesn't exist
echo "📦 Step 1: Creating database (if not exists)..."
echo "   Connecting to: $POSTGRES_HOST:$POSTGRES_PORT as $POSTGRES_USER"

# Check if database already exists first (faster than trying to create)
DB_EXISTS=$(psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'" 2>/dev/null || echo "0")

if [ "$DB_EXISTS" = "1" ]; then
    echo "   ℹ️  Database already exists, skipping creation"
    CREATE_EXIT_CODE=0
    CREATE_OUTPUT="already exists"
else
    # Use timeout to prevent hanging (10 seconds for local, should be fast)
    # Note: macOS doesn't have timeout by default, so we'll handle it differently
    if command -v timeout >/dev/null 2>&1; then
        CREATE_OUTPUT=$(timeout 10 psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d postgres -c "CREATE DATABASE $DB_NAME;" 2>&1)
        CREATE_EXIT_CODE=$?
    else
        # macOS fallback: use psql directly (should be fast for local)
        CREATE_OUTPUT=$(psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d postgres -c "CREATE DATABASE $DB_NAME;" 2>&1)
        CREATE_EXIT_CODE=$?
    fi
fi

if [ $CREATE_EXIT_CODE -eq 0 ]; then
    echo "   ✅ Database created successfully"
elif echo "$CREATE_OUTPUT" | grep -q "already exists"; then
    echo "   ℹ️  Database already exists, skipping creation"
elif echo "$CREATE_OUTPUT" | grep -q "permission denied\|must be owner\|CREATE DATABASE"; then
    echo "   ⚠️  Cannot create database (permission denied)"
    echo "   ℹ️  Attempting to use existing database..."
    # Try to connect to the database to see if it exists
    if timeout 5 psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$DB_NAME" -c "SELECT 1;" >/dev/null 2>&1; then
        echo "   ✅ Database exists and is accessible"
    else
        echo ""
        echo "   ❌ ERROR: Database '$DB_NAME' does not exist and cannot be created."
        echo "   The user '$POSTGRES_USER' does not have CREATE DATABASE permissions."
        echo ""
        if [ "$POSTGRES_HOST" = "localhost" ] || [ "$POSTGRES_HOST" = "127.0.0.1" ]; then
            echo "   For LOCAL PostgreSQL, try:"
            echo "   1. Create database manually:"
            echo "      psql -U postgres -d postgres -c \"CREATE DATABASE $DB_NAME;\""
            echo "   2. Or use postgres superuser:"
            echo "      sudo -u postgres psql -c \"CREATE DATABASE $DB_NAME;\""
            echo "   3. Or update POSTGRES_USER in .env to a user with CREATE DATABASE permissions"
        else
            echo "   For REMOTE PostgreSQL:"
            echo "   1. Create the database manually with an admin user"
            echo "   2. Use a different database user with CREATE DATABASE permissions"
            echo "   3. Use an existing database by setting CHAINLIT_DB_NAME in .env"
        fi
        exit 1
    fi
else
    echo "   ⚠️  Unexpected error: $CREATE_OUTPUT"
    # Continue anyway - might be a connection issue that will surface later
fi

# Step 2: Create schema with TIMESTAMPTZ columns
echo "📋 Step 2: Creating schema with TIMESTAMPTZ columns..."
if command -v timeout >/dev/null 2>&1; then
    # Linux: use timeout
    if ! timeout 30 psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$DB_NAME" -f "$PROJECT_ROOT/scripts/create_chainlit_schema.sql"; then
        echo ""
        echo "   ❌ ERROR: Failed to create schema. Possible issues:"
        echo "      - Database connection failed"
        echo "      - Password not set (check PGPASSWORD or .env)"
        echo "      - User lacks CREATE TABLE permissions"
        exit 1
    fi
else
    # macOS: run without timeout (local should be fast)
    if ! psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$DB_NAME" -f "$PROJECT_ROOT/scripts/create_chainlit_schema.sql"; then
        echo ""
        echo "   ❌ ERROR: Failed to create schema. Possible issues:"
        echo "      - Database connection failed"
        echo "      - Password not set (check PGPASSWORD or .env)"
        echo "      - User lacks CREATE TABLE permissions"
        exit 1
    fi
fi

echo ""
echo "✅ Chainlit database initialized successfully!"
echo "   Database: $DB_NAME"
echo "   Schema: All datetime columns use TIMESTAMPTZ"
echo ""
echo "📋 Next steps:"
echo "   1. Add to .env file:"
if [ -n "$POSTGRES_PASSWORD" ]; then
    echo "      CHAINLIT_DATABASE_URL=postgresql://$POSTGRES_USER:$POSTGRES_PASSWORD@$POSTGRES_HOST:$POSTGRES_PORT/$DB_NAME"
else
    echo "      CHAINLIT_DATABASE_URL=postgresql://$POSTGRES_USER@$POSTGRES_HOST:$POSTGRES_PORT/$DB_NAME"
fi
echo "   2. Restart Chainlit: chainlit run app.py -w"
echo "   3. Verify no asyncpg errors in console"

