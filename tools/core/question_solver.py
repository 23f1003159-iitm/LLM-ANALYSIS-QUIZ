"""Dynamic question solver - adapts strategy to each unique quiz."""
import sys
import json
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from log import info, success, error, warn
from llm import call
from tools.helper.paths import (
    get_session_dir, get_question_path, get_answer_path, 
    get_code_path, list_input_files
)
from tools.helper.code_generator import generate_code
from tools.helper.code_executor import execute_code, save_code


async def solve(quiz_url: str, instruction_prompt: str) -> dict:
    """
    Dynamically solve quiz - LLM decides the best solving strategy for THIS question.
    
    Args:
        quiz_url: Quiz URL to find session folder
        instruction_prompt: The solving instruction prompt
    
    Returns:
        dict with success, answer, method used
    """
    info("solver", "analyzing question to determine solving strategy")
    
    session_dir = get_session_dir(quiz_url)
    info("solver", f"📁 SESSION: {session_dir.name}")
    
    question_file = get_question_path(quiz_url)
    question_data = json.loads(question_file.read_text())
    
    question = question_data.get("question", "")
    answer_type = question_data.get("answer_type", "text")
    context = question_data.get("context", "")
    
    # Step 1: LLM analyzes THIS question and decides solving strategy
    strategy_prompt = f"""Analyze this question and decide the BEST solving approach:

QUESTION: {question}
ANSWER TYPE: {answer_type}
CONTEXT: {context}

Determine:
1. Can this be solved with direct reasoning? (yes/no)
2. Does it require code execution? (yes/no)
3. If code: what type? (data filtering, calculation, aggregation, etc.)
4. What's the critical step to get the right answer?

Provide your strategic decision:"""
    
    strategy = await call(strategy_prompt, task="fast")
    info("solver", f"strategy: {strategy[:100]}...")
    
    # Check if data files are actually available using paths helper
    from tools.helper.paths import list_files_by_type
    files_by_type = list_files_by_type(quiz_url)
    csv_files = files_by_type.get("csv", [])
    has_data = len(csv_files) > 0
    info("solver", f"found {len(csv_files)} CSV files")
    
    # Step 2: Execute based on strategy AND data availability
    needs_code = any(keyword in strategy.lower() for keyword in 
                     ["yes" and "code", "require code", "need code", "csv", "filter", "calculate"])
    
    # Check if this is a visualization/chart question
    needs_chart = any(keyword in question.lower() for keyword in 
                      ["chart", "plot", "graph", "visualiz", "diagram", "bar chart", "line chart", "pie chart"])
    
    if answer_type in ("chart", "image", "base64", "visualization"):
        needs_chart = True
    
    if needs_chart:
        info("solver", "question requires chart/visualization generation")
        return await _solve_with_chart(quiz_url, instruction_prompt, session_dir, question)
    elif needs_code and has_data:
        info("solver", "strategy requires code execution and data is available")
        return await _solve_with_code(quiz_url, instruction_prompt, session_dir, answer_type)
    elif needs_code and not has_data:
        info("solver", "strategy wants code but NO data files found - using direct reasoning")
        return await _solve_direct(quiz_url, instruction_prompt, session_dir, answer_type)
    else:
        info("solver", "strategy uses direct reasoning")
        return await _solve_direct(quiz_url, instruction_prompt, session_dir, answer_type)


