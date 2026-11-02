#!/usr/bin/env python3
"""
Create numbered folders from a CSV export of the spreadsheet.

Rows 1 and 2 are headers and are skipped. Then, for each store row, one folder is
made for every filled name in columns F, G, H and I (shirt sizes removed):

    001_<A>_<B>_<C>_<name>

Column D is the number of associates. If fewer names are filled in than that
number, placeholder folders Assoc_1, Assoc_2, ... make up the difference.

When a row's column C is a group-photo line such as "(1) Photo of 8 (3 Stores)",
one group-shot folder is made for it:

    012_Group_1_Photo_of_8_3_Stores

Blank rows are ignored. The counter runs continuously across the whole sheet.

Usage:
    python3 make_folders.py data.csv            # preview only, creates nothing
    python3 make_folders.py data.csv --create   # actually create the folders
    python3 make_folders.py data.csv --dest "/some/other/folder" --create

The destination folder comes from destination.txt (see below) unless --dest
is given.
"""

import argparse
import csv
import os
import re
import sys

# The destination folder is read from destination.txt, kept next to this
# script and listed in .gitignore so it is never published. Put the full
# path on the first line, e.g.  /Volumes/MyDrive/07_TedGusek/2026_1105_Wakefern
DEST_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "destination.txt")

# Zero-based column positions: A=0, B=1, C=2, D=3, F=5, G=6, H=7, I=8
COL_A, COL_B, COL_C, COL_D = 0, 1, 2, 3

HEADER_ROWS = 2  # rows at the top of the CSV to skip
NAME_COLS = [5, 6, 7, 8]  # F, G, H, I

ILLEGAL = re.compile(r'[\\/:*?"<>|\x00-\x1f]')
PHOTO_ROW = re.compile(r"photo\s+of", re.IGNORECASE)

# Words that make up a shirt size, e.g. "mens large", "3XL", "2X", "xs".
SIZE_WORD = (r"(?:mens|men's|men|womens|women's|women|ladies|youth|"
             r"small|medium|large|extra|x-?large|"
             r"\d?x{0,3}[sml]|\d?x{1,3}l?|\d?xl)")
# A size after a hyphen: "Coronel-large", "Bird- 3XL", "Boniface - mens large".
HYPHEN_SIZE = re.compile(r"\s*-\s*(?:" + SIZE_WORD + r"[\s\-]*)+$", re.IGNORECASE)
# A size code with no hyphen, only when it is clearly a code: "3XL", "2X", "XL", "XS".
# (Plain words like "Small" or "Large" are left alone so surnames are safe.)
CODE_SIZE = re.compile(r"\s+(?:\d?x{1,3}[sl]?|\dx*l?)$", re.IGNORECASE)


def load_default_dest():
    try:
        with open(DEST_FILE, encoding="utf-8") as f:
            for line in f:
                line = line.strip().strip("'\"")  # allow a dragged-in path with quotes
                if line and not line.startswith("#"):
                    return line
    except FileNotFoundError:
        pass
    return None


def clean(value):
    """Trim, remove characters not allowed in folder names, spaces -> underscores."""
    value = (value or "").replace("/", "-")  # "139/152" -> "139-152"
    value = ILLEGAL.sub("", value).strip()
    value = re.sub(r"\s+", "_", value)       # any run of spaces -> one underscore
    value = re.sub(r"_+", "_", value)        # no doubled underscores
    return value.strip("._")                 # no leading dot (hidden on Mac) or stray underscores


def strip_size(name):
    """'Eleanor Coronel-large (L)' -> 'Eleanor Coronel'; 'Amber Bird- 3XL' -> 'Amber Bird'."""
    name = re.sub(r"\([^)]*\)", " ", name or "")   # anything in parentheses
    name = name.strip(" -")
    for pattern in (HYPHEN_SIZE, CODE_SIZE):
        shorter = pattern.sub("", name).strip(" -")
        if shorter:
            name = shorter
    return name


def cell(row, i):
    return row[i] if i < len(row) else ""


def build_names(csv_path):
    names = []
    counter = 1
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        for _ in range(HEADER_ROWS):
            next(reader, None)  # skip header rows
        for line_no, row in enumerate(reader, start=HEADER_ROWS + 1):
            col_c = cell(row, COL_C)

            if PHOTO_ROW.search(col_c):
                label = clean(re.sub(r"[()]", "", col_c))
                names.append((line_no, f"{counter:03d}_Group_{label}"))
                counter += 1
                continue

            prefix_parts = [clean(cell(row, c)) for c in (COL_A, COL_B, COL_C)]
            if not any(prefix_parts):
                continue  # blank row
            prefix = "_".join(prefix_parts)
            people = [clean(strip_size(cell(row, c))) for c in NAME_COLS]
            people = [p for p in people if p]

            # Column D is the number of associates. If fewer names are filled
            # in, add placeholders Assoc_1, Assoc_2, ... to make up the count.
            try:
                expected = int(float(cell(row, COL_D).strip()))
            except ValueError:
                expected = len(people)
            missing = expected - len(people)
            if missing > 0:
                people += [f"Assoc_{i}" for i in range(1, missing + 1)]

            for person in people:
                names.append((line_no, f"{counter:03d}_{prefix}_{person}"))
                counter += 1
    return names


def main():
    parser = argparse.ArgumentParser(description="Create numbered folders from a CSV.")
    parser.add_argument("csv_file", help="CSV downloaded from the spreadsheet")
    parser.add_argument("--dest", help="Folder to create the folders in (overrides destination.txt)")
    parser.add_argument("--create", action="store_true", help="Actually create folders (default is preview)")
    args = parser.parse_args()

    if not args.dest:
        args.dest = load_default_dest()
    if not args.dest:
        sys.exit(f"No destination set. Create {DEST_FILE}\n"
                 "with the full path of the destination folder on its first line,\n"
                 "or pass --dest \"/path/to/folder\".")

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