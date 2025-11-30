# Performance Optimization Plan: Sequential to Parallel Architecture

**Last Updated**: Current Session  
**Status**: Documented - Ready for Implementation  
**Expected Impact**: 60-70% performance improvement (20s → 6-8s)

---

## Problem Statement

**Current Performance**: ~20 seconds for knowledge base queries with local Postgres database.

**Root Cause**: Architecture problem, not database problem. The system uses a **Sequential Chain** pattern (A → B → C) instead of **Parallel Map-Reduce** pattern (A → [B1, B2] → C).

**Bottleneck Breakdown** (from audit):
1. **Sequential Search Execution** (~8-10s): Supervisor routes → semantic_search → Supervisor thinks → semantic_search again
2. **Verbose Response Generation** (~5-8s): LLM generates 500+ word responses without brevity constraints
3. **CPU-Only Embedding Model** (~2-3s): SentenceTransformer runs on CPU, ignoring Mac's Neural Engine (MPS)

**Database Performance**: Local Postgres with pgvector is fast (<0.05s per query). Not the bottleneck.

---

## Architecture Shift: Sequential → Parallel

**Current Pattern (Sequential Chain)**:
```
Supervisor → semantic_search → Supervisor (thinks) → semantic_search → Supervisor → FINISH → Synthesis
Time: ~20s (sequential ping-pong)
```

**Target Pattern (Parallel Map-Reduce)**:
```
Supervisor → [semantic_search(query1), semantic_search(query2)] (parallel) → Supervisor → FINISH → Synthesis
Time: ~6-8s (parallel scatter-gather)
```

---

## Optimization Phases

### Phase 1: Hardware Optimization (Quick Win)

**Goal**: Speed up embedding generation by 50% (Savings: 0.5s - 1s)

**Priority**: HIGHEST (quickest to implement, immediate baseline improvement)

**Implementation**:
- **File**: `src/core/base_agent.py`
- **Change**: Update `_create_embedding_model()` to detect and use Apple Silicon MPS

**Code Change**:
```python
def _create_embedding_model(self):
    """Create local embedding model for semantic search."""
    import torch
    
    # Detect optimal device
    device = "cpu"
    if torch.backends.mps.is_available():
        device = "mps"  # Apple Metal Performance Shaders (Mac Neural Engine)
        logger.info("✅ Using Apple Silicon MPS for embedding model")
    elif torch.cuda.is_available():
        device = "cuda"  # NVIDIA GPU
        logger.info("✅ Using CUDA GPU for embedding model")
    else:
        logger.info("⚠️ Using CPU for embedding model (no GPU/MPS available)")
    
    if not SENTENCE_TRANSFORMERS_AVAILABLE:
        # ... existing fallback code ...
    
    try:
        model = SentenceTransformer("all-MiniLM-L6-v2", device=device)
        logger.info(f"✅ Local embedding model loaded on device: {device}")
        # ... rest of existing code ...
```

**Expected Impact**: 
- Mac M1/M2/M3: ~50% faster embeddings (500ms → 250ms per query)
- Zero risk change (fallback to CPU if MPS unavailable)

**Files to Update**:
- `src/core/base_agent.py` - Add device detection logic

---

### Phase 2: Parallel Search Execution (Biggest Impact)

**Goal**: Reduce latency by ~40-50% (Savings: 8s)

**Priority**: HIGH (biggest architectural change, solves the '20 second' wait)

**Architecture Change**: Move from Sequential Chain to Parallel Map-Reduce

**Current Flow**:
1. Supervisor routes to semantic_search with single query
2. semantic_search executes, returns results
3. Supervisor reads results, realizes more info needed
4. Supervisor routes to semantic_search again with new query
5. Repeat until satisfied

**Target Flow**:
1. Supervisor analyzes question and generates ALL necessary queries upfront
2. Supervisor routes to semantic_search ONCE with list of queries
3. semantic_search executes ALL queries in parallel
4. semantic_search merges results and returns
5. Supervisor synthesizes final answer

**Implementation Steps**:

**Step 2.1: Update Supervisor Prompt**
- **File**: `prompts/orchestrator/supervisor.txt`
- **Change**: Add instruction to generate multiple queries upfront

**New Instruction**:
```
ROUTING RULES:
...
8. For knowledge base queries requiring multiple topics (e.g., "what is X and how does Y work"), generate ALL necessary search queries upfront. Output queries as a JSON list or newline-separated list in the instruction field.
   Example: User asks "what are supply deals and the supply->curate->activate flow"
   → Route: semantic_search, Instruction: ["Search for definition of supply deals in Bedrock platform", "Search for supply->curate->activate workflow"]
```

