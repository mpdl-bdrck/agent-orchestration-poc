# Bedrock Agent Orchestration POC

A robust, multi-agent orchestration system built on **LangGraph**, **LangChain**, and **Google Gemini 2.5 Flash**. This system demonstrates the **Supervisor Pattern** to coordinate specialist agents for Programmatic Advertising (DSP) portfolio management.

## 🌟 Key Features

- **LangGraph Supervisor Architecture**: A central Orchestrator node uses structured outputs (`RouteDecision`) to intelligently route tasks to specialist agents or knowledge base tools.
- **"Glass Box" Visibility**: Real-time streaming of agent reasoning, tool inputs, and state transitions via Chainlit.
- **Robust Tooling**: Implements the **"Canary Pattern"** and **Double-Ended Sanitation** to prevent LLM-induced crashes (handling malformed list/string inputs).
- **Cost & Inhibition Protocols**: "Tool Holster" logic prevents agents from using expensive tools for simple greetings or out-of-scope queries.
- **Hybrid Interface**: 
  - **CLI**: Detailed debug/reasoning output.
  - **Chainlit UI**: Modern, split-view interface (Orchestrator in main chat, Agents in nested steps).

## 🤖 Agent Roster

The system orchestrates four specialized agents:

1.  **🛡️ Guardian Agent**: Portfolio oversight, health monitoring, and anomaly detection. Equipped with the `analyze_portfolio_pacing` tool.
2.  **🔧 Specialist Agent**: Deep diagnostic analysis, root cause identification, and troubleshooting.
3.  **🎯 Optimizer Agent**: Budget allocation, bid optimization, and creative rotation strategies.
4.  **🧭 Pathfinder Agent**: Supply chain navigation, QPS optimization, and SSP relationship management.

## 🏗️ Architecture

![LangGraph Agent Orchestration](docs/images/langgraph_agent_orchestration.png)

*Figure: High-level Supervisor Architecture showing the flow between Orchestrator, Agents, and Shared State.*

```mermaid
graph TD
    UserInput --> Orchestrator
    Orchestrator --"RouteDecision"--> Router{Condition}
    
    Router --"next='guardian'"--> GuardianNode
    Router --"next='specialist'"--> SpecialistNode
    Router --"next='optimizer'"--> OptimizerNode
    Router --"next='pathfinder'"--> PathfinderNode
    Router --"next='semantic_search'"--> SearchServiceNode
    
    GuardianNode --> Orchestrator
    SpecialistNode --> Orchestrator
    OptimizerNode --> Orchestrator
    PathfinderNode --> Orchestrator
    SearchServiceNode --> Orchestrator
    
    Router --"next='FINISH'"--> End
```

## 🚀 Quick Start

### 1. Prerequisites

  - **Python 3.13** (Recommended - fully compatible with Chainlit)
  - Python 3.10-3.12 also supported
  - ⚠️ **Python 3.14+ NOT recommended** - Chainlit has compatibility issues
  - PostgreSQL with `pgvector` extension installed.
  - Google Gemini API Key (Verified for `gemini-2.5-flash`).

### 2. Installation

**Quick Setup (Python 3.13):**

```bash
# Run the setup script (creates venv and installs dependencies)
./setup_python313.sh

# Or manually:
python3.13 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**Manual Installation:**

```bash
# Clone and install dependencies
pip install -r requirements.txt
```

### 3. Configuration

Create `.env` file and configure:

```env
GEMINI_API_KEY=your_key_here

# Knowledge Base (Vector Storage) - LOCAL PostgreSQL
DATABASE_URL=postgresql://postgres:password@localhost:5432/knowledge_base

# Chainlit UI Persistence (Conversation History) - LOCAL PostgreSQL
# Use dedicated database to prevent schema conflicts
CHAINLIT_DATABASE_URL=postgresql://postgres:password@localhost:5432/chainlit_db

# PostgreSQL Connection (for scripts) - LOCAL only
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password_here

# Optional: Override default chainlit database name
# CHAINLIT_DB_NAME=chainlit_db
```

**Important**: 
- This setup uses **LOCAL PostgreSQL** only (localhost)
- Chainlit uses a **dedicated database** (`chainlit_db`) separate from the knowledge base
- This prevents schema conflicts and datetime casting errors

**Quick Setup**:
```bash
# 1. Ensure PostgreSQL is running locally
pg_isready

# 2. Initialize Chainlit database (creates chainlit_db and schema)
./scripts/init_chainlit_db.sh

# 3. The script will show you the exact CHAINLIT_DATABASE_URL to add to .env
```

### 4. Knowledge Base Ingestion

Before using the application, you need to ingest the knowledge base into the vector database. The knowledge base files are located in the `knowledge-base/` directory.

**Quick Setup (Recommended):**
```bash
# Activate virtual environment
source venv/bin/activate

