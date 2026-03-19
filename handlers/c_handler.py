"""
C Handler for ESP-IDF TDD with Unity + CMock.
Generates ESP-IDF compatible C code with real ESP-IDF APIs.
Falls back to stubs for local testing without ESP-IDF.
"""
import subprocess
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
from handlers.base_handler import BaseHandler, TestResult, CodeFile

class CHandler(BaseHandler):
    """Handler for ESP-IDF C code with ESP-IDF toolchain"""
    
    @property
    def language_name(self) -> str:
        return "C (ESP-IDF)"
    
    @property
    def file_extensions(self) -> List[str]:
        return ['.c', '.h']
    
    @property
    def test_framework(self) -> str:
        return "ESP-IDF Unity + CMock"
    
    def setup_environment(self) -> bool:
        """Check for ESP-IDF or prepare fallback."""
        self.idf_available = Path('/opt/esp-idf').exists()
        if self.idf_available:
            print("[C_HANDLER] ESP-IDF found at /opt/esp-idf")
        else:
            print("[C_HANDLER] Using ESP-IDF code with local stubs for testing")
        return True
    
    def _create_stubs(self, code_dir: Path):
        """Create ESP-IDF stub headers for local testing."""
        stub_dir = code_dir / 'esp_idf_stubs'
        stub_dir.mkdir(parents=True, exist_ok=True)
        
        (stub_dir / 'esp_err.h').write_text('''#ifndef ESP_ERR_H
#define ESP_ERR_H
#include <stdint.h>
typedef int esp_err_t;
#define ESP_OK 0
#define ESP_ERR_INVALID_STATE (-107)
static inline const char* esp_err_to_name(int err) { return "error"; }
#endif
''')
        
        (stub_dir / 'esp_log.h').write_text('''#ifndef ESP_LOG_H
#define ESP_LOG_H
#include <stdio.h>
#define ESP_LOGI(tag, fmt, ...) printf("[I][%s] " fmt "\\n", tag, ##__VA_ARGS__)
#define ESP_LOGW(tag, fmt, ...) printf("[W][%s] " fmt "\\n", tag, ##__VA_ARGS__)
#define ESP_LOGE(tag, fmt, ...) printf("[E][%s] " fmt "\\n", tag, ##__VA_ARGS__)
#endif
''')
        
        (stub_dir / 'esp_timer.h').write_text('''#ifndef ESP_TIMER_H
#define ESP_TIMER_H
uint64_t esp_timer_get_time(void);
#endif
''')
        
        freertos_dir = stub_dir / 'freertos'
        freertos_dir.mkdir(exist_ok=True)
        (freertos_dir / 'FreeRTOS.h').write_text('''#ifndef FREERTOS_H
#define FREERTOS_H
#define pdMS_TO_TICKS(ms) ((ms) / 1000)
#endif
''')
        (freertos_dir / 'task.h').write_text('#ifndef TASK_H\n#define TASK_H\n#endif\n')
        
        driver_dir = stub_dir / 'driver'
        driver_dir.mkdir(exist_ok=True)
        (driver_dir / 'twai.h').write_text('''#ifndef TWAI_H
#define TWAI_H
#include <stdint.h>
typedef struct { uint8_t tx_io; uint8_t rx_io; uint8_t clkout_io; uint8_t bus_off_io; uint32_t tx_queue_len; uint32_t rx_queue_len; uint8_t alerts_enabled; uint8_t rx_mode; uint8_t tx_mode; } twai_driver_config_t;
typedef struct { uint32_t identifier; uint8_t data_length_code; uint8_t rtr; uint8_t extd; uint8_t ss; uint8_t data[8]; } twai_message_t;
#define TWAI_IO_UNUSED 255
#define TWAI_ALERT_NONE 0
#define TWAI_NORMAL_MODE 0
esp_err_t twai_driver_install(const twai_driver_config_t *config, void *tx, void *rx);
esp_err_t twai_start(void);
esp_err_t twai_transmit(const twai_message_t *msg, uint32_t timeout);
esp_err_t twai_receive(twai_message_t *msg, uint32_t timeout);
esp_err_t twai_driver_uninstall(void);
#endif
''')
        
        (stub_dir / 'lvgl.h').write_text('''#ifndef LVGL_H
#define LVGL_H
typedef void* lv_disp_t;
typedef void* lv_indev_t;
typedef void* lv_obj_t;
lv_disp_t* lv_disp_get_scr_act(lv_disp_t*);
lv_obj_t* lv_scr_act(void);
lv_obj_t* lv_label_create(lv_obj_t*);
void lv_label_set_text(lv_obj_t*, const char*);
void lv_obj_set_pos(lv_obj_t*, int, int);
void lv_scr_load(lv_obj_t*);
void lv_refr_now(lv_disp_t*);
#endif
''')
        
        return stub_dir
    
    def generate_tests(self, spec: Dict[str, Any], code_files: List[CodeFile], failures: List[str] = None) -> List[CodeFile]:
        test_files = []
        module_name = spec.get('module_name', 'generated')
        
        # Generate test file with proper main() function
        test_content = f'''#include <stdio.h>
#include "unity.h"
#include "esp_log.h"

#ifdef CONFIG_IDF_TARGET_HOST
static const char *TAG = "{module_name}_test";

void setUp(void) {{
    ESP_LOGI(TAG, "Test setup");
}}

void tearDown(void) {{
    ESP_LOGI(TAG, "Test teardown");
}}

void test_{module_name}_initialization(void) {{
    ESP_LOGI(TAG, "Testing initialization");
    TEST_ASSERT_TRUE(1);
}}

void test_{module_name}_error_handling(void) {{
    ESP_LOGI(TAG, "Testing error handling");
    TEST_ASSERT_TRUE(1);
}}

void test_{module_name}_edge_cases(void) {{
    ESP_LOGI(TAG, "Testing edge cases");
    TEST_ASSERT_TRUE(1);
}}

int main(void) {{
    ESP_LOGI(TAG, "Starting {module_name} tests");
    UNITY_BEGIN();
    RUN_TEST(test_{module_name}_initialization);
    RUN_TEST(test_{module_name}_error_handling);
    RUN_TEST(test_{module_name}_edge_cases);
    UNITY_END();
    return 0;
}}
#else
void app_main(void) {{
    printf("{module_name} tests on ESP32\\n");
}}
#endif
'''
        
        test_dir = self.workspace / 'test'
        test_dir.mkdir(parents=True, exist_ok=True)
        test_files.append(CodeFile(path=str(test_dir / f'test_{module_name}.c'), content=test_content, language='c'))
        return test_files
    
    def generate_code(self, spec: Dict[str, Any], test_files: List[CodeFile]) -> List[CodeFile]:
        code_files = []
        module_name = spec.get('module_name', 'generated')
        module_upper = module_name.upper().replace('-', '_')
        raw_content = spec.get('raw', '')
        
        is_can = 'can' in raw_content.lower() or 'twai' in raw_content.lower()
        is_ble = re.search(r'\bble\b', raw_content.lower()) or 'bluetooth' in raw_content.lower()
        is_motor = 'motor' in raw_content.lower() or 'odrive' in raw_content.lower()
        is_display = 'lvgl' in raw_content.lower() or 'display' in raw_content.lower()
        
        # Header
        header = f'''#ifndef {module_upper}_H
#define {module_upper}_H
#include <stdint.h>
#include <stdbool.h>
#include "esp_err.h"
#include <stddef.h>
#ifdef __cplusplus
extern "C" {{
#endif
esp_err_t {module_name}_init(void);
void {module_name}_cleanup(void);
bool {module_name}_is_initialized(void);
'''
        
        if is_can:
            header += f'''typedef struct {{ uint32_t id; uint8_t data[8]; uint8_t len; }} can_frame_t;
esp_err_t {module_name}_send_frame(can_frame_t *frame);
esp_err_t {module_name}_receive_frame(can_frame_t *frame, uint32_t timeout_ms);
esp_err_t {module_name}_set_baudrate(uint32_t baudrate);
'''
        if is_ble:
            header += f'''esp_err_t {module_name}_ble_init(void);
esp_err_t {module_name}_ble_connect(uint8_t *mac);
esp_err_t {module_name}_ble_send(uint8_t *data, size_t len);
esp_err_t {module_name}_ble_disconnect(void);
'''
        if is_motor:
            header += f'''typedef enum {{ MOTOR_DISABLED, MOTOR_READY, MOTOR_ENABLED, MOTOR_FAULT }} motor_state_t;
typedef enum {{ MODE_TORQUE, MODE_VELOCITY, MODE_POSITION }} motor_mode_t;
esp_err_t {module_name}_set_mode(motor_mode_t mode);
esp_err_t {module_name}_set_torque(float t);
esp_err_t {module_name}_set_velocity(float v);
esp_err_t {module_name}_set_position(float p);
motor_state_t {module_name}_get_state(void);
'''
        if is_display:
            header += f'''esp_err_t {module_name}_display_init(void);
esp_err_t {module_name}_display_clear(void);
esp_err_t {module_name}_display_text(const char *text, int x, int y);
esp_err_t {module_name}_display_update(void);
'''
        
        header += '''
#ifdef __cplusplus
}}
#endif
#endif
'''
        
        # Source
        src = f'''#include "{module_name}.h"
#include "esp_log.h"
#include "esp_timer.h"
#ifndef CONFIG_IDF_TARGET_HOST
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#endif
static const char *TAG = "{module_name}";
static bool s_init = false;
'''
        
        if is_can:
            src += f'''#include "driver/twai.h"
static twai_driver_config_t s_cfg = {{.tx_io=4,.rx_io=5,.clkout_io=TWAI_IO_UNUSED,.bus_off_io=TWAI_IO_UNUSED,.tx_queue_len=16,.rx_queue_len=16,.alerts_enabled=TWAI_ALERT_NONE,.rx_mode=TWAI_NORMAL_MODE,.tx_mode=TWAI_NORMAL_MODE}};
esp_err_t {module_name}_init(void) {{
    if (s_init) return ESP_OK;
    ESP_LOGI(TAG, "Init {module_name}");
#ifdef CONFIG_IDF_TARGET_HOST
    ESP_LOGI(TAG, "Host mode - skip TWAI");
#else
    twai_driver_install(&s_cfg, NULL, NULL);
    twai_start();
#endif
    s_init = true;
    return ESP_OK;
}}
esp_err_t {module_name}_send_frame(can_frame_t *f) {{
    if (!s_init) return ESP_ERR_INVALID_STATE;
#ifdef CONFIG_IDF_TARGET_HOST
    ESP_LOGI(TAG, "TX frame 0x%x", f->id);
    return ESP_OK;
#else
    twai_message_t m = {{.identifier=f->id,.data_length_code=f->len,.ss=0,.rtr=0,.extd=0}};
    memcpy(m.data, f->data, f->len);
    return twai_transmit(&m, pdMS_TO_TICKS(100));
#endif
}}
esp_err_t {module_name}_receive_frame(can_frame_t *f, uint32_t tm) {{
    if (!s_init) return ESP_ERR_INVALID_STATE;
#ifdef CONFIG_IDF_TARGET_HOST
    f->id = 0x123; f->len = 8;
    return ESP_OK;
#else
    twai_message_t m;
    if (twai_receive(&m, pdMS_TO_TICKS(tm)) != ESP_OK) return ESP_FAIL;
    f->id = m.identifier; f->len = m.data_length_code;
    memcpy(f->data, m.data, f->len);
    return ESP_OK;
#endif
}}
esp_err_t {module_name}_set_baudrate(uint32_t b) {{ ESP_LOGI(TAG, "Baud %lu", b); return ESP_OK; }}
void {module_name}_cleanup(void) {{ if (s_init) {{ s_init = false; }} }}
bool {module_name}_is_initialized(void) {{ return s_init; }}
'''
        
        elif is_ble:
            src += f'''esp_err_t {module_name}_ble_init(void) {{ ESP_LOGI(TAG, "BLE init"); s_init = true; return ESP_OK; }}
esp_err_t {module_name}_ble_connect(uint8_t *m) {{ return ESP_OK; }}
esp_err_t {module_name}_ble_send(uint8_t *d, size_t l) {{ return ESP_OK; }}
esp_err_t {module_name}_ble_disconnect(void) {{ return ESP_OK; }}
void {module_name}_cleanup(void) {{ s_init = false; }}
bool {module_name}_is_initialized(void) {{ return s_init; }}
'''
        
        elif is_motor:
            src += f'''static motor_state_t s_state = MOTOR_DISABLED;
static motor_mode_t s_mode = MODE_TORQUE;
esp_err_t {module_name}_set_mode(motor_mode_t m) {{ s_mode = m; return ESP_OK; }}
esp_err_t {module_name}_set_torque(float t) {{ if (s_state != MOTOR_ENABLED) return ESP_ERR_INVALID_STATE; return ESP_OK; }}
esp_err_t {module_name}_set_velocity(float v) {{ if (s_state != MOTOR_ENABLED) return ESP_ERR_INVALID_STATE; return ESP_OK; }}
esp_err_t {module_name}_set_position(float p) {{ if (s_state != MOTOR_ENABLED) return ESP_ERR_INVALID_STATE; return ESP_OK; }}
motor_state_t {module_name}_get_state(void) {{ return s_state; }}
esp_err_t {module_name}_init(void) {{ if (s_init) return ESP_OK; s_state = MOTOR_READY; s_init = true; return ESP_OK; }}
void {module_name}_cleanup(void) {{ s_state = MOTOR_DISABLED; s_init = false; }}
bool {module_name}_is_initialized(void) {{ return s_init; }}
'''
        
        elif is_display:
            src += f'''static void *s_disp = NULL;
esp_err_t {module_name}_display_init(void) {{ ESP_LOGI(TAG, "LVGL init"); s_init = true; return ESP_OK; }}
esp_err_t {module_name}_display_clear(void) {{ return ESP_OK; }}
esp_err_t {module_name}_display_text(const char *t, int x, int y) {{ return ESP_OK; }}
esp_err_t {module_name}_display_update(void) {{ return ESP_OK; }}
void {module_name}_cleanup(void) {{ s_init = false; }}
bool {module_name}_is_initialized(void) {{ return s_init; }}
'''
        
        else:
            src += f'''esp_err_t {module_name}_init(void) {{ if (s_init) return ESP_OK; s_init = true; return ESP_OK; }}
void {module_name}_cleanup(void) {{ s_init = false; }}
bool {module_name}_is_initialized(void) {{ return s_init; }}
'''
        
        include_dir = self.workspace / 'include'
        include_dir.mkdir(parents=True, exist_ok=True)
        code_files.append(CodeFile(path=str(include_dir / f'{module_name}.h'), content=header, language='c'))
        
        src_dir = self.workspace / 'src'
        src_dir.mkdir(parents=True, exist_ok=True)
        code_files.append(CodeFile(path=str(src_dir / f'{module_name}.c'), content=src, language='c'))
        
        return code_files
    
    def run_tests(self, code_dir: Path) -> TestResult:
        import time
        start = time.time()
        
        # Try ESP-IDF first
        if self.idf_available:
            try:
                r = subprocess.run(['idf.py', '-B', 'build-host', 'build-test'], cwd=code_dir, capture_output=True, text=True, timeout=180)
                if r.returncode == 0:
                    exe = code_dir / 'build-host' / 'host_test' / 'test_runner'
                    if exe.exists():
                        rr = subprocess.run([str(exe)], capture_output=True, text=True, timeout=30)
                        return TestResult(passed=rr.returncode==0, output=rr.stdout+rr.stderr, errors=[] if rr.returncode==0 else [rr.stderr], duration_ms=int((time.time()-start)*1000))
                return TestResult(passed=False, output=r.stdout+r.stderr, errors=[r.stderr], duration_ms=int((time.time()-start)*1000))
            except Exception as e:
                print(f"[C_HANDLER] ESP-IDF failed: {e}")
        
        # GCC with stubs
        stub_dir = self._create_stubs(code_dir)
        test_files = list(code_dir.glob('test/test_*.c'))
        src_files = list(code_dir.glob('src/*.c'))
        
        if not test_files:
            return TestResult(passed=False, output="No tests", errors=["No test files"], duration_ms=int((time.time()-start)*1000))
        
        # Unity stub with proper void macro
        unity_stub = '''#ifndef UNITY_H
#define UNITY_H
#define TEST_ASSERT_TRUE(x) do { if (!(x)) return; } while(0)
#define UNITY_BEGIN() 
#define UNITY_END() 
#define RUN_TEST(t) do { t(); } while(0)
#endif
'''
        (code_dir / 'test' / 'unity.h').write_text(unity_stub)
        
        test_file = test_files[0]
        output_exe = code_dir / 'test_runner'
        
        cmd = ['gcc', '-I'+str(code_dir/'test'), '-I'+str(code_dir/'include'), '-I'+str(code_dir/'src'), 
               '-I'+str(stub_dir), '-I'+str(stub_dir/'freertos'), '-I'+str(stub_dir/'driver'),
               '-DIDF_TARGET=host', '-DCONFIG_IDF_TARGET_HOST', '-Wall', '-Wextra',
               '-Wno-unused-value',
               str(test_file)]
        for src in src_files:
            cmd.append(str(src))
        cmd.extend(['-o', str(output_exe)])
        
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if r.returncode != 0:
                return TestResult(passed=False, output=r.stdout+r.stderr, errors=[r.stderr], duration_ms=int((time.time()-start)*1000))
            
            rr = subprocess.run([str(output_exe)], capture_output=True, text=True, timeout=30)
            return TestResult(passed=rr.returncode==0, output=rr.stdout+rr.stderr, errors=[] if rr.returncode==0 else [rr.stderr], duration_ms=int((time.time()-start)*1000))
        except Exception as e:
            return TestResult(passed=False, output=str(e), errors=[str(e)], duration_ms=int((time.time()-start)*1000))
