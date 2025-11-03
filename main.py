import base64
import os
import time
import unittest

import test
from test import AtmocubeCommandTests
from csv_export import export_records_to_csv
from device_config import print_device_config
from history import read_history_file, parse_history_record
from mcumgr_wrapper import run_mcumgr_shell_command, run_mcumgr_download_command, \
    run_mcumgr_image_list_command, run_mcumgr_image_upload_command, run_mcumgr_image_confirm_command, \
    run_mcumgr_reset_command
import serial.tools.list_ports

from ota import check_firmware_update, download_file

MACS = {}
FWS = {}
SERIALS = {}
UPDATE = {}


def list_devices_by_vid_pid(vid: int = 0x16c0, pid: int = 0x05e1) -> list[str]:
    """Return a list of device paths matching given VID:PID."""
    matches = []
    ports = serial.tools.list_ports.comports()
    for port in ports:
        if port.vid == vid and port.pid == pid:
            matches.append(port.device)
    return matches


def select_device_interactively(devices: list[str]) -> str | None:
    """Show device list and prompt user to choose one."""
    if not devices:
        print("No matching devices found.")
        return None

    print("Found matching devices:")
    for i, device in enumerate(devices):
        print(f"{i + 1}) {device}: MAC: {MACS.get(device, 'N/A')}, SN: {SERIALS.get(device, 'N/A')}, FW: {FWS.get(device, 'N/A')}")
    print("0) Exit")
    while True:
        choice = input(f"Select a device (0-{len(devices)}): ")
        if choice.isdigit():
            index = int(choice) - 1
            if index == -1:
                print("Exiting.")
                return None
            if 0 <= index < len(devices):
                return devices[index]
        print("Invalid selection. Please try again.")


def summarize_devices(devices):
    for device in devices:
        # repeat 3 times with delay
        for _ in range(3):
            mac, stderr, raw = run_mcumgr_shell_command(device, "mac", timeout=1)
            if stderr:
                MACS[device] = "N/A"
            else:
                MACS[device] = mac if mac else "N/A"
                break
            time.sleep(1)
        fw, stderr, raw = run_mcumgr_shell_command(device, "version app")
        if stderr:
            FWS[device] = "N/A"
        else:
            FWS[device] = fw if fw else "N/A"
        identity, stderr, raw = run_mcumgr_shell_command(device, "identity")
        if stderr:
            SERIALS[device] = "N/A"
        else:
            identity_data = identity.split(" ")
            if len(identity_data) > 4:
                SERIALS[device] = identity_data[4]
            else:
                SERIALS[device] = "N/A"


def parse_image_list(output: str) -> dict:
    lines = output.strip().splitlines()
    result = {}
    current_version = None

    for line in lines:
        line = line.strip()
        if line.startswith("version:"):
            current_version = line.split("version:")[1].strip()
        elif line.startswith("hash:") and current_version:
            hash_val = line.split("hash:")[1].strip()
            result[current_version] = hash_val
            current_version = None  # reset for next entry

    return result


def countdown(seconds: int = 60):
    width = len(str(seconds))  # e.g. 2 for "60"
    for i in range(seconds, 0, -1):
        # :{width}d makes i occupy 'width' chars (right‑aligned), so " 9" not "9"
        msg = f"Rebooting... {i:{width}d}s"
        # add a couple spaces to blank out leftovers
        print(msg + "  ", end="\r", flush=True)
        time.sleep(1)
    print()


def run_tests(device_path):
    test.device_path = device_path

    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(AtmocubeCommandTests)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result