async def _solve_with_code(quiz_url: str, instruction_prompt: str, session_dir: Path, answer_type: str) -> dict:
    """Solve using code generation and execution."""
    info("solver", "solving with code generation")
    
    # Load question data for code generator
    question_file = get_question_path(quiz_url)
    question_data = json.loads(question_file.read_text())
    question = question_data.get("question", "")
    
    # Build data info for code generator using path helpers
    from tools.helper.paths import list_files_by_type
    files_by_type = list_files_by_type(quiz_url)
    csv_files = files_by_type.get("csv", [])
    
    data_info = {}
    if csv_files:
        data_info["csv_files"] = [f.name for f in csv_files]
        info("solver", f"CSV files: {', '.join(data_info['csv_files'])}")
        # Get CSV preview
        import pandas as pd
        try:
            df = pd.read_csv(csv_files[0])
            preview = f"Columns: {', '.join(df.columns)}\nFirst 3 rows:\n{df.head(3).to_string()}"
            data_info["csv_preview"] = preview
        except:
            pass
    else:
        info("solver", "NO CSV files - cannot use code generation")
    
    # Use code_generator to create Python code
    code_result = await generate_code(question, data_info)
    
    if not code_result.get("success"):
        error("solver", "code generation failed")
        return {"success": False, "answer": None, "error": "code generation failed"}
    
    code = code_result["code"]
    
    # Save code to .py file
    code_file = get_code_path(quiz_url)
    save_code(code, session_dir, code_file.name)
    
    # Save code with metadata to JSON for debugging
    code_debug = {
        "code": code,
        "strategy": code_result.get("strategy", ""),
        "question": question,
        "data_files": data_info.get("csv_files", []),
        "generation_method": "dynamic_code_generator"
    }
    code_json_file = session_dir / "code.json"
    code_json_file.write_text(json.dumps(code_debug, indent=2))
    info("solver", "saved code.json for debugging")
    
    # Execute code
    exec_result = await execute_code(code, session_dir)
    
    if exec_result["success"]:
        raw_answer = exec_result["output"].strip()
        answer = _extract_final_answer(raw_answer, answer_type)
        
        # Save clean answer (only answer and type)
        answer_data = {
            "answer": answer,
            "answer_type": answer_type
        }
        _save_answer(session_dir, answer_data)
        
        # Save detailed metadata separately
        metadata = {
            "method": "code_execution",
            "raw_output": raw_answer,
            "code_file": "generated_code.py",
            "execution_status": "success"
        }
        _save_metadata(session_dir, metadata)
        
        success("solver", f"CODE → {answer}")
        
        return {
            "success": True,
            "answer": answer,
            "method": "code_execution",
            "code": code
        }
    else:
        warn("solver", f"code failed: {exec_result['error'][:100]}")
        # Fallback to direct
        return await _solve_direct(quiz_url, instruction_prompt, session_dir, answer_type)


async def _solve_with_chart(quiz_url: str, instruction_prompt: str, session_dir: Path, question: str) -> dict:
    """Solve by generating a chart/visualization."""
    import base64
    info("solver", "generating chart/visualization")
    
    # Get available data files
    from tools.helper.paths import list_files_by_type, get_chart_path
    files_by_type = list_files_by_type(quiz_url)
    csv_files = files_by_type.get("csv", [])
    
    data_info = ""
    if csv_files:
        import pandas as pd
        try:
            df = pd.read_csv(csv_files[0])
            data_info = f"CSV file: {csv_files[0].name}\nColumns: {', '.join(df.columns)}\nSample data:\n{df.head().to_string()}"
        except:
            data_info = f"CSV file: {csv_files[0].name}"
    
    # Generate matplotlib code for the chart
    chart_prompt = f"""Write Python code to generate a chart/visualization.

QUESTION: {question}
DATA: {data_info}

Requirements:
1. Use matplotlib
2. Read data from CSV file in current directory if needed
3. Create the chart as specified in the question
4. Save chart to 'chart.png' using plt.savefig('chart.png', dpi=100, bbox_inches='tight')
5. Print 'chart.png' as the output

Write complete, executable Python code:"""
    
    code_response = await call(chart_prompt, task="code")
    
    if not code_response:
        error("solver", "chart code generation failed")
        return await _solve_direct(quiz_url, instruction_prompt, session_dir, "text")
    
    # Extract code
    code = code_response.strip()
    if "```python" in code:
        code = code.split("```python")[1].split("```")[0].strip()
    elif "```" in code:
        code = code.split("```")[1].split("```")[0].strip()
    
    # Ensure matplotlib uses Agg backend
    if "matplotlib.use" not in code:
        code = "import matplotlib\nmatplotlib.use('Agg')\n" + code
    
    # Execute the code
    exec_result = await execute_code(code, session_dir)
    
    if exec_result["success"]:
        chart_path = session_dir / "chart.png"
        
        if chart_path.exists():
            # Convert chart to base64 data URI
            img_data = chart_path.read_bytes()
            b64 = base64.b64encode(img_data).decode()
            data_uri = f"data:image/png;base64,{b64}"
            
            # Save answer
            answer_data = {
                "answer": data_uri,
                "answer_type": "base64",
                "chart_file": "chart.png"
            }
            _save_answer(session_dir, answer_data)
            
            success("solver", f"chart generated: {chart_path.name}")
            
            return {
                "success": True,
                "answer": data_uri,
                "answer_type": "base64",
                "method": "chart_generation",
                "code": code
            }
        else:
            warn("solver", "chart file not created")
    else:
        warn("solver", f"chart code failed: {exec_result['error'][:100]}")
    
    # Fallback to direct reasoning
    return await _solve_direct(quiz_url, instruction_prompt, session_dir, "text")


