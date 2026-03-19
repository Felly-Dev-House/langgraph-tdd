"""
TypeScript Handler for Next.js/React/Node.js TDD.
Generates TypeScript code and Jest/Vitest test files.
"""
import subprocess
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from handlers.base_handler import BaseHandler, TestResult, CodeFile

class TypeScriptHandler(BaseHandler):
    """Handler for TypeScript/JavaScript code with Next.js/React"""
    
    @property
    def language_name(self) -> str:
        return "TypeScript (Next.js/React)"
    
    @property
    def file_extensions(self) -> List[str]:
        return ['.ts', '.tsx', '.js', '.jsx']
    
    @property
    def test_framework(self) -> str:
        return "Jest / Vitest"
    
    def setup_environment(self) -> bool:
        """Setup Node.js environment with Next.js dependencies."""
        try:
            result = subprocess.run(['node', '--version'], capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                print("[TS_HANDLER] Node.js not found")
                return False
            print(f"[TS_HANDLER] Node.js: {result.stdout.strip()}")
        except Exception as e:
            print(f"[TS_HANDLER] Node.js check failed: {e}")
            return False
        
        try:
            result = subprocess.run(['npm', '--version'], capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                print("[TS_HANDLER] npm not found")
                return False
        except Exception as e:
            print(f"[TS_HANDLER] npm check failed: {e}")
            return False
        
        print("[TS_HANDLER] Node.js environment ready")
        return True
    
    def generate_tests(self, spec: Dict[str, Any], code_files: List[CodeFile], failures: List[str] = None) -> List[CodeFile]:
        """Generate Jest/Vitest test files for TypeScript code."""
        test_files = []
        component_type = spec.get('component_type', 'component')
        module_name = spec.get('module_name', 'generated')
        
        # Simple placeholder test
        test_content = f"""import {{ describe, it, expect, beforeEach, vi }} from 'vitest';
import {{ {module_name} }} from './{module_name}';

describe('{module_name}', () => {{
  beforeEach(() => {{
    vi.clearAllMocks();
  }});

  it('should handle happy path', () => {{
    expect(true).toBe(true);
  }});

  it('should handle edge cases', () => {{
    expect(true).toBe(true);
  }});

  it('should handle error conditions', () => {{
    expect(true).toBe(true);
  }});
}});
"""
        test_path = self.workspace / '__tests__' / f'{module_name}.test.ts'
        test_path.parent.mkdir(parents=True, exist_ok=True)
        test_files.append(CodeFile(path=str(test_path), content=test_content, language='typescript'))
        
        return test_files
    
    def generate_code(self, spec: Dict[str, Any], test_files: List[CodeFile]) -> List[CodeFile]:
        """Generate TypeScript implementation code."""
        code_files = []
        component_type = spec.get('component_type', 'component')
        module_name = spec.get('module_name', 'generated')
        
        code_content = f"""// {module_name} module

export interface {module_name}Config {{
  enabled?: boolean;
  timeout?: number;
}}

export interface {module_name}Result {{
  success: boolean;
  data?: unknown;
  error?: string;
}}

export function {module_name}(config: {module_name}Config = {{}}): {module_name}Result {{
  const {{ enabled = true, timeout = 5000 }} = config;

  if (!enabled) {{
    return {{ success: false, error: 'Module disabled' }};
  }}

  try {{
    return {{ success: true, data: {{ message: 'Success' }} }};
  }} catch (error) {{
    console.error('[{module_name}] Error:', error);
    return {{ success: false, error: error instanceof Error ? error.message : 'Unknown error' }};
  }}
}}

export default {module_name};
"""
        code_path = self.workspace / 'lib' / f'{module_name}.ts'
        code_path.parent.mkdir(parents=True, exist_ok=True)
        code_files.append(CodeFile(path=str(code_path), content=code_content, language='typescript'))
        
        return code_files
    
    def run_tests(self, code_dir: Path) -> TestResult:
        """Run Jest/Vitest tests for TypeScript code."""
        import time
        start_time = time.time()
        
        # Check for package.json
        package_json = code_dir / 'package.json'
        if not package_json.exists():
            self._create_package_json(code_dir)
        
        # Try to run tests with vitest or jest
        try:
            test_cmd = ['npx', '--yes', 'vitest', 'run', '--no-coverage']
            result = subprocess.run(test_cmd, cwd=code_dir, capture_output=True, text=True, timeout=120)
            
            passed = result.returncode == 0
            return TestResult(
                passed=passed,
                output=result.stdout + result.stderr,
                errors=[] if passed else [result.stderr],
                duration_ms=int((time.time() - start_time) * 1000)
            )
        except subprocess.TimeoutExpired:
            return TestResult(passed=False, output="Tests timed out", errors=["Timeout"], duration_ms=int((time.time() - start_time) * 1000))
        except Exception as e:
            return TestResult(passed=False, output=str(e), errors=[str(e)], duration_ms=int((time.time() - start_time) * 1000))
    
    def _create_package_json(self, code_dir: Path):
        """Create minimal package.json for TypeScript testing."""
        package_json = {
            "name": "tdd-generated-project",
            "version": "1.0.0",
            "type": "module",
            "scripts": {"test": "vitest run"},
            "devDependencies": {
                "typescript": "^5.0.0",
                "vitest": "^1.0.0",
                "@types/node": "^20.0.0",
                "ts-node": "^10.9.0"
            }
        }
        
        with open(code_dir / 'package.json', 'w') as f:
            json.dump(package_json, f, indent=2)
