-- Chainlit Database Schema Creation Script
-- Run this script in your PostgreSQL database to create the required tables for Chainlit persistence
-- Database: knowledge_base (or whatever DATABASE_URL points to)

-- User table
CREATE TABLE IF NOT EXISTS "user" (
    "id" UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    "identifier" TEXT NOT NULL UNIQUE,
    "metadata" JSONB NOT NULL DEFAULT '{}',
    "createdAt" TEXT NOT NULL
);

-- Thread table (conversation threads)
CREATE TABLE IF NOT EXISTS "thread" (
    "id" TEXT PRIMARY KEY,
    "createdAt" TEXT NOT NULL,
    "name" TEXT,
    "userId" UUID REFERENCES "user"("id"),
    "userIdentifier" TEXT,
    "tags" TEXT[],
    "metadata" JSONB
);

-- Step table (individual steps within threads)
CREATE TABLE IF NOT EXISTS "step" (
    "id" TEXT PRIMARY KEY,
    "name" TEXT NOT NULL,
    "type" TEXT NOT NULL,
    "threadId" TEXT NOT NULL REFERENCES "thread"("id"),
    "parentId" TEXT,
    "disableFeedback" BOOLEAN NOT NULL DEFAULT false,
    "streaming" BOOLEAN NOT NULL DEFAULT false,
    "waitForAnswer" BOOLEAN DEFAULT false,
    "isError" BOOLEAN DEFAULT false,
    "metadata" JSONB,
    "tags" TEXT[],
    "input" JSONB,
    "output" JSONB,
    "createdAt" TEXT,
    "start" TEXT,
    "end" TEXT,
    "generation" JSONB,
    "showInput" BOOLEAN DEFAULT false,
    "language" TEXT,
    "indent" INT
);

-- Element table (for file attachments, images, etc.)
CREATE TABLE IF NOT EXISTS "element" (
    "id" UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    "threadId" TEXT REFERENCES "thread"("id"),
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
    "forId" TEXT NOT NULL REFERENCES "step"("id"),
    "value" INT NOT NULL,
    "comment" TEXT
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_thread_userId ON "thread"("userId");
CREATE INDEX IF NOT EXISTS idx_thread_userIdentifier ON "thread"("userIdentifier");
CREATE INDEX IF NOT EXISTS idx_step_threadId ON "step"("threadId");
CREATE INDEX IF NOT EXISTS idx_step_parentId ON "step"("parentId");
CREATE INDEX IF NOT EXISTS idx_element_threadId ON "element"("threadId");
CREATE INDEX IF NOT EXISTS idx_feedback_forId ON "feedback"("forId");

