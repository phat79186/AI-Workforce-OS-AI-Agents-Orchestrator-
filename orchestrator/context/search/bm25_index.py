"""
BM25 Index for Keyword Search.

Implements BM25 (Best Matching 25) algorithm for fast keyword-based
retrieval from the context graph.
"""

from __future__ import annotations

import logging
import math
import re
from collections import Counter, defaultdict
from typing import Any

from orchestrator.context.models.schemas import Node, NodeType
from orchestrator.context.store.graph_store import GraphStore


class BM25Index:
    """BM25 search index for keyword retrieval."""

    def __init__(
        self,
        graph_store: GraphStore,
        k1: float = 1.5,
        b: float = 0.75,
        delta: float = 0.0,
    ):
        """Initialize BM25 index.

        Args:
            graph_store: Graph store instance
            k1: Term frequency saturation parameter
            b: Document length normalization parameter
            delta: BM25+ delta parameter
        """
        self.logger = logging.getLogger("context.bm25")
        self.graph_store = graph_store
        self.k1 = k1
        self.b = b
        self.delta = delta

        self._doc_freqs: dict[str, int] = defaultdict(int)
        self._doc_lens: dict[str, int] = {}
        self._avg_doc_len: float = 0.0
        self._total_docs: int = 0
        self._inverted_index: dict[str, set[str]] = defaultdict(set)
        self._doc_terms: dict[str, Counter] = {}
        self._stopwords = self._default_stopwords()

    def _default_stopwords(self) -> set[str]:
        """Get default English stopwords."""
        return {
            "a",
            "an",
            "and",
            "are",
            "as",
            "at",
            "be",
            "by",
            "for",
            "from",
            "has",
            "he",
            "in",
            "is",
            "it",
            "its",
            "of",
            "on",
            "that",
            "the",
            "to",
            "was",
            "were",
            "will",
            "with",
            "this",
            "but",
            "they",
            "have",
            "had",
            "what",
            "when",
            "where",
            "who",
            "which",
            "why",
            "how",
            "all",
            "each",
            "every",
            "both",
            "few",
            "more",
            "most",
            "other",
            "some",
            "such",
            "no",
            "nor",
            "not",
            "only",
            "own",
            "same",
            "so",
            "than",
            "too",
            "very",
            "can",
            "just",
            "should",
            "now",
            "or",
            "if",
        }

    def tokenize(self, text: str) -> list[str]:
        """Tokenize text into terms.

        Args:
            text: Input text

        Returns:
            List of lowercase tokens
        """
        if not text:
            return []

        text = text.lower()
        tokens = re.findall(r"\b[a-zA-Z0-9_]+\b", text)
        tokens = [t for t in tokens if t not in self._stopwords and len(t) > 1]

        return tokens

    def _node_to_document(self, node: Node) -> str:
        """Convert node to document text for indexing."""
        parts = []

        if node.title:
            parts.append(node.title)
            parts.append(node.title)

        if node.content:
            parts.append(node.content)

        if node.tags:
            parts.extend(node.tags)

        node_dict = node.to_dict()
        text_fields = [
            "description",
            "summary",
            "task_description",
            "purpose",
            "rationale",
            "error_message",
            "correction",
            "code",
        ]
        for field in text_fields:
            if field in node_dict and node_dict[field]:
                parts.append(str(node_dict[field]))

        return " ".join(parts)

    def index_node(self, node: Node) -> None:
        """Add a node to the BM25 index.

        Args:
            node: Node to index
        """
        doc_text = self._node_to_document(node)
        terms = self.tokenize(doc_text)

        if not terms:
            return

        if node.id in self._doc_terms:
            self._remove_from_index(node.id)

        term_counts = Counter(terms)
        self._doc_terms[node.id] = term_counts
        self._doc_lens[node.id] = len(terms)

        for term in term_counts:
            if node.id not in self._inverted_index[term]:
                self._doc_freqs[term] += 1
            self._inverted_index[term].add(node.id)

        self._update_stats()

    def _remove_from_index(self, node_id: str) -> None:
        """Remove a node from the index."""
        if node_id not in self._doc_terms:
            return

        for term in self._doc_terms[node_id]:
            self._inverted_index[term].discard(node_id)
            if not self._inverted_index[term]:
                del self._inverted_index[term]
                del self._doc_freqs[term]
            else:
                self._doc_freqs[term] = len(self._inverted_index[term])

        del self._doc_terms[node_id]
        del self._doc_lens[node_id]

        self._update_stats()

    def _update_stats(self) -> None:
        """Update aggregate statistics."""
        self._total_docs = len(self._doc_lens)
        if self._total_docs > 0:
            self._avg_doc_len = sum(self._doc_lens.values()) / self._total_docs
        else:
            self._avg_doc_len = 0.0

    def _bm25_score(self, query_terms: list[str], doc_id: str) -> float:
        """Calculate BM25 score for a document.

        Args:
            query_terms: Query terms
            doc_id: Document ID

        Returns:
            BM25 relevance score
        """
        if doc_id not in self._doc_terms:
            return 0.0

        doc_len = self._doc_lens[doc_id]
        doc_term_counts = self._doc_terms[doc_id]
        score = 0.0

        for term in query_terms:
            if term not in doc_term_counts:
                continue

            tf = doc_term_counts[term]
            df = self._doc_freqs.get(term, 0)

            if df == 0:
                continue

            idf = math.log((self._total_docs - df + 0.5) / (df + 0.5) + 1)

            tf_component = (tf * (self.k1 + 1)) / (
                tf + self.k1 * (1 - self.b + self.b * doc_len / max(self._avg_doc_len, 1))
            )

            score += idf * (tf_component + self.delta)

        return score

    def search(
        self,
        query: str,
        limit: int = 20,
        node_types: list[NodeType] | None = None,
        min_score: float = 0.0,
    ) -> list[tuple[Node, float]]:
        """Search the index using BM25.

        Args:
            query: Search query
            limit: Maximum results
            node_types: Filter by node types
            min_score: Minimum BM25 score threshold

        Returns:
            List of (node, score) tuples sorted by relevance
        """
        query_terms = self.tokenize(query)
        if not query_terms:
            return []

        candidate_docs: set[str] = set()
        for term in query_terms:
            candidate_docs.update(self._inverted_index.get(term, set()))

        if not candidate_docs:
            return []

        results: list[tuple[str, float]] = []
        for doc_id in candidate_docs:
            score = self._bm25_score(query_terms, doc_id)
            if score >= min_score:
                results.append((doc_id, score))

        results.sort(key=lambda x: x[1], reverse=True)

        final_results: list[tuple[Node, float]] = []
        for doc_id, score in results[: limit * 2]:
            node = self.graph_store.get_node(doc_id)
            if node:
                if node_types and node.node_type not in node_types:
                    continue
                final_results.append((node, score))
                if len(final_results) >= limit:
                    break

        return final_results

    def build_index(self, batch_size: int = 1000) -> dict[str, Any]:
        """Build index from all nodes in graph store.

        Args:
            batch_size: Process nodes in batches

        Returns:
            Statistics about indexing
        """
        self._doc_freqs.clear()
        self._doc_lens.clear()
        self._inverted_index.clear()
        self._doc_terms.clear()

        indexed = 0
        skipped = 0

        offset = 0
        while True:
            nodes = self.graph_store.query_nodes(limit=batch_size, offset=offset)
            if not nodes:
                break

            for node in nodes:
                doc_text = self._node_to_document(node)
                terms = self.tokenize(doc_text)

                if terms:
                    term_counts = Counter(terms)
                    self._doc_terms[node.id] = term_counts
                    self._doc_lens[node.id] = len(terms)

                    for term in term_counts:
                        self._inverted_index[term].add(node.id)
                        self._doc_freqs[term] = len(self._inverted_index[term])

                    indexed += 1
                else:
                    skipped += 1

            offset += batch_size

        self._update_stats()

        self.logger.info("BM25 index built: %s indexed, %s skipped", indexed, skipped)

        return {
            "indexed": indexed,
            "skipped": skipped,
            "vocabulary_size": len(self._doc_freqs),
            "average_doc_length": self._avg_doc_len,
        }

    def get_stats(self) -> dict[str, Any]:
        """Get index statistics."""
        return {
            "total_documents": self._total_docs,
            "vocabulary_size": len(self._doc_freqs),
            "average_doc_length": self._avg_doc_len,
            "k1": self.k1,
            "b": self.b,
            "delta": self.delta,
        }

    def get_term_frequency(self, term: str) -> int:
        """Get document frequency for a term."""
        return self._doc_freqs.get(term.lower(), 0)

    def get_top_terms(self, limit: int = 50) -> list[tuple[str, int]]:
        """Get most frequent terms in the corpus."""
        sorted_terms = sorted(self._doc_freqs.items(), key=lambda x: x[1], reverse=True)
        return sorted_terms[:limit]
