"""LLM Client - Llama 3.3 70B for quiz solving via NVIDIA NIM.

This module provides an async client for interacting with Meta's Llama 3.3 70B
model through NVIDIA's NIM (NVIDIA Inference Microservices) API.
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

# Model configuration
MODEL = "meta/llama-3.3-70b-instruct"


class LLMClient:
    """Llama 3.3 70B client via NVIDIA NIM.

    Provides async interface to Meta's Llama model through NVIDIA's
    inference API for quiz solving with tool-calling capabilities.
    """

    def __init__(self):
        """Initialize the LLM client."""
        self.api_key = NVIDIA_API_KEY
        self.base_url = "https://integrate.api.nvidia.com/v1"
        self.model = MODEL
        logger.debug(f"Initialized LLM client with model: {self.model}")

    async def chat(
        self,
        messages: list,
        system_prompt: str = None,
        max_tokens: int = 1000,
    ) -> str:
        """Send chat request to NVIDIA NIM API.

        Args:
            messages: List of message dicts with 'role' and 'content'.
            system_prompt: Optional system prompt to prepend.
            max_tokens: Maximum tokens in response (default: 1000).

        Returns:
            str: LLM response content.

        Example:
            >>> client = LLMClient()
            >>> messages = [{"role": "user", "content": "What is 2+2?"}]
            >>> response = await client.chat(messages)
            >>> print(response)
            4
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

        logger.debug("Sending LLM request")

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    headers=headers,
                    timeout=60.0,
                )
                response.raise_for_status()
                data = response.json()

            content = data["choices"][0]["message"]["content"]
            logger.debug(f"LLM response received: {len(content)} chars")
            return content

        except Exception as e:
            logger.error(f"LLM request failed: {e}")
            return f"[Error: {e}]"

    async def solve(self, question: str, context: str = None) -> str:
        """Solve a quiz question with optional context.

        Args:
            question: The question to solve.
            context: Optional context information.

        Returns:
            str: The answer from the LLM.
        """
        from llm.prompts import SYSTEM_PROMPT

        user_msg = f"{context}\n\n{question}" if context else question

        messages = [{"role": "user", "content": user_msg}]
        return await self.chat(messages, system_prompt=SYSTEM_PROMPT)


async def solve(question: str, context: str = None) -> str:
    """Solve a question using the LLM.

    Convenience function that creates a client and solves the question.

    Args:
        question: The question to solve.
        context: Optional context information.

    Returns:
        str: The answer from the LLM.

    Example:
        >>> answer = await solve("What is 2+2?")
        >>> print(answer)
        4
    """
    client = LLMClient()
    return await client.solve(question, context)


if __name__ == "__main__":
    import asyncio

    async def main():
        """Test the LLM client."""
        logger.info(f"Model: {MODEL}")
        answer = await solve("What is 2+2? Just the number.")
        logger.info(f"Answer: {answer}")

    asyncio.run(main())
