# Skill: Embeddings & Retrieval

Implement vector embeddings and semantic search for RAG and similarity matching.

## Capabilities
- Text embedding generation
- Vector similarity search
- Hybrid search (keyword + semantic)
- Chunking strategies
- Embedding model selection

## Patterns

### Sentence Transformers Embeddings
```python
from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List, Optional

class EmbeddingService:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self._model: Optional[SentenceTransformer] = None
        self._model_name = model_name

    @property
    def model(self) -> SentenceTransformer:
        """Lazy load model."""
        if self._model is None:
            self._model = SentenceTransformer(self._model_name)
        return self._model

    def embed(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings for texts."""
        return self.model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False
        )

    def embed_single(self, text: str) -> np.ndarray:
        """Generate embedding for single text."""
        return self.embed([text])[0]
```

### Cosine Similarity Search
```python
import numpy as np
from typing import List, Tuple

def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Compute cosine similarity between two vectors."""
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

def search_similar(
    query_embedding: np.ndarray,
    embeddings: np.ndarray,
    top_k: int = 10
) -> List[Tuple[int, float]]:
    """Find most similar embeddings."""
    # Compute similarities
    similarities = np.dot(embeddings, query_embedding)

    # Get top-k indices
    top_indices = np.argsort(similarities)[-top_k:][::-1]

    return [(int(idx), float(similarities[idx])) for idx in top_indices]
```

### Hybrid Search with RRF
```python
from typing import List, Dict, Tuple

def reciprocal_rank_fusion(
    rankings: List[List[Tuple[str, float]]],
    k: int = 60
) -> List[Tuple[str, float]]:
    """Combine multiple rankings using RRF."""
    scores: Dict[str, float] = {}

    for ranking in rankings:
        for rank, (doc_id, _) in enumerate(ranking):
            if doc_id not in scores:
                scores[doc_id] = 0.0
            scores[doc_id] += 1.0 / (k + rank + 1)

    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return sorted_scores

class HybridSearch:
    def __init__(self, embedding_service, bm25_index):
        self.embeddings = embedding_service
        self.bm25 = bm25_index

    def search(
        self,
        query: str,
        top_k: int = 10,
        semantic_weight: float = 0.5
    ) -> List[Tuple[str, float]]:
        """Hybrid search combining BM25 and semantic."""
        # Get BM25 results
        bm25_results = self.bm25.search(query, top_k=top_k * 2)

        # Get semantic results
        query_embedding = self.embeddings.embed_single(query)
        semantic_results = self.semantic_search(query_embedding, top_k * 2)

        # Combine with RRF
        combined = reciprocal_rank_fusion([bm25_results, semantic_results])

        return combined[:top_k]
```

### Text Chunking
```python
from typing import List

def chunk_text(
    text: str,
    chunk_size: int = 512,
    overlap: int = 50
) -> List[str]:
    """Split text into overlapping chunks."""
    words = text.split()
    chunks = []

    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk = ' '.join(words[start:end])
        chunks.append(chunk)

        if end >= len(words):
            break
        start = end - overlap

    return chunks

def chunk_by_sentences(
    text: str,
    max_chunk_size: int = 512,
    sentence_overlap: int = 1
) -> List[str]:
    """Split text by sentences with overlap."""
    import re
    sentences = re.split(r'(?<=[.!?])\s+', text)

    chunks = []
    current_chunk = []
    current_size = 0

    for sentence in sentences:
        sentence_size = len(sentence.split())

        if current_size + sentence_size > max_chunk_size and current_chunk:
            chunks.append(' '.join(current_chunk))
            # Keep last N sentences for overlap
            current_chunk = current_chunk[-sentence_overlap:]
            current_size = sum(len(s.split()) for s in current_chunk)

        current_chunk.append(sentence)
        current_size += sentence_size

    if current_chunk:
        chunks.append(' '.join(current_chunk))

    return chunks
```

## Model Selection Guide
| Model | Dimensions | Speed | Quality | Use Case |
|-------|-----------|-------|---------|----------|
| all-MiniLM-L6-v2 | 384 | Fast | Good | General purpose |
| all-mpnet-base-v2 | 768 | Medium | Better | Higher quality |
| bge-small-en-v1.5 | 384 | Fast | Good | English text |
| text-embedding-3-small | 1536 | API | High | OpenAI API |

## Checklist
- [ ] Model loaded lazily
- [ ] Embeddings normalized
- [ ] Chunking preserves context
- [ ] Hybrid search for best results
- [ ] Batch processing for efficiency
- [ ] Similarity threshold applied
- [ ] Results deduplicated
