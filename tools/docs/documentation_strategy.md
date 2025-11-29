# Documentation Strategy

This directory contains technical specifications and implementation documentation specific to the analysis tools.

## 📁 **Directory Purpose**

**Scope**: Tool-specific technical documentation  
**Audience**: Developers, implementers, AI agents consuming tool specifications  
**Separation**: Knowledge base remains standalone and RAG-optimized

## 📋 **Documentation Index**

### **Core Technical Specifications**
- **[TECHNICAL-SPECIFICATIONS.md](./TECHNICAL-SPECIFICATIONS.md)** - Complete technical specification for diagnostic rules, issue classifications, and AI agent workflows
- **[PRIMARY-ISSUES-CLASSIFICATION.md](./PRIMARY-ISSUES-CLASSIFICATION.md)** - Current implementation status and development roadmap for diagnostic rules

### **Tool-Specific Guides**
- **[Campaign Analysis Tool](../campaign-analysis/README.md)** - Complete campaign analysis and deal relationship documentation
- **[Tools README](../README.md)** - Quick reference for all analysis tools

## 🎯 **Content Strategy**

### **What Belongs Here**
- ✅ **Diagnostic rules and classifications** - Technical implementation specs
- ✅ **API integration specifications** - BidSwitch and database integration details  
- ✅ **Implementation guidelines** - Code integration, testing, and deployment
- ✅ **Agent workflow specifications** - Structured data formats for AI consumption
- ✅ **Tool architecture documentation** - Technical design and patterns

### **What Stays in Knowledge Base**
- ✅ **Business context and strategy** - RAG-optimized for agent consumption
- ✅ **Operational procedures** - Campaign troubleshooting workflows
- ✅ **Platform overview** - Business features and technical architecture
- ✅ **Integration guides** - SSP connections and third-party systems
- ✅ **Maintenance procedures** - Database management and system monitoring

## 🔗 **Cross-References**

### **Knowledge Base Integration**
The knowledge base (`/knowledge-base/`) provides business context that complements these technical specifications:

- **[Campaign Troubleshooting](/knowledge-base/06-operations/campaign-troubleshooting.md)** - Operational context for diagnostic rules
- **[Deal Debug Workflow](/knowledge-base/06-operations/deal-debug-workflow.md)** - Industry best practices and automation patterns
- **[BidSwitch Diagnostic Patterns](/knowledge-base/08-bidswitch-integration/diagnostic-patterns.md)** - Automated diagnostic rules and thresholds
- **[BidSwitch Deals Management](/knowledge-base/08-bidswitch-integration/bidswitch-deals-management.md)** - Deal troubleshooting and lifecycle
- **[Platform Architecture](/knowledge-base/03-technical-features/platform-architecture.md)** - System context for tool integration

### **Tool Integration**
These specifications support multiple analysis tools:

- **Campaign Analysis Tool** (`/tools/campaign-analysis/`) - Uses diagnostic rules for campaign-level analysis
- **Deal Debugging Tool** (`/tools/deal-debugging/`) - Implements BidSwitch diagnostic patterns
- **Future Tools** - Extensible specifications for new debugging capabilities

## 📊 **Maintenance**

### **Update Process**
1. **Technical Changes**: Update specifications in this directory
2. **Business Context**: Update knowledge base for RAG optimization
3. **Cross-Reference Validation**: Ensure links between technical and business docs remain accurate
4. **Agent Testing**: Validate AI agent consumption of updated specifications

### **Version Control**
- **Technical Specifications**: Version controlled with tool implementations
- **Knowledge Base**: Independently versioned for RAG database updates
- **Cross-References**: Validated during documentation audits

---

*This directory maintains the technical foundation for analysis tools while preserving the knowledge base's role as a standalone, RAG-optimized resource for AI agents.*