def update_device(device, fw_file: str, update_info: dict):
    print(f"Uploading... (this may take 3 minutes)")
    stdout, stderr = run_mcumgr_image_upload_command(device, fw_file)
    if stderr:
        print("Error uploading firmware:\n", stderr)
    else:
        print(f"Upload complete!")
        stdout, stderr = run_mcumgr_image_list_command(device)
        if stderr:
            print("Error listing images:\n", stderr)
        else:
            images = parse_image_list(stdout)
            print(images)
            for version, hash_val in images.items():
                if version.startswith(update_info['ver']):
                    stdout, stderr = run_mcumgr_image_confirm_command(device, hash_val)
                    if stderr:
                        print(f"Error confirming image {version}:\n", stderr)
                    else:
                        print(f"Image {version} confirmed successfully.")
                        # confirm new firmware
                        check_firmware_update(MACS.get(device, ""), update_info['ver'])
                    break
            stdout, stderr = run_mcumgr_reset_command(device)
            if stderr:
                print("Error resetting device:\n", stderr)
            else:
                print("Device reset successfully. Firmware update complete.")
                countdown(60)
                UPDATE.pop(device)
                print("Setting time...")
                time_result = set_time(device)
                count = 0
                while not time_result:
                    time.sleep(1)
                    time_result = set_time(device)
                    count += 1
                    if count > 10:
                        print("Failed to set time after multiple attempts.")
                        break


def find_fw_bins(search_dir: str):
    entries = []
    with os.scandir(search_dir) as it:
        for entry in it:
            if entry.is_file() and entry.name.startswith("fw_") and entry.name.endswith(".bin"):
                # use entry.stat() once (faster than os.path.getmtime later)
                st = entry.stat()
                entries.append((entry.path, st.st_mtime))
    # sort by mtime descending
    entries.sort(key=lambda x: x[1], reverse=True)
    return [path for path, _ in entries]


def get_local_fw_file(search_dir: str | None = None) -> str | None:
    if not search_dir:
        search_dir = os.getcwd()
    try:
        candidates = find_fw_bins(search_dir)
        return candidates[0] if candidates else None
    except Exception as e:
        print(f"Error scanning local firmware files: {e}")
        return None


def extract_version_from_fw_filename(path: str) -> str:
    base = os.path.basename(path)
    if base.startswith("fw_") and base.endswith(".bin"):
        ver = base[3:-4]
        return ver or "local"
    return "local"


def interactive_command_menu(device: str):
    while True:
        print("\nSelect a command:")
        print("1) Download history")
        print("2) Get current data")
        print("3) Get last history")
        if os.path.exists("config.json"):
            print("5) Set configuration (from config.json)")
        print("6) RECOVERY")
        local_file = get_local_fw_file()
        if local_file:
            print(f"7) Update firmware from local file ({os.path.basename(local_file)})")
        elif UPDATE.get(device):
            print(f"7) Update firmware to {UPDATE[device]['ver']}")
        print("8) Clear history")
        print("9) Run test")
        print("0) Exit")
        choice = input("Enter command: ")
        if choice == "1":
            print("Downloading history...")
            download_history(device)
        elif choice == "2":
            print("Fetching current data...")
            data, stderr, raw = run_mcumgr_shell_command(device, "data get")
            if stderr:
                print("Error:\n", stderr)
            else:
                if data:
                    decoded_data = base64.b64decode(data)
                    record = parse_history_record(decoded_data)
                    print(record)
                else:
                    print("No data found.")
        elif choice == "3":
            print("Fetching last history data...")
            data, stderr, raw = run_mcumgr_shell_command(device, "history last")
            if stderr:
                print("Error:\n", stderr)
            else:
                if data:
                    try:
                        decoded_data = base64.b64decode(data)
                        record = parse_history_record(decoded_data)
                        print(record)
                    except:
                        print("No data found.")
                else:
                    print("No data found.")
        elif choice == "5":
            if os.path.exists("config.json"):
                print("Setting configuration from config.json...")
                from config import apply_config, load_config
                try:
                    device_config = load_config("config.json")
                    apply_config(device, device_config)
                except Exception as e:
                    print(f"Error applying configuration: {e}")
            else:
                print("config.json not found. Please create it first.")
        elif choice == "6":
            update_info = None
            while True:
                print("\nSelect recovery option:")
                print("1) RECOVERY")
                print("2) RECOVERY BETA")
                print("0) Exit")
                sub_choice = input("Enter command: ")
                if sub_choice == "1":
                    update_info = check_firmware_update("", "", recovery=True)
                    break
                elif sub_choice == "2":
                    update_info = check_firmware_update("", "", recovery=True, beta=True)
                    break
                elif sub_choice == "0":
                    print("Returning to main menu.")
                    break
            # download firmware to fs
            if update_info:
                url = update_info['url']
                print(f"Downloading firmware from {url}")
                fw_dir = os.path.join(os.getcwd(), 'fw')
                os.makedirs(fw_dir, exist_ok=True)
                fw_file = os.path.join(fw_dir, f"{update_info['ver']}.bin")
                downloaded = download_file(url, fw_file)
                if downloaded:
                    print(f"Firmware downloaded to {fw_file}")
                    print(f"Running recovery mode on {device}...")
                    # reboot device into recovery mode
                    stdout, stderr, raw = run_mcumgr_shell_command(device, "reboot")
                    print("Waiting for device to enter recovery mode...")
                    while True:
                        stdout, stderr = run_mcumgr_image_list_command(device)
                        if stdout:
                            print("Device is in recovery mode.")
                            images = parse_image_list(stdout)
                            print(images)
                            break
                    update_device(device, fw_file, update_info)
        elif choice == "7":
            fw_file = get_local_fw_file()
            if fw_file:
                ver = extract_version_from_fw_filename(fw_file)
                print(f"Using local firmware: {fw_file} (version: {ver})")
                update_info = {"ver": ver, "url": None}
                update_device(device, fw_file, update_info)
            else:
                update_info = UPDATE.get(device)
                # download firmware to fs
                if update_info:
                    url = update_info['url']
                    print(f"Downloading firmware from {url}")
                    fw_dir = os.path.join(os.getcwd(), 'fw')
                    os.makedirs(fw_dir, exist_ok=True)
                    fw_file = os.path.join(fw_dir, f"{update_info['ver']}.bin")
                    downloaded = download_file(url, fw_file)
                    if downloaded:
                        print(f"Firmware downloaded to {fw_file}")
                        update_device(device, fw_file, update_info)
        elif choice == "8":
            print("Clearing history...")
            out, stderr, raw = run_mcumgr_shell_command(device, "history clear")
            if stderr or out != "ok":
                print("Error clearing history:\n", stderr)
            else:
                print("History cleared successfully.")
        elif choice == "9":
            run_tests(device)
        elif choice == "0":
            print("Exiting.")
            break
        else:
            print("Invalid choice. Try again.")


