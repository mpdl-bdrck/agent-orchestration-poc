# Knowledge Base Style Guide

## Purpose

This KB serves **troubleshooting tools and AI agents** - not business planning or strategic documentation. Content must be **operationally actionable**.

---

## File Size Guidelines

### Target Ranges

| File Size | Status | Action |
|-----------|--------|--------|
| **< 200 lines** | Optimal | Maintain |
| **200-400 lines** | Acceptable | Monitor for growth |
| **400-500 lines** | Review needed | Compress or split |
| **> 500 lines** | Too large | Immediate action required |

**Why**: RAG systems perform best with 200-400 line documents. Large files degrade semantic search and increase token costs.

---

## Content Principles

### ✅ Include

**Actionable Patterns**:
- Diagnostic criteria (symptoms, detection, resolution)
- Troubleshooting workflows
- Configuration examples (ONE canonical example)
- Performance thresholds and metrics
- Quick reference tables
- Cross-references to related topics

**Format**:
```markdown
## Issue Name

**Symptoms**: Observable behaviors
**Detection**: How to identify (automated checks)
**Resolution**: Specific actions to fix
**Expected Impact**: Quantified results
```

### ❌ Exclude

**Strategic Content**:
- Business strategy and market positioning
- Competitive analysis
- Sales materials
- Client onboarding processes
- Revenue optimization strategy

**Verbose Content**:
- Multiple similar examples
- Extensive background context
- Detailed technical architecture (move to architecture docs)
- Step-by-step tutorials (link to API docs instead)

---

## Writing Style

### Conciseness Rules

1. **One canonical example** per concept (not 3-5)
2. **Bullet points** over paragraphs
3. **Tables** for comparisons and thresholds
4. **Cross-references** instead of duplication
5. **Actionable first**, context second

### Good vs. Bad

❌ **Bad** (verbose):
```markdown
### Resolution Process

To resolve this issue, you should follow these steps:

1. First, access the Terminal UI by navigating to app.bedrockplatform.com
2. Then, locate the campaign in question by searching for it
3. Next, review the configuration settings carefully
4. After that, make the necessary adjustments
5. Finally, save your changes and monitor the results
```

✅ **Good** (concise):
```markdown
### Resolution

Access Terminal UI → Locate campaign → Adjust configuration → Save → Monitor for 24-48h.
```

---

## Structure Standards

### Required Sections

Every troubleshooting document should have:
1. **Overview** (1-2 sentences, what this doc covers)
2. **Main Content** (patterns, diagnostics, procedures)
3. **Related Documentation** (cross-references)

### Heading Hierarchy

```markdown
# Document Title (H1) - One per file

## Major Section (H2) - Main topics

### Subsection (H3) - Specific patterns or procedures

**Bold for emphasis** - Not a heading
```

### Code Blocks

**Use for**:
- SQL queries (one per pattern, not multiple variations)
- JSON configurations (canonical example only)
- Command examples (essential commands only)

**Don't use for**:
- Extensive logging output
- Multiple similar variations
- Tutorial-style walkthroughs

---

## Cross-References

### Format

```markdown
## Related Documentation

- [Specific Topic](../folder/file.md) - Brief description of relevance
- [Another Topic](file-in-same-folder.md) - Why to reference this
```

### When to Cross-Reference

✅ **Do**:
- Link to related troubleshooting patterns
- Reference technical architecture for details
- Point to API docs for full schemas

❌ **Don't**:
- Duplicate content across files
- Create circular references
- Link to deprecated or low-value docs

---

## Maintenance

### Before Adding New Content

1. **Check for existing coverage** - Don't duplicate
2. **Estimate final size** - Will file exceed 400 lines?
3. **Identify removal candidates** - What can be compressed?
4. **Consider split** - Should this be a separate file?

### When Updating Content

1. **Remove before adding** - Keep file size stable
2. **Update cross-references** - Fix broken links
3. **Consolidate examples** - Remove redundant variations
4. **Compress verbose sections** - Maintain conciseness

### Quarterly Audit

- Identify files > 400 lines
- Check for duplication across files
- Remove outdated content
- Update benchmarks and thresholds

---

## Folder Organization

### Current Structure

```
knowledge-base/
├── 01-platform-overview/     (100-200 lines per file)
├── 02-business-features/     (150-250 lines per file)
├── 03-technical-features/    (200-400 lines per file)
├── 04-business-strategy/     (compress or move to /docs)
├── 05-integrations/          (200-300 lines per file)
├── 06-operations/            (250-500 lines per file) ← TROUBLESHOOTING FOCUS
├── 07-maintenance/           (200-400 lines per file)
└── 08-bidswitch-integration/ (200-500 lines per file) ← TROUBLESHOOTING FOCUS
```

