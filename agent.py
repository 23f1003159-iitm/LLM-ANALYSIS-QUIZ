"""Agent - LLM-controlled quiz solver using tools.

This module implements the main quiz-solving agent that orchestrates
the use of core tools (scraper, converter, runner, submitter) under
LLM control to solve quiz questions dynamically.
"""

import re

from config import EMAIL, SECRET_KEY
from core import convert, execute, scrape, submit
from llm import SYSTEM_PROMPT, LLMClient
from logs.logger import get_logger

logger = get_logger("agent")


async def solve_quiz(url: str) -> dict:
    """Solve a quiz using LLM-controlled tools.

    Implements the workflow: URL → SCRAPE → CONVERT → LLM → RUN_CODE/SCRAPE → SUBMIT

    Args:
        url: The quiz URL to solve.

    Returns:
        dict: Result containing:
            - correct (bool): Whether the answer was correct
            - reason (str): Error message if wrong
            - next_url (str): URL to next quiz if available

    Example:
        >>> result = await solve_quiz("https://quiz.com/q1")
        >>> print(result['correct'])
        True
    """
    logger.info(f"Scraping: {url}")
    scraped = await scrape(url)

    logger.info("Converting data")
    converted = await convert(scraped)

    logger.info("Starting LLM solver")
    answer = await solve_with_llm(converted["context"], converted["data"], url)

    logger.info(f"Submitting: {answer[:50]}...")
    result = await submit(
        url="https://tds-llm-analysis.s-anand.net/submit",
        email=EMAIL,
        secret=SECRET_KEY,
        quiz_url=url,
        answer=answer,
    )

    if result["correct"]:
        logger.info("✓ CORRECT!")
    else:
        logger.warning(f"✗ WRONG: {result.get('reason', '')}")

    return result


async def solve_with_llm(context: str, data: dict, quiz_url: str) -> str:
    """Solve quiz using LLM with iterative tool calling.

    The LLM can use three tools:
    - RUN_CODE: Execute Python for calculations/processing
    - SCRAPE: Fetch additional URLs
    - SUBMIT: Submit the final answer

    Args:
        context: Formatted context string from converter
        data: Collected data (CSV, params, etc.)
        quiz_url: Original quiz URL for resolving relative URLs

    Returns:
        str: The final answer to submit

    Note:
        Runs up to 5 iterations to allow LLM to use tools before submitting.
    """
    client = LLMClient()

    messages = [{"role": "user", "content": f"Solve this quiz:\n\n{context}"}]
    max_iterations = 5

    for i in range(max_iterations):
        logger.debug(f"LLM Iteration {i + 1}/{max_iterations}")

        response = await client.chat(
            messages=messages, system_prompt=SYSTEM_PROMPT, max_tokens=2000
        )
        logger.debug(f"LLM Response: {response[:100]}...")

        # Check for RUN_CODE tool FIRST (highest priority)
        if "TOOL: RUN_CODE" in response:
            code = extract_code(response)
            if code:
                logger.debug("Executing code...")
                result = execute(code, data)

                if result["error"]:
                    tool_result = f"CODE ERROR: {result['error']}"
                    logger.error(f"Code execution error: {result['error']}")
                else:
                    tool_result = f"CODE OUTPUT: {result['output']}"
                    logger.debug(f"Code output: {result['output']}")

                messages.append({"role": "assistant", "content": response})
                messages.append(
                    {
                        "role": "user",
                        "content": f"{tool_result}\n\nNow submit the final answer using TOOL: SUBMIT",
                    }
                )
                continue

        # Check for SCRAPE tool (fetch additional URL)
        if "TOOL: SCRAPE" in response:
            url_match = re.search(r"URL:\s*(\S+)", response)
            if url_match:
                from urllib.parse import urljoin

                scrape_url = url_match.group(1)
                # Resolve relative URLs
                if not scrape_url.startswith("http"):
                    scrape_url = urljoin(quiz_url, scrape_url)
                logger.debug(f"Scraping additional URL: {scrape_url}")
                scraped = await scrape(scrape_url)

                tool_result = f"SCRAPED:\n{scraped['text']}"
                messages.append({"role": "assistant", "content": response})
                messages.append({"role": "user", "content": tool_result})
                continue

        # Check for SUBMIT tool LAST (final answer)
        if "TOOL: SUBMIT" in response or "ANSWER:" in response:
            answer = extract_answer(response)
            logger.debug(f"Extracted answer: {answer[:100]}...")
            return answer

        # No tool found - try to extract answer directly
        answer = extract_answer(response)
        if answer:
            logger.debug(f"Extracted answer from response: {answer[:100]}...")
            return answer

        # Ask LLM to provide answer
        logger.debug("No tool found, asking for SUBMIT")
        messages.append({"role": "assistant", "content": response})
        messages.append(
            {
                "role": "user",
                "content": "Please provide the final answer using: TOOL: SUBMIT\nANSWER: your_answer",
            }
        )

    logger.error("Max iterations reached without answer")
    return "ERROR: Max iterations reached"


