import struct
from datetime import datetime

from aqs import calculate_aqs

FIELDS_MAPPING = {
    "timestamp": "Date (UTC+00:00)",
    "aqs": "AQS",
    # PM data
    "pm1_ug_m3": "PM1.0 (µg/m³)",
    "pm25_ug_m3": "PM2.5 (µg/m³)",
    "pm10_ug_m3": "PM10 (µg/m³)",
    # Extended PM data
    "pm0.5_particles": "PM0.5 Particles",
    "pm1.0_particles": "PM1.0 Particles",
    "pm2.5_particles": "PM2.5 Particles",
    "pm10.0_particles": "PM10.0 Particles",
    "particle_size_nm": "Typical Particle Size (µm)",
    #
    "temperature_c": "Temperature (˚C)",
    "humidity_percent": "Humidity (%)",
    "pressure_mbar": "Pressure (hPa)",
    "voc_index": "TVOC Index",
    "voc_ppm": "TVOC (ppm)",
    "nox_index": "NOx Index",
    "co2_ppm": "CO₂ (ppm)",
    "latitude": "Latitude",
    "longitude": "Longitude",
    "altitude_m": "Altitude (m)",
    "position_error_m": "Position Error (m)",
    # Extended GPS data
    "gnss_snr0_19": "GNSS SNR 0-19",
    "gnss_snr20_49": "GNSS SNR 20-49",
    "gnss_snr50_99": "GNSS SNR 50-99",
    "gnss_snr_avg": "GNSS SNR Avg",
    "satellites_fixed": "Satellites Fixed",
    "satellites_in_view": "Satellites in View",
    # Battery
    "battery_percent": "Battery (%)",
    "charging": "Charging",
    "motion": "Motion"
}


def check_fw_new(demanded: tuple[int, int, int], fw: str | None) -> bool:
    is_new = False
    if fw:
        main_part = fw.split("-", maxsplit=1)[0]
        components = main_part.split(".")
        fw_major = int(components[0]) if len(components) > 0 else 0
        fw_minor = int(components[1]) if len(components) > 1 else 0
        fw_patch = int(components[2]) if len(components) > 2 else 0
        is_new = (fw_major, fw_minor, fw_patch) >= demanded
    return is_new


def compute_crc8_maxim(data: bytes) -> int:
    crc = 0x00
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x80:
                crc = ((crc << 1) ^ 0x31) & 0xFF
            else:
                crc = (crc << 1) & 0xFF
    return crc


def round_voc(value):
    if value < 0.01:
        return round(value, 3)
    elif value < 1:
        return round(value, 2)
    else:
        return round(value, 1)


def read_history_file(path: str, is_new_pm_format: bool):
    with open(path, "rb") as f:
        raw = f.read()

    records = []
    offset = 0
    while offset < len(raw):
        try:
            record = parse_history_record(raw[offset:], is_new_pm_format)
            records.append(record)
            offset += record["_total_length"]
        except Exception as e:
            print(f"Failed to parse record at offset {offset}: {e}")
            break

    return records


# Constants for packet type bits
VOC_BIT = 0b00000001
CO2_BIT = 0b00000010
PM_BIT = 0b00000100
PM_EXT_BIT = 0b00001000
GPS_BIT = 0b00010000
GPS_EXT_BIT = 0b00100000

PM_ENCODING_FLAG = 0x8000
PM_ENCODING_VALUE_MASK = 0x7FFF


def decode_pm_value(raw: int) -> float:
    if (raw & PM_ENCODING_FLAG) != 0:
        # Bit 15 set → integer format
        return float(raw & PM_ENCODING_VALUE_MASK)
    else:
        # Bit 15 clear → 0.1-precision format
        return float(raw) / 10.0


