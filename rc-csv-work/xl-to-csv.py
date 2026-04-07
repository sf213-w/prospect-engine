#!/usr/bin/env python3
"""
Simple converter: reads an Excel workbook and writes one or more
CSV files (one per sheet) to the same directory.

Usage:
    python convert_excel_to_csv.py input.xlsx [output_dir]

If the workbook has a single sheet, the script will write a single
CSV named after the workbook.  If there are multiple sheets, each
sheet gets its own file named `<workbook>_<sheetname>.csv`.
"""

import sys
from pathlib import Path

import pandas as pd


def excel_to_csv(src: Path, dest_dir: Path) -> None:
    dest_dir.mkdir(parents=True, exist_ok=True)
    xls = pd.ExcelFile(src)
    if len(xls.sheet_names) == 1:
        # single-sheet workbook
        df = pd.read_excel(xls, sheet_name=0)
        out = dest_dir / f"{src.stem}.csv"
        df.to_csv(out, index=False)
        print(f"wrote {out}")
    else:
        for sheet in xls.sheet_names:
            df = pd.read_excel(xls, sheet_name=sheet)
            # sanitize sheet name for filename
            safe = "".join(c if c.isalnum() or c in "_-" else "_" for c in sheet)
            out = dest_dir / f"{src.stem}_{safe}.csv"
            df.to_csv(out, index=False)
            print(f"wrote {out}")


def main() -> None:
    if len(sys.argv) < 2:
        print("usage: python convert_excel_to_csv.py file.xlsx [output_dir]")
        sys.exit(1)

    src = Path(sys.argv[1])
    if not src.exists():
        print(f"input file not found: {src}")
        sys.exit(2)

    dest = Path(sys.argv[2]) if len(sys.argv) > 2 else src.parent
    excel_to_csv(src, dest)


if __name__ == "__main__":
    main()