**Step 2.2: Update Semantic Search Node**
- **File**: `src/agents/orchestrator/graph/nodes/semantic_search.py`
- **Change**: Accept list of queries, execute in parallel

**Code Change**:
```python
def semantic_search_node(state: AgentState) -> AgentState:
    instruction = state.get("current_task_instruction", "")
    user_question = state.get("user_question", "")
    
    # Parse instruction - could be single query or list of queries
    if instruction.startswith('[') or '\n' in instruction:
        # Try to parse as JSON list or newline-separated
        try:
            import json
            queries = json.loads(instruction)
        except:
            # Fallback: newline-separated
            queries = [q.strip() for q in instruction.split('\n') if q.strip()]
    else:
        queries = [instruction if instruction else user_question]
    
    # Execute searches in parallel
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(queries)) as executor:
        search_futures = [
            executor.submit(semantic_search_func, query=q, chunk_types=None, limit=5)
            for q in queries
        ]
        search_results = [future.result() for future in concurrent.futures.as_completed(search_futures)]
    
    # Merge and format results
    # ... aggregate logic ...
```

**Step 2.3: Update Supervisor Routing Logic**
- **File**: `src/agents/orchestrator/graph/supervisor.py`
- **Change**: Ensure supervisor only routes to semantic_search once per question

**Expected Impact**: 
- Eliminates sequential ping-pong routing
- Reduces from 2-3 search iterations to 1 parallel batch
- ~40-50% reduction in total time (20s → 12s)

**Files to Update**:
- `prompts/orchestrator/supervisor.txt` - Add multi-query instruction
- `src/agents/orchestrator/graph/nodes/semantic_search.py` - Add parallel execution
- `src/agents/orchestrator/graph/supervisor.py` - Update routing logic

---

### Phase 3: Verbosity Control (UX Polish)

**Goal**: Speed up text generation by ~30% (Savings: 5s)

**Priority**: MEDIUM (polishes final output speed)

**Problem**: Orchestrator generates verbose responses (500+ words) without brevity constraints.

**Implementation**:

**Step 3.1: Update Synthesis Prompt**
- **File**: `src/agents/orchestrator/orchestrator.py`
- **Change**: Add explicit brevity constraints

**Code Change**:
```python
synthesis_prompt = f"""The user asked: {question}

The following specialist agents have provided their responses:

{responses_text}

Please synthesize these responses into a clear, concise answer that directly addresses the user's question. 
**IMPORTANT:**
- Be CONCISE. Use bullet points for lists.
- Limit response to key facts found.
- Do NOT summarize the search process itself.
- Get to the point quickly - avoid fluff and repetition.
- Target: 100-200 words maximum unless the question requires detailed explanation.

Combine insights from all agents where relevant, and present the information efficiently."""
```

**Step 3.2: Reduce Max Tokens**
- **File**: `config/config.yaml`
- **Change**: Reduce `default_max_tokens` from 2000 to 1000-1500

**Expected Impact**:
- Faster generation (fewer tokens = less time)
- More focused responses
- ~30% reduction in generation time (5-8s → 3-5s)

**Files to Update**:
- `src/agents/orchestrator/orchestrator.py` - Update synthesis prompt
- `config/config.yaml` - Reduce max_tokens

---

## Implementation Priority Order

**Approved by Consultant**:

1. **Phase 1: Hardware Optimization** (Fix 3)
   - **Priority**: HIGHEST
   - **Reason**: Quickest to implement, immediate baseline improvement
   - **Risk**: Zero (fallback to CPU if MPS unavailable)
   - **Time**: ~15 minutes

2. **Phase 2: Parallelization** (Fix 1)
   - **Priority**: HIGH
   - **Reason**: Biggest architectural change, solves the '20 second' wait
   - **Risk**: Low (adds parallel execution, maintains backward compatibility)
   - **Time**: ~2-3 hours

3. **Phase 3: Verbosity Control** (Fix 2)
   - **Priority**: MEDIUM
   - **Reason**: Polishes final output speed
   - **Risk**: Very Low (just prompt/config changes)
   - **Time**: ~30 minutes

**NOT Approved Yet**:
- **Fix 4: Reducing Routing Iterations** - Consultant wants to see if Phase 2 (Parallelization) solves routing redundancy naturally first.

---

## Expected Performance Improvements

| Phase | Current Time | Optimized Time | Savings | Cumulative |
|-------|--------------|----------------|---------|------------|
| Baseline | 20s | - | - | 20s |
| Phase 1 (Hardware) | 20s | 19s | 1s (5%) | 19s |
| Phase 2 (Parallel) | 19s | 11s | 8s (42%) | 11s |
| Phase 3 (Verbosity) | 11s | 6-8s | 3-5s (27-45%) | **6-8s** |

