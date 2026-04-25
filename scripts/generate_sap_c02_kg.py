#!/usr/bin/env python3
"""Generate a lightweight knowledge graph from sap_c02_patterns_full.html.

Outputs JSON with nodes and edges suitable for graph viewers, RAG, or conversion to
Neo4j/RDF. The source HTML is structured as domain headers plus pattern cards with
IF/WHEN, THEN, NEVER, WHY, and tags.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from bs4 import BeautifulSoup, Tag


def slug(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return re.sub(r"^-+|-+$", "", text) or "node"


def clean_text(tag: Tag | None) -> str:
    if not tag:
        return ""
    label = tag.select_one(".block-label")
    if label:
        label.extract()
    return " ".join(tag.get_text(" ", strip=True).split())


def split_never(text: str) -> list[str]:
    if not text:
        return []
    # NEVER blocks use bullet characters in source; keep phrases compact.
    items = [x.strip(" -–—;.,") for x in re.split(r"\s*•\s*", text) if x.strip()]
    return items or [text]


def add_node(nodes: dict[str, dict], node: dict) -> str:
    node_id = node["id"]
    if node_id not in nodes:
        nodes[node_id] = node
    return node_id


def add_edge(edges: list[dict], source: str, target: str, relation: str, **props) -> None:
    edges.append({"source": source, "target": target, "relation": relation, **props})


def build_graph(html_path: Path) -> dict:
    soup = BeautifulSoup(html_path.read_text(encoding="utf-8"), "html.parser")
    nodes: dict[str, dict] = {}
    edges: list[dict] = []

    graph_id = "kg:sap-c02-decision-patterns"
    add_node(nodes, {
        "id": graph_id,
        "type": "KnowledgeBase",
        "label": "SAP-C02 Decision Patterns",
        "source": str(html_path),
    })

    domain_order = 0
    pattern_order = 0
    wrapper = soup.select_one(".wrapper") or soup
    for child in wrapper.find_all(recursive=False):
        classes = child.get("class") or []
        if "domain-header" not in classes:
            continue

        domain_order += 1
        domain_label = " ".join(child.get_text(" ", strip=True).split())
        domain_id = f"domain:{slug(domain_label)}"
        add_node(nodes, {
            "id": domain_id,
            "type": "Domain",
            "label": domain_label,
            "order": domain_order,
        })
        add_edge(edges, graph_id, domain_id, "HAS_DOMAIN", order=domain_order)

        sib = child.find_next_sibling()
        while sib and "domain-header" not in (sib.get("class") or []):
            if isinstance(sib, Tag) and "pattern-card" in (sib.get("class") or []):
                pattern_order += 1
                title = sib.select_one(".summary-text").get_text(" ", strip=True)
                counter = sib.select_one(".counter")
                scenario_ref = counter.get_text(" ", strip=True) if counter else ""
                p_id = f"pattern:{slug(title)}"

                if_text = clean_text(sib.select_one(".if-block"))
                then_text = clean_text(sib.select_one(".then-block"))
                not_text = clean_text(sib.select_one(".not-block"))
                why_text = clean_text(sib.select_one(".why-block"))
                tags = [t.get_text(" ", strip=True) for t in sib.select(".tags .tag")]

                add_node(nodes, {
                    "id": p_id,
                    "type": "DecisionPattern",
                    "label": title,
                    "scenario_ref": scenario_ref,
                    "if_when": if_text,
                    "then": then_text,
                    "never": split_never(not_text),
                    "why": why_text,
                    "order": pattern_order,
                })
                add_edge(edges, domain_id, p_id, "CONTAINS_PATTERN", order=pattern_order)

                for tag in tags:
                    c_id = f"concept:{slug(tag)}"
                    add_node(nodes, {"id": c_id, "type": "Concept", "label": tag})
                    add_edge(edges, p_id, c_id, "USES_CONCEPT")

                for idx, anti in enumerate(split_never(not_text), 1):
                    a_id = f"anti-pattern:{slug(title)}:{idx}"
                    add_node(nodes, {"id": a_id, "type": "AntiPattern", "label": anti})
                    add_edge(edges, p_id, a_id, "AVOIDS", order=idx)

            sib = sib.find_next_sibling()

    return {
        "metadata": {
            "title": "SAP-C02 Decision Patterns Knowledge Graph",
            "source": str(html_path),
            "schema_version": "1.0",
            "node_count": len(nodes),
            "edge_count": len(edges),
            "modeling_note": "Domains contain decision patterns; patterns carry IF/WHEN, THEN, NEVER, WHY attributes and link to concept/anti-pattern nodes.",
        },
        "nodes": list(nodes.values()),
        "edges": edges,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", nargs="?", default="sap_c02_patterns_full.html")
    parser.add_argument("-o", "--output", default="data/sap_c02_knowledge_graph.json")
    args = parser.parse_args()

    graph = build_graph(Path(args.input))
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(graph, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {out} ({graph['metadata']['node_count']} nodes, {graph['metadata']['edge_count']} edges)")


if __name__ == "__main__":
    main()
