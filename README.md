# Atmotube PRO2 Python Tool

A lightweight Python utility for communicating with and managing Atmotube PRO2 devices via USB using the [mcumgr](https://github.com/vouch-opensource/mcumgr-client/) and [Atmotube PRO 2 API](https://support.atmotube.com/en/articles/12714501-atmotube-pro-2-api-documentation).

---

## Features

- Connect to Atmotube PRO2 over BLE  
- Send mcumgr commands
- Log and parse device responses
- Cross-platform support (macOS, Linux, Windows)

---

## Requirements

- Python 3.12 or newer
- `mcumgr` command-line tool
- [Atmotube PRO 2 device](https://store.atmotube.com/products/atmotube-pro-2)

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/atmotube/atmotube-pro2-python
cd atmotube-pro2-tool
```

### 2. Install `mcumgr`

Install from source or use pre-built binaries:

[https://github.com/vouch-opensource/mcumgr-client/](https://github.com/vouch-opensource/mcumgr-client/)

---

## Setup and Run

### macOS / Linux

```bash
python3 -m venv env
source env/bin/activate
pip install -r requirements.txt
python main.py
```

### Windows

```bash
python3 -m venv env
.\env\Scripts\activate.bat
pip install -r requirements.txt
python main.py
```

---

## Build a Standalone Executable (Windows)

To generate a single-file binary:

```bash
pip install pyinstaller
pyinstaller --onefile main.py
```

The compiled binary will appear in the `dist/` folder.