**Total Expected Improvement**: **60-70% reduction** (20s → 6-8s)

---

## Technical Details

### Parallel Execution Pattern

**Current (Sequential)**:
```python
# Supervisor routes
result1 = semantic_search(query1)  # Wait 2s
# Supervisor thinks
result2 = semantic_search(query2)  # Wait 2s
# Total: 4s
```

**Target (Parallel)**:
```python
# Supervisor routes with list
results = parallel_search([query1, query2])  # Wait 2s (both run simultaneously)
# Total: 2s
```

**Implementation Options**:
1. **ThreadPoolExecutor** (Recommended for local): Simple, works with synchronous code
2. **asyncio.gather()**: Requires async/await refactoring
3. **LangGraph parallel nodes**: Would require graph restructuring

**Recommendation**: Use `ThreadPoolExecutor` for Phase 2 - minimal code changes, maximum impact.

### Device Detection Logic

**Mac Detection**:
```python
import torch
if torch.backends.mps.is_available():
    device = "mps"  # Apple Silicon Neural Engine
```

**Benefits**:
- MPS uses Mac's Neural Engine (dedicated ML hardware)
- ~2x faster than CPU for transformer models
- Zero code changes elsewhere (transparent to rest of codebase)

---

## Testing Plan

**Before Implementation**:
1. Baseline measurement: Time a complex query (e.g., "what are supply deals and the supply->curate->activate flow")
2. Record: Total time, number of searches, response length

**After Each Phase**:
1. Re-run same query
2. Compare: Time reduction, search count, response quality
3. Verify: No regressions in answer quality

**Success Criteria**:
- Phase 1: Embedding time reduced by ~50%
- Phase 2: Total time reduced by ~40-50%, single parallel search instead of multiple sequential
- Phase 3: Response generation time reduced by ~30%, responses more concise

---

## Risk Assessment

| Phase | Risk Level | Mitigation |
|-------|-----------|------------|
| Phase 1 (Hardware) | **Zero** | Fallback to CPU if MPS unavailable |
| Phase 2 (Parallel) | **Low** | Maintain backward compatibility (single query still works) |
| Phase 3 (Verbosity) | **Very Low** | Just prompt/config changes, easily reversible |

---

## Future Considerations

**Not Implementing Now** (per consultant):
- **Fix 4: Reducing Routing Iterations** - Wait to see if Phase 2 naturally solves this

**Potential Future Optimizations**:
- **Caching**: Cache embedding results for common queries
- **Streaming**: Stream responses as they're generated (already partially implemented)
- **Batch Embedding**: Batch multiple queries into single embedding call (if model supports)
- **Graph Restructuring**: Use LangGraph's parallel node execution (requires larger refactor)

---

## Key Learnings

1. **Database is NOT the bottleneck**: Local Postgres with pgvector is fast (<0.05s). The bottleneck is LLM cognition time and sequential execution.

2. **Architecture matters more than hardware**: Moving from sequential to parallel execution has bigger impact than hardware optimization alone.

3. **Prompt engineering can control verbosity**: Explicit brevity instructions significantly reduce generation time without sacrificing quality.

4. **Mac hardware is underutilized**: MPS (Metal Performance Shaders) provides significant speedup for transformer models but requires explicit device specification.

---

## Files Summary

**Phase 1 (Hardware)**:
- `src/core/base_agent.py` - Add device detection

**Phase 2 (Parallel)**:
- `prompts/orchestrator/supervisor.txt` - Add multi-query instruction
- `src/agents/orchestrator/graph/nodes/semantic_search.py` - Add parallel execution
- `src/agents/orchestrator/graph/supervisor.py` - Update routing logic

**Phase 3 (Verbosity)**:
- `src/agents/orchestrator/orchestrator.py` - Update synthesis prompt
- `config/config.yaml` - Reduce max_tokens

**Total Files**: 6 files to modify

---

## Consultant Approval Summary

✅ **Approved for Implementation**:
- Phase 1: Hardware Optimization (MPS)
- Phase 2: Parallel Search Execution
- Phase 3: Verbosity Control

⏸️ **Deferred**:
- Fix 4: Reducing Routing Iterations (wait to see if Phase 2 solves it naturally)

**Priority Order**: Hardware → Parallel → Verbosity

**Expected Result**: 20s → 6-8s (60-70% improvement)

---

## References

- **Audit Report**: See `AI_HANDOFF.md` for detailed codebase audit findings
- **Consultant Recommendations**: Based on performance analysis and architecture review
- **Related Documents**: `docs/langgraph_migration_plan.md` for architectural context

