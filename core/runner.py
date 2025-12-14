"""Core Runner - Execute Python code with full data access.

This module provides a safe code execution environment with access
to collected data, pandas DataFrames, and standard libraries.
"""

from io import StringIO

import pandas as pd

from helpers import run_code
from logs.logger import get_logger

logger = get_logger("runner")


def execute(code: str, data: dict = None) -> dict:
    """Execute Python code with access to collected data.

    Prepares a context with CSV data as DataFrame and extracted parameters,
    then runs the code in a sandboxed environment.

    Args:
        code: Python code to execute.
        data: Collected data dictionary containing:
            - csv_content (str): Raw CSV data
            - params (dict): Extracted parameters (cutoff, etc.)
            - Other data from converter

    Returns:
        dict: Execution result containing:
            - output (str): Printed output from code
            - image (str): Base64 encoded image if plot generated
            - error (str): Error message if execution failed

    Example:
        >>> data = {'csv_content': '0\\n12345\\n67890', 'params': {'cutoff': 50000}}
        >>> result = execute('print(df[df[0] >= cutoff][0].sum())', data)
        >>> print(result['output'])
        67890
    """
    logger.debug("Executing code in sandbox")

    # Prepare data context for code
    context = data.copy() if data else {}

    # Add CSV as DataFrame if available
    if data and data.get("csv_content"):
        logger.debug("Loading CSV data into DataFrame")
        context["df"] = pd.read_csv(StringIO(data["csv_content"]), header=None)
        context["csv_data"] = data["csv_content"]

    # Add params as top-level variables
    if data and data.get("params"):
        logger.debug(f"Adding parameters: {list(data['params'].keys())}")
        context.update(data["params"])

    # Run code in sandbox
    result = run_code(code, context)

    if result["error"]:
        logger.error(f"Code execution failed: {result['error']}")
    else:
        logger.debug(f"Code executed successfully, output: {result['output'][:100]}")

    return result
