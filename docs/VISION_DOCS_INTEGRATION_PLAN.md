# Vision Documentation Integration Plan

**Status**: Planning Document (to be removed after completion)  
**Date**: December 2025  
**Purpose**: Comprehensive plan to integrate vision documentation from `agentic_framework/` into `docs/vision/`, remove MCP references, add Orchestrator agent, and establish cross-references.

---

## Executive Summary

This plan outlines the integration of strategic vision documentation into the main codebase documentation structure. The vision docs currently reference MCP (Model Context Protocol) which was abandoned in favor of LangGraph's direct tool integration. Additionally, the Orchestrator agent (central supervisor) is missing from the vision docs but is critical to the current implementation.

**Key Objectives**:
1. Relocate vision docs to `docs/vision/` for better organization
2. Remove all MCP references and replace with LangGraph-based architecture
3. Add Orchestrator agent documentation throughout vision docs
4. Establish cross-references between vision and implementation docs
5. Update main README and AI_HANDOFF.md to reference vision docs

---

## Current State Analysis

### Vision Docs Location
- **Current**: `/agentic_framework/` (5 markdown files)
- **Target**: `/docs/vision/` (new subdirectory)

### Files to Migrate
1. `README.md` - Vision overview
2. `FOUR_LAYER_ARCHITECTURE.md` - Architecture foundation
3. `PROGRESSIVE_AUTONOMY.md` - 4-stage autonomy model
4. `SYSTEM_OF_RECORD.md` - Learning engine design
5. `TOOL_DEVELOPMENT_MATRIX.md` - Tool registry and roadmap

### MCP References Found
- **Total**: 97 instances across all files
- **Types**: "MCP Server", "MCP wrapper", "MCP.call_tool()", "MCP Live" status, etc.
- **Replacement Strategy**: Replace with LangGraph-based architecture terminology

### Missing Component
- **Orchestrator Agent**: Central supervisor/router not mentioned in any vision docs
- **Impact**: Vision docs don't reflect current LangGraph Supervisor Pattern implementation

---

## Phase 1: File Relocation

### Actions
- [ ] Create `docs/vision/` directory
- [ ] Move all 5 files from `agentic_framework/` to `docs/vision/`
- [ ] Delete `agentic_framework/` directory after verification

### New Structure
```
docs/
├── vision/                          # NEW: Vision & strategic planning
│   ├── README.md                    # Vision overview (main entry point)
│   ├── FOUR_LAYER_ARCHITECTURE.md  # Architecture foundation
│   ├── PROGRESSIVE_AUTONOMY.md    # 4-stage autonomy model
│   ├── SYSTEM_OF_RECORD.md         # Learning engine design
│   └── TOOL_DEVELOPMENT_MATRIX.md  # Tool registry & roadmap
├── PROACTIVE_NOTIFICATION_PANEL.md  # Existing feature docs
├── TOOL_INSTRUCTIONS_ARCHITECTURE.md
└── CHAINLIT_SQLITE_PERSISTENCE.md
```

---

## Phase 2: MCP Removal & Architecture Updates

**Objective**: Remove ALL MCP references from vision docs. This project does NOT use MCP - there are no legitimate external references. The only "mcp" found elsewhere is "mCPM" (advertising metric), which is unrelated.

### Terminology Replacement Table

| Old (MCP-based) | New (LangGraph-based) |
|----------------|----------------------|
| "Level 2: MCP (Communication)" | "Level 2: LangGraph Tool Integration" |
| "MCP Server" | "LangGraph Tool Registry" or "Tool Integration Layer" |
| "MCP wrapper" | "Direct tool integration" |
| "MCP tool" | "Tool" or "LangGraph tool" |
| "MCP.call_tool()" | "Tool invocation via LangGraph" |
| "MCP Live" status | "Production Ready" or "Integrated" |
| "MCP Integration Needed" | "Needs Integration" or "POC Ready" |
| "MCP's Critical Role" | "LangGraph Tool Integration's Role" |

### File-Specific Updates

#### 2.1 FOUR_LAYER_ARCHITECTURE.md

