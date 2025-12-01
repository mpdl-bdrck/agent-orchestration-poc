# Chainlit SQLite Persistence Guide

**Date**: December 1, 2025  
**Status**: ✅ **RECOMMENDED SOLUTION** - SQLite for Chainlit persistence  
**Current State**: Persistence disabled (acceptable for POC)

---

## Overview

This document describes the recommended approach for enabling Chainlit conversation history persistence using **SQLite**.

### The "Best of Both Worlds" Architecture

**SQLite for UI Persistence** + **Postgres for Vector Search** = Clean separation of concerns

- **SQLite** (UI Memory): Handles Chainlit's conversation history with permissive type handling
- **Postgres** (Agent Brain): Handles vector search and knowledge base queries with strict types

This architecture decouples "UI Memory" from "Agent Brain", avoiding schema conflicts and type mismatches.

---

## Why SQLite?

### 1. Permissive Type Handling
SQLite doesn't care if Chainlit sends a `datetime` object to a `TEXT` column. It just stores it. No crashes.

### 2. No Schema Conflicts
SQLite handles Chainlit's data types gracefully without strict schema enforcement, avoiding the type mismatch errors that occur with PostgreSQL.

### 3. Simple File-Based Storage
No database server required. Chainlit creates a single `chainlit.db` file in your project root.

### 4. Performance
SQLite is fast enough for conversation history (small data, simple queries). Postgres remains for heavy vector operations.

---

## Implementation

### Step 1: Install SQLite Async Driver

```bash
pip install aiosqlite
```

### Step 2: Update `.env`

Add or update the `CHAINLIT_DATABASE_URL` to point to SQLite:

```env
# 1. Brain: Vector Search (Keep using Postgres)
DATABASE_URL=postgresql://user:pass@localhost:5432/knowledge_base

# 2. Memory: UI Persistence (Use SQLite)
# Chainlit will create this file automatically in the root folder.
CHAINLIT_DATABASE_URL=sqlite:///chainlit.db
```

### Step 3: Remove Disable Code (If Present)

If you have code that disables Chainlit persistence, remove or comment it out:

```python
# Remove this line if present:
os.environ["CHAINLIT_DATABASE_URL"] = ""
```

**Location**: Check `src/interface/chainlit/config.py` for any forced disable code.

### Step 4: Restart the App

```bash
chainlit run app.py -w
```

---

## What Happens

1. **Driver Switch**: Chainlit sees `sqlite:///` and automatically switches from `asyncpg` (Postgres driver) to `aiosqlite` (SQLite driver).

2. **Database Creation**: Chainlit automatically creates a file named `chainlit.db` in the project root.

3. **Schema Creation**: Chainlit creates its tables (Steps, Threads, etc.) inside that file.

4. **No Errors**: SQLite accepts the data types that Postgres was rejecting, eliminating crashes.

---

## File Locations

- **SQLite Database**: `chainlit.db` (created automatically in project root)
- **Postgres Database**: `knowledge_base` (for vector search)
- **Environment Config**: `.env` (contains `CHAINLIT_DATABASE_URL`)

---

## Current Status

- ✅ **Current**: Persistence disabled (acceptable for POC)
- 🔮 **Future**: SQLite recommended if persistence needed
- ❌ **Not Recommended**: Postgres for Chainlit persistence (too strict, causes errors)

---

## Benefits

- ✅ **Clean Console**: No database errors or type mismatch warnings
- ✅ **Persistent History**: Conversation history survives browser refreshes
- ✅ **Simple Setup**: No database server configuration required
- ✅ **Separation of Concerns**: UI persistence separate from knowledge base storage

---

## Notes

- The `chainlit.db` file is created automatically - no manual schema setup required
- SQLite is included in Python's standard library (via `aiosqlite` package)
- The database file can be safely deleted to reset conversation history
- Add `chainlit.db` to `.gitignore` to prevent committing conversation history

---

**Last Updated**: December 1, 2025
