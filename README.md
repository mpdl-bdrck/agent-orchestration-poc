# Bedrock Agent Orchestration POC

A robust, multi-agent orchestration system built on **LangGraph**, **LangChain**, and **Google Gemini 2.5 Flash**. This system demonstrates the **Supervisor Pattern** to coordinate specialist agents for Programmatic Advertising (DSP) portfolio management.

## 🎯 Vision & Strategy

This POC implements the foundational architecture for **Bedrock Platform's autonomous agentic AI vision**. 

> **📖 [Read the full vision →](docs/vision/README.md)**  
> The vision document outlines our path from reactive problem-solving to proactive autonomous optimization, with progressive autonomy stages that build trust through validated performance.

**Key Concepts**:
- **Four-Stage Progressive Autonomy**: Alerts → Recommendations → Approval-Based → Autonomous
- **System of Record Learning**: Agents learn from human expertise by observing outcomes
- **Multi-Agent Collaboration**: Specialized agents coordinate to optimize programmatic advertising operations 24/7

For detailed architecture, autonomy models, and strategic planning, see [`docs/vision/README.md`](docs/vision/README.md).

---

## 🌟 Key Features

- **LangGraph Supervisor Architecture**: A central Orchestrator node uses structured outputs (`RouteDecision`) to intelligently route tasks to specialist agents or knowledge base tools.
- **"Glass Box" Visibility**: Real-time streaming of agent reasoning, tool inputs, and state transitions via Chainlit.
- **Robust Tooling**: Tools handle malformed inputs gracefully, preventing LLM-induced crashes.
- **Hybrid Interface**: 
  - **CLI**: Detailed debug/reasoning output.
  - **Chainlit UI**: Modern multi-agent chat interface with real-time streaming and agent-specific chat bubbles.

## 🤖 Agent Roster

The system orchestrates five agents:

1.  **💠 Orchestrator Agent**: Central supervisor and router that coordinates all specialist agents, handles knowledge base queries, and provides conversational interface.
2.  **🛡️ Guardian Agent**: Portfolio oversight, health monitoring, and anomaly detection. Equipped with the `analyze_portfolio_pacing` tool.
3.  **🔬 Specialist Agent**: Deep diagnostic analysis, root cause identification, and troubleshooting.
4.  **🎯 Optimizer Agent**: Budget allocation, bid optimization, and creative rotation strategies.
5.  **🧭 Pathfinder Agent**: Supply chain navigation, QPS optimization, and SSP relationship management.

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

# PostgreSQL Connection (for scripts) - LOCAL only
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password_here
```

**Important**: 
- This setup uses **LOCAL PostgreSQL** only (localhost)
- Chainlit persistence is currently disabled (acceptable for POC)
- If you need conversation history persistence, see [`docs/CHAINLIT_SQLITE_PERSISTENCE.md`](docs/CHAINLIT_SQLITE_PERSISTENCE.md) for SQLite setup

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

## 🛡️ Stability & Reliability

This project implements robust error handling to prevent crashes from malformed LLM inputs. The system includes middleware normalization, input sanitization, and validation bypass mechanisms to ensure reliable operation even with unpredictable LLM outputs.

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

**Fix:** Already handled by middleware normalization. The system automatically unwraps nested lists and sanitizes inputs before validation.

**Issue:** Infinite loops or "Ghost" output.

**Cause:** Agent logic bypassing the `execute_agent_loop` streaming callbacks.

**Fix:** Ensure all agents return to the Supervisor and use the standard execution wrapper.

**Issue:** Chainlit async context errors (Python 3.14+)

**Cause:** Python 3.14 has compatibility issues with Chainlit's async dependencies (`anyio`, `sniffio`).

**Fix:** Use Python 3.13 instead. Run `./setup_python313.sh` to set up a compatible environment.


## 📚 Documentation

### Core Architecture
- **`docs/TOOL_INSTRUCTIONS_ARCHITECTURE.md`**: Complete guide to tool development and instruction injection at runtime

### 🎯 Vision & Strategic Planning

> **Start here**: [`docs/vision/README.md`](docs/vision/README.md) - **The strategic vision** that guides this implementation, outlining the path from reactive problem-solving to proactive autonomous optimization.

- **`docs/vision/README.md`**: Vision for autonomous deal optimization & supply chain management
- **`docs/vision/THREE_LAYER_ARCHITECTURE.md`**: Foundation architecture separating intelligence, communication, and capabilities
- **`docs/vision/PROGRESSIVE_AUTONOMY.md`**: Four-stage evolution from alerts to autonomous action
- **`docs/vision/SYSTEM_OF_RECORD.md`**: Learning engine design for building trust and validation
- **`docs/vision/TOOL_DEVELOPMENT_MATRIX.md`**: Comprehensive tool registry and development roadmap

### UI & Persistence
- **`docs/CHAINLIT_SQLITE_PERSISTENCE.md`**: Guide to enabling Chainlit conversation history using SQLite (recommended approach)
- **`docs/PROACTIVE_NOTIFICATION_PANEL.md`**: North star feature - transforming from reactive chatbot to proactive command center