# Run ingestion script (defaults to ./knowledge-base → bedrock_kb)
./ingest.sh bedrock_kb

# Or with custom path:
./ingest.sh --kb-path ./knowledge-base --context-id bedrock_kb
```

**Manual Setup:**
```bash
source venv/bin/activate
python -m src.ingestion.ingest --kb-path ./knowledge-base --context-id bedrock_kb
```

**What happens during ingestion:**
- All `.md` files in `knowledge-base/` are processed
- Content is chunked by sections (or by size with `--chunk-by-size`)
- Embeddings are generated using SentenceTransformer (`all-MiniLM-L6-v2`)
- Chunks are stored in PostgreSQL with pgvector extension
- Context ID `bedrock_kb` is used to organize chunks

**When to re-ingest:**
- After adding new markdown files to `knowledge-base/`
- After modifying existing files (to update the index)
- When you want to refresh the entire knowledge base

**Verify ingestion:**
```bash
# Check chunk count in database
psql $DATABASE_URL -c "SELECT COUNT(*) FROM knowledge_chunks;"
```

For more details, see [`USAGE_GUIDE.md`](USAGE_GUIDE.md#2-knowledge-base-ingestion-already-done).

### 5. Running the Application

**Run the Chainlit UI (Recommended):**

```bash
# Activate virtual environment
source venv/bin/activate

# Run Chainlit
chainlit run app.py -w
```

**Run the CLI (For debugging):**

```bash
python -m src.interface.cli.main --context-id bedrock_kb
```

## 🛡️ Stability Patterns (The "Anti-Crash" Layer)

This project implements specific patterns to handle "Eager" LLMs (like Gemini Flash) that often hallucinate input formats:

1.  **Middleware Normalization**: `agent_loop.py` recursively unwraps nested lists before they hit Pydantic validation.
2.  **The Canary Pattern**: Tools use `@tool` decorators with internal `safe_str` sanitizers rather than strict Pydantic schemas, preventing schema validation crashes.
3.  **Validation Bypass**: The execution loop attempts to call the raw Python function (`.func`) directly to bypass LangChain's internal validation layer when necessary.

## 📂 Project Structure

```
src/
├── agents/
│   ├── orchestrator/       # Supervisor logic & Graph definition
│   └── specialists/        # Agent definitions (Guardian, etc.)
├── tools/                  # Robust tool definitions (guardian_v2_tool.py)
├── utils/
│   └── agent_loop.py       # Core execution loop with Middleware Safety
└── graph/                  # LangGraph state & node logic
```

## ⚠️ Common Issues & Fixes

**Issue:** `AttributeError: 'list' object has no attribute 'strip'`

**Cause:** The LLM sent `['value']` instead of `"value"`.

**Fix:** Already handled by the **Double-Ended Sanitation** layer. If this recurs, ensure you are using `guardian_v2_tool.py` and not the legacy version.

**Issue:** Infinite loops or "Ghost" output.

**Cause:** Agent logic bypassing the `execute_agent_loop` streaming callbacks.

**Fix:** Ensure all agents return to the Supervisor and use the standard execution wrapper.

**Issue:** Chainlit async context errors (Python 3.14+)

**Cause:** Python 3.14 has compatibility issues with Chainlit's async dependencies (`anyio`, `sniffio`).

**Fix:** Use Python 3.13 instead. Run `./setup_python313.sh` to set up a compatible environment.

**Issue:** `asyncpg.exceptions.DataError: invalid input for query argument` or `relation "Thread" does not exist`

**Cause:** Chainlit database schema is missing or incorrect. This happens when:
- Database doesn't exist
- Schema has TEXT columns instead of TIMESTAMPTZ (causes datetime casting errors)
- Chainlit is sharing the same database as knowledge_base (schema conflicts)

**Fix:** 
1. Run `./scripts/init_chainlit_db.sh` to create dedicated `chainlit_db` database with correct schema
2. Add `CHAINLIT_DATABASE_URL` to `.env` (the script shows you the exact value)
3. Restart Chainlit - errors should disappear

**Note:** Chainlit uses a dedicated database (`chainlit_db`) separate from the knowledge base (`knowledge_base`) to prevent schema conflicts.

## 📚 Documentation

- **`AI_HANDOFF.md`**: Comprehensive architectural decisions, patterns, and troubleshooting guide
- **`docs/chainlit_ui_implementation_plan.md`**: Chainlit UI implementation details
- **`docs/chainlit_ui_tickets.md`**: Implementation ticket tracking
