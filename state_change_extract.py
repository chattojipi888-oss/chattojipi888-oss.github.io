"""Extract observed state changes from periodic timestamp,status CSV logs.

Diagnostic example only. A recorded change time is an observation time, not
necessarily the instant the equipment changed state.
"""
import csv
from datetime import datetime, timezone
from pathlib import Path

ALLOWED = {"RUNNING", "STOPPED", "UNKNOWN"}


def extract_changes(path, max_bytes=1_048_576):
    """Return (UTC datetime, status) for first observation and each change."""
    if max_bytes <= 0:
        raise ValueError("max_bytes must be positive")
    source = Path(path)
    if source.stat().st_size > max_bytes:
        raise ValueError("input file too large")
    changes = []
    previous_time = None
    previous_status = None
    with source.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.reader(stream, strict=True)
        if next(reader, None) != ["timestamp", "status"]:
            raise ValueError("expected exact timestamp,status header")
        for row in reader:
            if len(row) != 2 or not all(cell.strip() for cell in row):
                raise ValueError(f"invalid row at physical line {reader.line_num}")
            stamp, status = row
            if status not in ALLOWED:
                raise ValueError(f"invalid status at physical line {reader.line_num}")
            try:
                moment = datetime.fromisoformat(stamp)
            except ValueError as exc:
                raise ValueError(f"invalid timestamp at physical line {reader.line_num}") from exc
            if moment.tzinfo is None or moment.utcoffset() is None:
                raise ValueError("UTC offset required")
            moment = moment.astimezone(timezone.utc)
            if previous_time is not None and moment <= previous_time:
                raise ValueError("timestamps must strictly increase")
            if previous_status is None or status != previous_status:
                changes.append((moment, status))
            previous_time, previous_status = moment, status
    if previous_time is None:
        raise ValueError("no observations")
    return changes


def export_changes(input_path, output_path):
    """Write to a new output file; never overwrite an existing file."""
    source, destination = Path(input_path), Path(output_path)
    if source.resolve() == destination.resolve():
        raise ValueError("input and output must differ")
    changes = extract_changes(source)
    with destination.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["timestamp", "status"])
        for moment, status in changes:
            writer.writerow([moment.isoformat(), status])
    return len(changes)


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        raise SystemExit("Usage: python3 state_change_extract.py input.csv output.csv")
    print(f"observed events: {export_changes(sys.argv[1], sys.argv[2])}")
