"""Execute Python code safely in a controlled environment."""
import sys
import subprocess
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from log import info, success, error, warn


async def execute_code(code: str, session_dir: Path) -> dict:
    """
    Execute Python code safely and return the output.
    
    Args:
        code: Python code to execute
        session_dir: Session directory (contains data files)
    
    Returns:
        dict with success, output, error
    """
    info("executor", "running Python code")
    
    # Create temporary Python file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        temp_file = Path(f.name)
        f.write(code)
    
    try:
        # Run code in subprocess with timeout
        result = subprocess.run(
            [sys.executable, str(temp_file)],
            cwd=str(session_dir),  # Run in session dir so files are accessible
            capture_output=True,
            text=True,
            timeout=30  # 30 second timeout
        )
        
        output = result.stdout.strip()
        error_output = result.stderr.strip()
        
        # Clean up temp file
        temp_file.unlink()
        
        if result.returncode == 0:
            success("executor", f"code executed successfully: {output[:100]}")
            return {
                "success": True,
                "output": output,
                "error": ""
            }
        else:
            error("executor", f"code failed: {error_output[:200]}")
            return {
                "success": False,
                "output": output,
                "error": error_output
            }
    
    except subprocess.TimeoutExpired:
        temp_file.unlink()
        error("executor", "code execution timeout (30s)")
        return {
            "success": False,
            "output": "",
            "error": "Execution timeout after 30 seconds"
        }
    
    except Exception as e:
        temp_file.unlink()
        error("executor", f"execution error: {str(e)}")
        return {
            "success": False,
            "output": "",
            "error": str(e)
        }


def save_code(code: str, session_dir: Path, filename: str = "generated_code.py") -> Path:
    """
    Save generated code to session directory for debugging.
    
    Args:
        code: Python code to save
        session_dir: Session directory
        filename: Filename to save as
    
    Returns:
        Path to saved file
    """
    code_file = session_dir / filename
    code_file.write_text(code)
    info("executor", f"saved code to {filename}")
    return code_file
