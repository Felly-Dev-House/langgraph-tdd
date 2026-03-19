"""
Language-Agnostic TDD Handler System

This package provides handlers for multiple programming languages:
- Python (pytest)
- C (ESP-IDF with Unity + CMock)  
- TypeScript (Next.js/React with Vitest/Jest)

Usage:
    from handlers import get_handler, detect_language_from_spec
    
    spec = {...}
    language = detect_language_from_spec(spec)
    handler = get_handler(language, workspace)
"""

from .base_handler import (
    BaseHandler, TestResult, CodeFile,
    detect_language_from_spec, get_handler
)
from .python_handler import PythonHandler
from .c_handler import CHandler
from .typescript_handler import TypeScriptHandler

__all__ = [
    'BaseHandler',
    'TestResult', 
    'CodeFile',
    'detect_language_from_spec',
    'get_handler',
    'PythonHandler',
    'CHandler',
    'TypeScriptHandler'
]
