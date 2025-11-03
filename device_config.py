from mcumgr_wrapper import run_mcumgr_shell_command
from enum import IntEnum


class PMState(IntEnum):
    OFF = 0
    ON = 1

    def __str__(self):
        return self.name.replace('_', ' ').title().lower()


class PMMode(IntEnum):
    ON_DEMAND = 0
    ALWAYS_ON = 1
    MIN_15 = 2
    MIN_10 = 3
    MIN_5 = 4

    def __str__(self):
        return self.name.replace('_', ' ').title().lower()


class PMChargingMode(IntEnum):
    OFF = 0
    ON = 1

    def __str__(self):
        return self.name.replace('_', ' ').title().lower()


class HistoryMode(IntEnum):
    DEFAULT = 0
    EXTENDED_PM = 1
    EXTENDED_GPS = 2
    EXTENDED_PM_GPS = 3

    def __str__(self):
        return self.name.replace('_', ' ').title().lower()


class ButtonMode(IntEnum):
    DISABLED = 0
    AQS = 1
    CO2 = 2
    TVOC = 3
    NOX = 4
    PM = 5

    def __str__(self):
        return self.name.replace('_', ' ').title().lower()


class ButtonPMMode(IntEnum):
    OFF = 0
    ON = 1

    def __str__(self):
        return self.name.replace('_', ' ').title().lower()


class IntervalMode(IntEnum):
    AVERAGE = 0
    MEDIAN = 1
    MIN = 2
    MAX = 3

    def __str__(self):
        return self.name.replace('_', ' ').title().lower()


class Interval:
    def __init__(self, seconds: int, mode: IntervalMode):
        self.seconds = seconds
        self.mode = mode

    def __str__(self):
        return f"Interval: {self.seconds}s | mode = {self.mode}"


class CalibrationData:
    def __init__(self, temperature_offset: float, humidity_offset: float):
        self.temperature_offset = temperature_offset
        self.humidity_offset = humidity_offset

    def __str__(self):
        return f"Calibration Data: t = {self.temperature_offset} | h = {self.humidity_offset}"


class PmStatus:
    def __init__(self, state: PMState, mode: PMMode, charging: PMChargingMode, timer: str):
        self.state = state
        self.mode = mode
        self.charging = charging
        self.timer = timer

    def __str__(self):
        return f"PM Status: {self.state} | {self.mode} | charging = {self.charging} | timer = {self.timer}"


class Button:
    def __init__(self, mode: ButtonMode, pm_mode: ButtonPMMode):
        self.mode = mode
        self.pm_mode = pm_mode

    def __str__(self):
        return f"Button Mode: {self.mode} | pm = {self.pm_mode}"


def get_pm_status(device: str) -> PmStatus | None:
    pm_status_str, stderr, raw = run_mcumgr_shell_command(device, "pm status")
    if stderr:
        return None
    try:
        parts = pm_status_str.strip().split(" ")

        state = PMState(int(parts[0]))
        mode = PMMode(int(parts[1]))
        charging = PMChargingMode(int(parts[2]))
        timer = parts[3]

        result = PmStatus(state, mode, charging, timer)
        return result

    except:
        return None


def get_pm_limit(device: str) -> int | None:
    pm_limit, stderr, raw = run_mcumgr_shell_command(device, "pm limit")
    if stderr:
        return False
    try:
        return int(pm_limit.strip())
    except:
        return None


def get_history_mode(device: str) -> HistoryMode | None:
    history_mode_str, stderr, raw = run_mcumgr_shell_command(device, "history mode")
    if stderr:
        return None
    try:
        mode = HistoryMode(int(history_mode_str))
        return mode
    except:
        return None


def get_interval(device: str) -> Interval | None:
    interval_str, stderr, raw = run_mcumgr_shell_command(device, "interval")
    if stderr:
        return None
    try:
        parts = interval_str.strip().split(" ")
        if len(parts) != 2:
            return None
        interval_seconds = int(parts[0])
        interval_mode = IntervalMode(int(parts[1]))
        return Interval(interval_seconds, interval_mode)
    except:
        return None


def get_calibration(device: str) -> CalibrationData | None:
    calibration_data, stderr, raw = run_mcumgr_shell_command(device, "calibration")
    if stderr:
        return None
    try:
        calibration_data = calibration_data.split(" ")
        t = float(calibration_data[0])
        h = float(calibration_data[1])
        data = CalibrationData(t, h)
        return data
    except:
        return None


def get_button_mode(device: str) -> Button | None:
    button_mode_raw, stderr, raw = run_mcumgr_shell_command(device, "button mode")
    if stderr:
        return None
    try:
        parts = button_mode_raw.strip().split(" ")
        mode = ButtonMode(int(float(parts[0])))
        pm_mode = ButtonPMMode(int(float(parts[1])))

        button = Button(mode, pm_mode)
        return button

    except:
        print("Failed to parse button mode output:", button_mode_raw)
        return None


def print_device_config(device):
    print("=" * 60)
    print(get_pm_status(device))
    print(f"PM limit: {get_pm_limit(device)}")
    print(f"History mode: {get_history_mode(device)}")
    print(get_interval(device))
    print(get_calibration(device))
    print(get_button_mode(device))
    print("=" * 60)
