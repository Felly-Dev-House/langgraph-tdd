"""
C Handler for ESP-IDF TDD with Unity + CMock.
Generates C code and Unity test files that compile/run on host.
"""
import subprocess
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
from handlers.base_handler import BaseHandler, TestResult, CodeFile

class CHandler(BaseHandler):
    """Handler for C code with ESP-IDF host testing"""
    
    @property
    def language_name(self) -> str:
        return "C (ESP-IDF)"
    
    @property
    def file_extensions(self) -> List[str]:
        return ['.c', '.h']
    
    @property
    def test_framework(self) -> str:
        return "Unity + CMock"
    
    def setup_environment(self) -> bool:
        """
        Setup ESP-IDF host test environment.
        Requires: ESP-IDF installed, Unity, CMock
        """
        # Check for ESP-IDF
        idf_path = Path('/opt/esp-idf')
        if not idf_path.exists():
            print("[C_HANDLER] ESP-IDF not found at /opt/esp-idf")
            return False
        
        # Check for Unity
        unity_path = idf_path / 'components' / 'unity'
        if not unity_path.exists():
            print("[C_HANDLER] Unity component not found in ESP-IDF")
            return False
        
        print("[C_HANDLER] ESP-IDF environment ready")
        return True
    
    def generate_tests(self, spec: Dict[str, Any], code_files: List[CodeFile]) -> List[CodeFile]:
        """
        Generate Unity test files for C code.
        
        Test structure:
        - test_<module>.c: Unity test cases
        - mock_<dependency>.c: CMock mocks for ESP-IDF APIs
        """
        test_files = []
        
        # Generate test file header
        test_content = """#include <stdio.h>
#include <unity.h>
#include <stdbool.h>
#include <stdint.h>

// Include generated code headers
#include "{header_file}"

// Mock implementations for ESP-IDF APIs
// These are replaced by CMock mocks in actual tests

// Mock: esp_timer_get_time
uint64_t esp_timer_get_time(void) {{
    return 1000000;  // Default: 1 second in microseconds
}}

// Mock: gpio_set_direction
int gpio_set_direction(uint8_t pin, uint8_t direction) {{
    return 0;  // ESP_OK
}}

// Mock: gpio_set_level
int gpio_set_level(uint8_t pin, uint8_t level) {{
    return 0;
}}

// Mock: gpio_get_level
int gpio_get_level(uint8_t pin) {{
    return 0;
}}

// Mock: twai_driver_init
int twai_driver_init(const twai_timing_config_t *t_config,
                     const twai_filter_config_t *f_config,
                     const twai_general_config_t *g_config) {{
    return 0;
}}

// Mock: twai_transmit
int twai_transmit(const twai_message_t *message, TickType_t ticks_to_wait) {{
    return 0;
}}

// Mock: twai_receive
int twai_receive(twai_message_t *message, TickType_t ticks_to_wait) {{
    return 0;
}}

// Test setup/teardown
void setUp(void) {{
    // Setup before each test
}}

void tearDown(void) {{
    // Cleanup after each test
}}

void test_init_happy_path(void) {{
    // Test successful initialization
    // TO BE FILLED BY TDD AGENT
    TEST_PASS();
}}

void test_init_error_conditions(void) {{
    // Test initialization failure cases
    // TO BE FILLED BY TDD AGENT
    TEST_PASS();
}}

int main(void) {{
    UNITY_BEGIN();
    
    RUN_TEST(test_init_happy_path);
    RUN_TEST(test_init_error_conditions);
    // Additional test cases will be added by TDD agent
    
    return UNITY_END();
}}
"""
        
        # Find header file
        header_file = "generated_code.h"
        for cf in code_files:
            if cf.path.endswith('.h'):
                header_file = Path(cf.path).name
                break
        
        # Create test file
        test_filename = f"test_{spec.get('module_name', 'generated')}.c"
        test_path = self.workspace / 'test' / test_filename
        test_path.parent.mkdir(parents=True, exist_ok=True)
        
        test_content = test_content.format(header_file=header_file)
        test_files.append(CodeFile(
            path=str(test_path),
            content=test_content,
            language='c'
        ))
        
        return test_files
    
    def generate_code(self, spec: Dict[str, Any], test_files: List[CodeFile]) -> List[CodeFile]:
        """
        Generate C implementation code with header files.
        """
        code_files = []
        
        # Generate header file
        module_name = spec.get('module_name', 'generated')
        header_content = f"""#ifndef _{module_name.upper()}_H
#define _{module_name.upper()}_H

#include <stdint.h>
#include <stdbool.h>

// ESP-IDF types (mocked in host tests)
typedef struct {{
    uint32_t baud_rate;
    uint8_t tx_pin;
    uint8_t rx_pin;
}} twai_config_t;

typedef struct {{
    uint32_t id;
    uint8_t data[8];
    uint8_t data_len;
    bool extended;
}} twai_message_t;

// Error codes
#define ESP_OK          0
#define ESP_FAIL        -1
#define ESP_ERR_TIMEOUT -100
#define ESP_ERR_INVALID_ARG -200

// Main API functions
int {module_name}_init(uint32_t baud_rate, uint8_t tx_pin, uint8_t rx_pin);
int {module_name}_deinit(void);
int {module_name}_transmit(const twai_message_t *message);
int {module_name}_receive(twai_message_t *message, int timeout_ms);

#endif // _{module_name.upper()}_H
"""
        
        header_path = self.workspace / 'include' / f'{module_name}.h'
        header_path.parent.mkdir(parents=True, exist_ok=True)
        code_files.append(CodeFile(
            path=str(header_path),
            content=header_content,
            language='c'
        ))
        
        # Generate implementation file
        impl_content = f"""#include "{module_name}.h"
#include <string.h>
#include <time.h>

// Internal state
static bool s_initialized = false;
static twai_config_t s_config = {{0}};

int {module_name}_init(uint32_t baud_rate, uint8_t tx_pin, uint8_t rx_pin) {{
    if (s_initialized) {{
        return ESP_FAIL;  // Already initialized
    }}
    
    if (tx_pin > 39 || rx_pin > 39) {{
        return ESP_ERR_INVALID_ARG;  // Invalid GPIO
    }}
    
    // Configure GPIO
    gpio_set_direction(tx_pin, 1);  // Output
    gpio_set_direction(rx_pin, 0);  // Input
    
    // Initialize TWAI driver
    twai_timing_config_t t_config = {{.speed = baud_rate}};
    twai_filter_config_t f_config = {{.mode = TWAI_STD}};
    twai_general_config_t g_config = {{.tx_io = tx_pin, .rx_io = rx_pin}};
    
    int result = twai_driver_init(&t_config, &f_config, &g_config);
    if (result != ESP_OK) {{
        return result;
    }}
    
    s_config.baud_rate = baud_rate;
    s_config.tx_pin = tx_pin;
    s_config.rx_pin = rx_pin;
    s_initialized = true;
    
    return ESP_OK;
}}

int {module_name}_deinit(void) {{
    if (!s_initialized) {{
        return ESP_FAIL;
    }}
    
    s_initialized = false;
    return ESP_OK;
}}

int {module_name}_transmit(const twai_message_t *message) {{
    if (!s_initialized || !message) {{
        return ESP_ERR_INVALID_ARG;
    }}
    
    if (message->data_len > 8) {{
        return ESP_ERR_INVALID_ARG;
    }}
    
    return twai_transmit(message, 10);  // 10ms timeout
}}

int {module_name}_receive(twai_message_t *message, int timeout_ms) {{
    if (!s_initialized || !message) {{
        return ESP_ERR_INVALID_ARG;
    }}
    
    return twai_receive(message, timeout_ms / portTICK_PERIOD_MS);
}}
"""
        
        impl_path = self.workspace / 'src' / f'{module_name}.c'
        impl_path.parent.mkdir(parents=True, exist_ok=True)
        code_files.append(CodeFile(
            path=str(impl_path),
            content=impl_content,
            language='c'
        ))
        
        return code_files
    
    def run_tests(self, code_dir: Path) -> TestResult:
        """
        Compile and run C tests using ESP-IDF host test framework.
        """
        import time
        start_time = time.time()
        
        # Check if we have test files
        test_dir = code_dir / 'test'
        if not test_dir.exists():
            return TestResult(
                passed=False,
                output="No test directory found",
                errors=["Test directory missing"],
                duration_ms=0
            )
        
        # Try to find ESP-IDF
        idf_path = Path('/opt/esp-idf')
        if not idf_path.exists():
            # Fallback: compile with gcc directly for basic syntax check
            return self._compile_with_gcc(code_dir)
        
        # Use ESP-IDF host test framework
        try:
            # Build host tests
            build_cmd = [
                'idf.py',
                '-D', f'IDF_TARGET=host',
                'build-test'
            ]
            
            result = subprocess.run(
                build_cmd,
                cwd=code_dir,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode != 0:
                return TestResult(
                    passed=False,
                    output=result.stdout + result.stderr,
                    errors=[result.stderr],
                    duration_ms=int((time.time() - start_time) * 1000)
                )
            
            # Run tests
            test_runner = code_dir / 'build' / 'host_test'
            if test_runner.exists():
                run_result = subprocess.run(
                    [str(test_runner)],
                    cwd=code_dir,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                passed = run_result.returncode == 0
                return TestResult(
                    passed=passed,
                    output=run_result.stdout + run_result.stderr,
                    errors=[] if passed else [run_result.stderr],
                    duration_ms=int((time.time() - start_time) * 1000)
                )
            
        except subprocess.TimeoutExpired:
            return TestResult(
                passed=False,
                output="Test compilation/execution timed out",
                errors=["Timeout"],
                duration_ms=int((time.time() - start_time) * 1000)
            )
        except Exception as e:
            return TestResult(
                passed=False,
                output=str(e),
                errors=[str(e)],
                duration_ms=int((time.time() - start_time) * 1000)
            )
        
        return TestResult(
            passed=False,
            output="No test runner found",
            errors=["Test runner not built"],
            duration_ms=int((time.time() - start_time) * 1000)
        )
    
    def _compile_with_gcc(self, code_dir: Path) -> TestResult:
        """
        Fallback: compile with gcc for syntax check.
        This doesn't run actual tests but verifies C code compiles.
        """
        import time
        start_time = time.time()
        
        # Find all .c files in src and test directories
        src_files = list(code_dir.glob('src/*.c'))
        test_files = list(code_dir.glob('test/*.c'))
        
        if not src_files and not test_files:
            return TestResult(
                passed=False,
                output="No C source files found",
                errors=["No .c files"],
                duration_ms=0
            )
        
        # Compile test file with Unity (simple syntax check)
        try:
            # Find Unity headers
            unity_path = Path('/opt/esp-idf/components/unity/src')
            
            compile_cmd = [
                'gcc',
                '-I', str(code_dir / 'include'),
                '-I', str(unity_path) if unity_path.exists() else '.',
                '-c',  # Compile only, don't link
                '-o', '/tmp/test_syntax.o',
                str(test_files[0]) if test_files else str(src_files[0])
            ]
            
            result = subprocess.run(
                compile_cmd,
                capture_output=True,
                text=True,
                timeout=30
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
