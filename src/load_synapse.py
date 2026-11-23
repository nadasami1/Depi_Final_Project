"""Load validated Gold facts and append shared quality results to existing Synapse tables."""

import argparse
import json
import re
import struct
from pathlib import Path

import pandas as pd
from publish_adls import inventory

ROOT = Path(__file__).resolve().parents[1]
TABLES = {
    "fact_water_usage": ROOT / "datasets/gold/fact_water_usage.csv",
    "fact_water_annual": ROOT / "datasets/gold/fact_water_annual.csv",
    "data_quality_log": ROOT / "datasets/quality/data_quality_log.csv",
}


def load_frames():
    inventory()  # Require unchanged inputs and a successful current build.
    return {name: pd.read_csv(path) for name, path in TABLES.items()}


def rows_for_sql(frame):
    safe = frame.astype(object).where(pd.notna(frame), None)
    return [tuple(int(value) if isinstance(value, bool) else value for value in row)
            for row in safe.itertuples(index=False, name=None)]


def upload(connection, frames, schema="dbo", replace=False):
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", schema):
        raise ValueError("Invalid schema identifier")
    if set(frames) - set(TABLES):
        raise ValueError("Only the assigned fact and quality tables may be loaded")
    cursor = connection.cursor()
    counts = {}
    try:
        # Preflight every target before any write.
        for name, frame in frames.items():
            for column in frame.columns:
                if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", column):
                    raise ValueError("Unexpected column identifier")
            columns = ",".join(f"[{column}]" for column in frame.columns)
            cursor.execute(f"SELECT TOP 0 {columns} FROM [{schema}].[{name}]")
            cursor.execute(f"SELECT COUNT_BIG(*) FROM [{schema}].[{name}]")
            counts[name] = int(cursor.fetchone()[0])
            if name != "data_quality_log" and counts[name] and not replace:
                raise ValueError(f"{name} is not empty; refusing duplicate load. Review before using --replace")
        result = {}
        for name, frame in frames.items():
            if name == "data_quality_log":
                cursor.execute(f"SELECT run_id,dataset,check_name FROM [{schema}].[{name}]")
                existing = {tuple(row) for row in cursor.fetchall()}
                mask = [tuple(row) not in existing for row in frame[["run_id", "dataset", "check_name"]].itertuples(index=False, name=None)]
                frame = frame.loc[mask].drop_duplicates(["run_id", "dataset", "check_name"])
                if frame.details.fillna("").str.len().gt(4000).any():
                    raise ValueError("Quality details exceed SQL schema length; enlarge schema before load")
            elif replace:
                cursor.execute(f"DELETE FROM [{schema}].[{name}]")
            columns = ",".join(f"[{column}]" for column in frame.columns)
            placeholders = ",".join("?" for _ in frame.columns)
            rows = rows_for_sql(frame)
            statement = f"INSERT INTO [{schema}].[{name}] ({columns}) VALUES ({placeholders})"
            for start in range(0, len(rows), 200):
                cursor.executemany(statement, rows[start:start+200])
            cursor.execute(f"SELECT COUNT_BIG(*) FROM [{schema}].[{name}]")
            actual = int(cursor.fetchone()[0])
            expected = counts[name] + len(rows) if name == "data_quality_log" else len(rows)
            if actual != expected:
                raise ValueError(f"{name}: row count validation failed ({actual} != {expected})")
            result[name] = {"inserted": len(rows), "target_rows": actual}
        connection.commit()
        return result
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--server")
    parser.add_argument("--database")
    parser.add_argument("--schema", default="dbo")
    parser.add_argument("--replace", action="store_true", help="Replace existing fact rows transactionally; quality history is preserved")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    frames = load_frames()
    if args.dry_run:
        print(json.dumps({name: {"rows": len(frame), "columns": list(frame.columns)} for name, frame in frames.items()}, indent=2))
        return
    if not args.server or not args.database:
        parser.error("--server and --database are required for a live load")
    if not re.fullmatch(r"[a-zA-Z0-9.-]+", args.server) or any(char in args.database for char in ";{}"):
        parser.error("Invalid server or database identifier")
    import pyodbc
    from azure.identity import DefaultAzureCredential
    token = DefaultAzureCredential().get_token("https://database.windows.net/.default").token.encode("utf-16-le")
    packed = struct.pack(f"<I{len(token)}s", len(token), token)
    connection = pyodbc.connect(
        f"DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={args.server};DATABASE={args.database};Encrypt=yes;TrustServerCertificate=no;",
        attrs_before={1256: packed}, autocommit=False)
    try:
        print(json.dumps(upload(connection, frames, args.schema, args.replace), indent=2))
    finally:
        connection.close()


if __name__ == "__main__":
    main()
