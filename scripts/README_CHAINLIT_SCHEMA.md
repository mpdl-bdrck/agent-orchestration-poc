# Chainlit Database Schema Setup

**IMPORTANT**: 
- This setup uses **LOCAL PostgreSQL** only (localhost)
- Chainlit uses a **dedicated database** (`chainlit_db`) separate from the knowledge base (`knowledge_base`)
- This prevents schema conflicts and datetime casting errors

## Why Separate Databases?

- **Knowledge Base** (`knowledge_base`): Vector storage with pgvector extension for semantic search
- **Chainlit UI** (`chainlit_db`): Conversation history with strict TIMESTAMPTZ schema

Sharing databases causes:
- Schema conflicts (pgvector vs Chainlit tables)
- Datetime casting errors (`asyncpg.exceptions.DataError`)
- Migration conflicts when updating either system

## Prerequisites

- **Local PostgreSQL** running on localhost:5432
- PostgreSQL user with CREATE DATABASE permissions (typically `postgres` user)
- Check PostgreSQL is running: `pg_isready`

## Quick Setup

### Option 1: Enable Persistence (Recommended)

1. **Initialize the dedicated Chainlit database:**
   ```bash
   ./scripts/init_chainlit_db.sh
   ```
   This script:
   - Creates `chainlit_db` database (if it doesn't exist)
   - Creates schema with TIMESTAMPTZ columns (fixes datetime casting errors)
   - Shows you the exact `CHAINLIT_DATABASE_URL` to add to `.env`

2. **Add to `.env` file:**
   ```bash
   CHAINLIT_DATABASE_URL=postgresql://user:password@host:5432/chainlit_db
   ```

3. **Restart Chainlit:**
   ```bash
   chainlit run app.py -w
   ```

4. **Verify no errors:**
   - Check console for `✅ Chainlit database schema validated`
   - No `asyncpg.exceptions.DataError` messages
   - Conversation history persists across sessions

### Option 2: Disable Persistence

Leave `CHAINLIT_DATABASE_URL` unset or set it to empty in `.env`:
```bash
CHAINLIT_DATABASE_URL=""
```

Chainlit will work without persistence (conversations won't be saved).

## Tables Created

- `user` - User accounts
- `thread` - Conversation threads
- `step` - Individual steps within threads (agent actions, tool calls, etc.)
- `element` - File attachments, images, etc.
- `feedback` - User feedback on steps

## Troubleshooting

**Error: `relation "Thread" does not exist`**
- Solution: Run `./scripts/init_chainlit_db.sh` to create the database and schema
- Or: Set `CHAINLIT_DATABASE_URL=""` to disable persistence

**Error: `asyncpg.exceptions.DataError: invalid input for query argument $11: 'json' (a boolean is required)`**
- **Root Cause**: Chainlit passes the string `'json'` where a boolean is expected for `showInput` field
- **Solution**: Run `./scripts/init_chainlit_db.sh` to recreate schema with `showInput` as TEXT (not BOOLEAN)
- The schema has been updated to handle this Chainlit bug

**Error: `asyncpg.exceptions.DataError: invalid input for query argument` (datetime)**
- **Root Cause**: Schema has TEXT columns instead of TIMESTAMPTZ
- **Solution**: Run `./scripts/init_chainlit_db.sh` to recreate schema with correct types
- This error occurs when Chainlit passes Python datetime objects to TEXT columns

**Error: `permission denied for schema public`**
- Solution: Grant permissions: `GRANT ALL ON SCHEMA public TO your_user;`

**Error: `database does not exist`**
- Solution: Run `./scripts/init_chainlit_db.sh` - it creates the database automatically

**Warning: `Chainlit database schema may be incorrect`**
- This appears on startup if schema validation fails
- Run `./scripts/init_chainlit_db.sh` to fix the schema

