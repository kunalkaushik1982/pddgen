r"""
Purpose: Worker package marker.
Full filepath: C:\Users\work\Documents\PddGenerator\worker\__init__.py
"""

# Ensure backend imports are available whenever the worker package is imported.
from worker import bootstrap as _bootstrap  # noqa: F401
