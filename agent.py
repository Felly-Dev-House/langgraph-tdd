#!/usr/bin/env python3
"""
Language-Agnostic TDD Agent

This agent supports multiple programming languages through a handler system:
- Python (pytest)
- C (ESP-IDF with Unity + CMock)
- TypeScript (Next.js/React with Vitest/Jest)
- (Extensible for Rust, Go, etc.)

Usage:
    python agent.py --ticket <ticket_id> --spec <spec_path>
"""

import argparse
import json
import sys
import os
import re
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

# Add handlers to path
sys.path.insert(0, str(Path(__file__).parent))

from handlers.base_handler import (
    BaseHandler, TestResult, CodeFile,
    detect_language_from_spec, get_handler
)

class TDDAgent:
    """Main TDD orchestrator with language dispatch"""
    
    def __init__(self, ticket_id: str, spec_path: str, workspace: str = '/mnt/workspace/tasks', max_iterations: int = 10):
        self.ticket_id = ticket_id
        self.spec_path = Path(spec_path)
        self.workspace = Path(workspace) / ticket_id
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.max_iterations = max_iterations
        
        # Load spec
        self.spec = self._load_spec()
        
        # Detect language and get handler
        self.language = detect_language_from_spec(self.spec)
        if not self.language:
            raise ValueError(f"Could not detect language from spec: {spec_path}")
        
        self.handler = get_handler(self.language, str(self.workspace))
        if not self.handler:
            raise ValueError(f"No handler found for language: {self.language}")
        
        print(f"[TDD_AGENT] Starting {self.handler.language_name} TDD for ticket {ticket_id}")
    
    def _load_spec(self) -> Dict[str, Any]:
        """Load and parse spec file"""
        with open(self.spec_path) as f:
            content = f.read()
        
        # Handle markdown-wrapped specs
        raw_content = content
        if '```markdown' in content:
            raw_content = content.split('```markdown')[1].split('```')[0]
        elif '```' in content:
            raw_content = content.split('```')[1].split('```')[0]
        
        # Extract module name from spec
        module_name = self._extract_module_name(raw_content)
        
        return {
            'raw': raw_content,
            'module_name': module_name,
            'language': self.spec_path.stem.split('-')[0] if '-' in self.spec_path.stem else None
        }
    
    def _extract_module_name(self, content: str) -> str:
        """Extract a reasonable module name from spec content."""
        # Try to find "Project Name" or similar
        patterns = [
            r'Project Name[":\s]+[`"]?(\w+)[`"]?',
            r'Project Name:\s+`(\w+)`',
            r'### .*?\((\w+)\)',
            r'module_name:\s*(\w+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1)
        
        # Fallback: use ticket ID but clean it up
        # e.g., "20260318-esp32-can-bus-foundation-for-r" -> "can_bus_foundation"
        parts = self.ticket_id.split('-')
        if len(parts) > 3:
            # Skip date and use descriptive parts
            descriptive = [p for p in parts[1:] if p not in ['for', 'the', 'a', 'an', 'and']]
            if descriptive:
                return '_'.join(descriptive[-3:])  # Last 3 meaningful parts
        
        # Last resort: use last part of ticket
        return parts[-1] if parts else 'generated'
    
    def run(self) -> bool:
        """
        Run the TDD loop.
        Returns True if tests pass within iteration limit.
        """
        print(f"[TDD_AGENT] Language: {self.language}")
        print(f"[TDD_AGENT] Handler: {self.handler.language_name}")
        print(f"[TDD_AGENT] Test Framework: {self.handler.test_framework}")
        print(f"[TDD_AGENT] Module: {self.spec['module_name']}")
        
        # Setup environment
        print(f"[TDD_AGENT] Setting up environment...")
        if not self.handler.setup_environment():
            print(f"[TDD_AGENT] WARNING: Environment setup incomplete")
        
        # TDD Loop
        code_files = []
        test_files = []
        
        for iteration in range(1, self.max_iterations + 1):
            print(f"\n[TDD_AGENT] === Iteration {iteration}/{self.max_iterations} ===")
            
            try:
                # Generate tests (if first iteration) or update based on failures
                if iteration == 1:
                    test_files = self.handler.generate_tests(self.spec, code_files)
                    self._write_files(test_files)
                
                # Generate code based on tests
                code_files = self.handler.generate_code(self.spec, test_files)
                self._write_files(code_files)
                
                # Run tests
                print(f"[TDD_AGENT] Running tests...")
                test_result = self.handler.run_tests(self.workspace)
                
                print(f"[TDD_AGENT] Test result: {'PASSED' if test_result.passed else 'FAILED'}")
                print(f"[TDD_AGENT] Duration: {test_result.duration_ms}ms")
                
                if test_result.output:
                    print(f"[TDD_AGENT] Output: {test_result.output[:200]}")
                
                if test_result.passed:
                    # Judge evaluation
                    print(f"[TDD_AGENT] Running judge evaluation...")
                    if self._judge_accept(code_files, test_result):
                        print(f"[TDD_AGENT] ✅ JUDGE ACCEPTED - SUCCESS")
                        return True
                    else:
                        print(f"[TDD_AGENT] Judge rejected, continuing iterations...")
                
                # If failed, update tests for next iteration
                if not test_result.passed:
                    test_files = self.handler.generate_tests(
                        self.spec, code_files, 
                        failures=test_result.errors
                    )
                    self._write_files(test_files)
                
            except Exception as e:
                print(f"[TDD_AGENT] Error in iteration {iteration}: {e}")
                if iteration == self.max_iterations:
                    raise
        
        print(f"[TDD_AGENT] ❌ MAX ITERATIONS EXHAUSTED - ESCALATING")
        return False
    
    def _write_files(self, files: list):
        """Write CodeFile objects to disk"""
        for cf in files:
            path = Path(cf.path)
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, 'w') as f:
                f.write(cf.content)
            print(f"[TDD_AGENT] Written: {cf.path}")
    
    def _judge_accept(self, code_files: list, test_result: TestResult) -> bool:
        """
        Judge evaluation - determines if code quality is acceptable.
        Simple implementation: checks test pass.
        """
        return test_result.passed


def main():
    parser = argparse.ArgumentParser(description='Language-Agnostic TDD Agent')
    parser.add_argument('--ticket', required=True, help='Ticket/Issue ID')
    parser.add_argument('--spec', required=True, help='Path to spec file')
    parser.add_argument('--workspace', default='/mnt/workspace/tasks', help='Workspace directory')
    parser.add_argument('--max-iterations', type=int, default=10, help='Max TDD iterations')
    
    args = parser.parse_args()
    
    try:
        agent = TDDAgent(args.ticket, args.spec, args.workspace, args.max_iterations)
        success = agent.run()
        
        if success:
            print(f"\n{'='*60}")
            print(f"SUCCESS: Ticket {args.ticket} completed")
            print(f"{'='*60}")
            sys.exit(0)
        else:
            print(f"\n{'='*60}")
            print(f"FAILURE: Ticket {args.ticket} escalated")
            print(f"{'='*60}")
            sys.exit(1)
    
    except Exception as e:
        print(f"\n{'='*60}")
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        print(f"{'='*60}")
        sys.exit(2)


if __name__ == '__main__':
    main()
