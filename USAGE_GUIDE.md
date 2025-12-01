# Usage Guide - Bedrock Agent Orchestration POC

## Quick Start

### 1. Set Your GEMINI API Key

Edit the `.env` file in the project root:

```bash
# Open .env file
nano .env
# or
vim .env
# or use any text editor
```

Find this line:
```
GEMINI_API_KEY=your_gemini_api_key_here
```

Replace `your_gemini_api_key_here` with your actual Gemini API key:
```
GEMINI_API_KEY=AIzaSy...your_actual_key_here
```

**Location**: The `.env` file is in the project root: `/Users/mpdl/devhome/agent_orchestration_poc/.env`

---

## 2. Knowledge Base Ingestion (Already Done!)

✅ **The knowledge base has already been ingested!**

**What happened:**
- The `knowledge-base/` folder (31 markdown files) was processed
- 997 chunks were generated and stored in the PostgreSQL database
- Database: `bedrock_kb` (per-context database)

**When ingestion happens:**
- Ingestion is a **one-time setup step** (unless you add new files)
- Run ingestion when:
  - You add new markdown files to `knowledge-base/`
  - You modify existing files and want to re-index
  - You want to start fresh (re-ingest)

**To re-ingest or ingest new content:**

**Easy way (recommended):**
```bash
./ingest.sh bedrock_kb
# Or with custom path:
./ingest.sh --kb-path ./knowledge-base --context-id bedrock_kb
```

**Manual way:**
```bash
source venv/bin/activate
python -m src.ingestion.ingest --kb-path ./knowledge-base --context-id bedrock_kb
```

**Note**: The current ingestion is complete - you have 997 chunks ready to query!

---

## 3. Using the CLI Chat Interface

### Start the Chat (Easy Way - Recommended)

```bash
# Use the convenience script (automatically activates venv)
./chat.sh bedrock_kb

# Or use default context (bedrock_kb)
./chat.sh
```

### Start the Chat (Manual Way)

```bash
# Activate virtual environment
source venv/bin/activate

# Start CLI chat with bedrock_kb context
python -m src.interface.cli.main --context-id bedrock_kb
```

### Example Session

```
> What is the Bedrock platform?

[The system will search the knowledge base and provide an answer]

> How do I troubleshoot campaign issues?

[The system will find relevant troubleshooting documentation]

> help

Available commands:
  help          - Show this help message
  clear         - Clear the screen
  exit/quit/q   - Exit the chat

> exit
Goodbye!
```

### CLI Commands

- `help` - Show help message
- `clear` - Clear the screen
- `exit` / `quit` / `q` - Exit the chat

---

## 4. Using Programmatically (Python)

```python
from src.agents.orchestrator import OrchestratorAgent

# Initialize orchestrator
agent = OrchestratorAgent()

# Set knowledge base context
agent.set_context('bedrock_kb')

# Ask questions
answer = agent.chat('What is the Bedrock platform?')
print(answer)

# Ask follow-up questions (conversation history maintained)
answer2 = agent.chat('Tell me more about campaign troubleshooting')
print(answer2)
```

---

## 5. Workflow Summary

### Initial Setup (One-Time)
1. ✅ Set up database (done)
2. ✅ Ingest knowledge base (done - 997 chunks)
3. ⚠️ **Set GEMINI_API_KEY in `.env`** (you need to do this)

### Daily Usage
1. Start CLI: `python -m src.interface.cli.main --context-id bedrock_kb`
2. Ask questions about your knowledge base
3. Get answers with semantic search and CRAG validation

### When to Re-Ingest
- After adding new markdown files to `knowledge-base/`
- After modifying existing markdown files
- When you want to refresh the index

---

## 6. File Locations

- **Knowledge Base**: `/Users/mpdl/devhome/agent_orchestration_poc/knowledge-base/`
- **Environment File**: `/Users/mpdl/devhome/agent_orchestration_poc/.env`
- **Database**: PostgreSQL `bedrock_kb` database
- **Config**: `/Users/mpdl/devhome/agent_orchestration_poc/config/`

---

## 7. Troubleshooting

### "GEMINI_API_KEY not set" error
- Edit `.env` file and set your actual API key
- Make sure there are no quotes around the key value

### "No knowledge base context" error
- Make sure you're using `--context-id bedrock_kb`
- Verify the database exists: `psql -U mpdl -d bedrock_kb -c "SELECT COUNT(*) FROM knowledge_chunks;"`

### "No results found"
- Check that ingestion completed successfully (should show 997 chunks)
- Verify files exist in `knowledge-base/` folder

---

## 8. What's Happening Behind the Scenes

1. **Question Asked** → Orchestrator receives question
2. **Semantic Search** → Finds relevant chunks from 997 stored chunks
3. **CRAG Validation** → Validates relevance (0.0-1.0 scores)
4. **LLM Processing** → Uses Gemini to generate answer from context
5. **Response** → Returns answer with citations

The knowledge base is **already in the database** - you're querying it, not ingesting it each time!

