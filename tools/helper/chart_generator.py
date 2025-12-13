"""Generate charts and visualizations."""
import sys
import base64
import asyncio
from pathlib import Path
from io import BytesIO

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from log import error, info, success


async def generate_chart(
    data: dict,
    chart_type: str = "bar",
    title: str = "",
    save_path: str = None
) -> dict:
    """
    Generate a chart from data.
    
    Args:
        data: Dict with 'x' and 'y' keys for data
        chart_type: bar, line, pie, scatter
        title: Chart title
        save_path: Optional path to save chart
    
    Returns:
        dict with success, base64_image, path
    """
    info("chart", f"generating {chart_type} chart")
    
    try:
        loop = asyncio.get_event_loop()
        
        def _create_chart():
            import matplotlib
            matplotlib.use('Agg')  # Non-interactive backend
            import matplotlib.pyplot as plt
            
            fig, ax = plt.subplots(figsize=(10, 6))
            
            x = data.get("x", [])
            y = data.get("y", [])
            labels = data.get("labels", x)
            
            if chart_type == "bar":
                ax.bar(range(len(y)), y, tick_label=labels)
            elif chart_type == "line":
                ax.plot(x if x else range(len(y)), y, marker='o')
            elif chart_type == "pie":
                ax.pie(y, labels=labels, autopct='%1.1f%%')
            elif chart_type == "scatter":
                ax.scatter(x, y)
            
            if title:
                ax.set_title(title)
            
            plt.tight_layout()
            
            # Save to buffer
            buf = BytesIO()
            plt.savefig(buf, format='png', dpi=100)
            buf.seek(0)
            
            # Convert to base64
            img_base64 = base64.b64encode(buf.read()).decode()
            
            # Save to file if path provided
            if save_path:
                buf.seek(0)
                Path(save_path).write_bytes(buf.read())
            
            plt.close()
            
            return img_base64
        
        img_base64 = await loop.run_in_executor(None, _create_chart)
        
        success("chart", f"generated {chart_type} chart")
        
        return {
            "success": True,
            "base64_image": img_base64,
            "data_uri": f"data:image/png;base64,{img_base64}",
            "path": save_path,
            "error": ""
        }
    except ImportError:
        error("chart", "matplotlib not installed")
        return {"success": False, "error": "matplotlib not installed"}
    except Exception as e:
        error("chart", str(e))
        return {"success": False, "error": str(e)}


async def generate_chart_from_code(code: str, save_path: str = None) -> dict:
    """
    Execute matplotlib code to generate a chart.
    
    Args:
        code: Python code that creates a matplotlib figure
        save_path: Path to save the chart
    
    Returns:
        dict with success, base64_image
    """
    info("chart", "generating chart from code")
    
    try:
        from tools.helper.code_executor import execute_code
        
        # Wrap code to save figure
        wrapped_code = f"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import base64
from io import BytesIO

{code}

# Save figure
buf = BytesIO()
plt.savefig(buf, format='png', dpi=100)
buf.seek(0)
print(base64.b64encode(buf.read()).decode())
plt.close()
"""
        
        result = await execute_code(wrapped_code, Path(save_path).parent if save_path else Path("."))
        
        if result["success"] and result["output"]:
            img_base64 = result["output"].strip()
            
            if save_path:
                img_bytes = base64.b64decode(img_base64)
                Path(save_path).write_bytes(img_bytes)
            
            success("chart", "generated chart from code")
            return {
                "success": True,
                "base64_image": img_base64,
                "data_uri": f"data:image/png;base64,{img_base64}",
                "path": save_path,
                "error": ""
            }
        else:
            return {"success": False, "error": result.get("error", "Code execution failed")}
    except Exception as e:
        error("chart", str(e))
        return {"success": False, "error": str(e)}
