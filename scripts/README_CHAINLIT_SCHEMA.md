# Chainlit Database Schema Setup

Chainlit requires specific database tables to persist conversation history. This is optional - Chainlit will work without persistence, but you'll see database errors in the console.

## Quick Setup

### Option 1: Enable Persistence (Recommended for Production)

1. **Set Chainlit database URL in `.env`:**
   ```bash
   CHAINLIT_DATABASE_URL=postgresql://user:password@host:5432/database_name
   ```

2. **Create the schema:**
   ```bash
   ./scripts/create_chainlit_schema.sh [database_name]
   ```
   
   Or manually run the SQL:
   ```bash
   psql -h your_host -U your_user -d your_database -f scripts/create_chainlit_schema.sql
   ```

### Option 2: Disable Persistence (Default for POC)

Leave `CHAINLIT_DATABASE_URL` unset or empty in `.env`. Chainlit will work without persistence (conversations won't be saved).

**Note:** You'll still see database errors in the console, but they're harmless. To suppress them completely, you can set:
```bash
CHAINLIT_DATABASE_URL=""
```

## Tables Created

- `user` - User accounts
- `thread` - Conversation threads
- `step` - Individual steps within threads (agent actions, tool calls, etc.)
- `element` - File attachments, images, etc.
- `feedback` - User feedback on steps

## Troubleshooting

**Error: `relation "Thread" does not exist`**
- Solution: Run `./scripts/create_chainlit_schema.sh` to create the tables
- Or: Set `CHAINLIT_DATABASE_URL=""` to disable persistence

**Error: `permission denied for schema public`**
- Solution: Grant permissions: `GRANT ALL ON SCHEMA public TO your_user;`

**Error: `database does not exist`**
- Solution: Create the database first: `CREATE DATABASE your_database_name;`

