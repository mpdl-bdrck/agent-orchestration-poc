# Agent Orchestration POC

A generic, domain-agnostic multi-agent CRAG (Corrective Retrieval-Augmented Generation) system for knowledge base Q&A. Extracted and generalized from StoryForge's Agentic CRAG architecture.

## Features

- **Multi-Agent Orchestration**: Orchestrator agent delegates complex queries to specialist agents
- **CRAG Integration**: Corrective RAG validation ensures retrieved context is relevant
- **Hybrid Search**: Combines keyword (TSVECTOR) and semantic (pgvector) search
- **CLI-First Interface**: "Glass box" terminal output showing reasoning, tool calls, and answers
- **Markdown Knowledge Base**: Ingest Markdown files with automatic metadata extraction
- **Domain-Agnostic**: No domain-specific logic - works with any knowledge base

## Quick Start

### 1. Installation

```bash
# Clone the repository
cd agent_orchestration_poc

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys and database URL
```

### 2. Configure Database

Ensure PostgreSQL with pgvector extension is installed:

```sql
CREATE DATABASE knowledge_base;
\c knowledge_base
CREATE EXTENSION IF NOT EXISTS vector;
```

Update `DATABASE_URL` in `.env`:

```
DATABASE_URL=postgresql://user:password@localhost:5432/knowledge_base
```

### 3. Prepare Knowledge Base

Organize your Markdown files in a directory structure:

```
knowledge_base/
├── category1/
│   ├── document1.md
│   └── document2.md
└── category2/
    └── document3.md
```

See [KB_STRUCTURE.md](./KB_STRUCTURE.md) for detailed guidelines.

### 4. Ingest Knowledge Base

```bash
python -m src.ingestion.ingest --kb-path ./knowledge_base --context-id my_kb
```

### 5. Start CLI Chat

```bash
python -m src.interface.cli.main --context-id my_kb
```

## Architecture

### Core Components

- **BaseAgent**: Base class for all agents with LLM, memory, and tool execution
- **OrchestratorAgent**: Main agent that manages conversation flow and delegates to specialists
- **Specialist Agents**: Content, Structure, Detail, and Format analyzers for deep analysis
- **CRAG Validator**: Validates and corrects retrieved context for relevance
- **Semantic Search**: Hybrid search combining keyword and vector embeddings

### Data Flow

1. User asks question via CLI
2. OrchestratorAgent determines if multi-agent orchestration is needed
3. Semantic search retrieves relevant chunks (with CRAG validation)
4. Specialist agents analyze complex queries
5. OrchestratorAgent synthesizes responses
6. "Glass box" output shows reasoning, tool calls, and final answer

## Configuration

### Environment Variables

- `GEMINI_API_KEY`: Google Gemini API key (required)
- `DATABASE_URL`: PostgreSQL connection string
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR)

### Config Files

- `config/config.yaml`: Main configuration
- `config/orchestrator.yaml`: Orchestrator agent configuration
- `config/prompts/`: Prompt templates for agents

## Usage Examples

### Simple Question

```
> What is the main topic of the knowledge base?

[REASONING] Processing question...
[TOOL] semantic_search(query="main topic")
🔍 CRAG Validation: 3/5 chunks validated (avg relevance: 0.85)

[Final Answer]
The knowledge base covers...
```

### Complex Question (Multi-Agent)

```
> How is the content structured and what are the key details?

[REASONING] Processing question...
🔄 Multi-Agent Orchestration: Structure Analyzer, Detail Analyzer

🧠 Structure Analyzer:
[Analysis of document structure...]

🔍 Detail Analyzer:
[Analysis of key details...]

[Final Answer]
[Synthesized answer combining both analyses...]
```

## Knowledge Base Setup

See [KB_STRUCTURE.md](./KB_STRUCTURE.md) for:
- Folder structure guidelines
- Naming conventions
- Metadata extraction rules
- Best practices

## Advanced

### Multi-Agent Orchestration

The orchestrator automatically triggers specialist agents for:
- Complex analytical questions
- Questions requiring multiple perspectives
- Deep-dive analysis requests

### CRAG Validation

CRAG (Corrective RAG) ensures retrieved chunks are relevant:
- Grades chunks for relevance (0.0-1.0)
- Rewrites queries when insufficient relevant chunks found
- Provides metrics in "glass box" output

### Custom Agents

Create custom specialist agents by inheriting from `BaseSpecialistAgent`:

```python
from src.agents.base_specialist import BaseSpecialistAgent

class CustomAnalyzerAgent(BaseSpecialistAgent):
    def __init__(self, config_path: str):
        super().__init__(config_path)
        # Custom initialization
```

## Troubleshooting

### Database Connection Issues

- Verify PostgreSQL is running
- Check `DATABASE_URL` format
- Ensure pgvector extension is installed

### No Results from Search

- Verify knowledge base was ingested successfully
- Check `context_id` matches ingestion context_id
- Ensure chunks exist in database

### Import Errors

- Verify all dependencies installed: `pip install -r requirements.txt`
- Check Python path includes project root
- Verify `__init__.py` files exist in all packages

## Contributing

This is a boilerplate project extracted from StoryForge. Contributions welcome!

## License

[Specify license]

## Acknowledgments

Extracted and generalized from StoryForge's Agentic CRAG system.

