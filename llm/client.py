"""LLM Client - Multi-model architecture for quiz solving via NVIDIA NIM.

This module provides async clients for multiple models, each specialized
for different task types: fast reasoning, deep reasoning, and coding.
"""

import sys
from pathlib import Path

import httpx

if __name__ == "__main__":
    # Allow running as script
    sys.path.insert(0, str(Path(__file__).parent.parent))

from config import NVIDIA_API_KEY
from logs.logger import get_logger

logger = get_logger("llm")

# Multi-model configuration - optimized for speed + accuracy
MODELS = {
    # Fast models (for simple questions)
    "fast": "meta/llama-3.3-70b-instruct",  # Good balance of speed/quality
    "ultra_fast": "meta/llama-3.1-8b-instruct",  # Fastest for trivial questions
    # Reasoning models (for complex analysis)
    "reasoning": "meta/llama-3.1-405b-instruct",  # Best accuracy (22/23)
    "nemotron": "nvidia/llama-3.1-nemotron-70b-instruct",  # NVIDIA optimized
    # Coding models
    "coder": "qwen/qwen2.5-coder-32b-instruct",  # Code generation
    # Specialized
    "math": "nvidia/llama-3.1-nemotron-70b-instruct",  # Better math/RMSE
}

# Default model for quiz solving
DEFAULT_MODEL = "reasoning"


class LLMClient:
    """Multi-model LLM client via NVIDIA NIM.

    Supports routing between fast (70B), reasoning (405B), and coder models.
    """

    def __init__(self, model_type: str = None):
        """Initialize the LLM client.

        Args:
            model_type: One of 'fast', 'reasoning', 'coder', or None for default
        """
        self.api_key = NVIDIA_API_KEY
        self.base_url = "https://integrate.api.nvidia.com/v1"
        self.model_type = model_type or DEFAULT_MODEL
        self.model = MODELS.get(self.model_type, MODELS[DEFAULT_MODEL])
        logger.debug(f"Initialized LLM client: {self.model_type} -> {self.model}")

    async def chat(
        self,
        messages: list,
        system_prompt: str = None,
        max_tokens: int = 2000,
    ) -> str:
        """Send chat request to NVIDIA NIM API.

        Args:
            messages: List of message dicts with 'role' and 'content'.
            system_prompt: Optional system prompt to prepend.
            max_tokens: Maximum tokens in response.

        Returns:
            str: LLM response content.
        """
        if system_prompt:
            messages = [{"role": "system", "content": system_prompt}] + messages

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.2,
            "max_tokens": max_tokens,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        logger.debug(f"Sending request to {self.model_type} model")

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    headers=headers,
                    timeout=90.0,
                )
                response.raise_for_status()
                data = response.json()

            content = data["choices"][0]["message"]["content"]
            logger.debug(f"Response from {self.model_type}: {len(content)} chars")
            return content

        except Exception as e:
            logger.error(f"LLM request failed ({self.model_type}): {e}")
            return f"[Error: {e}]"


class MultiModelRouter:
    """Routes questions to appropriate models based on task type."""

    def __init__(self):
        self.ultra_fast = LLMClient("ultra_fast")  # 8B for trivial
        self.fast = LLMClient("fast")  # 70B for simple
        self.reasoning = LLMClient("reasoning")  # 405B for complex
        self.coder = LLMClient("coder")  # Qwen for code
        self.math = LLMClient("math")  # Nemotron for math

    def detect_task_type(self, context: str) -> str:
        """Detect task type from context.

        Returns: 'ultra_fast', 'fast', 'reasoning', 'coder', or 'math'
        """
        context_lower = context.lower()

        # Math/RMSE tasks - use specialized math model
        math_keywords = [
            "rmse",
            "mse",
            "mean squared",
            "root mean",
            "regression",
            "r-squared",
            "correlation",
            "standard deviation",
        ]
        if any(kw in context_lower for kw in math_keywords):
            return "math"

        # Code generation tasks
        code_keywords = [
            "fastapi",
            "write a",
            "function",
            "route",
            "endpoint",
            "python code",
            "implement",
            "script",
            "@app",
        ]
        if any(kw in context_lower for kw in code_keywords):
            return "coder"

        # Complex reasoning tasks (PDF, calculations)
        complex_keywords = [
            "pdf",
            "calculate",
            "sum",
            "average",
            "parse",
            "extract",
            "group by",
            "sql",
            "total",
        ]
        if any(kw in context_lower for kw in complex_keywords):
            return "reasoning"

        # Ultra simple - just extracting values
        trivial_keywords = ["url", "submit url", "what is the"]
        if any(kw in context_lower for kw in trivial_keywords):
            return "ultra_fast"

        # Simple direct answer tasks
        simple_keywords = [
            "how many",
            "which",
            "select",
            "decode",
            "base64",
            "curl",
            "github",
            "header",
        ]
        if any(kw in context_lower for kw in simple_keywords):
            return "fast"

        # Default to reasoning for safety
        return "reasoning"

    async def chat(
        self, messages: list, system_prompt: str = None, max_tokens: int = 2000, context: str = ""
    ) -> str:
        """Route chat to appropriate model based on context."""
        task_type = self.detect_task_type(context)
        logger.info(f"Task type detected: {task_type}")

        clients = {
            "ultra_fast": self.ultra_fast,
            "fast": self.fast,
            "reasoning": self.reasoning,
            "coder": self.coder,
            "math": self.math,
        }

        client = clients.get(task_type, self.reasoning)
        return await client.chat(messages, system_prompt, max_tokens)


# Global router instance
_router = None


def get_router() -> MultiModelRouter:
    """Get or create the multi-model router."""
    global _router
    if _router is None:
        _router = MultiModelRouter()
    return _router


async def solve(question: str, context: str = None) -> str:
    """Solve a question using the appropriate model.

    Args:
        question: The question to solve.
        context: Optional context information.

    Returns:
        str: The answer from the LLM.
    """
    from llm.prompts import SYSTEM_PROMPT

    router = get_router()
    user_msg = f"{context}\n\n{question}" if context else question
    messages = [{"role": "user", "content": user_msg}]

    return await router.chat(messages, system_prompt=SYSTEM_PROMPT, context=context or question)


if __name__ == "__main__":
    import asyncio

    async def main():
        """Test the multi-model client."""
        router = get_router()

        # Test task detection
        tests = [
            "Write a FastAPI endpoint",  # coder
            "Calculate the sum of values",  # reasoning
            "What is the URL?",  # fast
        ]

        for test in tests:
            task_type = router.detect_task_type(test)
            logger.info(f"'{test[:30]}...' -> {task_type}")

    asyncio.run(main())
