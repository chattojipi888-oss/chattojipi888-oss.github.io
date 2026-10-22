import csv
import tempfile
import unittest
from pathlib import Path
from state_change_extract import extract_changes, export_changes


class TestStateChangeExtract(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.input = Path(temp.name) / "input.csv"
        self.output = Path(temp.name) / "output.csv"

    def parse(self, text, **kwargs):
        self.input.write_bytes(text if isinstance(text, bytes) else text.encode("utf-8"))
        return extract_changes(self.input, **kwargs)

    def test_change_and_first_observation(self):
        result = self.parse("timestamp,status\n2026-10-18T09:00:00+09:00,RUNNING\n2026-10-18T09:00:10+09:00,RUNNING\n2026-10-18T09:00:20+09:00,STOPPED\n")
        self.assertEqual([status for _, status in result], ["RUNNING", "STOPPED"])
        self.assertEqual(result[1][0].isoformat(), "2026-10-18T00:00:20+00:00")

    def test_unknown_retained(self):
        rows = "timestamp,status\n2026-10-18T09:00:00+09:00,RUNNING\n2026-10-18T09:00:10+09:00,UNKNOWN\n2026-10-18T09:00:20+09:00,RUNNING\n"
        self.assertEqual([status for _, status in self.parse(rows)], ["RUNNING", "UNKNOWN", "RUNNING"])

    def test_one_observation(self):
        self.assertEqual(len(self.parse("timestamp,status\n2026-10-18T09:00:00+09:00,STOPPED\n")), 1)

    def test_equivalent_utc_offsets(self):
        rows = "timestamp,status\n2026-10-18T09:00:00+09:00,RUNNING\n2026-10-18T00:00:10+00:00,STOPPED\n"
        self.assertEqual(len(self.parse(rows)), 2)

    def test_duplicate_time(self):
        with self.assertRaisesRegex(ValueError, "increase"):
            self.parse("timestamp,status\n2026-10-18T09:00:00+09:00,RUNNING\n2026-10-18T09:00:00+09:00,STOPPED\n")

    def test_reverse_time(self):
        with self.assertRaisesRegex(ValueError, "increase"):
            self.parse("timestamp,status\n2026-10-18T09:00:10+09:00,RUNNING\n2026-10-18T09:00:00+09:00,STOPPED\n")

    def test_missing_timezone(self):
        with self.assertRaisesRegex(ValueError, "offset"):
            self.parse("timestamp,status\n2026-10-18T09:00:00,RUNNING\n")

    def test_invalid_timestamp(self):
        with self.assertRaisesRegex(ValueError, "timestamp"):
            self.parse("timestamp,status\nnot-a-time,RUNNING\n")

    def test_invalid_status(self):
        with self.assertRaisesRegex(ValueError, "status"):
            self.parse("timestamp,status\n2026-10-18T09:00:00+09:00,FAILED\n")

    def test_bad_header(self):
        with self.assertRaisesRegex(ValueError, "header"):
            self.parse("time,status\n2026-10-18T09:00:00+09:00,RUNNING\n")

    def test_empty_rows(self):
        with self.assertRaisesRegex(ValueError, "observations"):
            self.parse("timestamp,status\n")

    def test_extra_column(self):
        with self.assertRaisesRegex(ValueError, "invalid row"):
            self.parse("timestamp,status\n2026-10-18T09:00:00+09:00,RUNNING,extra\n")

    def test_empty_cell(self):
        with self.assertRaisesRegex(ValueError, "invalid row"):
            self.parse("timestamp,status\n2026-10-18T09:00:00+09:00,\n")

    def test_blank_line_rejected(self):
        with self.assertRaisesRegex(ValueError, "invalid row"):
            self.parse("timestamp,status\n2026-10-18T09:00:00+09:00,RUNNING\n\n2026-10-18T09:00:10+09:00,STOPPED\n")

    def test_bom(self):
        self.assertEqual(len(self.parse(b"\xef\xbb\xbftimestamp,status\n2026-10-18T09:00:00+09:00,RUNNING\n")), 1)

    def test_malformed_quote(self):
        with self.assertRaises(csv.Error):
            self.parse('timestamp,status\n2026-10-18T09:00:00+09:00,"RUNNING\n')

    def test_size_limit(self):
        with self.assertRaisesRegex(ValueError, "large"):
            self.parse("timestamp,status\n", max_bytes=3)

    def test_export_new_file(self):
        self.input.write_text("timestamp,status\n2026-10-18T09:00:00+09:00,RUNNING\n2026-10-18T09:00:10+09:00,RUNNING\n2026-10-18T09:00:20+09:00,STOPPED\n", encoding="utf-8")
        self.assertEqual(export_changes(self.input, self.output), 2)
        with self.output.open(encoding="utf-8", newline="") as f:
            rows = list(csv.reader(f))
        self.assertEqual(rows[0], ["timestamp", "status"])
        self.assertEqual(rows[1][0], "2026-10-18T00:00:00+00:00")
        self.assertEqual(rows[2][1], "STOPPED")

    def test_export_no_overwrite(self):
        self.input.write_text("timestamp,status\n2026-10-18T09:00:00+09:00,RUNNING\n", encoding="utf-8")
        self.output.write_text("keep", encoding="utf-8")
        with self.assertRaises(FileExistsError):
            export_changes(self.input, self.output)
        self.assertEqual(self.output.read_text(encoding="utf-8"), "keep")

    def test_export_no_same_path(self):
        self.input.write_text("timestamp,status\n2026-10-18T09:00:00+09:00,RUNNING\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "differ"):
            export_changes(self.input, self.input)


if __name__ == "__main__":
    unittest.main()
