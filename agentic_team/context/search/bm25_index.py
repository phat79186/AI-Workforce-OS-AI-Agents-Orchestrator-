"""
BM25 Index for Keyword Search — Agentic Team Context.

Independent implementation — does NOT import from orchestrator/context.
Implements BM25 (Best Matching 25) algorithm for fast keyword-based
retrieval from the agentic team context graph.
"""

from __future__ import annotations

import logging
import math
import re
from collections import Counter, defaultdict
from typing import Any

from agentic_team.context.models.schemas import Node, NodeType
from agentic_team.context.store.graph_store import GraphStore


class BM25Index:
    """BM25 search index for keyword retrieval over agentic team context."""

    def __init__(
        self,
        graph_store: GraphStore,
        k1: float = 1.5,
        b: float = 0.75,
    ):
        """Initialize BM25 index.

        Args:
            graph_store: Graph store instance.
            k1: Term frequency saturation parameter.
            b: Document length normalization parameter.
        """
        self.logger = logging.getLogger("agentic_team.context.bm25")
        self.graph_store = graph_store
        self.k1 = k1
        self.b = b

        self._doc_freqs: dict[str, int] = defaultdict(int)
        self._doc_lens: dict[str, int] = {}
        self._avg_doc_len: float = 0.0
        self._total_docs: int = 0
        self._inverted_index: dict[str, set[str]] = defaultdict(set)
        self._doc_terms: dict[str, Counter] = {}
        self._stopwords = self._default_stopwords()

    # ------------------------------------------------------------------
    # Stopwords & tokenisation
    # ------------------------------------------------------------------

    @staticmethod
    def _default_stopwords() -> set[str]:
        """Return a compact set of English stopwords."""
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

    def _tokenize(self, text: str) -> list[str]:
        """Tokenize *text* into lower-case alphanumeric tokens.

        Removes stopwords and single-character tokens.

        Args:
            text: Raw input string.

        Returns:
            List of cleaned tokens.
        """
        if not text:
            return []
        tokens = re.findall(r"[a-z0-9_]+", text.lower())
        return [t for t in tokens if t not in self._stopwords and len(t) > 1]

    # ------------------------------------------------------------------
    # Document helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _node_to_text(node: Node) -> str:
        """Convert a *node* to a single text document for indexing.

        Title is duplicated to give it higher weight.
        """
        parts: list[str] = []
        if node.title:
            parts.append(node.title)
            parts.append(node.title)
        if node.content:
            parts.append(node.content)
        if node.tags:
            parts.extend(node.tags)

        node_dict = node.to_dict()
        for field in (
            "description",
            "summary",
            "task_description",
            "purpose",
            "rationale",
            "error_message",
            "correction",
            "code",
        ):
            val = node_dict.get(field)
            if val:
                parts.append(str(val))

        return " ".join(parts)

    # ------------------------------------------------------------------
    # Index management
    # ------------------------------------------------------------------

    def _update_stats(self) -> None:
        """Recompute aggregate statistics after index changes."""
        self._total_docs = len(self._doc_lens)
        if self._total_docs > 0:
            self._avg_doc_len = sum(self._doc_lens.values()) / self._total_docs
        else:
            self._avg_doc_len = 0.0

    def _remove_from_index(self, node_id: str) -> None:
        """Remove a single document from the in-memory index."""
        if node_id not in self._doc_terms:
            return

        for term in self._doc_terms[node_id]:
            self._inverted_index[term].discard(node_id)
            if not self._inverted_index[term]:
                del self._inverted_index[term]
                self._doc_freqs.pop(term, None)
            else:
                self._doc_freqs[term] = len(self._inverted_index[term])

        del self._doc_terms[node_id]
        del self._doc_lens[node_id]
        self._update_stats()

    def index_node(self, node: Node) -> None:
        """Add or replace a node in the BM25 index.

        Args:
            node: Node to index.
        """
        doc_text = self._node_to_text(node)
        terms = self._tokenize(doc_text)
        if not terms:
            return

        if node.id in self._doc_terms:
            self._remove_from_index(node.id)

        term_counts = Counter(terms)
        self._doc_terms[node.id] = term_counts
        self._doc_lens[node.id] = len(terms)

        for term in term_counts:
            self._inverted_index[term].add(node.id)
            self._doc_freqs[term] = len(self._inverted_index[term])

        self._update_stats()

    def build_index(self, batch_size: int = 1000) -> dict[str, Any]:
        """Build (or rebuild) the index from all nodes in the graph store.

        Args:
            batch_size: Number of nodes to fetch per batch.

        Returns:
            Statistics dict with *indexed*, *skipped*, *vocabulary_size*,
            and *average_doc_length* keys.
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
                terms = self._tokenize(self._node_to_text(node))
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
        self.logger.info("BM25 index built: %d indexed, %d skipped", indexed, skipped)

        return {
            "indexed": indexed,
            "skipped": skipped,
            "vocabulary_size": len(self._doc_freqs),
            "average_doc_length": self._avg_doc_len,
        }

    # ------------------------------------------------------------------
    # BM25 scoring
    # ------------------------------------------------------------------

    def _bm25_score(self, query_terms: list[str], doc_id: str) -> float:
        """Compute BM25 relevance score for *doc_id* given *query_terms*."""
        if doc_id not in self._doc_terms:
            return 0.0

        doc_len = self._doc_lens[doc_id]
        doc_term_counts = self._doc_terms[doc_id]
        score = 0.0

        for term in query_terms:
            tf = doc_term_counts.get(term, 0)
            if tf == 0:
                continue
            df = self._doc_freqs.get(term, 0)
            if df == 0:
                continue

            idf = math.log((self._total_docs - df + 0.5) / (df + 0.5) + 1.0)
            norm = 1.0 - self.b + self.b * doc_len / max(self._avg_doc_len, 1.0)
            tf_component = (tf * (self.k1 + 1.0)) / (tf + self.k1 * norm)
            score += idf * tf_component

        return score

    # ------------------------------------------------------------------
    # Public search API
    # ------------------------------------------------------------------

    def search(
        self,
        query: str,
        limit: int = 10,
        node_types: list[NodeType] | None = None,
        min_score: float = 0.0,
    ) -> list[tuple[Node, float]]:
        """Search the index using BM25 ranking.

        Args:
            query: Natural-language search query.
            limit: Maximum number of results.
            node_types: Optional filter by node type(s).
            min_score: Minimum BM25 score threshold.

        Returns:
            List of ``(Node, score)`` tuples sorted by descending relevance.
        """
        query_terms = self._tokenize(query)
        if not query_terms:
            return []

        candidate_ids: set[str] = set()
        for term in query_terms:
            candidate_ids.update(self._inverted_index.get(term, set()))

        if not candidate_ids:
            return []

        scored: list[tuple[str, float]] = []
        for doc_id in candidate_ids:
            s = self._bm25_score(query_terms, doc_id)
            if s >= min_score:
                scored.append((doc_id, s))

        scored.sort(key=lambda x: x[1], reverse=True)

        results: list[tuple[Node, float]] = []
        for doc_id, s in scored[: limit * 2]:
            node = self.graph_store.get_node(doc_id)
            if node is None:
                continue
            if node_types and node.node_type not in node_types:
                continue
            results.append((node, s))
            if len(results) >= limit:
                break

        return results

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    def get_stats(self) -> dict[str, Any]:
        """Return index statistics."""
        return {
            "total_documents": self._total_docs,
            "vocabulary_size": len(self._doc_freqs),
            "average_doc_length": self._avg_doc_len,
            "k1": self.k1,
            "b": self.b,
        }
