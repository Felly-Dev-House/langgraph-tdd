#!/usr/bin/env python3
"""
Language-Agnostic TDD Agent with Langfuse Integration

This agent supports multiple programming languages through a handler system:
- Python (pytest)
- C (ESP-IDF with Unity + CMock)
- TypeScript (Next.js/React with Vitest/Jest)
- (Extensible for Rust, Go, etc.)

Features:
- Language auto-detection from spec content
- ESP-IDF toolchain support (on CT 204)
- QEMU testing for ESP32 code
- Langfuse tracing for observability

Usage:
    python agent.py --ticket <ticket_id> --spec <spec_path>
"""

import argparse
import json
import sys
import os
import re
import time
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

# Add handlers to path
sys.path.insert(0, str(Path(__file__).parent))

from handlers.base_handler import (
    BaseHandler, TestResult, CodeFile,
    detect_language_from_spec, get_handler
)

# Langfuse integration
LANGFUSE_ENABLED = os.environ.get('LANGFUSE_HOST') is not None
LANGFUSE_HOST = os.environ.get('LANGFUSE_HOST', '')
LANGFUSE_PUBLIC_KEY = os.environ.get('LANGFUSE_PUBLIC_KEY', '')
LANGFUSE_SECRET_KEY = os.environ.get('LANGFUSE_SECRET_KEY', '')

class LangfuseTracer:
    """Langfuse tracing with SDK integration"""
    
    def __init__(self, session_id: str = None):
        self.session_id = session_id or f"tdd-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        self.enabled = LANGFUSE_ENABLED and LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY
        self.events = []
        self.langfuse = None
        self.trace_id = None
        self.last_event = None
        
        if self.enabled:
            try:
                from langfuse import Langfuse
                self.langfuse = Langfuse(
                    public_key=LANGFUSE_PUBLIC_KEY,
                    secret_key=LANGFUSE_SECRET_KEY,
                    host=LANGFUSE_HOST
                )
                print(f"[LANGFUSE] Connected to {LANGFUSE_HOST}")
                print(f"[LANGFUSE] Session: {self.session_id}")
            except Exception as e:
                print(f"[LANGFUSE] SDK init failed: {e}")
                self.enabled = False
        else:
            if not LANGFUSE_ENABLED:
                print("[LANGFUSE] Not enabled - no LANGFUSE_HOST set")
            elif not (LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY):
                print("[LANGFUSE] Not enabled - missing credentials")
    
    def trace_event(self, name: str, event_type: str, data: Dict[str, Any] = None):
        """Record a trace event"""
        event = {
            'timestamp': datetime.now().isoformat(),
            'session_id': self.session_id,
            'name': name,
            'type': event_type,
            'data': data or {}
        }
        self.events.append(event)
        
        # Log to console
        print(f"[LANGFUSE] {event_type}: {name}")
        
        # Send to Langfuse if available
        if self.enabled and self.langfuse:
            try:
                from langfuse.types import TraceContext
                self.last_event = self.langfuse.create_event(
                    trace_context=TraceContext(id=self.session_id),
                    name=name,
                    input=data or {},
                    level="DEFAULT" if event_type != "error" else "ERROR"
                )
            except Exception as e:
                print(f"[LANGFUSE] Send failed: {e}")
    
    def trace_success(self, data: Dict[str, Any] = None):
        """Mark trace as successful"""
        self.trace_event('tdd_success', 'success', data or {"status": "success"})
    
    def trace_error(self, data: Dict[str, Any] = None):
        """Mark trace as failed"""
        self.trace_event('tdd_failure', 'error', data or {"status": "failure"})
    
    def flush(self):
        """Flush pending events"""
        if self.enabled and self.langfuse:
            try:
                self.langfuse.flush()
                print(f"[LANGFUSE] Events flushed")
            except Exception as e:
                print(f"[LANGFUSE] Flush failed: {e}")
    
    def save(self, output_path: str = None):
        """Save trace events to file"""
        if not output_path:
            output_path = f"/tmp/langfuse-trace-{self.session_id}.json"
        
        with open(output_path, 'w') as f:
            json.dump({
                'session_id': self.session_id,
                'events': self.events,
                'langfuse_host': LANGFUSE_HOST if self.enabled else None,
                'sent_to_api': self.enabled
            }, f, indent=2)
        
        print(f"[LANGFUSE] Traces saved to: {output_path}")


