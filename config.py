import json
from mcumgr_wrapper import run_mcumgr_shell_command


class ConfigError(Exception):
    """Custom exception for invalid configuration values."""
    pass


def load_config(path: str) -> dict:
    """
    Load and validate the device configuration from a JSON file.

    :param path: Path to the JSON config file
    :return: Dictionary of configuration settings
    :raises ConfigError: If the file is missing required fields or contains invalid values
    """
    with open(path, 'r') as f:
        config = json.load(f)

    # Define valid options for each field
    valid = {
        'pm': {
            'mode': {'on_demand', 'always_on', '15_min', '10_min', '5_min'},
            'charging_mode': {'on', 'off'},
            'limit': lambda v: isinstance(v, int) and 1000 <= v <= 65500
        },
        'history': {
            'mode': {'default', 'ext_pm', 'ext_gps', 'ext_pm_gps'}
        },
        'gps': {
            'mode': {'always_on', 'always_off', 'timer'},
            'timer': lambda v: isinstance(v, int) and 0 < v <= 60
        },
        'interval': {
            'seconds': lambda v: isinstance(v, int) and 0 < v <= 60,
            'mode': {'average', 'median', 'min', 'max'}
        },
        'button': {
            'mode': {'off', 'aqs', 'co2', 'pm', 'tvoc', 'nox'},
            'pm_mode': {'off', 'on'}
        },
        'voc': {
            'mode': {'off', 'always_on'}
        },
        'calibration': {
            't': lambda v: isinstance(v, (float, int)) and -5 <= v <= 5,
            'h': lambda v: isinstance(v, int) and -10 <= v <= 10
        }
    }

    # Validate each section
    for section, rules in valid.items():
        if section not in config:
            raise ConfigError(f"Missing section '{section}' in config")
        for field, rule in rules.items():
            if field not in config[section]:
                raise ConfigError(f"Missing field '{field}' in section '{section}'")
            value = config[section][field]
            if callable(rule):
                if not rule(value):
                    raise ConfigError(f"Invalid value for {section}.{field}: {value}")
            else:
                if value not in rule:
                    raise ConfigError(f"Invalid value for {section}.{field}: {value}")

    return config


def apply_config(device_path: str, config: dict) -> None:
    """
    Apply the configuration settings to the device via McuMgrClient commands.

    :param config: Configuration dictionary
    :param client: Initialized McuMgrClient instance
    """
    pm = config['pm']
    mode = ('on_demand', 'always_on', '15_min', '10_min', '5_min').index(pm['mode'])
    charging_mode = ('off', 'on').index(pm['charging_mode'])
    response, error, raw = run_mcumgr_shell_command(device_path, "pm mode", [str(mode), str(charging_mode)])
    if error:
        raise RuntimeError(f"Failed to set PM mode: {error}")
    pm_limit = pm['limit']
    response, error, raw = run_mcumgr_shell_command(device_path, "pm limit", [str(pm_limit)])
    if error:
        raise RuntimeError(f"Failed to set PM limit: {error}")

    history_mode = ('default', 'ext_pm', 'ext_gps', 'ext_pm_gps').index(config['history']['mode'])
    response, error, raw = run_mcumgr_shell_command(device_path, "history mode", [str(history_mode)])
    if error:
        raise RuntimeError(f"Failed to set history mode: {error}")

    gps = config['gps']
    gps_mode = ('always_off', 'timer', 'always_on').index(gps['mode'])
    response, error, raw = run_mcumgr_shell_command(device_path, "gnss mode", [str(gps_mode)])
    if error:
        raise RuntimeError(f"Failed to set GPS mode: {error}")

    gps_timer = gps['timer']
    response, error, raw = run_mcumgr_shell_command(device_path, "gnss timer", [str(gps_timer)])
    if error:
        raise RuntimeError(f"Failed to set GPS timer: {error}")

    interval = config['interval']
    interval_seconds = interval['seconds']
    interval_mode = ('average', 'median', 'min', 'max').index(interval['mode'])
    response, error, raw = run_mcumgr_shell_command(device_path, "interval", [str(interval_seconds), str(interval_mode)])
    if error:
        raise RuntimeError(f"Failed to set interval: {error}")

    button = config['button']
    button_mode = ('off', 'aqs', 'co2', 'tvoc', 'nox', 'pm').index(button['mode'])
    pm_mode = ('off', 'on').index(button['pm_mode'])
    response, error, raw = run_mcumgr_shell_command(device_path, "button mode", [str(button_mode), str(pm_mode)])
    if error:
        raise RuntimeError(f"Failed to set button mode: {error}")

    voc = config['voc']
    voc_mode = ('off', 'always_on').index(voc['mode'])
    response, error, raw = run_mcumgr_shell_command(device_path, "voc mode", [str(voc_mode)])
    if error:
        raise RuntimeError(f"Failed to set VOC mode: {error}")

    calibration = config['calibration']
    t = calibration['t']
    h = calibration['h']
    response, error, raw = run_mcumgr_shell_command(device_path, "calibration", [str(t), str(h)])
    if error:
        raise RuntimeError(f"Failed to set calibration: {error}")

    print("Configuration applied successfully.")