def parse_history_record(data: bytes, is_new_pm_format: bool = False) -> dict:
    if len(data) < 18:
        raise ValueError("Data too short to contain required fields")

    record = {}
    offset = 0

    # Header
    record["history_type"] = data[offset]
    offset += 1
    packet_type = data[offset]
    record["packet_type"] = packet_type
    offset += 1

    # Core data (16 bytes)
    core_fmt = "<IhBIBH"
    (
        ts,
        temp,
        hum,
        pressure,
        battery,
        error_flags
    ) = struct.unpack_from(core_fmt, data, offset)
    offset += struct.calcsize(core_fmt)

    if temp == -1:
        temp = None

    if hum == 0xFF:
        hum = None

    if pressure == 0xFFFFFFFF:
        pressure = None


    record.update({
        "timestamp": datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S"),
        "temperature_c": round(temp / 100.0, 1) if temp is not None else "",
        "humidity_percent": hum if hum is not None else "",
        "pressure_mbar": pressure / 10.0 if pressure is not None else "",
        "battery_percent": battery,
        "error_flags": error_flags
    })

    # Optional fields
    if packet_type & VOC_BIT:
        voc_fmt = "<HHH"
        voc_idx, voc_ppb, nox_idx = struct.unpack_from(voc_fmt, data, offset)
        offset += struct.calcsize(voc_fmt)
        record.update({
            "voc_index": voc_idx,
            "voc_ppm": round_voc(voc_ppb / 1000),
            "nox_index": nox_idx
        })

    if packet_type & CO2_BIT:
        co2_fmt = "<H"
        (co2_ppm,) = struct.unpack_from(co2_fmt, data, offset)
        offset += struct.calcsize(co2_fmt)
        record["co2_ppm"] = co2_ppm

    if packet_type & PM_BIT:
        pm_fmt = "<HHH"
        pm1, pm25, pm10 = struct.unpack_from(pm_fmt, data, offset)
        offset += struct.calcsize(pm_fmt)
        if is_new_pm_format:
            record.update({
                "pm1_ug_m3": decode_pm_value(pm1),
                "pm25_ug_m3": decode_pm_value(pm25),
                "pm10_ug_m3": decode_pm_value(pm10)
            })
        else:
            record.update({
                "pm1_ug_m3": pm1 / 10.0,
                "pm25_ug_m3": pm25 / 10.0,
                "pm10_ug_m3": pm10 / 10.0
            })

    if packet_type & GPS_BIT:
        gps_fmt = "<ii"
        lat, lon = struct.unpack_from(gps_fmt, data, offset)
        offset += struct.calcsize(gps_fmt)
        record.update({
            "latitude": lat / 1e6,
            "longitude": lon / 1e6
        })

    if packet_type & PM_EXT_BIT:
        pm_ext_fmt = "<HHHHH"
        p05, p10, p25, p100, size_nm = struct.unpack_from(pm_ext_fmt, data, offset)
        offset += struct.calcsize(pm_ext_fmt)
        record.update({
            "pm0.5_particles": p05,
            "pm1.0_particles": p10,
            "pm2.5_particles": p25,
            "pm10.0_particles": p100,
            "particle_size_nm": size_nm
        })

    if packet_type & GPS_EXT_BIT:
        gps_ext_fmt = "<BBBBhBBh"
        snr19, snr49, snr99, snr_avg, alt, sat_fix, sat_view, err = struct.unpack_from(gps_ext_fmt, data, offset)
        offset += struct.calcsize(gps_ext_fmt)
        record.update({
            "gnss_snr0_19": snr19,
            "gnss_snr20_49": snr49,
            "gnss_snr50_99": snr99,
            "gnss_snr_avg": snr_avg,
            "altitude_m": alt,
            "satellites_fixed": sat_fix,
            "satellites_in_view": sat_view,
            "position_error_m": err
        })

    # CRC
    crc_expected = data[offset]
    offset += 1

    data_to_check = data[:offset - 1]  # exclude CRC itself
    crc_actual = compute_crc8_maxim(data_to_check)

    record["crc"] = crc_expected
    record["crc_valid"] = (crc_actual == crc_expected)
    record["_total_length"] = offset

    record["aqs"] = calculate_aqs(co2=record.get("co2_ppm"), pm1=record.get("pm1_ug_m3"), pm25=record.get("pm25_ug_m3"), pm10=record.get("pm10_ug_m3"), voc_index=record.get("voc_index"), nox_index=record.get("nox_index"))
    record["charging"] = "yes" if (record["error_flags"] & 0x4000) != 0 else "no"
    record["motion"] = "yes" if (record["error_flags"] & 0x1000) != 0 else "no"
    return record
