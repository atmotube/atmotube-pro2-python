import requests


def check_firmware_update(mac: str, fw_version: str, recovery: bool = False, beta: bool = False) -> dict | None:
    if recovery:
        if beta:
            url = "https://ota2.atmotube.com/api/v1-public/ota?fw=2.0.0"
        else:
            url = "https://ota2.atmotube.com/api/v1-public/ota?fw=3.0.0"
    else:
        url = "https://ota2.atmotube.com/api/v1-public/ota"
    params = {"mac": mac.upper(), "fw": fw_version}

    try:
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()

        if data.get("status") == 0 and "data" in data and 'ver' in data["data"]:
            update_info = data["data"]
            print(f"Update available: {update_info['ver']}")
            return update_info
        else:
            print("Device is up to date.")
            return None
    except requests.RequestException as e:
        print(f"Failed to check update: {e}")
        return None


def download_file(url: str, output_path: str) -> bool:
    try:
        response = requests.get(url, stream=True, timeout=10)
        response.raise_for_status()

        with open(output_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        print(f"Downloaded file to {output_path}")
        return True
    except requests.RequestException as e:
        print(f"Failed to download file: {e}")
        return False