def download_history(device: str):
    mac = MACS.get(device, "unknown_mac")
    mac_dir = os.path.join(os.getcwd(), 'export', mac)
    os.makedirs(mac_dir, exist_ok=True)

    # Run and print result
    files, stderr, raw = run_mcumgr_shell_command(device, "history get")
    if stderr:
        print("Error:\n", stderr)
    else:
        if files:
            for file in files.split(";"):
                if not file.strip():
                    continue
                file_data = file.split(",")
                fname = file_data[0].strip()
                fsize = file_data[1].strip()
                print(f"File: {fname}, Size: {fsize} bytes")
                fname_parts = fname.split('/')
                # Download the file
                out_name = os.path.join(mac_dir, mac + '_' + fname_parts[-2] + "_" + fname_parts[-1])
                stdout, stderr = run_mcumgr_download_command(device, fname, out_name)
                if stderr:
                    print(f"Error downloading {fname}:\n", stderr)
                else:
                    print(f"Downloaded {fname} successfully.")
                records = read_history_file(out_name)
                export_records_to_csv(records, out_name + ".csv")
                os.remove(out_name)


def set_time(device):
    out, stderr, raw = run_mcumgr_shell_command(device, "time", [str(int(time.time()))])
    if stderr:
        return False
    return out == "ok"


def main():
    print("Atmotube PRO2 Interactive Shell")
    while True:
        print("Searching for devices...")
        devices = list_devices_by_vid_pid()
        summarize_devices(devices)
        device = select_device_interactively(devices)

        if device:
            if set_time(device):
                print(f"Time set successfully.")
            else:
                print(f"Failed to set time!")
            update = check_firmware_update(MACS.get(device, ""), FWS.get(device, ""))
            if update:
                UPDATE[device] = update
            print_device_config(device)
            interactive_command_menu(device)
        else:
            return


if __name__ == "__main__":
    main()
