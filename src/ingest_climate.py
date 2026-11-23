"""Download the team's original climate workbooks into local Bronze storage."""

import argparse
import hashlib
import io
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen
from zipfile import BadZipFile, ZipFile


SOURCES = {
    "pr": "1fwYvpG2A8-VgjX5xE7UrybaVneJ-Fymp",
    "tas": "1GgLvrqu5IQlaHQL5IiY7snxKh-axKLiY",
}
FILENAME = (
    "cru-x0.5_timeseries_{metric}_timeseries_annual_1901-2025_"
    "mean_historical_cru_ts4.10_mean.xlsx"
)
DEFAULT_OUTPUT = Path(__file__).resolve().parents[1] / "datasets/raw/world_bank"


def ingest(output_dir):
    """Keep source bytes unchanged and record provenance for each download."""
    output_dir.mkdir(parents=True, exist_ok=True)
    records = []
    for metric, file_id in SOURCES.items():
        source_url = f"https://drive.google.com/uc?export=download&id={file_id}"
        with urlopen(source_url, timeout=60) as response:
            content = response.read()

        # Drive can return an HTML sign-in page instead of a workbook.
        try:
            with ZipFile(io.BytesIO(content)) as workbook:
                if "xl/workbook.xml" not in workbook.namelist():
                    raise ValueError(f"{metric}: download is not an XLSX workbook")
                if workbook.testzip() is not None:
                    raise ValueError(f"{metric}: workbook archive is damaged")
        except BadZipFile as exc:
            raise ValueError(f"{metric}: download is not a valid XLSX file") from exc

        filename = FILENAME.format(metric=metric)
        destination = output_dir / filename
        if destination.exists() and destination.read_bytes() != content:
            raise ValueError(
                f"{filename}: source changed; preserve the existing raw file "
                "and choose a new --output-dir for the new version"
            )
        destination.write_bytes(content)
        records.append({
            "filename": filename,
            "variable": metric,
            "source_name": "world_bank_cckp",
            "source_url": source_url,
            "ingestion_date": datetime.now(timezone.utc).isoformat(),
            "sha256": hashlib.sha256(content).hexdigest(),
            "size_bytes": len(content),
        })
        print(f"Saved {metric}: {destination}")

    manifest = output_dir / "ingestion_manifest.json"
    manifest.write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")
    print(f"Saved download metadata: {manifest}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    ingest(args.output_dir)
