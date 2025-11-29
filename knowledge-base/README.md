# Bedrock AI Knowledge Base

RAG-optimized content for troubleshooting tools and AI agents. **Optimized for conciseness and actionability** - see [kb-style-guide.md](kb-style-guide.md) for contribution guidelines.

## Optimization Stats

**Total Reduction**: 2,001+ lines removed (30% reduction)
- 6 files compressed (average 40% reduction per file)
- 4 low-value files removed
- All files now < 500 lines (optimal for RAG performance)

---

## Content Structure

### 01-platform-overview/
Business context and high-level platform capabilities

### 02-business-features/
Campaign management, retargeting, frequency capping, reporting (customer-facing features)

### 03-technical-features/
Platform architecture, APIs, integration capabilities, real-time processing

### 04-business-strategy/
Business strategy, revenue optimization (consider moving to `/docs`)

### 05-integrations/
Partner ecosystem, integration setup, external system connections

### 06-operations/ ⭐ **PRIMARY TROUBLESHOOTING FOCUS**
- **campaign-troubleshooting.md** - Campaign-level issue resolution
- **deal-debug-workflow.md** - Deal debugging best practices
- **performance-optimization.md** - Performance tuning strategies
- Data quality management, system monitoring, platform updates

### 07-maintenance/
Database management, system administration

### 08-bidswitch-integration/ ⭐ **PRIMARY DEAL TROUBLESHOOTING FOCUS**
- **diagnostic-patterns.md** - Automated diagnostic rules
- **bidswitch-deals-management.md** - Deal lifecycle and troubleshooting
- **smartswitch-mechanism.md** - SmartSwitch ML behavior

---

## Content Guidelines

### File Size Targets
- **Optimal**: < 200 lines
- **Acceptable**: 200-400 lines
- **Review needed**: 400-500 lines
- **Too large**: > 500 lines (compress or split immediately)

### Writing Principles
- **Actionable first**: Symptoms → Detection → Resolution → Impact
- **One example per concept**: No duplicates
- **Cross-reference over duplicate**: Link instead of copying
- **Concise format**: Bullet points, tables, compressed prose
- **Tool-focused**: Serve troubleshooting agents, not business planning

### Quality Standards
- No duplicate content across files
- All cross-references valid after folder renumbering
- Consistent formatting (see kb-style-guide.md)
- Focus on operational procedures, not strategy

---

## Recent Optimizations (Oct 2025)

**Compressed Files**:
- `deal-debug-workflow.md`: 614 → 281 lines (54% reduction)
- `diagnostic-patterns.md`: 636 → 446 lines (30% reduction)
- `campaign-troubleshooting.md`: 766 → 489 lines (36% reduction)
- `retargeting.md`: 321 → 208 lines (35% reduction)
- `frequency-capping.md`: 314 → 158 lines (50% reduction)
- `performance-optimization.md`: 923 → 240 lines (74% reduction)

**Removed Files**:
- `competitive-analysis.md` (low-value strategic content)
- `market-insights.md` (industry trends, not operational)
- `client-onboarding.md` (process docs, not troubleshooting)
- `integration-strategy.md` (meta-documentation, moved to /plans)

**Structural Improvements**:
- Fixed folder numbering collision (04-integrations → 05-integrations)
- Updated all cross-references
- Created kb-style-guide.md for future contributions

---

## For Contributors

Before adding or updating KB content:
1. Read [kb-style-guide.md](kb-style-guide.md)
2. Check for existing coverage (avoid duplication)
3. Write concisely (actionable patterns over comprehensive context)
4. Target 200-400 lines per file
5. Use cross-references instead of copying content