class TDDAgent:
    """Main TDD orchestrator with language dispatch and Langfuse tracing"""
    
    def __init__(self, ticket_id: str, spec_path: str, workspace: str = '/mnt/workspace/tasks', 
                 max_iterations: int = 10, use_qemu: bool = False):
        self.ticket_id = ticket_id
        self.spec_path = Path(spec_path)
        self.workspace = Path(workspace) / ticket_id
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.max_iterations = max_iterations
        self.use_qemu = use_qemu
        
        # Initialize tracer
        self.tracer = LangfuseTracer(session_id=ticket_id)
        
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
        
        # Log start
        self.tracer.trace_event('tdd_start', 'info', {
            'ticket_id': ticket_id,
            'language': self.language,
            'handler': self.handler.language_name,
            'spec_path': str(spec_path)
        })
    
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
        patterns = [
            r'Project Name[":\s]+[`"]?(\w+)[`"]?',
            r'Project Name:\s+`(\w+)`',
            r'module_name:\s*(\w+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1)
        
        # Fallback: use ticket ID
        parts = self.ticket_id.split('-')
        if len(parts) > 3:
            descriptive = [p for p in parts[1:] if p not in ['for', 'the', 'a', 'an', 'and']]
            if descriptive:
                return '_'.join(descriptive[-3:])
        
        return parts[-1] if parts else 'generated'
    
    def run(self) -> bool:
        """Run the TDD loop with tracing."""
        print(f"[TDD_AGENT] Language: {self.language}")
        print(f"[TDD_AGENT] Handler: {self.handler.language_name}")
        print(f"[TDD_AGENT] Test Framework: {self.handler.test_framework}")
        print(f"[TDD_AGENT] Module: {self.spec['module_name']}")
        print(f"[TDD_AGENT] QEMU Mode: {'Enabled' if self.use_qemu else 'Disabled'}")
        
        # Log language detection
        self.tracer.trace_event('language_detected', 'info', {
            'language': self.language,
            'handler': self.handler.language_name
        })
        
        # Setup environment
        print(f"[TDD_AGENT] Setting up environment...")
        if not self.handler.setup_environment():
            print(f"[TDD_AGENT] WARNING: Environment setup incomplete")
        
        self.tracer.trace_event('environment_setup', 'info', {'status': 'complete'})
        
        # TDD Loop
        code_files = []
        test_files = []
        
        for iteration in range(1, self.max_iterations + 1):
            print(f"\n[TDD_AGENT] === Iteration {iteration}/{self.max_iterations} ===")
            
            # Log iteration start
            self.tracer.trace_event('iteration_start', 'info', {'iteration': iteration})
            
            try:
                # Generate tests
                if iteration == 1:
                    test_files = self.handler.generate_tests(self.spec, code_files)
                    self._write_files(test_files)
                    self.tracer.trace_event('tests_generated', 'info', {
                        'iteration': iteration,
                        'files': len(test_files)
                    })
                
                # Generate code
                code_files = self.handler.generate_code(self.spec, test_files)
                self._write_files(code_files)
                self.tracer.trace_event('code_generated', 'info', {
                    'iteration': iteration,
                    'files': len(code_files)
                })
                
                # Run tests
                print(f"[TDD_AGENT] Running tests...")
                test_result = self.handler.run_tests(self.workspace)
                
                # Log test result
                self.tracer.trace_event('tests_executed', 'info', {
                    'iteration': iteration,
                    'passed': test_result.passed,
                    'duration_ms': test_result.duration_ms
                })
                
                print(f"[TDD_AGENT] Test result: {'PASSED' if test_result.passed else 'FAILED'}")
                print(f"[TDD_AGENT] Duration: {test_result.duration_ms}ms")
                
                if test_result.output:
                    output_preview = test_result.output[:300] if len(test_result.output) > 300 else test_result.output
                    print(f"[TDD_AGENT] Output: {output_preview}")
                
                if test_result.passed:
                    # Judge evaluation
                    print(f"[TDD_AGENT] Running judge evaluation...")
                    judge_result = self._judge_accept(code_files, test_result)
                    
                    self.tracer.trace_event('judge_evaluation', 'info', {
                        'iteration': iteration,
                        'accepted': judge_result
                    })
                    
                    if judge_result:
                        print(f"[TDD_AGENT] ✅ JUDGE ACCEPTED - SUCCESS")
                        
                        # Log success
                    self.tracer.trace_success({
                            'ticket_id': self.ticket_id,
                            'iterations': iteration
                        })
                        
                        # Flush and save traces
                        self.tracer.flush()
                        self.tracer.save(str(self.workspace / 'langfuse_trace.json'))
                        
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
                
                # Log error
                self.tracer.trace_event('iteration_error', 'error', {
                    'iteration': iteration,
                    'error': str(e)
                })
                
                if iteration == self.max_iterations:
                    raise
        
        # Log failure
        self.tracer.trace_error({
            'ticket_id': self.ticket_id,
            'max_iterations': self.max_iterations
        })
        
        print(f"[TDD_AGENT] ❌ MAX ITERATIONS EXHAUSTED - ESCALATING")
        
        # Flush and save traces
        self.tracer.flush()
        self.tracer.save(str(self.workspace / 'langfuse_trace.json'))
        
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
        """Judge evaluation - determines if code quality is acceptable."""
        # Simple implementation: check test pass
        return test_result.passed

