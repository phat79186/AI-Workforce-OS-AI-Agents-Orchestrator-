---
name: omniroute-gateway
description: Universal AI Gateway with 352 providers (150+ free), 1200+ models, quota-aware auto-fallback, and RTK + Caveman token compression. Use when routing agent tasks, handling rate-limit/quota errors, or optimizing API costs.
---

# OmniRoute Universal AI Gateway Skill

Imported from **[diegosouzapw/OmniRoute](https://github.com/diegosouzapw/OmniRoute)** — Free MIT AI gateway: one endpoint, 352 providers (150+ free), 1200+ models (Kimi, Claude, GPT, Gemini, GLM, DeepSeek, MiniMax). Works with Claude Code, Codex, Cursor, OpenCode, Cline & Copilot. Quota-aware auto-fallback, RTK+Caveman compression saves 15-95% tokens, MCP/A2A, Desktop/PWA.

## When to Use
- **Multi-Provider Routing**: Route agent tasks across 352 AI providers with 1200+ models from a single unified gateway.
- **Quota-Aware Auto-Fallback**: Automatically fall back to free or secondary provider tiers when encountering 429 quota limits or latency spikes.
- **Extreme Token Compression**: Apply combined RTK (Redundant Token Killer) + Caveman compression to trim prompt bloat by 15-95%.
- **Zero-Cost Scaling**: Prioritize 150+ verified free tier providers before consuming paid API credits.

## Quick Python Usage

```python
from orchestrator.integrations import ExternalEcosystemHub

hub = ExternalEcosystemHub()

# 1. Route with Quota-Aware Auto-Fallback
route_res = hub.omniroute.route_request(
    prompt="Analyze the distributed database topology and generate high-availability failover steps.",
    model_preference="deepseek-v3",
    optimize_tokens=True,
    quota_exhausted=False
)
print(f"Provider: {route_res['provider']} | Model: {route_res['model']} | Endpoint: {route_res['endpoint']}")

# 2. Simulate 429 Rate-Limit Fallback
fallback_res = hub.omniroute.route_request(
    prompt="Audit code security",
    model_preference="claude-3-5-sonnet",
    quota_exhausted=True
)
print(f"Fallback Provider: {fallback_res['provider']} | Status: {fallback_res['status']}")

# 3. Apply RTK + Caveman Compression
comp_res = hub.omniroute.compress_payload(
    "Please kindly look into the following code and make sure you do a complete analysis without skipping any lines."
)
print(f"Compressed: {comp_res['compressed_text']} | Saved: {comp_res['saved_tokens_percentage']}%")
```

## Supported Provider Tiers
- **Free Tiers (154 providers)**: Ollama, Groq, Together Free, Cloudflare Workers AI, HuggingFace Inference, DeepSeek Open, Kimi Free Tier, Zhipu GLM Open, MiniMax Starter.
- **Commercial Tiers (198 providers)**: Anthropic Claude, OpenAI GPT, Google Gemini, Mistral, Cohere, Perplexity.

## Verification
Run tests:
```bash
python -m pytest tests/test_external_integrations.py -o addopts="" -k "omniroute"
```
