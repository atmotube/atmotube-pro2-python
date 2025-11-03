import csv

from history import FIELDS_MAPPING


def export_records_to_csv(records: list[dict], path: str):
    # Step 1: Filter valid records and extract only mapped fields
    fieldnames = list(FIELDS_MAPPING.keys())
    clean_records = []

    for r in records:
        if not r.get("crc_valid"):
            continue
        filtered = {k: r.get(k, "") for k in fieldnames}
        clean_records.append(filtered)

    if not clean_records:
        print("No valid records to export.")
        return

    # Step 2: Determine non-empty fields
    non_empty_fields = []
    for key in fieldnames:
        if any(record.get(key) not in ("", None) for record in clean_records):
            non_empty_fields.append(key)

    if not non_empty_fields:
        print("All fields are empty after filtering.")
        return

    # Step 3: Prepare CSV headers and rows
    final_headers = [FIELDS_MAPPING[k] for k in non_empty_fields]

    with open(path, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(final_headers)
        for record in clean_records:
            row = [record.get(k, "") for k in non_empty_fields]
            writer.writerow(row)

    print(f"Exported {len(clean_records)} records to {path} with {len(non_empty_fields)} columns")