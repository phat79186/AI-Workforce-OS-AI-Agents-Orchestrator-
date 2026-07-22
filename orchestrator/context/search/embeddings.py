"""
Embedding System for Semantic Search.

Provides vector embeddings for nodes using sentence-transformers,
enabling semantic similarity search across the context graph.
"""

from __future__ import annotations

import logging
import struct
from typing import Any

from orchestrator.context.models.schemas import Node
from orchestrator.context.store.graph_store import GraphStore


class EmbeddingStore:
    """Manages embeddings for semantic search."""

    DEFAULT_MODEL = "all-MiniLM-L6-v2"
    EMBEDDING_DIM = 384

    def __init__(
        self,
        graph_store: GraphStore,
        model_name: str | None = None,
        use_gpu: bool = False,
    ):
        """Initialize the embedding store.

        Args:
            graph_store: Graph store instance
            model_name: Sentence transformer model name
            use_gpu: Whether to use GPU for embeddings
        """
        self.logger = logging.getLogger("context.embeddings")
        self.graph_store = graph_store
        self.model_name = model_name or self.DEFAULT_MODEL
        self.use_gpu = use_gpu
        self._model = None
        self._dimension: int | None = None

    def _get_model(self):
        """Lazy load the sentence transformer model."""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer

                device = "cuda" if self.use_gpu else "cpu"
                self._model = SentenceTransformer(self.model_name, device=device)
                if self._model is not None:
                    self._dimension = self._model.get_sentence_embedding_dimension()
                    self.logger.info(
                        "Loaded embedding model: %s (dim=%s)",
                        self.model_name,
                        self._dimension,
                    )
            except ImportError:
                self.logger.warning(
                    "sentence-transformers not installed. "
                    "Install with: pip install sentence-transformers"
                )
                self._model = None
        return self._model

    @property
    def dimension(self) -> int:
        """Get embedding dimension."""
        if self._dimension is None:
            model = self._get_model()
            if model:
                self._dimension = model.get_sentence_embedding_dimension()
            else:
                self._dimension = self.EMBEDDING_DIM
        return self._dimension

    def generate_embedding(self, text: str) -> list[float] | None:
        """Generate embedding for text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector or None if model unavailable
        """
        model = self._get_model()
        if model is None:
            return None

        if not text or not text.strip():
            return None

        embedding = model.encode(text, convert_to_numpy=True)
        return embedding.tolist()

    def generate_embeddings_batch(self, texts: list[str]) -> list[list[float] | None]:
        """Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        model = self._get_model()
        if model is None:
            return [None] * len(texts)

        valid_texts = [(i, t) for i, t in enumerate(texts) if t and t.strip()]
        if not valid_texts:
            return [None] * len(texts)

        indices, clean_texts = zip(*valid_texts)
        embeddings = model.encode(list(clean_texts), convert_to_numpy=True, show_progress_bar=False)

        results: list[list[float] | None] = [None] * len(texts)
        for idx, emb in zip(indices, embeddings):
            results[idx] = emb.tolist()

        return results

    def _embedding_to_bytes(self, embedding: list[float]) -> bytes:
        """Convert embedding list to bytes for storage."""
        return struct.pack(f"{len(embedding)}f", *embedding)

    def _bytes_to_embedding(self, data: bytes) -> list[float]:
        """Convert bytes back to embedding list."""
        count = len(data) // 4
        return list(struct.unpack(f"{count}f", data))

    def store_embedding(self, node_id: str, embedding: list[float]) -> bool:
        """Store embedding for a node.

        Args:
            node_id: Node ID
            embedding: Embedding vector

        Returns:
            True if stored successfully
        """
        from datetime import datetime, timezone

        conn = self.graph_store._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                INSERT OR REPLACE INTO embeddings (node_id, embedding, model_name, created_at)
                VALUES (?, ?, ?, ?)
            """,
                (
                    node_id,
                    self._embedding_to_bytes(embedding),
                    self.model_name,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            conn.commit()
            return True
        except Exception as e:
            self.logger.error("Failed to store embedding for %s: %s", node_id, e)
            conn.rollback()
            return False
        finally:
            cursor.close()

    def get_embedding(self, node_id: str) -> list[float] | None:
        """Get stored embedding for a node.

        Args:
            node_id: Node ID

        Returns:
            Embedding vector or None
        """
        conn = self.graph_store._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT embedding FROM embeddings WHERE node_id = ?", (node_id,))
            row = cursor.fetchone()
            if row:
                return self._bytes_to_embedding(row[0])
            return None
        finally:
            cursor.close()

    def embed_node(self, node: Node, force: bool = False) -> list[float] | None:
        """Generate and store embedding for a node.

        Args:
            node: Node to embed
            force: Regenerate even if embedding exists

        Returns:
            Embedding vector
        """
        if not force:
            existing = self.get_embedding(node.id)
            if existing:
                return existing

        text = self._node_to_text(node)
        embedding = self.generate_embedding(text)

        if embedding:
            self.store_embedding(node.id, embedding)

        return embedding

    def _node_to_text(self, node: Node) -> str:
        """Convert node to text for embedding."""
        parts = []

        if node.title:
            parts.append(node.title)

        if node.content:
            parts.append(node.content)

        if node.tags:
            parts.append(" ".join(node.tags))

        node_dict = node.to_dict()
        for key in ["description", "summary", "task_description", "purpose", "rationale"]:
            if key in node_dict and node_dict[key]:
                parts.append(str(node_dict[key]))

        return " ".join(parts)

    def cosine_similarity(self, vec1: list[float], vec2: list[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        import numpy as np  # pylint: disable=C0415

        a = np.array(vec1)
        b = np.array(vec2)

        dot_product = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return float(dot_product / (norm_a * norm_b))

    def semantic_search(
        self,
        query: str,
        limit: int = 20,
        min_similarity: float = 0.5,
        node_types: list[str] | None = None,
    ) -> list[tuple[Node, float]]:
        """Search nodes by semantic similarity.

        Args:
            query: Search query text
            limit: Maximum results
            min_similarity: Minimum cosine similarity threshold
            node_types: Filter by node types

        Returns:
            List of (node, similarity_score) tuples sorted by similarity
        """
        query_embedding = self.generate_embedding(query)
        if query_embedding is None:
            return []

        conn = self.graph_store._get_connection()
        cursor = conn.cursor()

        try:
            if node_types:
                placeholders = ",".join("?" * len(node_types))
                cursor.execute(  # noqa: B608  # parameterized with ? placeholders
                    f"""
                    SELECT n.*, e.embedding
                    FROM nodes n
                    JOIN embeddings e ON n.id = e.node_id
                    WHERE n.node_type IN ({placeholders})
                """,
                    node_types,
                )
            else:
                cursor.execute("""
                    SELECT n.*, e.embedding
                    FROM nodes n
                    JOIN embeddings e ON n.id = e.node_id
                """)

            results: list[tuple[Node, float]] = []

            for row in cursor.fetchall():
                stored_embedding = self._bytes_to_embedding(row["embedding"])
                similarity = self.cosine_similarity(query_embedding, stored_embedding)

                if similarity >= min_similarity:
                    node = self.graph_store._row_to_node(row)
                    results.append((node, similarity))

            results.sort(key=lambda x: x[1], reverse=True)
            return results[:limit]

        finally:
            cursor.close()

    def find_similar_nodes(
        self,
        node_id: str,
        limit: int = 10,
        min_similarity: float = 0.6,
        exclude_connected: bool = True,
    ) -> list[tuple[Node, float]]:
        """Find nodes similar to a given node.

        Args:
            node_id: Reference node ID
            limit: Maximum results
            min_similarity: Minimum similarity threshold
            exclude_connected: Exclude already-connected nodes

        Returns:
            List of (similar_node, similarity) tuples
        """
        source_embedding = self.get_embedding(node_id)
        if source_embedding is None:
            node = self.graph_store.get_node(node_id)
            if node:
                source_embedding = self.embed_node(node)
            if source_embedding is None:
                return []

        connected_ids = set()
        if exclude_connected:
            for edge in self.graph_store.get_edges_from(node_id):
                connected_ids.add(edge.target_id)
            for edge in self.graph_store.get_edges_to(node_id):
                connected_ids.add(edge.source_id)

        conn = self.graph_store._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                SELECT n.*, e.embedding
                FROM nodes n
                JOIN embeddings e ON n.id = e.node_id
                WHERE n.id != ?
            """,
                (node_id,),
            )

            results: list[tuple[Node, float]] = []

            for row in cursor.fetchall():
                if row["id"] in connected_ids:
                    continue

                stored_embedding = self._bytes_to_embedding(row["embedding"])
                similarity = self.cosine_similarity(source_embedding, stored_embedding)

                if similarity >= min_similarity:
                    node = self.graph_store._row_to_node(row)
                    results.append((node, similarity))

            results.sort(key=lambda x: x[1], reverse=True)
            return results[:limit]

        finally:
            cursor.close()

    def embed_all_nodes(self, batch_size: int = 100) -> dict[str, int]:
        """Generate embeddings for all nodes that don't have them.

        Args:
            batch_size: Process nodes in batches

        Returns:
            Statistics about embedding generation
        """
        conn = self.graph_store._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT n.id, n.title, n.content, n.tags, n.extra_data
                FROM nodes n
                LEFT JOIN embeddings e ON n.id = e.node_id
                WHERE e.node_id IS NULL
            """)

            nodes_to_embed = cursor.fetchall()
            total = len(nodes_to_embed)
            embedded = 0
            failed = 0

            for i in range(0, total, batch_size):
                batch = nodes_to_embed[i : i + batch_size]

                texts = []
                for row in batch:
                    parts = []
                    if row["title"]:
                        parts.append(row["title"])
                    if row["content"]:
                        parts.append(row["content"])
                    if row["tags"]:
                        import json

                        tags = json.loads(row["tags"])
                        if tags:
                            parts.append(" ".join(tags))
                    texts.append(" ".join(parts))

                embeddings = self.generate_embeddings_batch(texts)

                for row, embedding in zip(batch, embeddings):
                    if embedding:
                        if self.store_embedding(row["id"], embedding):
                            embedded += 1
                        else:
                            failed += 1
                    else:
                        failed += 1

            return {
                "total": total,
                "embedded": embedded,
                "failed": failed,
            }

        finally:
            cursor.close()

    def get_stats(self) -> dict[str, Any]:
        """Get embedding statistics."""
        conn = self.graph_store._get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT COUNT(*) FROM embeddings")
            count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM nodes")
            total_nodes = cursor.fetchone()[0]

            return {
                "total_embeddings": count,
                "total_nodes": total_nodes,
                "coverage_percent": (count / total_nodes * 100) if total_nodes > 0 else 0,
                "model_name": self.model_name,
                "dimension": self.dimension,
            }
        finally:
            cursor.close()
