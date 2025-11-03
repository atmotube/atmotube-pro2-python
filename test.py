import json
import unittest
import time
import base64

from history import parse_history_record
from mcumgr_wrapper import run_mcumgr_shell_command

device_path = ""


class AtmocubeCommandTests(unittest.TestCase):

    def test_time_get(self):
        response, error, raw = run_mcumgr_shell_command(device_path, "time")
        self.assertRegex(response, r"^\d+$", msg=f"Unexpected response: {raw}")

    def test_time_set(self):
        ts = int(time.time())
        response, error, raw = run_mcumgr_shell_command(device_path, f"time", [str(ts)])
        self.assertEqual(response, "ok", msg=f"Unexpected response: {raw}")

    def test_time_set_error(self):
        ts = -1
        response, error, raw = run_mcumgr_shell_command(device_path, f"time", [str(ts)])
        self.assertEqual(response, "err", msg=f"Unexpected response: {raw}")

    def test_pm_on(self):
        response, error, raw = run_mcumgr_shell_command(device_path, "pm on")
        self.assertEqual(response, "ok", msg=f"Unexpected response: {raw}")

    def test_pm_status(self):
        response, error, raw = run_mcumgr_shell_command(device_path, "pm status")
        self.assertRegex(response, r"^[01] [0-4] [01] \d+$", msg=f"Unexpected response: {raw}")

    def test_pm_mode(self):
        for mode in [0, 1, 2, 3, 4]:
            for charging_mode in [0, 1]:
                response, error, raw = run_mcumgr_shell_command(device_path, "pm mode", [str(mode), str(charging_mode)])
                self.assertEqual(response, "ok", msg=f"Unexpected response: {raw}")

    def test_pm_mode_error(self):
        for mode in [-1, 5, 'str', 1000000000]:
            for charging_mode in [-1, 2]:
                response, error, raw = run_mcumgr_shell_command(device_path, "pm mode", [str(mode), str(charging_mode)])
                self.assertEqual(response, "err", msg=f"Unexpected response: {raw}")

    def test_pm_limit(self):
        for val in [1000, 30000, 65500]:
            response, error, raw = run_mcumgr_shell_command(device_path, f"pm limit", [f"{val}"])
            self.assertEqual(response, "ok", msg=f"Unexpected response: {raw}")

    def test_pm_limit_error(self):
        for val in [-1, 70000, 'str', 1000000000]:
            response, error, raw = run_mcumgr_shell_command(device_path, f"pm limit", [f"{val}"])
            self.assertEqual(response, "err", msg=f"Unexpected response: {raw}")

    def test_pm_clean(self):
        response, error, raw = run_mcumgr_shell_command(device_path, "pm clean")
        self.assertEqual(response, "ok", msg=f"Unexpected response: {raw}")

    def test_pm_keepalive(self):
        response, error, raw = run_mcumgr_shell_command(device_path, "pm keepalive", ["60"])
        self.assertEqual(response, "ok", msg=f"Unexpected response: {raw}")

    def test_pm_keepalive_error(self):
        for val in [-1, 1000, 'str', 1000000000]:
            response, error, raw = run_mcumgr_shell_command(device_path, "pm keepalive", [str(val)])
            self.assertEqual(response, "err", msg=f"Unexpected response: {raw}")

    def test_history_get(self):
        response, error, raw = run_mcumgr_shell_command(device_path, "history get")
        for file in response.split(";"):
            file_data = file.split(",")
            if len(file_data) == 1 and file_data[0] == '':
                # ignore the last part
                continue
            self.assertTrue(len(file_data) == 2, msg=f"Unexpected response: {response}")
            fname = file_data[0].strip()
            fsize = int(file_data[1].strip())
            self.assertRegex(fname, r"^/fs/h_(active|new|sync)/\d+$", msg=f"Unexpected file name: {fname}")
            self.assertGreater(fsize, 0, msg=f"Unexpected file size: {fsize}")

    def test_history_sync_error(self):
        response, error, raw = run_mcumgr_shell_command(device_path, "history sync", ["/fs/h_new/1234567890"])
        self.assertEqual(response, "err", msg=f"Unexpected response: {raw}")

    def test_history_sync_rm_error(self):
        response, error, raw = run_mcumgr_shell_command(device_path, "history rm", ["/fs/h_new/1234567890"])
        self.assertEqual(response, "err", msg=f"Unexpected response: {raw}")

    def test_history_mode(self):
        for val in [3, 2, 1, 0]:
            response, error, raw = run_mcumgr_shell_command(device_path, "history mode", [str(val)])
            self.assertEqual(response, "ok", msg=f"Unexpected response: {raw}")

    def test_history_mode_error(self):
        for val in [-1, 400, 'str', 1000000000]:
            response, error, raw = run_mcumgr_shell_command(device_path, "history mode", [str(val)])
            self.assertEqual(response, "err", msg=f"Unexpected response: {raw}")

    def test_history_last(self):
        response, error, raw = run_mcumgr_shell_command(device_path, f"history last")
        try:
            decoded_data = base64.b64decode(response)
        except Exception as e:
            self.fail(f"Failed to decode base64 data: {e}")
        record = parse_history_record(decoded_data)
        if record is None:
            self.fail(f"Failed to parse record!")

    def test_data_get(self):
        response, error, raw = run_mcumgr_shell_command(device_path, f"data get")
        try:
            decoded_data = base64.b64decode(response)
        except Exception as e:
            self.fail(f"Failed to decode base64 data: {e}")
        record = parse_history_record(decoded_data)
        if record is None:
            self.fail(f"Failed to parse record!")

    def test_version_app(self):
        response, error, raw = run_mcumgr_shell_command(device_path, f"version app")
        self.assertRegex(response, fr"^\d+\.\d+\.\d+", msg=f"Unexpected response: {raw}")

    def test_version_hw(self):
        response, error, raw = run_mcumgr_shell_command(device_path, f"version hw")
        self.assertRegex(response, fr"^\d+\.\d+", msg=f"Unexpected response: {raw}")

    def test_gnss_mode(self):
        for val in [0, 1, 2]:
            response, error, raw = run_mcumgr_shell_command(device_path, f"gnss mode", [f"{val}"])
            self.assertEqual(response, "ok", msg=f"Unexpected response: {raw}")

    def test_gnss_timer(self):
        for val in [100, 10]:
            response, error, raw = run_mcumgr_shell_command(device_path, f"gnss timer", [f"{val}"])
            self.assertEqual(response, "ok", msg=f"Unexpected response: {raw}")

    def test_gnss_timer_error(self):
        for val in [-1, 'str', 1000000000]:
            response, error, raw = run_mcumgr_shell_command(device_path, f"gnss timer", [f"{val}"])
            self.assertEqual(response, "err", msg=f"Unexpected response: {raw}")

    def test_gnss_status(self):
        response, error, raw = run_mcumgr_shell_command(device_path, "gnss status")
        self.assertRegex(response, r"^[0-2]( [0-2] [0-9]+)?$", msg=f"Unexpected response: {raw}")

    def test_gnss_info(self):
        response, error, raw = run_mcumgr_shell_command(device_path, "gnss info")
        self.assertRegex(
            response,
            r"^[0-2] [-+]?\d+\.\d+ [-+]?\d+\.\d+ [-+]?\d+(?:\.\d+)? \d+/\d+$",
            msg=f"Unexpected response: {raw}"
        )

    def test_identity(self):
        response, error, raw = run_mcumgr_shell_command(device_path, "identity")
        parts = response.strip().split()
        self.assertGreaterEqual(len(parts), 6, msg=f"Unexpected response: {raw}")

    def test_set_interval(self):
        for val in [1, 10, 60]:
            response, error, raw = run_mcumgr_shell_command(device_path, f"interval", [f"{val}", "0"])
            self.assertEqual(response, "ok", msg=f"Unexpected response: {raw}")

    def test_set_interval_error(self):
        for val in [-1, 61, 'str', 1000000000]:
            response, error, raw = run_mcumgr_shell_command(device_path, f"interval", [f"{val}", "0"])
            self.assertEqual(response, "err", msg=f"Unexpected response: {raw}")

    def test_set_interval_mode(self):
        for val in [3, 2, 1, 0]:
            response, error, raw = run_mcumgr_shell_command(device_path, f"interval", ["60", f"{val}"])
            self.assertEqual(response, "ok", msg=f"Unexpected response: {raw}")

    def test_set_interval_mode_error(self):
        for val in [-1, 4, 'str', 1000000000]:
            response, error, raw = run_mcumgr_shell_command(device_path, f"interval", ["60", f"{val}"])
            self.assertEqual(response, "err", msg=f"Unexpected response: {raw}")

    def test_set_calibration_valid(self):
        for val in [(1.0, 2), (0, 0)]:
            response, error, raw = run_mcumgr_shell_command(device_path, f"calibration", [f"{val[0]}", f"{val[1]}"])
            self.assertEqual(response, "ok", msg=f"Unexpected response: {raw}")

    def test_set_calibration_valid_error(self):
        for val in [(6.0, 15.0), ('str', 'str')]:
            response, error, raw = run_mcumgr_shell_command(device_path, f"calibration", [f"{val[0]}", f"{val[1]}"])
            self.assertEqual(response, "err", msg=f"Unexpected response: {raw}")

    def test_get_calibration_valid_error(self):
        response, error, raw = run_mcumgr_shell_command(device_path, f"calibration")
        self.assertRegex(
            response,
            r"^[-+]?\d+(\.\d+)? [-+]?\d+$",
            msg=f"Unexpected response: {raw}"
        )

    def test_set_calibration_co2_error(self):
        for val in [-1, 6000, 'str', 1000000000]:
            response, error, raw = run_mcumgr_shell_command(device_path, f"calibration_co2", [f"{val}"])
            self.assertEqual(response, "err", msg=f"Unexpected response: {raw}")

    def test_set_button_mode(self):
        for mode in [5, 4, 3, 2, 0, 1]:
            for pm_mode in [0, 1]:
                response, error, raw = run_mcumgr_shell_command(device_path, "button mode", [str(mode), str(pm_mode)])
                self.assertEqual(response, "ok", msg=f"Unexpected response: {raw}")

    def test_set_button_mode_error(self):
        for mode in [-1, 6, 1000000000, 'str']:
            for pm_mode in [-1, 6, 1000000000, 'str']:
                response, error, raw = run_mcumgr_shell_command(device_path, "button mode", [str(mode), str(pm_mode)])
                self.assertEqual(response, "err", msg=f"Unexpected response: {raw}")

    def test_get_button_mode(self):
        response, error, raw = run_mcumgr_shell_command(device_path, "button mode")
        self.assertRegex(response,
                         r"^[0-5] [01]$",
                         msg=f"Unexpected response: {raw}")

    def test_get_voc_mode(self):
        response, error, raw = run_mcumgr_shell_command(device_path, "voc mode")
        self.assertRegex(response,
                         r"^[01]$",
                         msg=f"Unexpected response: {raw}")

    def test_set_voc_mode(self):
        for mode in [0, 1]:
            response, error, raw = run_mcumgr_shell_command(device_path, "voc mode", [str(mode)])
            self.assertEqual(response, "ok", msg=f"Unexpected response: {raw}")

    def test_set_voc_mode_error(self):
        for mode in [-1, 2, 1000000000, 'str']:
            response, error, raw = run_mcumgr_shell_command(device_path, "voc mode", [str(mode)])
            self.assertEqual(response, "err", msg=f"Unexpected response: {raw}")

    def test_battery_status(self):
        response, error, raw = run_mcumgr_shell_command(device_path, "battery status")
        parts = response.strip().split()
        self.assertGreaterEqual(len(parts), 2, msg=f"Unexpected response: {raw}")
        try:
            cycles = int(parts[0])
            health = int(parts[1])
        except ValueError:
            self.fail(f"Non-integer response: {raw}")

        # Validate charging cycles count
        self.assertGreaterEqual(cycles, 0, msg=f"Invalid cycles count: {cycles} (raw={raw})")

        # Validate battery health
        self.assertGreaterEqual(health, 0, msg=f"Health below range: {health} (raw={raw})")
        self.assertLessEqual(health, 100, msg=f"Health above range: {health} (raw={raw})")
