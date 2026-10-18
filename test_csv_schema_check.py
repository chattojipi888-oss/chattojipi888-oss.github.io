"""python3 -B -m unittest -v test_csv_schema_check.py"""
import tempfile
import unittest
from pathlib import Path

from csv_schema_check import validate_csv


class TestCSVSchema(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "log.csv"

    def check(self, content, **kwargs):
        self.path.write_bytes(content.encode("utf-8") if isinstance(content, str) else content)
        return validate_csv(self.path, **kwargs)

    def test_normal(self):
        self.assertEqual(self.check("timestamp,status\n2026-01-01T00:00:00+09:00,RUNNING\n")[0]["status"], "RUNNING")

    def test_utf8_bom(self):
        self.assertEqual(len(self.check(b"\xef\xbb\xbftimestamp,status\nT,RUNNING\n")), 1)

    def test_quoted_comma(self):
        self.assertEqual(self.check('timestamp,status\nT,"RUNNING,TEST"\n')[0]["status"], "RUNNING,TEST")

    def test_quoted_newline(self):
        self.assertEqual(self.check('timestamp,status\nT,"RUNNING\nTEST"\n')[0]["status"], "RUNNING\nTEST")

    def test_crlf(self):
        self.assertEqual(len(self.check("timestamp,status\r\nT,RUNNING\r\n")), 1)

    def test_extra_column(self):
        with self.assertRaisesRegex(ValueError, "列数不一致"):
            self.check("timestamp,status\nT,RUNNING,EXTRA\n")

    def test_missing_column(self):
        with self.assertRaisesRegex(ValueError, "列数不一致"):
            self.check("timestamp,status\nT\n")

    def test_duplicate_header(self):
        with self.assertRaisesRegex(ValueError, "重複"):
            self.check("timestamp,timestamp\nT,RUNNING\n")

    def test_wrong_order(self):
        with self.assertRaisesRegex(ValueError, "順序"):
            self.check("status,timestamp\nRUNNING,T\n")

    def test_empty(self):
        with self.assertRaisesRegex(ValueError, "ヘッダー"):
            self.check("")

    def test_header_only(self):
        with self.assertRaisesRegex(ValueError, "データ行"):
            self.check("timestamp,status\n")

    def test_empty_cell(self):
        with self.assertRaisesRegex(ValueError, "空欄"):
            self.check("timestamp,status\nT,\n")

    def test_malformed_quote(self):
        with self.assertRaisesRegex(ValueError, "解析できません"):
            self.check('timestamp,status\n"T,RUNNING\n')

    def test_max_rows(self):
        with self.assertRaisesRegex(ValueError, "行数上限"):
            self.check("timestamp,status\nT,RUNNING\nU,STOPPED\n", max_rows=1)

    def test_max_bytes(self):
        with self.assertRaisesRegex(ValueError, "サイズ上限"):
            self.check("timestamp,status\nT,RUNNING\n", max_bytes=5)

    def test_non_utf8(self):
        with self.assertRaisesRegex(ValueError, "解析できません"):
            self.check("timestamp,status\nT,停止\n".encode("cp932"))

    def test_invalid_expected(self):
        with self.assertRaisesRegex(ValueError, "指定が不正"):
            self.check("timestamp,status\nT,RUNNING\n", expected=("status","status"))


if __name__ == "__main__":
    unittest.main()
