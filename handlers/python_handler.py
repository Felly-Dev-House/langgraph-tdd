"""
Python Handler for TDD with pytest.
This is the existing behavior, maintained for backward compatibility.
"""
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional
from handlers.base_handler import BaseHandler, TestResult, CodeFile

class PythonHandler(BaseHandler):
    """Handler for Python code with pytest"""
    
    @property
    def language_name(self) -> str:
        return "Python"
    
    @property
    def file_extensions(self) -> List[str]:
        return ['.py', '.pyx']
    
    @property
    def test_framework(self) -> str:
        return "pytest"
    
    def setup_environment(self) -> bool:
        """Verify Python and pytest are available"""
        try:
            result = subprocess.run(
                ['python3', '--version'],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode != 0:
                print("[PY_HANDLER] Python3 not found")
                return False
            print(f"[PY_HANDLER] Python: {result.stdout.strip()}")
            
            result = subprocess.run(
                ['pytest', '--version'],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode != 0:
                print("[PY_HANDLER] pytest not found")
                return False
        except Exception as e:
            print(f"[PY_HANDLER] Environment check failed: {e}")
            return False
        
        return True
    
    def generate_tests(self, spec: Dict[str, Any], code_files: List[CodeFile], failures: List[str] = None) -> List[CodeFile]:
        """Generate pytest test files"""
        # This is placeholder - actual test generation done by LLM
        test_files = []
        
        module_name = spec.get('module_name', 'generated')
        
        test_content = f"""import pytest
from unittest.mock import Mock, patch
import {module_name}

def test_happy_path():
    \"\"\"Test successful execution\"\"\"
    # TO BE FILLED BY TDD AGENT
    assert True

def test_error_handling():
    \"\"\"Test error conditions\"\"\"
    # TO BE FILLED BY TDD AGENT
    assert True
"""
        
        test_path = self.workspace / f'test_{module_name}.py'
        test_files.append(CodeFile(
            path=str(test_path),
            content=test_content,
            language='python'
        ))
        
        return test_files
    
    def generate_code(self, spec: Dict[str, Any], test_files: List[CodeFile]) -> List[CodeFile]:
        """Generate Python implementation code"""
        code_files = []
        
        module_name = spec.get('module_name', 'generated')
        
        code_content = f"""# {module_name} module

def main_function():
    \"\"\"Main function - TO BE IMPLEMENTED\"\"\"
    pass
"""
        
        code_path = self.workspace / f'{module_name}.py'
        code_files.append(CodeFile(
            path=str(code_path),
            content=code_content,
            language='python'
        ))
        
        return code_files
    
    def run_tests(self, code_dir: Path) -> TestResult:
        """Run pytest on the generated code"""
        import time
        start_time = time.time()
        
        try:
            result = subprocess.run(
                ['python3', '-m', 'pytest', '-v'],
                cwd=code_dir,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            passed = result.returncode == 0
            return TestResult(
                passed=passed,
                output=result.stdout + result.stderr,
                errors=[] if passed else [result.stderr],
                duration_ms=int((time.time() - start_time) * 1000)
            )
            
        except Exception as e:
            return TestResult(
                passed=False,
                output=str(e),
                errors=[str(e)],
                duration_ms=int((time.time() - start_time) * 1000)
            )
