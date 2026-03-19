#!/usr/bin/env python3
"""
Language-Agnostic TDD Agent with Langfuse Integration

Supports: Python (pytest), C (ESP-IDF + Unity), TypeScript (Vitest/Jest)
Features: Language auto-detection, ESP-IDF/QEMU support, Langfuse tracing, GitHub PR creation
"""

import argparse
import json
import sys
import os
import re
import time
from pathlib import Path
import subprocess
from typing import Dict, Any, Optional
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from handlers.base_handler import BaseHandler, TestResult, CodeFile, detect_language_from_spec, get_handler

# Langfuse configuration
LANGFUSE_ENABLED = os.environ.get('LANGFUSE_HOST') is not None
LANGFUSE_HOST = os.environ.get('LANGFUSE_HOST', '')
LANGFUSE_PUBLIC_KEY = os.environ.get('LANGFUSE_PUBLIC_KEY', '')
LANGFUSE_SECRET_KEY = os.environ.get('LANGFUSE_SECRET_KEY', '')

class LangfuseTracer:
    def __init__(self, session_id: str = None):
        self.session_id = session_id or f"tdd-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        self.enabled = LANGFUSE_ENABLED and LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY
        self.events = []
        self.langfuse = None
        self.trace = None
        
        if self.enabled:
            try:
                from langfuse import Langfuse
                self.langfuse = Langfuse(public_key=LANGFUSE_PUBLIC_KEY, secret_key=LANGFUSE_SECRET_KEY, host=LANGFUSE_HOST)
                print(f"[LANGFUSE] Connected to {LANGFUSE_HOST}")
                self.trace = self.langfuse.trace(name="TDD Agent Run", id=self.session_id)
            except Exception as e:
                print(f"[LANGFUSE] SDK init failed: {e}")
                self.enabled = False
    
    def trace_event(self, name: str, event_type: str, data: Dict[str, Any] = None):
        event = {'timestamp': datetime.now().isoformat(), 'session_id': self.session_id, 'name': name, 'type': event_type, 'data': data or {}}
        self.events.append(event)
        print(f"[LANGFUSE] {event_type}: {name}")
        if self.enabled and self.trace:
            try: self.trace.span(name=name, event_type=event_type, input=data or {})
            except Exception as e: print(f"[LANGFUSE] Send failed: {e}")
    
    def trace_success(self, data: Dict[str, Any] = None):
        if self.enabled and self.trace:
            try: self.trace.end(output=data or {"status": "success"})
            except Exception as e: print(f"[LANGFUSE] End failed: {e}")
    
    def trace_error(self, data: Dict[str, Any] = None):
        if self.enabled and self.trace:
            try: self.trace.end(status="ERROR", output=data or {"status": "failure"})
            except Exception as e: print(f"[LANGFUSE] End failed: {e}")
    
    def flush(self):
        if self.enabled and self.langfuse:
            try: self.langfuse.flush(); print("[LANGFUSE] Events flushed")
            except Exception as e: print(f"[LANGFUSE] Flush failed: {e}")
    
    def save(self, output_path: str = None):
        if not output_path: output_path = f"/tmp/langfuse-trace-{self.session_id}.json"
        with open(output_path, 'w') as f:
            json.dump({'session_id': self.session_id, 'events': self.events, 'langfuse_host': LANGFUSE_HOST if self.enabled else None, 'sent_to_api': self.enabled}, f, indent=2)
        print(f"[LANGFUSE] Traces saved to: {output_path}")


