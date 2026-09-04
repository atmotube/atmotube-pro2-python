import pandas as pd
import glob
import os
import argparse
import re
import csv


def extract_ts(filename: str) -> int:
    match = re.search(r"_(\d+)\.csv$", os.path.basename(filename))
    return int(match.group(1)) if match else 0


def is_data_like(value: str) -> bool:
    value = value.strip()
    if value == "":
        return True

    if value.lower() in {"yes", "no", "true", "false", "nan", "null"}:
        return True

    if re.match(r"^\d{4}-\d{2}-\d{2}( \d{2}:\d{2}:\d{2})?$", value):
        return True

    try:
        float(value)
        return True
    except ValueError:
        return False


def file_has_header(file_path: str) -> bool:
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace", newline="") as f:
            reader = csv.reader(f)
            first_row = next(reader, None)

        if not first_row:
            return False

        data_like_ratio = sum(is_data_like(cell) for cell in first_row) / len(first_row)

        # If most cells look like values, not column names -> probably no header
        return data_like_ratio < 0.5
    except Exception:
        return False


def read_header(file_path: str):
    return list(pd.read_csv(file_path, nrows=0).columns)


def collect_columns_in_original_order(csv_files: list[str]) -> tuple[list[str], dict[int, list[str]]]:
    ordered_columns = []
    seen = set()
    canonical_by_width = {}

    for file in csv_files:
        try:
            if file_has_header(file):
                cols = read_header(file)

                if len(cols) not in canonical_by_width:
                    canonical_by_width[len(cols)] = cols

                for col in cols:
                    if col not in seen:
                        seen.add(col)
                        ordered_columns.append(col)
        except Exception as e:
            print(f"Error reading header from {file}: {e}")

    return ordered_columns, canonical_by_width


def merge_csv(folder_path: str, output_file: str, pattern: str = "*.csv", chunksize: int = 100_000) -> None:
    csv_files = glob.glob(os.path.join(folder_path, pattern))
    output_abs = os.path.abspath(output_file)

    # Exclude output file itself
    csv_files = [f for f in csv_files if os.path.abspath(f) != output_abs]

    if not csv_files:
        print("No CSV files found")
        return

    csv_files.sort(key=extract_ts)

    print(f"Found {len(csv_files)} files (sorted by timestamp ASC)")

    all_columns, canonical_by_width = collect_columns_in_original_order(csv_files)

    if not all_columns:
        print("Could not determine columns from input files")
        return

    print(f"Total output columns: {len(all_columns)}")

    first_chunk_written = False

    with open(output_file, "w", newline="", encoding="utf-8") as f_out:
        for i, file in enumerate(csv_files, start=1):
            print(f"Processing {i}/{len(csv_files)}: {os.path.basename(file)}")

            try:
                has_header = file_has_header(file)

                if has_header:
                    reader = pd.read_csv(file, chunksize=chunksize)
                else:
                    # Read first row to determine column count
                    sample = pd.read_csv(file, header=None, nrows=5)
                    width = sample.shape[1]

                    if width in canonical_by_width:
                        file_columns = canonical_by_width[width]
                    else:
                        file_columns = [f"col_{j+1}" for j in range(width)]
                        for col in file_columns:
                            if col not in all_columns:
                                all_columns.append(col)

                    reader = pd.read_csv(
                        file,
                        header=None,
                        names=file_columns,
                        chunksize=chunksize,
                    )

                for chunk in reader:
                    chunk = chunk.reindex(columns=all_columns)
                    chunk.to_csv(
                        f_out,
                        index=False,
                        header=not first_chunk_written,
                    )
                    first_chunk_written = True

            except Exception as e:
                print(f"Error processing {file}: {e}")

    print(f"\nDone → {output_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Merge CSV files in a folder")
    parser.add_argument("folder", help="Path to folder with CSV files")
    parser.add_argument(
        "-o", "--output",
        default="combined.csv",
        help="Output file name (default: combined.csv)"
    )
    parser.add_argument(
        "-p", "--pattern",
        default="*.csv",
        help='File pattern, for example "*_h_*.csv"'
    )
    parser.add_argument(
        "--chunksize",
        type=int,
        default=100_000,
        help="Rows per chunk while reading CSV files"
    )

    args = parser.parse_args()

    folder_path = os.path.abspath(args.folder)
    output_file = os.path.join(folder_path, args.output)

    merge_csv(
        folder_path=folder_path,
        output_file=output_file,
        pattern=args.pattern,
        chunksize=args.chunksize,
    )