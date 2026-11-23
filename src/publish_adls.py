"""Upload raw, Silver and Gold outputs to an EXISTING ADLS Gen2 filesystem."""

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def inventory():
    manifest_path = ROOT / "datasets/gold/build_manifest.json"
    if not manifest_path.exists():
        raise ValueError("Run src/run_pipeline.py before publishing")
    manifest = json.loads(manifest_path.read_text())
    for filename, expected in manifest["inputs"].items():
        if hashlib.sha256((ROOT / filename).read_bytes()).hexdigest() != expected:
            raise ValueError(f"Input changed since validated build: {filename}")
    import csv
    with (ROOT / "datasets/quality/data_quality_log.csv").open() as stream:
        logs = list(csv.DictReader(stream))
    if not logs or logs[-1]["run_id"] != manifest["run_id"]:
        raise ValueError("Latest quality run does not match Gold build; rerun pipeline")
    if any(row["status"] == "fail" for row in logs if row["run_id"] == manifest["run_id"]):
        raise ValueError("Latest build has failed checks; publication blocked")
    mappings = [(ROOT / "datasets/raw", "bronze"),
                (ROOT / "datasets/processed", "silver"),
                (ROOT / "datasets/gold", "gold"),
                (ROOT / "datasets/quality", "quality")]
    records = []
    for directory, layer in mappings:
        for file in sorted(directory.rglob("*")):
            if file.is_file() and file.name != ".gitkeep" and file.suffix in [".csv", ".xlsx", ".json", ".parquet"]:
                records.append({"file": str(file.relative_to(ROOT)), "path": f"{layer}/{file.relative_to(directory).as_posix()}",
                                "sha256": hashlib.sha256(file.read_bytes()).hexdigest(), "bytes": file.stat().st_size})
    if not records:
        raise ValueError("No pipeline outputs found; run src/run_pipeline.py first")
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--account")
    parser.add_argument("--filesystem")
    parser.add_argument("--prefix", default="aquaagri")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    records = inventory()
    if args.dry_run:
        print(json.dumps(records, indent=2))
        return
    if not args.account or not args.filesystem:
        parser.error("--account and --filesystem are required unless --dry-run is used")
    from azure.identity import DefaultAzureCredential
    from azure.storage.filedatalake import DataLakeServiceClient
    client = DataLakeServiceClient(account_url=f"https://{args.account}.dfs.core.windows.net",
                                   credential=DefaultAzureCredential())
    filesystem = client.get_file_system_client(args.filesystem)
    filesystem.get_file_system_properties()  # Fails before uploads if access is unavailable.
    # Every publish gets a versioned folder: original Bronze files are never overwritten.
    version = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    prefix = f"{args.prefix.strip('/')}/runs/{version}"
    directories = set()
    for record in records:
        path = f"{prefix}/{record['path']}"
        parent = str(Path(path).parent)
        if parent not in directories:
            from azure.core.exceptions import ResourceExistsError
            try:
                filesystem.create_directory(parent)
            except ResourceExistsError:
                pass
            directories.add(parent)
        blob = filesystem.get_file_client(path)
        with (ROOT / record["file"]).open("rb") as stream:
            blob.upload_data(stream, overwrite=False, metadata={"source_name": "aquaagri_pipeline", "sha256": record["sha256"]})
        assert blob.get_file_properties().size == record["bytes"]
    manifest = {"published_at": version, "path": prefix, "files": records}
    filesystem.get_file_client(f"{prefix}/publish_manifest.json").upload_data(json.dumps(manifest), overwrite=False)
    print(json.dumps({"published_files": len(records), "path": prefix}))


if __name__ == "__main__":
    main()
