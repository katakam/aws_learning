# SAP-C02 Knowledge Graph Design

## Source understood

`sap_c02_patterns_full.html` is organized as:

- 6 exam/domain sections
- 62 decision pattern cards
- Each card has:
  - `IF / WHEN` trigger/context
  - `THEN` recommended AWS architecture/action
  - `NEVER` wrong answers / traps / anti-patterns
  - optional `WHY IT WORKS`
  - tags for AWS services and concepts

## Recommended graph model

Use a **decision-pattern knowledge graph**, not a generic page-link graph. The useful unit for study and retrieval is the exam decision rule.

### Node types

| Node type | Purpose |
|---|---|
| `KnowledgeBase` | Root node for the SAP-C02 pattern collection |
| `Domain` | SAP-C02 exam domain / universal reference section |
| `DecisionPattern` | One IF/WHEN/THEN/NEVER card |
| `Concept` | AWS service, feature, pattern, or concept from tags |
| `AntiPattern` | A wrong answer/trap extracted from `NEVER` |

### Edge types

| Edge | Meaning |
|---|---|
| `HAS_DOMAIN` | Knowledge base contains a domain |
| `CONTAINS_PATTERN` | Domain contains a decision pattern |
| `USES_CONCEPT` | Pattern depends on / mentions a tagged concept |
| `AVOIDS` | Pattern explicitly rejects an anti-pattern |

## Why this design

This keeps the graph simple enough to maintain but useful for:

1. Exam prep: “When do I choose X instead of Y?”
2. RAG/search: retrieve whole decision rules by service, domain, or trap.
3. Visualization: domain → patterns → services/traps.
4. Future Neo4j/RDF import: nodes and edges are already normalized.

## Generated artifact

Generated JSON:

`data/sap_c02_knowledge_graph.json`

Current size:

- 373 nodes
- 417 edges
- 62 decision patterns
- 181 concepts
- 123 anti-patterns

## Best next design choice

I recommend the next layer be an **interactive study graph** with these views:

1. **Domain view** — domain → pattern cards.
2. **Service view** — service/concept → all patterns using it.
3. **Trap view** — anti-pattern/wrong answer → correct pattern.
4. **Decision view** — show IF/WHEN, THEN, NEVER, WHY for selected pattern.

## Interactive viewer

Created:

`sap_c02_kg_viewer.html`

Run locally from the repository root:

```bash
python3 -m http.server 8000
```

Then open:

`http://localhost:8000/sap_c02_kg_viewer.html`

The viewer loads `data/sap_c02_knowledge_graph.json` and supports search, domain/type filters, graph node selection, neighbor highlighting, and decision-rule details.

## Optional enhancements

Potential next steps:

- Add automatic service extraction from `THEN` text, beyond existing tags.
- Add `RECOMMENDS_CONCEPT` vs `MENTIONS_CONCEPT` edge distinction.
- Add similarity edges between patterns sharing many concepts.
- Export to Neo4j CSV.
- Build a local HTML graph viewer with filters and search.
- Generate Mermaid/Graphviz summaries per domain.
