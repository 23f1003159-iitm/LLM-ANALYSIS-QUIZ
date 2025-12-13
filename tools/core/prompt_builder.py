"""Fully dynamic prompt builder - LLM creates perfect instructions for each question."""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from log import info, success, error
from llm import call
from tools.helper.paths import get_session_dir, get_question_path, get_prompt_path


async def build_instruction(quiz_url: str, session_data: dict) -> str:
    """
    Fully dynamic instruction builder - LLM analyzes and creates optimal prompt.
    
    Args:
        quiz_url: Quiz URL to load question.json
        session_data: Available data
    
    Returns:
        LLM-generated instruction prompt
    """
    info("prompt", "dynamic instruction generation")
    
    session_dir = get_session_dir(quiz_url)
    info("prompt", f"📁 SESSION: {session_dir.name}")
    
    question_file = get_question_path(quiz_url)
    
    if not question_file.exists():
        error("prompt", "question.json not found")
        return ""
    
    question_data = json.loads(question_file.read_text())
    
    question = question_data.get("question", "")
    answer_type = question_data.get("answer_type", "text")
    context = question_data.get("context", "")
    instructions = question_data.get("instructions", "")
    
    # Build data summary
    data_available = []
    if session_data.get("csv_data"):
        data_available.append(f"- CSV data (preview):\n{session_data['csv_data'][:400]}")
    if session_data.get("audio_text"):
        data_available.append(f"- Audio transcript: {session_data['audio_text'][:150]}")
    if session_data.get("vision_text"):
        data_available.append(f"- Screenshot analysis: {session_data['vision_text'][:150]}")
    
    data_summary = "\n".join(data_available) if data_available else "No additional data"
    
    # Step 1: Deep analysis of the question
    analysis_prompt = f"""Analyze this quiz question comprehensively:

QUESTION: {question}
ANSWER TYPE: {answer_type}
CONTEXT: {context}
INSTRUCTIONS: {instructions}

DATA AVAILABLE:
{data_summary}

Provide complete analysis:
1. Question type? (data analysis, simple calculation, text extraction, etc.)
2. Complexity level? (simple, moderate, complex, very complex)
3. Required approach? (direct reasoning, code execution, data processing)
4. Critical challenges? What makes this tricky?
5. What guarantees 100% accuracy?
6. Exact output format needed for answer_type: {answer_type}

Write detailed strategic analysis:"""
    
    analysis = await call(analysis_prompt, task="reason")
    
    if not analysis:
        error("prompt", "analysis failed")
        return ""
    
    info("prompt", f"analysis: {analysis[:100]}...")
    
    # Step 2: LLM creates perfect instruction prompt based on analysis
    meta_prompt = f"""You are the world's best prompt engineer. Create a PERFECT instruction prompt.

STRATEGIC ANALYSIS:
{analysis}

QUESTION TO SOLVE:
{question}

ANSWER TYPE: {answer_type}
CONTEXT: {context}
DATA: {data_summary}

YOUR MISSION:
Create an instruction prompt that guarantees perfect accuracy on first try.

The prompt you create MUST:
✓ Match the exact question type and complexity from analysis
✓ Use the optimal approach identified
✓ Be crystal clear about what's being asked
✓ Specify all available data and tools
✓ Give step-by-step solving approach
✓ Emphasize exact answer format: {answer_type}
✓ Tell solver to return ONLY the final answer (no explanations)
✓ Handle edge cases and potential errors
✓ If code needed: specify complete working code that prints only answer

CRITICAL REQUIREMENTS:
- Answer format: {answer_type}
- NO extra text in output
- If number: just number (e.g., 42)
- If text: just text
- If boolean: true or false
- If json: valid JSON only

Write the PERFECT instruction prompt now:"""
    
    instruction_prompt = await call(meta_prompt, task="prompt")
    
    if not instruction_prompt:
        error("prompt", "prompt generation failed")
        return ""
    
    # Save prompt
    prompt_file = get_prompt_path(quiz_url)
    prompt_file.write_text(instruction_prompt)
    info("prompt", f"saved to {prompt_file.name}")
    
    success("prompt", f"LLM generated ({len(instruction_prompt)} chars)")
    return instruction_prompt


async def build_code_execution_prompt(question: str, data: dict) -> str:
    """Build prompt for code execution tasks."""
    prompt = f"""Write Python code:

QUESTION: {question}
DATA: {data}

Print ONLY the final answer."""
    
    return prompt