### What Goes Where

**01-platform-overview**: High-level product positioning (minimal detail)

**02-business-features**: Feature descriptions for end-users (customer-facing language)

**03-technical-features**: Architecture and system design (technical but accessible)

**04-business-strategy**: Strategic planning (consider moving to /docs)

**05-integrations**: External system connections and setup

**06-operations**: **Primary troubleshooting focus** - diagnostic workflows, issue resolution

**07-maintenance**: Database management, system administration

**08-bidswitch-integration**: **Primary deal troubleshooting focus** - BidSwitch-specific patterns

---

## Examples of Optimization

### Before Optimization

```markdown
## Double Geo-Targeting Issue

### The "Tribal Knowledge" Problem

This issue took industry leaders **months to discover** through trial and error. 
It's now one of the most common causes of underperformance, especially for CTV deals.

### Root Cause

**The Problem**:
- Buyer applies geo-targeting using their DSP
- Seller applies geo-targeting using BidSwitch targeting groups
- Different geo-resolution libraries used (BidSwitch vs. DSP)
- Libraries may resolve same location to different codes
- Mismatch causes dramatic delivery reduction

### Symptoms

- CTV deals particularly affected (50-80% delivery drop)
- High bid request volume but low actual matches
- Delivery decline correlates with geo-targeting activation
- No other obvious configuration issues

[...continues for 50+ more lines...]
```
**Lines**: 80+

### After Optimization

```markdown
## Double Geo-Targeting Issue (25% of cases)

**Root Cause**: Buyer and seller both apply geo-targeting using different libraries (BidSwitch vs. DSP), causing mismatches.

**Symptoms**: CTV deals particularly affected (50-80% delivery drop), high bid requests but low matches.

**Detection**: Check both deal settings (BidSwitch groups: 8643=EU, 9000=BR) and line item filters. If BOTH present, flag as conflict (85%+ confidence).

**Resolution**: Remove supply-side geo-targeting (open to national), let buyer handle exclusively.

**Expected Impact**: 60-80% delivery restoration (immediate).
```
**Lines**: 9

**Reduction**: 88%

---

## Quality Checklist

Before committing KB changes:

- [ ] File size < 400 lines (< 500 absolute max)
- [ ] One canonical example per concept
- [ ] No duplicate content across files
- [ ] Cross-references instead of duplication
- [ ] Actionable patterns over background context
- [ ] Updated related documentation links
- [ ] Removed verbose explanations
- [ ] Consolidated similar sections

---

## RAG Optimization

### Semantic Chunking

**Good** (clear semantic boundaries):
```markdown
## Issue: Low Win Rate

**Symptoms**: High bid responses, low impressions
**Detection**: Win rate < 3%
**Resolution**: Increase bids, review targeting
```

**Bad** (poor chunking):
```markdown
There are several potential issues that could cause low performance.
One common issue is low win rates. This can happen for various reasons.
The symptoms include high bid responses. Also low impressions.
To detect this, you should check if win rate is below 3%.
[...continues with mixed topics...]
```

### Structured Data

Use **tables and lists** for better RAG retrieval:

✅ **Good**:
| Threshold | Status | Action |
|-----------|--------|--------|
| < 1% | Critical | Immediate fix |
| 1-3% | Warning | Monitor closely |

❌ **Bad**:
"If the win rate is less than 1%, it's critical and requires immediate action. If it's between 1 and 3%, it's a warning and should be monitored closely."

---

## Version Control

- KB optimizations should be committed as logical units
- Include line count reductions in commit messages
- Track major optimizations in changelog
- Review changes before push to avoid broken links

**Example Commit Message**:
```
Optimize KB: 2,001 lines removed (30% reduction)

- Compressed 6 files (deal-debug, diagnostics, troubleshooting, etc.)
- Deleted 4 low-value strategy files
- Fixed folder numbering (04-integrations → 05-integrations, etc.)
- Updated all cross-references

Improved RAG performance, reduced token costs, easier maintenance.
```

---

## Future Additions

When adding new KB content:

1. **Check existing files first** - Can this be added to existing doc?
2. **Estimate size** - Will this create a >400 line file?
3. **Consider compression** - What can be removed to make room?
4. **Write concisely** - Follow style guide from the start
5. **Review before commit** - Run through quality checklist

**Remember**: Less is more. Concise, actionable content performs better than comprehensive verbosity.

