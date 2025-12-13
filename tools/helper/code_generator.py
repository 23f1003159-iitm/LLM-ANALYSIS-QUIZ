"""Dynamic code generator - creates optimal code for ANY question type."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from log import info, success, error, warn
from llm import call


async def generate_code(question: str, data_info: dict) -> dict:
    """
    Fully dynamic code generation - LLM analyzes and creates best code.
    
    Args:
        question: The question to solve
        data_info: Information about available data
    
    Returns:
        dict with success, code
    """
    info("codegen", "dynamic code generation")
    
    # Build data context
    data_context = []
    if data_info.get("csv_files"):
        data_context.append(f"CSV files: {', '.join(data_info['csv_files'])}")
    if data_info.get("csv_preview"):
        data_context.append(f"Data preview:\n{data_info['csv_preview'][:500]}")
    if data_info.get("audio_text"):
        data_context.append(f"Audio: {data_info['audio_text'][:200]}")
    
    data_section = "\n".join(data_context) if data_context else "No data"
    
    # CRITICAL: Check if we actually have data files
    if not data_info.get("csv_files"):
        error("codegen", "no CSV files available - cannot generate code")
        return {
            "success": False,
            "code": "",
            "error": "No data files available for code generation"
        }
    
    # Step 1: Deep analysis of coding requirements
    analysis_prompt = f"""Analyze this coding task in detail:

QUESTION: {question}
AVAILABLE DATA: {data_section}

Provide deep analysis:
1. What exact operation is needed? (filtering, grouping, calculation, transformation, etc.)
2. What libraries are optimal? (pandas, numpy, statistics, etc.)
3. What's the step-by-step algorithm?
4. What edge cases must be handled?
5. What's the exact output format needed?
6. What's the critical logic that determines correctness?

Write detailed coding strategy:"""
    
    strategy = await call(analysis_prompt, task="reason")
    
    if not strategy:
        warn("codegen", "strategy generation failed, using simple approach")
        strategy = "Simple approach: Read CSV, filter data, calculate result"
    
    info("codegen", f"strategy: {strategy[:100]}...")
    
    # Step 2: Generate optimal code using the strategy
    code_generation_prompt = f"""You are a Python expert. Based on this strategy:

{strategy}

Write PERFECT Python code to solve:
QUESTION: {question}
DATA: {data_section}

CODE REQUIREMENTS:
✓ Import only necessary libraries
✓ CSV files are in current directory (use pd.read_csv('filename.csv'))
✓ Use the EXACT algorithm from strategy
✓ Handle ALL edge cases mentioned
✓ Print ONLY the final answer (no labels, no explanations)
✓ Code must be clean, efficient, and correct
✓ Add brief comments for critical logic

Write complete, executable Python code:"""
    
    response = await call(code_generation_prompt, task="code")
    
    if not response:
        error("codegen", "code generation failed")
        return {"success": False, "code": "", "error": "generation failed"}
    
    # Extract code
    code = response.strip()
    if "```python" in code:
        code = code.split("```python")[1].split("```")[0].strip()
    elif "```" in code:
        code = code.split("```")[1].split("```")[0].strip()
    
    success("codegen", f"generated {len(code)} chars with strategy")
    
    return {
        "success": True,
        "code": code,
        "strategy": strategy,
        "error": ""
    }
