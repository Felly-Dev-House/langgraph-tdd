"""
Base handler interface for language-agnostic TDD.
All language handlers must implement this interface.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from pathlib import Path
import subprocess
import re

@dataclass
class TestResult:
    """Result of a test run"""
    passed: bool
    output: str
    errors: List[str]
    duration_ms: int
    coverage: Optional[float] = None

@dataclass
class CodeFile:
    """Represents a generated code file"""
    path: str
    content: str
    language: str

class BaseHandler(ABC):
    """Abstract base class for language-specific TDD handlers"""
    
    def __init__(self, workspace_dir: str):
        self.workspace = Path(workspace_dir)
    
    @property
    @abstractmethod
    def language_name(self) -> str:
        """Human-readable language name (e.g., 'Python', 'C', 'TypeScript')"""
        pass
    
    @property
    @abstractmethod
    def file_extensions(self) -> List[str]:
        """List of file extensions for this language (e.g., ['.py', '.pyx'])"""
        pass
    
    @property
    @abstractmethod
    def test_framework(self) -> str:
        """Name of test framework (e.g., 'pytest', 'Unity', 'Jest')"""
        pass
    
    @abstractmethod
    def generate_tests(self, spec: Dict[str, Any], code_files: List[CodeFile], failures: List[str] = None) -> List[CodeFile]:
        """
        Generate test files for the given spec and code.
        Returns list of test file CodeFile objects.
        """
        pass
    
    @abstractmethod
    def generate_code(self, spec: Dict[str, Any], test_files: List[CodeFile]) -> List[CodeFile]:
        """
        Generate implementation code for the given spec and tests.
        Returns list of code file CodeFile objects.
        """
        pass
    
    @abstractmethod
    def run_tests(self, code_dir: Path) -> TestResult:
        """
        Run tests and return results.
        Must compile/build if needed before running tests.
        """
        pass
    
    @abstractmethod
    def setup_environment(self) -> bool:
        """
        Install dependencies and setup test environment.
        Returns True if successful.
        """
        pass
    
    def validate_spec(self, spec: Dict[str, Any]) -> bool:
        """Validate that spec contains required fields for this language"""
        return True
    
    def get_build_command(self) -> Optional[List[str]]:
        """Return build command if compilation is needed, None otherwise"""
        return None
    
    def cleanup(self):
        """Cleanup any temporary files or processes"""
        pass


def detect_language_from_spec(spec: Dict[str, Any]) -> Optional[str]:
    """
    Detect programming language from spec metadata.
    Returns: 'python', 'c', 'typescript', 'rust', 'go', or None
    """
    raw_content = spec.get('raw', '')
    
    # Check explicit language field
    if 'language' in spec:
        lang = spec['language'].lower()
        if 'python' in lang:
            return 'python'
        elif 'c' in lang and 'c++' not in lang and 'cpp' not in lang:
            return 'c'
        elif 'typescript' in lang or 'javascript' in lang or 'ts' in lang or 'js' in lang:
            return 'typescript'
        elif 'rust' in lang:
            return 'rust'
        elif 'go' in lang:
            return 'go'
    
    # Check for language keywords in raw content
    if "python" in raw_content.lower() and "esp32" not in raw_content.lower() and "esp-idf" not in raw_content.lower():
        if 'esp-idf' not in raw_content.lower() and 'arduino' not in raw_content.lower():
            return 'python'
    
    if 'esp-idf' in raw_content.lower() or 'twai' in raw_content.lower() or 'arduino' in raw_content.lower():
        return 'c'
    
    if 'next.js' in raw_content.lower() or 'nextjs' in raw_content.lower() or 'react' in raw_content.lower():
        return 'typescript'
    
    if 'typescript' in raw_content.lower() or 'typescript' in raw_content.lower():
        return 'typescript'
    
    # Check file extensions mentioned in spec
    if '.py' in raw_content:
        return 'python'
    if '.c' in raw_content or '.h' in raw_content:
        return 'c'
    if '.ts' in raw_content or '.tsx' in raw_content:
        return 'typescript'
    
    return None


def get_handler(language: str, workspace: str) -> Optional[BaseHandler]:
    """Factory function to get the appropriate handler for a language"""
    from handlers.python_handler import PythonHandler
    from handlers.c_handler import CHandler
    from handlers.typescript_handler import TypeScriptHandler
    
    handlers = {
        'python': PythonHandler,
        'c': CHandler,
        'typescript': TypeScriptHandler,
    }
    
    handler_class = handlers.get(language.lower())
    if handler_class:
        return handler_class(workspace)
    return None
