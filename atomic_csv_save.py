"""Write a complete equipment-status CSV snapshot using a temporary file.

Educational example; not a concurrent-writer protocol or crash-durable database.
"""
import csv
import os
import tempfile
from datetime import datetime
from pathlib import Path


def write_snapshot(path, records):
    target = Path(path)
    fd, temp_path = tempfile.mkstemp(
        prefix=f".{target.name}.", suffix=".tmp", dir=target.parent
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as stream:
            writer = csv.writer(stream, lineterminator="\n")
            writer.writerow(["timestamp", "status"])
            for stamp, status in records:
                if (
                    not isinstance(stamp, datetime)
                    or stamp.tzinfo is None
                    or stamp.utcoffset() is None
                ):
                    raise ValueError("timestamp must be timezone-aware datetime")
                if status not in {"RUNNING", "STOPPED", "UNKNOWN"}:
                    raise ValueError("unexpected equipment status")
                writer.writerow([stamp.isoformat(timespec="seconds"), status])
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_path, target)
    except BaseException:
        try:
            os.unlink(temp_path)
        except FileNotFoundError:
            pass
        raise
