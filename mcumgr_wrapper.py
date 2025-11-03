import subprocess

BAUD_RATE = 1000000  # Default baud rate for serial communication


def run_mcumgr_shell_command(device: str, cmd: str, args=None, timeout=4) -> tuple[str, str, str]:
    if args is None:
        args = []
    # surround args with quotes if they contain spaces
    args = [f'"{arg}"' if "-" in arg else arg for arg in args]
    conn_args = [
        "--conntype", "serial",
        "--connstring", f"dev={device},baud={BAUD_RATE}"
    ]
    """Run mcumgr with specified arguments."""
    command = ["./mcumgr"] + conn_args + ["shell", "exec"] + cmd.split(" ") + args
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True, timeout=timeout)
        full_cmd = cmd.split(" ") + args
        out, raw = parse_output(cmd, result.stdout, " ".join(full_cmd))
        return out, "", raw
    except subprocess.CalledProcessError as e:
        return e.stdout or "", e.stderr or "Unknown error", e.stdout or ""
    except subprocess.TimeoutExpired as e:
        return "", "Command timed out", e.stdout or ""


def run_mcumgr_download_command(device: str, file: str, out_file: str) -> tuple[str, str]:
    conn_args = [
        "--conntype", "serial",
        "--connstring", f"dev={device},baud={BAUD_RATE}"
    ]
    command = ["./mcumgr"] + conn_args + ["fs", "download"] + [file, out_file]
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        return result.stdout, ""
    except subprocess.CalledProcessError as e:
        return e.stdout or "", e.stderr or "Unknown error"


def run_mcumgr_image_upload_command(device: str, file: str) -> tuple[str, str]:
    conn_args = [
        "--conntype", "serial",
        "--connstring", f"dev={device},baud={BAUD_RATE}"
    ]
    command = ["./mcumgr"] + conn_args + ["image", "upload", file]

    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    stdout_full = []
    stderr_full = []

    try:
        for line in process.stdout:
            line = line.rstrip()
            stdout_full.append(line)

            if "%" in line:  # crude check for progress lines
                print(f"\r{line}", end="", flush=True)
            else:
                print("\n" + line)  # print other output normally

        process.wait()

        # Read remaining stderr
        stderr_output = process.stderr.read()
        if stderr_output:
            stderr_full.append(stderr_output.strip())

    except Exception as e:
        process.kill()
        return "", f"Error: {str(e)}"

    print()  # move to new line after progress
    return "\n".join(stdout_full), "\n".join(stderr_full)


def run_mcumgr_image_list_command(device: str, timeout=None) -> tuple[str, str]:
    conn_args = [
        "--conntype", "serial",
        "--connstring", f"dev={device},baud={BAUD_RATE}"
    ]
    command = ["./mcumgr"] + conn_args + ["image", "list"]
    try:
        if timeout:
            result = subprocess.run(command, capture_output=True, text=True, check=True, timeout=timeout)
        else:
            result = subprocess.run(command, capture_output=True, text=True, check=True)
        return result.stdout, ""
    except subprocess.CalledProcessError as e:
        return e.stdout or "", e.stderr or "Unknown error"


def run_mcumgr_image_confirm_command(device: str, hash: str) -> tuple[str, str]:
    conn_args = [
        "--conntype", "serial",
        "--connstring", f"dev={device},baud={BAUD_RATE}"
    ]
    command = ["./mcumgr"] + conn_args + ["image", "confirm", hash]
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        return result.stdout, ""
    except subprocess.CalledProcessError as e:
        return e.stdout or "", e.stderr or "Unknown error"


def run_mcumgr_reset_command(device: str) -> tuple[str, str]:
    conn_args = [
        "--conntype", "serial",
        "--connstring", f"dev={device},baud={BAUD_RATE}"
    ]
    command = ["./mcumgr"] + conn_args + ["reset"]
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        return result.stdout, ""
    except subprocess.CalledProcessError as e:
        return e.stdout or "", e.stderr or "Unknown error"


def parse_output(cmd: str, raw: str, full_cmd: str) -> (str | None, str | None):
    lines = raw.strip().splitlines()
    if len(lines) < 3:
        return None, f"{full_cmd} -> None"
    data = lines[2]
    if data.startswith(cmd) or data.lower().startswith(cmd):
        return data[len(cmd):].strip(), f"{full_cmd} -> {data}"
    if cmd.startswith("version"):
        return data, ""
    return None, f"{full_cmd} -> {data}"
