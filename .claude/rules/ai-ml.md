# AI/ML Development Rules

## Data Handling
- Validate data quality before training
- Implement proper train/validation/test splits
- Use stratified sampling for imbalanced data
- Version datasets with DVC or similar tools
- Document data preprocessing steps

## Model Development
- Start with simple baselines before complex models
- Use cross-validation for hyperparameter tuning
- Track experiments with MLflow, Weights & Biases, or similar
- Document model architecture decisions
- Version models and training configurations

## Embeddings & Vector Search
- Choose embedding model based on use case (dense vs sparse)
- Normalize embeddings for cosine similarity
- Use appropriate vector databases (FAISS, Pinecone, Chroma)
- Implement proper chunking strategies for text
- Monitor embedding quality with similarity benchmarks

## LLM Integration
- Use structured prompts with clear instructions
- Implement prompt templating for consistency
- Add guardrails and output validation
- Handle rate limits and API errors gracefully
- Cache responses when appropriate

## RAG Pipeline Best Practices
- Optimize chunk size for your use case (typically 512-1024 tokens)
- Use hybrid search (BM25 + semantic) for better recall
- Implement reranking for improved precision
- Add context compression for long documents
- Monitor retrieval quality with relevance metrics

## Production Considerations
- Implement model monitoring (data drift, prediction drift)
- Set up A/B testing for model comparisons
- Use feature stores for consistent feature computation
- Implement fallback strategies for model failures
- Document model limitations and edge cases

## Ethics & Bias
- Audit training data for bias
- Test models on diverse inputs
- Document known limitations
- Implement content filtering for generative models
- Provide transparency on AI-generated content
