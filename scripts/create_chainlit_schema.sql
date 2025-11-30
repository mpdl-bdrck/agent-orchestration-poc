-- Chainlit Database Schema Creation Script
-- Run this script in your PostgreSQL database to create the required tables for Chainlit persistence
-- Database: knowledge_base (or whatever DATABASE_URL points to)
--
-- IMPORTANT: This script uses TIMESTAMPTZ (not TEXT) for datetime columns.
-- Chainlit passes Python datetime objects, and asyncpg requires TIMESTAMPTZ for proper casting.

-- Drop existing tables first to reset schema (if they exist)
-- WARNING: This will delete all existing Chainlit data!
-- Note: Drop both lowercase and capital versions to handle any existing schema
DROP TABLE IF EXISTS "feedback";
DROP TABLE IF EXISTS "element";
DROP TABLE IF EXISTS "Step";      -- Chainlit expects capital S
DROP TABLE IF EXISTS "step";      -- Drop lowercase version if it exists
DROP TABLE IF EXISTS "Thread";
DROP TABLE IF EXISTS "thread";    -- Drop lowercase version if it exists
DROP TABLE IF EXISTS "user";

-- User table
CREATE TABLE IF NOT EXISTS "user" (
    "id" UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    "identifier" TEXT NOT NULL UNIQUE,
    "metadata" JSONB NOT NULL DEFAULT '{}',
    "createdAt" TIMESTAMPTZ NOT NULL DEFAULT NOW()  -- Fixed: Added DEFAULT NOW() for auto-timestamp
);

-- Thread table (conversation threads)
-- Chainlit expects "Thread" (capital T), not "thread" (lowercase)
CREATE TABLE IF NOT EXISTS "Thread" (
    "id" TEXT PRIMARY KEY,
    "createdAt" TIMESTAMPTZ NOT NULL DEFAULT NOW(),  -- Fixed: Added DEFAULT NOW() for auto-timestamp
    "updatedAt" TIMESTAMPTZ DEFAULT NOW(),           -- Fixed: Added DEFAULT NOW() for auto-timestamp
    "name" TEXT,
    "userId" UUID REFERENCES "user"("id"),
    "userIdentifier" TEXT,
    "tags" TEXT[],
    "metadata" JSONB
);

-- Step table (individual steps within threads)
-- CRITICAL: Chainlit expects "Step" (capital S), not "step" (lowercase)
CREATE TABLE IF NOT EXISTS "Step" (
    "id" TEXT PRIMARY KEY,
    "name" TEXT NOT NULL,
    "type" TEXT NOT NULL,
    "threadId" TEXT NOT NULL REFERENCES "Thread"("id"),
    "parentId" TEXT,
    "disableFeedback" BOOLEAN NOT NULL DEFAULT false,
    "streaming" BOOLEAN NOT NULL DEFAULT false,
    "waitForAnswer" BOOLEAN DEFAULT false,
    "isError" BOOLEAN DEFAULT false,
    "metadata" JSONB,
    "tags" TEXT[],
    "input" JSONB,
    "output" JSONB,
    "createdAt" TIMESTAMPTZ,  -- Fixed: Changed from TEXT to TIMESTAMPTZ
    "start" TIMESTAMPTZ,       -- Legacy column name (kept for compatibility)
    "end" TIMESTAMPTZ,         -- Legacy column name (kept for compatibility)
    "startTime" TIMESTAMPTZ,   -- CRITICAL: Chainlit expects camelCase "startTime"
    "endTime" TIMESTAMPTZ,     -- CRITICAL: Chainlit expects camelCase "endTime"
    "generation" JSONB,
    "showInput" BOOLEAN,  -- Made nullable - Chainlit may pass NULL or string values
    "language" TEXT,
    "indent" INT
);

-- Element table (for file attachments, images, etc.)
CREATE TABLE IF NOT EXISTS "element" (
    "id" UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    "threadId" TEXT REFERENCES "Thread"("id"),
    "type" TEXT,
    "url" TEXT,
    "chainlitKey" TEXT,
    "name" TEXT NOT NULL,
    "display" TEXT,
    "objectKey" TEXT,
    "size" TEXT,
    "page" INT,
    "language" TEXT,
    "forId" TEXT,
    "mime" TEXT
);

-- Feedback table (for user feedback on steps)
CREATE TABLE IF NOT EXISTS "feedback" (
    "id" UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    "forId" TEXT NOT NULL REFERENCES "Step"("id"),  -- Fixed: Use "Step" not "step"
    "value" INT NOT NULL,
    "comment" TEXT
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_thread_userId ON "Thread"("userId");
CREATE INDEX IF NOT EXISTS idx_thread_userIdentifier ON "Thread"("userIdentifier");
CREATE INDEX IF NOT EXISTS idx_step_threadId ON "Step"("threadId");      -- Fixed: Use "Step" not "step"
CREATE INDEX IF NOT EXISTS idx_step_parentId ON "Step"("parentId");      -- Fixed: Use "Step" not "step"
CREATE INDEX IF NOT EXISTS idx_element_threadId ON "element"("threadId");
CREATE INDEX IF NOT EXISTS idx_feedback_forId ON "feedback"("forId");

