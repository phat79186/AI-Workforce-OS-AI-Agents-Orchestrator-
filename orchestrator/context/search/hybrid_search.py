"""
Hybrid Search - Combined BM25 and Semantic Search.

Implements Reciprocal Rank Fusion (RRF) to combine keyword-based BM25
search with embedding-based semantic search for optimal retrieval.
"""

from __future__ import annotations

import logging
from typing import Any

from orchestrator.context.models.schemas import Node, NodeType, SearchResult
from orchestrator.context.search.bm25_index import BM25Index
from orchestrator.context.search.embeddings import EmbeddingStore
from orchestrator.context.store.graph_store import GraphStore


class HybridSearch:
    """Combined BM25 + semantic search with RRF fusion."""

    def __init__(
        self,
        graph_store: GraphStore,
        bm25_index: BM25Index | None = None,
        embedding_store: EmbeddingStore | None = None,
        rrf_k: int = 60,
        bm25_weight: float = 0.5,
        semantic_weight: float = 0.5,
    ):
        """Initialize hybrid search.

        Args:
            graph_store: Graph store instance
            bm25_index: Optional BM25 index (created if not provided)
            embedding_store: Optional embedding store (created if not provided)
            rrf_k: RRF constant (higher values favor top-ranked results less)
            bm25_weight: Weight for BM25 results in final score
            semantic_weight: Weight for semantic results in final score
        """
        self.logger = logging.getLogger("context.hybrid_search")
        self.graph_store = graph_store
        self.bm25_index = bm25_index or BM25Index(graph_store)
        self.embedding_store = embedding_store or EmbeddingStore(graph_store)
        self.rrf_k = rrf_k
        self.bm25_weight = bm25_weight
        self.semantic_weight = semantic_weight

    def _reciprocal_rank_fusion(
        self,
        rankings: list[list[tuple[str, float]]],
        weights: list[float],
    ) -> dict[str, float]:
        """Apply Reciprocal Rank Fusion to combine multiple rankings.

        RRF score = sum(weight_i / (k + rank_i)) for each ranking

        Args:
            rankings: List of rankings, each a list of (doc_id, score) tuples
            weights: Weight for each ranking

        Returns:
            Dictionary mapping doc_id to fused score
        """
        fused_scores: dict[str, float] = {}

        for ranking, weight in zip(rankings, weights):
            for rank, (doc_id, _) in enumerate(ranking, start=1):
                rrf_score = weight / (self.rrf_k + rank)
                fused_scores[doc_id] = fused_scores.get(doc_id, 0.0) + rrf_score

        return fused_scores

    def search(
        self,
        query: str,
        limit: int = 20,
        node_types: list[NodeType] | None = None,
        bm25_limit: int = 50,
        semantic_limit: int = 50,
        min_bm25_score: float = 0.0,
        min_semantic_similarity: float = 0.3,
        include_edges: bool = False,
    ) -> list[SearchResult]:
        """Perform hybrid search combining BM25 and semantic search.

        Args:
            query: Search query
            limit: Maximum final results
            node_types: Filter by node types
            bm25_limit: Maximum BM25 candidates
            semantic_limit: Maximum semantic candidates
            min_bm25_score: Minimum BM25 score threshold
            min_semantic_similarity: Minimum semantic similarity threshold
            include_edges: Include related edges in results

        Returns:
            List of SearchResult objects sorted by fused score
        """
        bm25_results = self.bm25_index.search(
            query=query,
            limit=bm25_limit,
            node_types=node_types,
            min_score=min_bm25_score,
        )

        semantic_results = self.embedding_store.semantic_search(
            query=query,
            limit=semantic_limit,
            min_similarity=min_semantic_similarity,
            node_types=[nt.value for nt in node_types] if node_types else None,
        )

        bm25_ranking = [(node.id, score) for node, score in bm25_results]
        semantic_ranking = [(node.id, score) for node, score in semantic_results]

        fused_scores = self._reciprocal_rank_fusion(
            rankings=[bm25_ranking, semantic_ranking],
            weights=[self.bm25_weight, self.semantic_weight],
        )

        bm25_scores = {node.id: score for node, score in bm25_results}
        semantic_scores = {node.id: score for node, score in semantic_results}
        all_nodes = {node.id: node for node, _ in bm25_results}
        all_nodes.update({node.id: node for node, _ in semantic_results})

        sorted_ids = sorted(fused_scores.items(), key=lambda x: x[1], reverse=True)

        results: list[SearchResult] = []
        for node_id, fused_score in sorted_ids[:limit]:
            node = all_nodes.get(node_id)
            if node is None:
                node = self.graph_store.get_node(node_id)
            if node is None:
                continue

            match_types = []
            if node_id in bm25_scores:
                match_types.append(f"bm25:{bm25_scores[node_id]:.3f}")
            if node_id in semantic_scores:
                match_types.append(f"semantic:{semantic_scores[node_id]:.3f}")

            related_edges = []
            if include_edges:
                related_edges = self.graph_store.get_edges_from(node_id)
                related_edges.extend(self.graph_store.get_edges_to(node_id))

            result = SearchResult(
                node=node,
                score=fused_score,
                match_type="+".join(match_types) if match_types else "unknown",
                highlights=self._extract_highlights(query, node),
                related_edges=related_edges,
            )
            results.append(result)

        return results

    def _extract_highlights(self, query: str, node: Node, max_highlights: int = 3) -> list[str]:
        """Extract text snippets that match the query.

        Args:
            query: Search query
            node: Node to extract highlights from
            max_highlights: Maximum number of highlights

        Returns:
            List of highlighted text snippets
        """
        query_terms = set(self.bm25_index.tokenize(query))
        if not query_terms:
            return []

        text = f"{node.title} {node.content}"
        sentences = text.replace("\n", ". ").split(". ")

        scored_sentences = []
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 10:
                continue

            sentence_terms = set(self.bm25_index.tokenize(sentence))
            overlap = len(query_terms & sentence_terms)

            if overlap > 0:
                scored_sentences.append((sentence[:200], overlap))

        scored_sentences.sort(key=lambda x: x[1], reverse=True)

        return [s[0] for s in scored_sentences[:max_highlights]]

    def search_bm25_only(
        self,
        query: str,
        limit: int = 20,
        node_types: list[NodeType] | None = None,
    ) -> list[SearchResult]:
        """Search using only BM25 (keyword search)."""
        results = self.bm25_index.search(query, limit=limit, node_types=node_types)

        return [
            SearchResult(
                node=node,
                score=score,
                match_type="bm25",
                highlights=self._extract_highlights(query, node),
            )
            for node, score in results
        ]

    def search_semantic_only(
        self,
        query: str,
        limit: int = 20,
        node_types: list[NodeType] | None = None,
    ) -> list[SearchResult]:
        """Search using only semantic similarity."""
        results = self.embedding_store.semantic_search(
            query,
            limit=limit,
            node_types=[nt.value for nt in node_types] if node_types else None,
        )

        return [
            SearchResult(
                node=node,
                score=score,
                match_type="semantic",
                highlights=[],
            )
            for node, score in results
        ]

    def find_related(
        self,
        node_id: str,
        limit: int = 10,
        include_graph_neighbors: bool = True,
        include_similar: bool = True,
    ) -> list[SearchResult]:
        """Find nodes related to a given node.

        Args:
            node_id: Reference node ID
            limit: Maximum results
            include_graph_neighbors: Include graph-connected nodes
            include_similar: Include semantically similar nodes

        Returns:
            List of related nodes with relationship info
        """
        results: dict[str, SearchResult] = {}

        if include_graph_neighbors:
            neighbors = self.graph_store.get_neighbors(node_id, direction="both")
            for neighbor_node, edge in neighbors:
                if neighbor_node.id not in results:
                    results[neighbor_node.id] = SearchResult(
                        node=neighbor_node,
                        score=edge.weight,
                        match_type=f"edge:{edge.edge_type.value}",
                        related_edges=[edge],
                    )

        if include_similar:
            similar = self.embedding_store.find_similar_nodes(
                node_id,
                limit=limit,
                exclude_connected=include_graph_neighbors,
            )
            for similar_node, similarity in similar:
                if similar_node.id not in results:
                    results[similar_node.id] = SearchResult(
                        node=similar_node,
                        score=similarity,
                        match_type="similar",
                    )

        sorted_results = sorted(results.values(), key=lambda x: x.score, reverse=True)
        return sorted_results[:limit]

    def build_indexes(self) -> dict[str, Any]:
        """Build both BM25 and embedding indexes."""
        bm25_stats = self.bm25_index.build_index()
        embedding_stats = self.embedding_store.embed_all_nodes()

        return {
            "bm25": bm25_stats,
            "embeddings": embedding_stats,
        }

    def get_stats(self) -> dict[str, Any]:
        """Get combined search statistics."""
        return {
            "bm25": self.bm25_index.get_stats(),
            "embeddings": self.embedding_store.get_stats(),
            "rrf_k": self.rrf_k,
            "bm25_weight": self.bm25_weight,
            "semantic_weight": self.semantic_weight,
        }
