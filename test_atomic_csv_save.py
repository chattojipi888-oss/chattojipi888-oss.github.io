import csv
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path

from atomic_csv_save import write_snapshot


class SnapshotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "equipment.csv"
        self.when = datetime(2026, 10, 18, 19, 0, tzinfo=timezone(timedelta(hours=9)))

    def read_rows(self):
        with self.path.open(encoding="utf-8", newline="") as stream:
            return list(csv.DictReader(stream))

    def assert_no_temp_files(self):
        self.assertEqual([p for p in self.path.parent.iterdir() if p.suffix == ".tmp"], [])

    def test_new_file(self):
        write_snapshot(self.path, [(self.when, "RUNNING")])
        self.assertEqual(self.read_rows(), [{"timestamp": "2026-10-18T19:00:00+09:00", "status": "RUNNING"}])
        self.assert_no_temp_files()

    def test_overwrite_is_complete_snapshot(self):
        write_snapshot(self.path, [(self.when, "RUNNING"), (self.when, "STOPPED")])
        write_snapshot(self.path, [(self.when, "UNKNOWN")])
        self.assertEqual(len(self.read_rows()), 1)
        self.assertEqual(self.read_rows()[0]["status"], "UNKNOWN")
        self.assert_no_temp_files()

    def test_invalid_status_keeps_old_file(self):
        write_snapshot(self.path, [(self.when, "RUNNING")])
        before = self.path.read_bytes()
        with self.assertRaises(ValueError):
            write_snapshot(self.path, [(self.when, "STOPPED"), (self.when, "=HYPERLINK(1)")])
        self.assertEqual(self.path.read_bytes(), before)
        self.assert_no_temp_files()

    def test_naive_datetime_rejected(self):
        with self.assertRaises(ValueError):
            write_snapshot(self.path, [(datetime(2026, 10, 18, 19), "RUNNING")])
        self.assertFalse(self.path.exists())
        self.assert_no_temp_files()

    def test_generator_failure_keeps_old_file(self):
        write_snapshot(self.path, [(self.when, "RUNNING")])
        before = self.path.read_bytes()
        def broken():
            yield self.when, "STOPPED"
            raise RuntimeError("sensor read failed")
        with self.assertRaises(RuntimeError):
            write_snapshot(self.path, broken())
        self.assertEqual(self.path.read_bytes(), before)
        self.assert_no_temp_files()

    def test_empty_records_writes_only_header(self):
        write_snapshot(self.path, [])
        self.assertEqual(self.read_rows(), [])
        self.assertEqual(self.path.read_text(encoding="utf-8"), "timestamp,status\n")
        self.assert_no_temp_files()


if __name__ == "__main__":
    unittest.main()
