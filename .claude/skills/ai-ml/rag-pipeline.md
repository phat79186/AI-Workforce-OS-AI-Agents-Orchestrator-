# Skill: RAG Pipeline Implementation

Build Retrieval-Augmented Generation pipelines for context-aware AI responses.

## Capabilities
- Document ingestion
- Chunking and indexing
- Query processing
- Context retrieval
- Response generation
- Pipeline orchestration

## Patterns

### Complete RAG Pipeline
```python
from dataclasses import dataclass
from typing import List, Optional
import asyncio

@dataclass
class Document:
    id: str
    content: str
    metadata: dict

@dataclass
class RetrievedContext:
    documents: List[Document]
    query: str
    scores: List[float]

@dataclass
class RAGResponse:
    answer: str
    context: RetrievedContext
    confidence: float

class RAGPipeline:
    def __init__(
        self,
        embedding_service,
        vector_store,
        llm_client,
        reranker: Optional[object] = None
    ):
        self.embeddings = embedding_service
        self.store = vector_store
        self.llm = llm_client
        self.reranker = reranker

    async def ingest(self, documents: List[Document]) -> int:
        """Ingest documents into the pipeline."""
        chunks = []
        for doc in documents:
            doc_chunks = self._chunk_document(doc)
            chunks.extend(doc_chunks)

        # Generate embeddings
        texts = [c.content for c in chunks]
        embeddings = self.embeddings.embed(texts)

        # Store in vector database
        await self.store.add(chunks, embeddings)

        return len(chunks)

    async def query(
        self,
        question: str,
        top_k: int = 5,
        min_score: float = 0.7
    ) -> RAGResponse:
        """Query the RAG pipeline."""
        # 1. Embed query
        query_embedding = self.embeddings.embed_single(question)

        # 2. Retrieve candidates
        candidates = await self.store.search(
            query_embedding,
            top_k=top_k * 2  # Get more for reranking
        )

        # 3. Optional: Rerank
        if self.reranker:
            candidates = self.reranker.rerank(question, candidates)

        # 4. Filter by score
        filtered = [
            (doc, score) for doc, score in candidates
            if score >= min_score
        ][:top_k]

        if not filtered:
            return RAGResponse(
                answer="I don't have enough context to answer this question.",
                context=RetrievedContext([], question, []),
                confidence=0.0
            )

        # 5. Build context
        context = RetrievedContext(
            documents=[doc for doc, _ in filtered],
            query=question,
            scores=[score for _, score in filtered]
        )

        # 6. Generate response
        answer = await self._generate_response(question, context)

        return RAGResponse(
            answer=answer,
            context=context,
            confidence=sum(context.scores) / len(context.scores)
        )

    async def _generate_response(
        self,
        question: str,
        context: RetrievedContext
    ) -> str:
        """Generate response using LLM with retrieved context."""
        context_text = "\n\n---\n\n".join(
            f"[Source {i+1}]: {doc.content}"
            for i, doc in enumerate(context.documents)
        )

        prompt = f"""Answer the question based on the provided context.
If the context doesn't contain enough information, say so.

Context:
{context_text}

Question: {question}

Answer:"""

        response = await self.llm.generate(prompt)
        return response.content

    def _chunk_document(
        self,
        doc: Document,
        chunk_size: int = 500,
        overlap: int = 50
    ) -> List[Document]:
        """Chunk document into smaller pieces."""
        words = doc.content.split()
        chunks = []

        start = 0
        chunk_idx = 0
        while start < len(words):
            end = min(start + chunk_size, len(words))
            chunk_content = ' '.join(words[start:end])

            chunks.append(Document(
                id=f"{doc.id}_chunk_{chunk_idx}",
                content=chunk_content,
                metadata={
                    **doc.metadata,
                    "parent_id": doc.id,
                    "chunk_index": chunk_idx
                }
            ))

            chunk_idx += 1
            if end >= len(words):
                break
            start = end - overlap

        return chunks
```

### Query Expansion
```python
async def expand_query(
    llm_client,
    original_query: str,
    num_expansions: int = 3
) -> List[str]:
    """Expand query to improve retrieval."""
    prompt = f"""Generate {num_expansions} alternative phrasings of this question.
Each should capture the same intent but use different words.

Original: {original_query}

Alternatives (one per line):"""

    response = await llm_client.generate(prompt)
    alternatives = response.content.strip().split('\n')

    return [original_query] + alternatives[:num_expansions]
```

### Contextual Compression
```python
async def compress_context(
    llm_client,
    documents: List[Document],
    question: str,
    max_tokens: int = 2000
) -> str:
    """Compress retrieved documents to relevant parts."""
    compressed_parts = []

    for doc in documents:
        prompt = f"""Extract only the parts relevant to the question.
If nothing is relevant, respond with "NOT_RELEVANT".

Question: {question}

Document:
{doc.content}

Relevant parts:"""

        response = await llm_client.generate(prompt, max_tokens=500)
        if "NOT_RELEVANT" not in response.content:
            compressed_parts.append(response.content)

    return "\n\n".join(compressed_parts)
```

### Evaluation Metrics
```python
from typing import List, Tuple

def compute_recall(
    retrieved: List[str],
    relevant: List[str]
) -> float:
    """Compute recall@k."""
    if not relevant:
        return 0.0

    retrieved_set = set(retrieved)
    relevant_set = set(relevant)

    return len(retrieved_set & relevant_set) / len(relevant_set)

def compute_mrr(
    retrieved: List[str],
    relevant: List[str]
) -> float:
    """Compute Mean Reciprocal Rank."""
    relevant_set = set(relevant)

    for i, doc_id in enumerate(retrieved):
        if doc_id in relevant_set:
            return 1.0 / (i + 1)

    return 0.0
```

## Checklist
- [ ] Documents properly chunked
- [ ] Chunk overlap maintains context
- [ ] Embeddings cached
- [ ] Retrieval filtered by threshold
- [ ] Context fits in LLM window
- [ ] Sources cited in response
- [ ] Evaluation metrics tracked
- [ ] Fallback for no context
