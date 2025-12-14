"""Helper - Code execution in sandbox.

Provides safe Python code execution with access to data science libraries
and collected data context.
"""

import base64
import contextlib
import io
import json
import sqlite3
import urllib

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def run_code(code: str, data_context: dict = None) -> dict:
    """Execute Python code and return result.

    Runs Python code in a sandboxed environment with access to pandas,
    numpy, matplotlib, and provided data context.

    Args:
        code: Python code string to execute.
        data_context: Optional dict of variables to make available in code.
            Common keys: df (DataFrame), cutoff (int), csv_data (str)

    Returns:
        dict: Execution result containing:
            - output (str): Captured stdout from print statements
            - image (str): Base64 PNG if matplotlib plot created
            - error (str): Error message if execution failed, None otherwise

    Example:
        >>> code = "result = df['amount'].sum()\\nprint(result)"
        >>> ctx = {'df': pd.DataFrame({'amount': [10, 20, 30]})}
        >>> result = run_code(code, ctx)
        >>> print(result['output'])
        60

    Note:
        Available libraries: pd (pandas), np (numpy), plt (matplotlib),
        json, base64, sqlite3, urllib, io
    """
    result = {"output": "", "image": None, "error": None}

    try:
        # Clear any existing plots
        plt.clf()
        plt.close("all")

        # Capture stdout
        stdout = io.StringIO()
        env = data_context.copy() if data_context else {}
        env.update(
            {
                "pd": pd,
                "np": np,
                "plt": plt,
                "json": json,
                "base64": base64,
                "sqlite3": sqlite3,
                "urllib": urllib,
                "io": io,
                "print": lambda *a: print(*a, file=stdout),
            }
        )

        # Execute code
        with contextlib.redirect_stdout(stdout):
            exec(code, env, env)

        result["output"] = stdout.getvalue().strip()

        # Check for matplotlib plot
        if plt.get_fignums():
            buf = io.BytesIO()
            plt.savefig(buf, format="png")
            buf.seek(0)
            result["image"] = base64.b64encode(buf.read()).decode()
            plt.close("all")

    except Exception as e:
        result["error"] = str(e)

    return result