async def _solve_direct(quiz_url: str, instruction_prompt: str, session_dir: Path, answer_type: str) -> dict:
    """Solve using direct LLM reasoning."""
    info("solver", "solving with direct reasoning")
    
    response = await call(instruction_prompt, task="reason")
    
    if not response:
        error("solver", "LLM reasoning failed")
        return {"success": False, "answer": None, "error": "LLM failed"}
    
    answer = _extract_final_answer(response, answer_type)
    
    # Save clean answer (only answer and type)
    answer_data = {
        "answer": answer,
        "answer_type": answer_type
    }
    _save_answer(session_dir, answer_data)
    
    # Save detailed metadata separately
    metadata = {
        "method": "direct_reasoning",
        "raw_response": response[:500]  # Truncate long responses
    }
    _save_metadata(session_dir, metadata)
    
    success("solver", f"REASONING → {answer}")
    
    return {
        "success": True,
        "answer": answer,
        "method": "direct_reasoning",
        "raw_response": response
    }


def _extract_final_answer(text: str, answer_type: str):
    """
    Extract ONLY the final answer with perfect accuracy.
    
    Args:
        text: Raw output text
        answer_type: Expected type (number/text/boolean/json)
    
    Returns:
        Cleaned answer in correct format
    """
    lines = text.strip().split("\n")
    
    # Clean markdown code blocks first
    clean_text = text.strip()
    if "```" in clean_text:
        # Extract content from code blocks
        import re
        code_match = re.search(r'```(?:\w+)?\s*([\s\S]*?)```', clean_text)
        if code_match:
            clean_text = code_match.group(1).strip()
            lines = clean_text.split("\n")
    
    # Get last non-empty, non-comment line
    answer_line = ""
    for line in reversed(lines):
        line = line.strip()
        # Skip empty, comments, and backticks-only lines
        if line and not line.startswith("#") and not line.startswith("//") and line != "```":
            answer_line = line
            break
    
    answer = answer_line if answer_line else clean_text.strip()
    
    # Clean common artifacts
    answer = answer.strip("`")  # Remove inline backticks
    answer = answer.strip("[]")  # Remove brackets
    
    # Type-specific extraction
    if answer_type == "number":
        match = re.search(r'-?\d+\.?\d*', answer)
        if match:
            num = match.group()
            if '.' not in num:
                return str(int(float(num)))
            return num
    
    elif answer_type == "boolean":
        lower = answer.lower()
        if "true" in lower or answer == "1":
            return "true"
        elif "false" in lower or answer == "0":
            return "false"
    
    elif answer_type == "json":
        if "{" in answer:
            start = answer.index("{")
            end = answer.rindex("}") + 1
            return answer[start:end]
    
    return answer.strip()


def _save_answer(session_dir: Path, answer_data: dict):
    """Save clean answer to JSON file (only answer and type)."""
    answer_file = session_dir / "answer.json"
    answer_file.write_text(json.dumps(answer_data, indent=2))
    info("solver", f"saved answer to {answer_file.name}")


def _save_metadata(session_dir: Path, metadata: dict):
    """Save detailed metadata to separate file."""
    metadata_file = session_dir / "solve_metadata.json"
    metadata_file.write_text(json.dumps(metadata, indent=2))
    info("solver", f"saved metadata to {metadata_file.name}")
