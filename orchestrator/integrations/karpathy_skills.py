"""Integration for multica-ai/andrej-karpathy-skills AI engineering and neural network skills library."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class KarpathySkill:
    """An Andrej Karpathy AI engineering skill pattern."""

    name: str
    category: str
    description: str
    tags: List[str]
    best_practices: List[str]


class KarpathySkillsEngine:
    """Karpathy Skills Engine discovering and serving AI engineering, transformer architecture, and PyTorch skill patterns."""

    def __init__(self) -> None:
        self.source_repo = "multica-ai/andrej-karpathy-skills"
        self.version = "1.0.0"
        self.skills: Dict[str, KarpathySkill] = {
            "micrograd-autograd": KarpathySkill(
                name="micrograd-autograd",
                category="ai-ml",
                description="Minimal autograd engine and backpropagation intuition for scalar values.",
                tags=["autograd", "backprop", "neural-network", "python"],
                best_practices=[
                    "Build explicit topological DAG for backprop graph evaluation.",
                    "Maintain zero external dependencies for core mathematical operations.",
                ],
            ),
            "nanogpt-transformer": KarpathySkill(
                name="nanogpt-transformer",
                category="ai-ml",
                description="Clean, readable decoder-only Transformer architecture with causal self-attention.",
                tags=["transformer", "gpt", "attention", "pytorch"],
                best_practices=[
                    "Implement Multi-Head Causal Self-Attention with FlashAttention where available.",
                    "Use residual connections and LayerNorm before attention blocks (Pre-LN).",
                ],
            ),
            "tokenizer-bpe": KarpathySkill(
                name="tokenizer-bpe",
                category="ai-ml",
                description="Byte Pair Encoding (BPE) LLM tokenizer implementation.",
                tags=["tokenizer", "bpe", "nlp", "llm"],
                best_practices=[
                    "Train BPE vocabulary iteratively on clean corpus bytes.",
                    "Handle special tokens and regex splitting patterns cleanly.",
                ],
            ),
            "makemore-nn": KarpathySkill(
                name="makemore-nn",
                category="ai-ml",
                description="Autoregressive character-level language modeling (Bigram, MLP, WaveNet, Transformer).",
                tags=["language-model", "autoregressive", "pytorch"],
                best_practices=[
                    "Monitor loss curves and learning rate decay carefully.",
                    "Audit weight initialization scaling to prevent vanishing/exploding gradients.",
                ],
            ),
            "pytorch-clean-code": KarpathySkill(
                name="pytorch-clean-code",
                category="ai-ml",
                description="Zero-redundancy clean PyTorch training loop and GPU memory optimization.",
                tags=["pytorch", "clean-code", "optimization", "gpu"],
                best_practices=[
                    "Use torch.compile() for fused kernel speedups.",
                    "Always set zero_grad(set_to_none=True) for memory efficiency.",
                ],
            ),
        }

    def list_skills(self) -> List[KarpathySkill]:
        """Return list of all registered Karpathy skills."""
        return list(self.skills.values())

    def get_skill(self, name: str) -> Optional[KarpathySkill]:
        """Retrieve a specific Karpathy skill by name."""
        return self.skills.get(name.lower().strip())

    def execute_skill_pattern(
        self, name: str, input_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute a Karpathy AI skill pattern with input context."""
        skill = self.get_skill(name)
        if not skill:
            skill = self.skills["pytorch-clean-code"]

        return {
            "source_repo": self.source_repo,
            "skill_name": skill.name,
            "category": skill.category,
            "description": skill.description,
            "tags": skill.tags,
            "best_practices": skill.best_practices,
            "input_context": input_context or {},
            "status": "PATTERN_EXECUTED",
        }