def extract_answer(response: str) -> str:
    """Extract answer from LLM response.

    Looks for ANSWER: pattern in the response and extracts the value.
    Preserves newlines for multi-line answers (e.g., YAML).
    Strips markdown code blocks and cleans up formatting.

    Args:
        response: LLM response text

    Returns:
        str: Extracted answer, or empty string if not found

    Note:
        Uses strip(' \\t') instead of strip() to preserve newlines in YAML.
    """
    # Check for ANSWER: followed by code block (```python\n...\n```)
    match = re.search(r"ANSWER:\s*```(?:python)?\n(.+?)```", response, re.DOTALL)
    if match:
        answer = match.group(1).strip()
        return answer

    # Check for ANSWER: pattern (inline or multi-line)
    match = re.search(r"ANSWER:\s*(.+)", response, re.DOTALL)
    if match:
        answer = match.group(1)
        # Clean up the answer
        answer = clean_answer(answer)
        # Stop at double newline if present
        if "\n\n" in answer:
            answer = answer.split("\n\n")[0]
        return answer.strip()

    # Check for TOOL: SUBMIT pattern with code block
    match = re.search(
        r"TOOL:\s*SUBMIT\s*\n.*?ANSWER:\s*```(?:python)?\n(.+?)```", response, re.DOTALL
    )
    if match:
        answer = match.group(1).strip()
        return answer

    # Check for TOOL: SUBMIT pattern (inline)
    match = re.search(r"TOOL:\s*SUBMIT\s*\n.*?ANSWER:\s*(.+)", response, re.DOTALL)
    if match:
        answer = match.group(1)
        answer = clean_answer(answer)
        if "\n\n" in answer:
            answer = answer.split("\n\n")[0]
        return answer.strip()

    return ""


def clean_answer(answer: str) -> str:
    """Clean up extracted answer.

    Removes markdown code blocks, strips whitespace, and fixes formatting.

    Args:
        answer: Raw extracted answer

    Returns:
        str: Cleaned answer
    """
    answer = answer.strip()

    # Remove markdown code blocks (```python, ```, etc.)
    if answer.startswith("```"):
        # Find the end of the first line (language specifier)
        first_newline = answer.find("\n")
        if first_newline != -1:
            answer = answer[first_newline + 1 :]
        # Remove trailing ```
        if answer.endswith("```"):
            answer = answer[:-3]
        answer = answer.strip()

    # Strip leading/trailing spaces but preserve internal newlines
    return answer.strip(" \t")


def extract_code(response: str) -> str:
    """Extract Python code from LLM response.

    Looks for code blocks in ```python format.

    Args:
        response: LLM response text

    Returns:
        str: Extracted Python code, or empty string if not found
    """
    match = re.search(r"```python\n(.*?)```", response, re.DOTALL)
    if match:
        return match.group(1).strip()
    return ""
