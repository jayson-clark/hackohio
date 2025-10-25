from typing import List, Dict, Any, Tuple
import networkx as nx


class HypothesisAgent:
    """
    Generate hypotheses from graph structure:
    - Indirect connections (A-B, B-C, but no A-C)
    - Bridge nodes with high betweenness
    - Community border connections
    """

    def __init__(self, nx_graph: nx.Graph):
        self.graph = nx_graph
        # Common over-generic entities to downweight or ignore
        self.generic_entities = {
            "cancer", "nsclc", "disease", "cell", "cells", "protein", "gene",
            "micrornas", "inflammation", "therapy", "treatment", "pathway",
            "field cancerization",
        }

    def indirect_connection_hypotheses(self, max_results: int = 10, focus: str | None = None) -> List[Dict[str, Any]]:
        hypotheses: List[Dict[str, Any]] = []
        nodes = [focus] if focus and focus in self.graph else list(self.graph.nodes())
        visited_pairs = set()

        for b in nodes:
            for a in self.graph.neighbors(b) if b in self.graph else []:
                for c in self.graph.neighbors(b):
                    if a == c:
                        continue
                    pair = tuple(sorted([a, c]))
                    if pair in visited_pairs:
                        continue
                    visited_pairs.add(pair)
                    if not self.graph.has_edge(a, c):
                         # Compute confidence from edge weights (penalize generic endpoints instead of skipping)
                        w_ab = float(self.graph.edges[a, b].get("weight", 1.0))
                        w_bc = float(self.graph.edges[b, c].get("weight", 1.0))
                        # Normalize by local degree context
                        deg_b = max(1, self.graph.degree(b))
                        base = (w_ab + w_bc) / max(2.0, deg_b)
                        # Map to confidence range [0.5, 0.9]
                        conf = 0.5 + max(0.0, min(0.4, base))
                        # Penalize if endpoints are generic
                        if a.lower() in self.generic_entities:
                            conf -= 0.08
                        if c.lower() in self.generic_entities:
                            conf -= 0.08
                        conf = max(0.3, conf)

                        ev_ab = self.graph.edges[a, b].get("evidence", [])[:1]
                        ev_bc = self.graph.edges[b, c].get("evidence", [])[:1]
                        hypotheses.append({
                            "title": f"Potential relationship between {a} and {c} via {b}",
                            "explanation": f"{a}→{b} (w={w_ab:.1f}) and {b}→{c} (w={w_bc:.1f}) indicate a possible {a}–{c} link.",
                            "entities": [a, b, c],
                            "evidence_sentences": ev_ab + ev_bc,
                            "edge_pairs": [[a, b], [b, c]],
                            "confidence": round(conf, 2),
                        })
                        if len(hypotheses) >= max_results:
                            return hypotheses
        return hypotheses

    def high_betweenness_bridges(self, top_k: int = 5) -> List[Dict[str, Any]]:
        if self.graph.number_of_nodes() < 3:
            return []
        try:
            centrality = nx.betweenness_centrality(self.graph)
        except Exception:
            return []
        # Sort and min-max normalize for clearer confidence scaling
        sorted_all = sorted(centrality.items(), key=lambda x: x[1], reverse=True)
        if not sorted_all:
            return []
        max_c = sorted_all[0][1]
        min_c = sorted_all[-1][1]
        span = (max_c - min_c) or 1.0
        items = sorted_all[:top_k]
        results: List[Dict[str, Any]] = []
        for node, score in items:
            # Skip generic labels
            if str(node).lower() in self.generic_entities:
                continue
            # Confidence in [0.6, 0.95]
            norm = (score - min_c) / span
            confidence = 0.6 + 0.35 * norm
            # Collect 1-2 sample neighbor evidences
            samples = []
            for nbr in list(self.graph.neighbors(node))[:3]:
                ev = self.graph.edges[node, nbr].get("evidence", [])
                if ev:
                    samples.append(ev[0])
            results.append({
                "title": f"Bridge node {node} with high betweenness",
                "explanation": f"{node} connects multiple subgraphs (betweenness={score:.3f}).",
                "entities": [node],
                "evidence_sentences": samples[:2],
                "edge_pairs": [],
                "confidence": round(confidence, 2),
            })
        return results

    def generate(self, focus: str | None = None, max_results: int = 10) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        # Aim for a mix of hypothesis types
        budget_indirect = max(1, int(max_results * 0.8))
        budget_bridge = max_results - budget_indirect
        results.extend(self.indirect_connection_hypotheses(max_results=budget_indirect, focus=focus))
        if len(results) < max_results:
            results.extend(self.high_betweenness_bridges(top_k=budget_bridge))
        # Fallback: if still empty, relax fully and return a couple of bridge nodes
        if not results:
            results.extend(self.high_betweenness_bridges(top_k=min(3, max_results)))
        return results[:max_results]


