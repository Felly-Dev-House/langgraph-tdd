# Language-Agnostic TDD Agent

A multi-language Test-Driven Development agent that supports Python, C, TypeScript, and is extensible to other languages.

## Architecture

```
agent.py (orchestrator)
  ├─ Language Detection (from spec)
  ├─ Handler Dispatch
  └─ Unified TDD Loop

Handlers:
  ├─ PythonHandler  → pytest
  ├─ CHandler       → Unity + CMock (ESP-IDF)
  ├─ TypeScriptHandler → Vitest/Jest (Next.js/React)
  └─ (Extensible)
```

## Supported Languages

| Language | Handler | Test Framework | Use Case |
|----------|---------|----------------|----------|
| Python | PythonHandler | pytest | General scripting, backend |
| C | CHandler | Unity + CMock | ESP-IDF, embedded, systems |
| TypeScript | TypeScriptHandler | Vitest/Jest | Next.js, React, Node.js |

## Usage

### Basic Usage

```bash
# Run TDD for a ticket
python agent.py --ticket 20260318-esp32-can-bus --spec /mnt/workspace/specs/20260318-esp32-can-bus-foundation-for-r.md
```

### With Language Detection

The agent automatically detects language from the spec file:

```yaml
# In spec.md:
language: C
framework: ESP-IDF
test_framework: unity
```

### Adding New Languages

1. Create `handlers/<language>_handler.py`:
```python
from base_handler import BaseHandler, TestResult, CodeFile

class MyLanguageHandler(BaseHandler):
    @property
    def language_name(self): return "My Language"
    
    @property
    def file_extensions(self): return ['.ml']
    
    @property
    def test_framework(self): return "OUnit"
    
    def generate_tests(self, spec, code): ...
    def generate_code(self, spec, tests): ...
    def run_tests(self, code_dir): ...
    def setup_environment(self): ...
```

2. Register in `handlers/__init__.py`:
```python
from .mylanguage_handler import MyLanguageHandler

# Add to get_handler() factory
handlers = {
    ...
    'mylanguage': MyLanguageHandler,
}
```

## Configuration

Environment variables:
```bash
export TDD_MAX_ITERATIONS=10      # Max TDD iterations
export TDD_JUDGE_THRESHOLD=0.8    # Judge acceptance threshold
export TDD_WORKSPACE=/mnt/workspace/tasks  # Workspace directory
```

## File Structure

```
langgraph_tdd/
├── agent.py                 # Main orchestrator
├── handlers/
│   ├── __init__.py         # Handler registry
│   ├── base_handler.py     # Abstract base class
│   ├── python_handler.py   # Python/pytest
│   ├── c_handler.py        # C/ESP-IDF/Unity
│   └── typescript_handler.py # TypeScript/Next.js/Vitest
└── README.md
```

## Example Spec Format

```markdown
# Technical Specification

## Metadata
- language: C
- framework: ESP-IDF
- test_framework: unity
- module_name: can_driver

## Requirements
- Initialize TWAI driver
- Send/receive CAN frames
- Handle error states
```

## Testing the Handlers

### Python Handler
```bash
cd /mnt/workspace/tasks/20260318-esp32-can-bus-foundation-for-r
python -m pytest
```

### C Handler (with ESP-IDF)
```bash
export IDF_PATH=/opt/esp-idf
cd /mnt/workspace/tasks/esp32-test
idf.py build-test
./build/host_test
```

### TypeScript Handler
```bash
cd /mnt/workspace/tasks/nextjs-test
npm install
npm test
```

## License

Internal use only - Felly Dev House
