"""
Run every query in sql/analysis.sql against the SQLite database and write the
results to reports/sql_results.md.

Run:  python src/run_sql.py
"""
from pathlib import Path
import re
import sqlite3

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "processed" / "appointments.db"
SQL_FILE = ROOT / "sql" / "analysis.sql"
OUT = ROOT / "reports" / "sql_results.md"


def split_queries(text: str) -> list[tuple[str, str]]:
    """Split the file on '-- name:' markers -> [(name, sql), ...]."""
    parts = re.split(r"^-- name:\s*(.+)$", text, flags=re.MULTILINE)
    return [(parts[i].strip(), parts[i + 1].strip()) for i in range(1, len(parts), 2)]


def main() -> None:
    queries = split_queries(SQL_FILE.read_text())
    lines = ["# SQL results", "", f"Generated from `sql/analysis.sql` ({len(queries)} queries).", ""]
    with sqlite3.connect(DB) as con:
        for name, sql in queries:
            result = pd.read_sql_query(sql, con)
            lines += [f"## {name}", "", result.to_markdown(index=False), ""]
            print(f"\n== {name} ==\n{result.head(12).to_string(index=False)}")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines))
    print(f"\nSaved -> {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
