#!/usr/bin/env python3
"""
Create numbered folders from a CSV export of the spreadsheet.

For each data row (row 1 is a header and is skipped), one folder is made for
every filled cell in columns K, L, N and O, then one "Group" folder:

    001_<A>_<B>_<C>_<K name>
    002_<A>_<B>_<C>_<L name>
    003_<A>_<B>_<C>_Group

The counter runs continuously across the whole sheet.

Usage:
    python3 make_folders.py data.csv            # preview only, creates nothing
    python3 make_folders.py data.csv --create   # actually create the folders
    python3 make_folders.py data.csv --dest "/some/other/folder" --create
"""

import argparse
import csv
import os
import re
import sys

DEFAULT_DEST = os.path.join(os.path.dirname(os.path.abspath(__file__)), "destination.txt")

# Zero-based column positions: A=0, B=1, C=2, K=10, L=11, N=13, O=14
COL_A, COL_B, COL_C = 0, 1, 2
NAME_COLS = [10, 11, 13, 14]  # K, L, N, O

ILLEGAL = re.compile(r'[\\/:*?"<>|\x00-\x1f]')


def clean(value):
    """Trim, remove characters not allowed in folder names, spaces -> underscores."""
    value = ILLEGAL.sub("", value or "").strip()
    value = re.sub(r"\s+", "_", value)       # any run of spaces -> one underscore
    value = re.sub(r"_+", "_", value)        # no doubled underscores
    return value.strip("._")                 # no leading dot (hidden on Mac) or stray underscores


def cell(row, i):
    return row[i] if i < len(row) else ""


def build_names(csv_path):
    names = []
    counter = 1
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        next(reader, None)  # skip header row
        for line_no, row in enumerate(reader, start=2):
            prefix_parts = [clean(cell(row, c)) for c in (COL_A, COL_B, COL_C)]
            if not any(prefix_parts):
                continue  # completely blank row
            prefix = "_".join(prefix_parts)
            people = [clean(cell(row, c)) for c in NAME_COLS]
            for person in [p for p in people if p] + ["Group"]:
                names.append((line_no, f"{counter:03d}_{prefix}_{person}"))
                counter += 1
    return names


def main():
    parser = argparse.ArgumentParser(description="Create numbered folders from a CSV.")
    parser.add_argument("csv_file", help="CSV downloaded from the spreadsheet")
    parser.add_argument("--dest", default=DEFAULT_DEST, help="Folder to create the folders in")
    parser.add_argument("--create", action="store_true", help="Actually create folders (default is preview)")
    args = parser.parse_args()

    if not os.path.isfile(args.csv_file):
        sys.exit(f"CSV file not found: {args.csv_file}")

    names = build_names(args.csv_file)
    if not names:
        sys.exit("No data rows found in the CSV.")

    if not args.create:
        print(f"PREVIEW - nothing will be created. Destination: {args.dest}\n")
        for line_no, name in names:
            print(f"  (row {line_no})  {name}")
        print(f"\n{len(names)} folders would be created. Run again with --create to make them.")
        return

    if not os.path.isdir(args.dest):
        sys.exit(f"Destination folder not found: {args.dest}\n"
                 "Is the external drive plugged in, and is the path correct?")

    made = skipped = 0
    for _, name in names:
        path = os.path.join(args.dest, name)
        if os.path.exists(path):
            print(f"  exists, skipped: {name}")
            skipped += 1
        else:
            os.mkdir(path)
            print(f"  created: {name}")
            made += 1
    print(f"\nDone. {made} created, {skipped} already existed.")


if __name__ == "__main__":
    main()