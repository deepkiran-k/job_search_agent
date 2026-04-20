"""
tests/conftest.py
Ensures the project root is on sys.path so that utils.*, tools.*, core.*
imports work correctly when pytest is run from any directory.
"""
import sys
import os

# Insert the project root (one level up from this file's directory) at the
# front of sys.path so that `from utils.ats_scanner import ATSScanner` etc. work.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
