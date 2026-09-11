---
name: hierarchical-rag-synthesis
description: Overcome PageIndex context fragmentation by combining global document summaries with page-scoped precision chunks for holistic RAG synthesis.
---

# Hierarchical RAG Synthesis Skill

Solves the global context fragmentation weakness in page-scoped document chunking by executing a 2-stage Map-Reduce retrieval pipeline across Obsidian vaults and project documentation.

## When to Use
- When answering broad architectural questions spanning multiple documents or large notes.
- When generating executive summaries from large Obsidian vaults or codebase specs.
- When cross-referencing decisions across multiple ADRs (Architectural Decision Records) without losing page-level precision.
- When single-page chunking fails to provide the overarching rationale of a system.

## The 2-Stage Retrieval Architecture

```text
                     USER ARCHITECTURAL QUERY
                                │
                                ▼
                   STAGE 1: GLOBAL SWEEP (MAP)
            (Scans YAML frontmatter, document titles,
             scope metadata, and executive overviews)
                                │
                                ▼
               IDENTIFY TOP-N RELEVANT DOCUMENTS
                                │
                                ▼
                STAGE 2: PAGE DEEP DIVE (REDUCE)
             (Fetches top-K PageIndexPage chunks with
              exact page_number & layout_hierarchy)
                                │
                                ▼
                   SYNTHESIZED HOLISTIC ANSWER
         (Combines macro architecture + micro page quotes)
```

## How to Execute in Code

```python
from orchestrator.context.obsidian_rag import ObsidianVaultRAG

rag = ObsidianVaultRAG("./shared_knowledge/obsidian_vault")

# 1. Stage 1: Document-Level Global Sweep
all_docs = list(rag._documents.values())
candidate_docs = []
query_terms = ["architecture", "security", "liveness"]

for doc in all_docs:
    # Check frontmatter and executive overview
    fm = doc.frontmatter
    title = doc.title.lower()
    if any(term in title or term in str(fm) for term in query_terms):
        candidate_docs.append(doc)

# 2. Stage 2: Page-Level Deep Chunking
page_hits = []
for doc in candidate_docs:
    for page in doc.pages:
        if any(term in page.content.lower() for term in query_terms):
            page_hits.append({
                "document": doc.title,
                "page_number": page.page_number,
                "hierarchy": page.layout_hierarchy,
                "snippet": page.content[:300]
            })

# 3. Output Structured Synthesis
print(f"Global Documents Analyzed: {len(candidate_docs)}")
print(f"Precise Page Highlights: {len(page_hits)}")
```

## Best Practices
- Always check `doc.frontmatter` first to identify the document's domain and scope.
- Retain both the high-level document title and specific page numbers when presenting citations to the user.
- If the query is narrow (e.g. "what is the timeout config?"), skip Stage 1 and use direct page search.