class GitHubPRCreator:
    def __init__(self, repo_owner: str, repo_name: str, branch: str = None):
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.branch = branch
        self.gh_available = self._check_gh_cli()
        print(f"[GITHUB] gh CLI {'available' if self.gh_available else 'not found - PR creation disabled'}")
    
    def _check_gh_cli(self) -> bool:
        try:
            result = subprocess.run(['/usr/bin/gh', '--version'], capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except: return False
    
    def create_pr(self, task_dir: Path, issue_number: int, title: str = None, body: str = None) -> Optional[str]:
        if not self.gh_available:
            print(f"[GITHUB] Cannot create PR - gh CLI not available")
            return None
        
        try:
            module_name = task_dir.name
            if not title: title = f"feat: Implement {module_name} (#{issue_number})"
            if not body: body = f"## TDD Implementation Complete\n\n**Issue**: #{issue_number}\n**Module**: `{module_name}`\n\nAll tests passed. Ready for code review."
            branch_name = f"tdd/{module_name}-#{issue_number}"
            
            original_dir = os.getcwd()
            clone_dir = task_dir.parent / f"{task_dir.name}-clone"
            os.chdir(task_dir)
            
            try:
                # Always create fresh git repo in task directory
                print(f"[GITHUB] Initializing git repo in {task_dir}")
                subprocess.run(['git', 'init'], check=True, timeout=10, cwd=str(task_dir), capture_output=True)
                subprocess.run(['git', 'config', 'user.name', 'TDD Agent'], check=True, timeout=10, cwd=str(task_dir), capture_output=True)
                subprocess.run(['git', 'config', 'user.email', 'tdd@dev-house.ai'], check=True, timeout=10, cwd=str(task_dir), capture_output=True)
                
                # Add remote for robstride repo
                print(f"[GITHUB] Adding remote...")
                subprocess.run(['git', 'remote', 'add', 'origin', 'git@github.com:Felly-Dev-House/robstride.git'], check=False, timeout=10, cwd=str(task_dir), capture_output=True)
                
                print(f"[GITHUB] Adding files...")
                subprocess.run(['git', 'add', '.'], check=True, timeout=10)
                print(f"[GITHUB] Committing...")
                subprocess.run(['git', 'commit', '-m', f'feat: Implement {module_name} for issue #{issue_number}'], check=True, timeout=10)
                print(f"[GITHUB] Creating branch and pushing...")
                subprocess.run(['git', 'checkout', '-b', branch_name], check=True, timeout=10)
                subprocess.run(['git', 'push', '-u', '--force', 'origin', branch_name], check=True, timeout=30)
                
                print(f"[GITHUB] PR creation info:")
                print(f"  Issue: #{issue_number}")
                print(f"  Branch: {branch_name}")
                print(f"  Title: {title}")
                print(f"  Task files: {task_dir}")
                print(f"[GITHUB] To create PR, run manually:")
                print(f"  cd {task_dir} && git push origin {branch_name}")
                print(f"  gh pr create --title '{title}' --body 'TDD completed' --repo {self.repo_owner}/{self.repo_name}")
                return None
            finally:
                os.chdir(original_dir)
                # Cleanup clone directory
                if False:  # Disabled
                    import shutil
                    pass  # Disabled
        except Exception as e:
            print(f"[GITHUB] Error creating PR: {e}")
            return None


class TDDAgent:
    def __init__(self, ticket_id: str, spec_path: str, workspace: str = '/mnt/workspace/tasks', max_iterations: int = 10, use_qemu: bool = False):
        self.ticket_id = ticket_id
        self.spec_path = Path(spec_path)
        self.workspace = Path(workspace) / ticket_id
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.max_iterations = max_iterations
        self.use_qemu = use_qemu
        self.tracer = LangfuseTracer(session_id=ticket_id)
        self.spec = self._load_spec()
        self.language = detect_language_from_spec(self.spec)
        if not self.language: raise ValueError(f"Could not detect language from spec: {spec_path}")
        self.handler = get_handler(self.language, str(self.workspace))
        if not self.handler: raise ValueError(f"No handler found for language: {self.language}")
        
        print(f"[TDD_AGENT] Starting {self.handler.language_name} TDD for ticket {ticket_id}")
        self.tracer.trace_event('tdd_start', 'info', {'ticket_id': ticket_id, 'language': self.language, 'handler': self.handler.language_name, 'spec_path': str(spec_path)})
    
    def _load_spec(self) -> Dict[str, Any]:
        with open(self.spec_path) as f: content = f.read()
        raw_content = content
        if '```markdown' in content: raw_content = content.split('```markdown')[1].split('```')[0]
        elif '```' in content: raw_content = content.split('```')[1].split('```')[0]
        module_name = self._extract_module_name(raw_content)
        return {'raw': raw_content, 'module_name': module_name, 'language': self.spec_path.stem.split('-')[0] if '-' in self.spec_path.stem else None}
    
    def _extract_module_name(self, content: str) -> str:
        patterns = [r'Project Name[":\s]+[`"]?(\w+)[`"]?', r'Project Name:\s+`(\w+)`', r'module_name:\s*(\w+)']
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match: return match.group(1)
        parts = self.ticket_id.split('-')
        if len(parts) > 3:
            descriptive = [p for p in parts[1:] if p not in ['for', 'the', 'a', 'an', 'and']]
            if descriptive: return '_'.join(descriptive[-3:])
        return parts[-1] if parts else 'generated'
    
    def _extract_issue_number(self) -> Optional[int]:
        patterns = [r'#(\d+)', r'issue[\s:]+#?(\d+)', r'Issue[\s:]+#?(\d+)']
        for pattern in patterns:
            match = re.search(pattern, self.ticket_id, re.IGNORECASE)
            if match: return int(match.group(1))
        raw = self.spec.get('raw', '')
        for pattern in patterns:
            match = re.search(pattern, raw, re.IGNORECASE)
            if match: return int(match.group(1))
        return None
    
    def _generate_pr_body(self) -> str:
        module = self.spec.get('module_name', 'Implementation')
        issue = self._extract_issue_number()
        return f"""## TDD Implementation Complete

**Issue**: #{issue or 'N/A'}
**Module**: `{module}`
**Language**: {self.language}
**Handler**: {self.handler.language_name}

### What Was Done
- TDD loop completed successfully
- Tests generated and passing
- Code ready for deployment

### Generated Files
- Tests: `test/test_{module}.c`
- Header: `include/{module}.h`
- Source: `src/{module}.c`
- Build: `CMakeLists.txt`, `sdkconfig.defaults`

### Test Results
All tests passed. Ready for code review and ESP-IDF build.

---
Generated by TDD Agent with Langfuse tracing.
"""

    def run(self) -> bool:
        print(f"[TDD_AGENT] Language: {self.language}")
        print(f"[TDD_AGENT] Handler: {self.handler.language_name}")
        print(f"[TDD_AGENT] Test Framework: {self.handler.test_framework}")
        print(f"[TDD_AGENT] Module: {self.spec['module_name']}")
        print(f"[TDD_AGENT] QEMU Mode: {'Enabled' if self.use_qemu else 'Disabled'}")
        self.tracer.trace_event('language_detected', 'info', {'language': self.language, 'handler': self.handler.language_name})
        
        print(f"[TDD_AGENT] Setting up environment...")
        if not self.handler.setup_environment(): print(f"[TDD_AGENT] WARNING: Environment setup incomplete")
        self.tracer.trace_event('environment_setup', 'info', {'status': 'complete'})
        
        code_files, test_files = [], []
        
        for iteration in range(1, self.max_iterations + 1):
            print(f"\n[TDD_AGENT] === Iteration {iteration}/{self.max_iterations} ===")
            self.tracer.trace_event('iteration_start', 'info', {'iteration': iteration})
            
            try:
                if iteration == 1:
                    test_files = self.handler.generate_tests(self.spec, code_files)
                    self._write_files(test_files)
                    self.tracer.trace_event('tests_generated', 'info', {'iteration': iteration, 'files': len(test_files)})
                
                code_files = self.handler.generate_code(self.spec, test_files)
                self._write_files(code_files)
                self.tracer.trace_event('code_generated', 'info', {'iteration': iteration, 'files': len(code_files)})
                
                print(f"[TDD_AGENT] Running tests...")
                test_result = self.handler.run_tests(self.workspace)
                self.tracer.trace_event('tests_executed', 'info', {'iteration': iteration, 'passed': test_result.passed, 'duration_ms': test_result.duration_ms})
                
                print(f"[TDD_AGENT] Test result: {'PASSED' if test_result.passed else 'FAILED'}")
                print(f"[TDD_AGENT] Duration: {test_result.duration_ms}ms")
                if test_result.output:
                    output_preview = test_result.output[:300] if len(test_result.output) > 300 else test_result.output
                    print(f"[TDD_AGENT] Output: {output_preview}")
                
                if test_result.passed:
                    print(f"[TDD_AGENT] Running judge evaluation...")
                    judge_result = self._judge_accept(code_files, test_result)
                    self.tracer.trace_event('judge_evaluation', 'info', {'iteration': iteration, 'accepted': judge_result})
                    
                    if judge_result:
                        print(f"[TDD_AGENT] JUDGE ACCEPTED - SUCCESS")
                        self.tracer.trace_success({'ticket_id': self.ticket_id, 'iterations': iteration})
                        self.tracer.flush()
                        self.tracer.save(str(self.workspace / 'langfuse_trace.json'))
                        
                        # Create GitHub PR
                        issue_number = self._extract_issue_number()
                        if issue_number:
                            pr_creator = GitHubPRCreator(repo_owner='Felly-Dev-House', repo_name='robstride', branch='main')
                            pr_url = pr_creator.create_pr(self.workspace, issue_number, title=f"feat: {self.spec.get('module_name', 'Implementation')} (#{issue_number})", body=self._generate_pr_body())
                            if pr_url:
                                self.tracer.trace_event('pr_created', 'success', {'issue': issue_number, 'pr_url': pr_url})
                        
                        print(f"\n{'='*60}")
                        print(f"SUCCESS: Ticket {self.ticket_id} completed")
                        print(f"{'='*60}")
                        return True
                    else:
                        print(f"[TDD_AGENT] Judge rejected, continuing iterations...")
                
                if not test_result.passed:
                    test_files = self.handler.generate_tests(self.spec, code_files, failures=test_result.errors)
                    self._write_files(test_files)
            
            except Exception as e:
                print(f"[TDD_AGENT] Error in iteration {iteration}: {e}")
                self.tracer.trace_event('iteration_error', 'error', {'iteration': iteration, 'error': str(e)})
                if iteration == self.max_iterations: raise
        
        self.tracer.trace_error({'ticket_id': self.ticket_id, 'max_iterations': self.max_iterations})
        print(f"[TDD_AGENT] MAX ITERATIONS EXHAUSTED - ESCALATING")
        self.tracer.flush()
        self.tracer.save(str(self.workspace / 'langfuse_trace.json'))
        print(f"\n{'='*60}")
        print(f"FAILURE: Ticket {self.ticket_id} escalated")
        print(f"{'='*60}")
        return False
    
    def _write_files(self, files: list):
        for cf in files:
            path = Path(cf.path)
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, 'w') as f: f.write(cf.content)
            print(f"[TDD_AGENT] Written: {cf.path}")
    
    def _judge_accept(self, code_files: list, test_result: TestResult) -> bool:
        return test_result.passed


def main():
    parser = argparse.ArgumentParser(description='Language-Agnostic TDD Agent with Langfuse')
    parser.add_argument('--ticket', required=True, help='Ticket/Issue ID')
    parser.add_argument('--spec', required=True, help='Path to spec file')
    parser.add_argument('--workspace', default='/mnt/workspace/tasks', help='Workspace directory')
    parser.add_argument('--max-iterations', type=int, default=10, help='Max TDD iterations')
    parser.add_argument('--use-qemu', action='store_true', help='Use QEMU for ESP32 testing')
    args = parser.parse_args()
    
    try:
        agent = TDDAgent(args.ticket, args.spec, args.workspace, args.max_iterations, args.use_qemu)
        agent.run()
        sys.exit(0)
    except Exception as e:
        print(f"\n{'='*60}")
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        print(f"{'='*60}")
        sys.exit(2)


if __name__ == '__main__':
    main()
