"""LLM Package - Multi-model architecture."""

from llm.client import MODELS, LLMClient, MultiModelRouter, get_router
from llm.prompts import SYSTEM_PROMPT, get_prompt

__all__ = ["LLMClient", "MODELS", "MultiModelRouter", "get_router", "SYSTEM_PROMPT", "get_prompt"]