**Updates Required**:
- [ ] Replace "Level 2: MCP" with "Level 2: LangGraph Tool Integration"
- [ ] Update all diagrams to show LangGraph instead of MCP Server
- [ ] Change `mcp.call_tool()` examples to LangGraph tool invocation patterns
- [ ] Update "MCP's Critical Role" section → "LangGraph Tool Integration's Role"
- [ ] Remove MCP discovery examples, replace with LangGraph tool binding examples
- [ ] Update Phase 1/2 stack diagrams to show LangGraph architecture

**Key Sections to Update**:
- Complete Stack Diagram (lines ~23-102)
- Information Flow examples (lines ~166-235)
- MCP's Critical Role section (lines ~312-344)
- Phase 1/2 Stack diagrams (lines ~565-620)

#### 2.2 PROGRESSIVE_AUTONOMY.md

**Updates Required**:
- [ ] Replace all `mcp.call_tool()` references with tool invocation examples
- [ ] Update workflow diagrams to remove MCP layer
- [ ] Keep autonomy stages intact (they're architecture-agnostic)
- [ ] Update code examples to show LangGraph tool calls

**Key Sections to Update**:
- Workflow examples (lines ~64-99)
- Stage 2-4 examples with tool calls (throughout)

#### 2.3 SYSTEM_OF_RECORD.md

**Updates Required**:
- [ ] Replace `mcp.call_tool()` references in code examples
- [ ] Update database schema if it references MCP tool names (check line 43)
- [ ] Keep learning logic intact (architecture-agnostic)
- [ ] Update tool invocation examples

**Key Sections to Update**:
- Code examples with tool calls (lines ~85, 206, 474)

#### 2.4 TOOL_DEVELOPMENT_MATRIX.md

**Updates Required**:
- [ ] Remove "MCP Status" column OR rename to "Integration Status"
- [ ] Update status values:
  - "MCP Live" → "Production Ready"
  - "MCP Integration Needed" → "Needs Integration"
  - "⚪ Not Started" → Keep as is
- [ ] Remove "POC → MCP Integration Process" section (lines ~377-410) OR replace with "POC → Production Integration Process"
- [ ] Update tool examples to remove MCP wrapper references
- [ ] Update development path visualizations (lines ~150-200)

**Key Sections to Update**:
- Master Tool Registry table (lines ~75-101)
- Column Definitions - MCP Status (lines ~135-140)
- Development Path Visualization (lines ~150-200)
- POC → MCP Integration Process (lines ~377-410)

#### 2.5 vision/README.md

**Updates Required**:
- [ ] Update "Foundation" line: Remove "communication (MCP)" reference
- [ ] Update "Key Principles" section to remove MCP references
- [ ] Update Phase 1/2 descriptions to reference LangGraph instead of MCP
- [ ] Update "Development Context" section to remove MCP references

**Key Sections to Update**:
- Foundation description (line 16)
- Key Principles - Separation of Concerns (line 87)
- Phase 1/2 implementation descriptions (lines ~118-138)

#### 2.6 Remove Tool Holster References

**README.md Updates**:
- [ ] Remove line 10: "Cost & Inhibition Protocols" bullet point about Tool Holster
- [ ] Update line 204: Remove "holstering, and" from TOOL_INSTRUCTIONS_ARCHITECTURE.md description

**TOOL_INSTRUCTIONS_ARCHITECTURE.md Updates**:
- [ ] Update overview (line 10): Change from 5 layers to 4 layers, remove "Tool Holstering"
- [ ] Remove entire "Layer 4: Tool Holstering" section (lines 161-212)
- [ ] Update "Complete Flow Diagram" (lines 239-279): Remove tool holstering decision branch
- [ ] Remove "Tool Holstering Implementation" section (lines 321-339)
- [ ] Update "File Locations" section (line 386): Remove `analyze_without_tools()` and holstering detection references
- [ ] Update "Benefits" section (line 405): Remove benefit #7 about tool holstering
- [ ] Remove "Step 4: Implement Tool Holstering" from "Adding New Tools" (lines 453-459)
- [ ] Update "Maintenance" section (line 468): Remove tool holstering maintenance note
- [ ] Remove "Tool Holstering" error handling subsection (lines 479-481)
- [ ] Update "Related Documentation" section (line 492): Remove tool holstering reference

---

## Phase 3: Orchestrator Agent Integration

### Architecture Update

**Current vision says**: "Three-layer architecture: Agents → Communication → Tools"  
**Should say**: "Four-layer architecture: Orchestrator → Specialist Agents → Tool Integration → Tools"

### Updated Architecture Layers

```
Level 4: HUMAN OPERATORS
    ↕️ Supervises
Level 3: ORCHESTRATOR AGENT (Coordination Layer)
    ↕️ Routes to
Level 2: SPECIALIST AGENTS (Intelligence Layer)
    • Guardian Agent (portfolio oversight)
    • Specialist Agent (diagnostics & fixes)
    • Optimizer Agent (budget & bid mgmt)
    • Pathfinder Agent (supply chain navigation)
    ↕️ Uses
Level 1: TOOL INTEGRATION (LangGraph Tool System)
    ↕️ Invokes
Level 0: TOOLS & KNOWLEDGE BASE (Capabilities)
```

### File-Specific Orchestrator Updates

#### 3.1 vision/README.md

**Updates Required**:
- [ ] Update "Agent Team" section to include Orchestrator first:
  ```markdown
  **Agent Team**:
  - **Orchestrator Agent**: Central supervisor and router that coordinates all specialist agents, handles knowledge base queries, and provides conversational interface
  - **Guardian Agent**: Portfolio oversight and system-wide monitoring
  - **Specialist Agent**: Individual diagnostics and autonomous fixes
  - **Optimizer Agent**: Campaign performance and budget optimization
  - **Pathfinder Agent**: Supply chain navigation and SSP coordination
  ```

- [ ] Update "Foundation" line:
  ```markdown
  **Foundation**: Four-layer architecture separating coordination (Orchestrator), intelligence (specialist agents), tool integration (LangGraph), and capabilities (tools) for maximum flexibility and reusability.
  ```

- [ ] Add new "I Want to Understand..." entry:
  ```markdown
  **"What is the Orchestrator Agent?"**
  → The Orchestrator is the central supervisor that routes user questions to appropriate specialist agents or answers directly. See [Four-Layer Architecture](FOUR_LAYER_ARCHITECTURE.md) for details.
  ```

#### 3.2 FOUR_LAYER_ARCHITECTURE.md

**Updates Required**:
- [ ] Add new section "The Orchestrator Agent (Coordination Layer)" after "Complete Stack Diagram"
  - Primary Role: Central supervisor and intelligent router
  - Responsibilities: Routing, coordination, conversational interface
  - Routing capabilities: Direct answer, semantic search, agent routing, multi-agent coordination
  - What it does NOT do: Execute specialist tasks, access tools directly

- [ ] Update "Agent Responsibilities" section - Add Orchestrator FIRST:
  - Primary Role: Intelligent routing, coordination, conversational interface
  - Routing Logic: Portfolio → Guardian, Technical → Specialist, etc.
  - Architecture Position: Sits above specialist agents

- [ ] Update "Complete Stack Diagram" to include Orchestrator as Level 3

- [ ] Update "Information Flow" section - Add Orchestrator to all flows:
  - Diagnostic Flow: User → Orchestrator → Supervisor → Guardian → Tools
  - Action Flow: User → Orchestrator → Supervisor → Optimizer → Tools

- [ ] Update "Phase 1 Stack" diagram:
  ```
  Humans
      ↕️
  Orchestrator Agent (Supervisor/Router)
      ↕️ Routes via LangGraph
  Guardian Agent
      ↕️
  LangGraph Tool Integration
      ↕️
  Diagnostic Tools (Python)
      ↕️
  Databases & APIs
  ```

- [ ] Update "Phase 2 Stack" diagram to show Orchestrator at top coordinating all agents

#### 3.3 PROGRESSIVE_AUTONOMY.md

**Updates Required**:
- [ ] Update all workflow examples to include Orchestrator:
  ```
  User Question → Orchestrator Agent
  Orchestrator → Supervisor Node (LangGraph)
  Supervisor → RouteDecision: "guardian"
  Guardian → [execution]
  Guardian → Response to Orchestrator
  Orchestrator → User
  ```

- [ ] Update Stage 1-4 workflow examples throughout document

#### 3.4 SYSTEM_OF_RECORD.md

**Updates Required**:
- [ ] Update "Overview" section to mention Orchestrator:
  ```markdown
  The Orchestrator coordinates specialist agents, which then log their recommendations and outcomes to the SoR for learning.
  
  **Flow**:
  1. User Question → Orchestrator → Routes to Specialist Agent
  2. Specialist Agent → Makes recommendation → Logs to SoR
  3. System detects changes → Updates SoR with outcomes
  4. SoR calculates success rates → Informs future agent decisions
  ```

#### 3.5 TOOL_DEVELOPMENT_MATRIX.md

**Updates Required**:
- [ ] Add Orchestrator to "AGENT ROLES & TOOL ACCESS PATTERNS" section FIRST:
  ```markdown
  ### Orchestrator Agent (Central Supervisor)
  
  **Primary Role**: Intelligent routing, coordination, and conversational interface
  
  **Responsibilities**:
  - Routes user questions to appropriate specialist agents
  - Handles knowledge base semantic search queries
  - Answers simple questions directly
  - Coordinates multi-agent workflows
  - Synthesizes responses from multiple agents
  
  **Tool Access**: 
  - Semantic Search tool (for knowledge base queries)
  - Does NOT access specialist tools directly (delegates to specialist agents)
  
  **Architecture Position**: Coordination layer above specialist agents
  ```

---

## Phase 4: Cross-Referencing Updates

### 4.1 Main README.md

**Location**: Root `/README.md`

**Updates Required**:
- [ ] Update "Agent Roster" section (lines 15-22):
  ```markdown
  ## 🤖 Agent Roster

  The system orchestrates five agents:

  1.  **💠 Orchestrator Agent**: Central supervisor and router that coordinates all specialist agents, handles knowledge base queries, and provides conversational interface.
  2.  **🛡️ Guardian Agent**: Portfolio oversight, health monitoring, and anomaly detection. Equipped with the `analyze_portfolio_pacing` tool.
  3.  **🔬 Specialist Agent**: Deep diagnostic analysis, root cause identification, and troubleshooting.
  4.  **🎯 Optimizer Agent**: Budget allocation, bid optimization, and creative rotation strategies.
  5.  **🧭 Pathfinder Agent**: Supply chain navigation, QPS optimization, and SSP relationship management.
  ```

- [ ] Add new section after "Documentation" heading:
  ```markdown
  ## 📚 Documentation

  ### Core Architecture
  - **`docs/TOOL_INSTRUCTIONS_ARCHITECTURE.md`**: Complete guide to tool development and instruction injection at runtime

  ### Vision & Strategic Planning
  - **`docs/vision/README.md`**: Vision for autonomous deal optimization & supply chain management
  - **`docs/vision/FOUR_LAYER_ARCHITECTURE.md`**: Foundation architecture separating coordination, intelligence, tool integration, and capabilities
  - **`docs/vision/PROGRESSIVE_AUTONOMY.md`**: Four-stage evolution from alerts to autonomous action
  - **`docs/vision/SYSTEM_OF_RECORD.md`**: Learning engine design for building trust and validation
  - **`docs/vision/TOOL_DEVELOPMENT_MATRIX.md`**: Comprehensive tool registry and development roadmap

  ### UI & Persistence
  - **`docs/CHAINLIT_SQLITE_PERSISTENCE.md`**: Guide to enabling Chainlit conversation history using SQLite
  - **`docs/PROACTIVE_NOTIFICATION_PANEL.md`**: North star feature - transforming from reactive chatbot to proactive command center
  ```

### 4.2 AI_HANDOFF.md

**Location**: Root `/AI_HANDOFF.md`

**Updates Required**:
- [ ] Add reference in "System Overview" section:
  ```markdown
  ## System Overview

  **Architecture**: LangGraph Supervisor Pattern  
  **Model Standard**: `gemini-2.5-flash` (all agents)  
  **Routing**: Structured Output (`RouteDecision`) - NO tools  
  **State Management**: LangGraph `AgentState` TypedDict

  **Vision**: See [`docs/vision/README.md`](../docs/vision/README.md) for the strategic vision and progressive autonomy model that guides this implementation.
  ```

### 4.3 vision/README.md

**Location**: `docs/vision/README.md` (after migration)

**Updates Required**:
- [ ] Update "Development Context" section:
  ```markdown
  ### Related Planning Documents

  - **[Deal Debugging Plan](../../plans/deal_debugging_plan.md)** - Technical specifications for diagnosis tools
  - **[Deal Toolkit Architecture](../../plans/deal_toolkit_architecture.md)** - Current tool capabilities and integration patterns
  - **[AI Handoff Document](../../AI_HANDOFF.md)** - Implementation reference for current architecture
  - **[Tool Instructions Architecture](../TOOL_INSTRUCTIONS_ARCHITECTURE.md)** - Tool development patterns
  ```

---

## Phase 5: Verification & Cleanup

### Verification Checklist
- [ ] Search codebase for remaining MCP references in vision docs (should be ZERO)
- [ ] Verify Orchestrator is properly documented in all vision docs
- [ ] Test all markdown links (internal and cross-references)
- [ ] Review for consistency with current architecture
- [ ] Verify all diagrams reflect LangGraph architecture
- [ ] Check that workflow examples include Orchestrator
- [ ] Ensure tool status tracking reflects current implementation

### Note on Knowledge Base Files
- The only "mcp" found in knowledge-base files is "mCPM" (milli Cost Per Mille), which is an advertising metric and unrelated to Model Context Protocol
- No action needed for knowledge-base files - they don't contain MCP references

### Final Cleanup
- [ ] Remove this plan document (`docs/VISION_DOCS_INTEGRATION_PLAN.md`) after completion
- [ ] Update any other docs that reference `agentic_framework/` path

---

## Implementation Order

### Recommended Sequence

1. **Phase 1**: File relocation (quick, low risk)
2. **Phase 2**: MCP removal (systematic, file by file)
   - **Phase 2.6**: Remove tool holster references (README.md + TOOL_INSTRUCTIONS_ARCHITECTURE.md)
3. **Phase 3**: Orchestrator integration (adds new content)
4. **Phase 4**: Cross-referencing (connects everything)
   - **Phase 4.1**: Update README.md (agent roster + documentation section)
5. **Phase 5**: Verification (ensures completeness)

### Estimated Effort

- **Phase 1**: 5 minutes (file operations)
- **Phase 2**: 2-3 hours (search/replace + review)
  - **Phase 2.6**: 30 minutes (tool holster removal)
- **Phase 3**: 1-2 hours (new content + updates)
- **Phase 4**: 45 minutes (link updates + README agent roster)
- **Phase 5**: 1 hour (verification + testing)

**Total**: ~5-7 hours

---

## Success Criteria

✅ All vision docs relocated to `docs/vision/`  
✅ Zero MCP references in vision docs (no exceptions - this project doesn't use MCP)  
✅ Zero tool holster references in README.md and TOOL_INSTRUCTIONS_ARCHITECTURE.md  
✅ Orchestrator agent documented in all relevant vision docs  
✅ README agent roster updated with Orchestrator (💠) and Specialist emoji changed to 🔬  
✅ All cross-references working correctly  
✅ Architecture diagrams reflect LangGraph Supervisor Pattern  
✅ Workflow examples include Orchestrator routing  
✅ Main README and AI_HANDOFF reference vision docs  
✅ All internal links verified and working  

---

## Notes

- **Preserve Core Concepts**: The vision's core concepts (progressive autonomy, four-layer architecture, system of record) remain valid - only the communication layer changes
- **Architecture Agnostic**: Autonomy stages and learning logic are architecture-agnostic and should remain intact
- **Tool Status**: Update tool status tracking to reflect current direct integration (no MCP wrapper needed)
- **Future-Proof**: Ensure updates don't lock us into current implementation details unnecessarily

---

**This plan will be removed after successful completion of all phases.**

