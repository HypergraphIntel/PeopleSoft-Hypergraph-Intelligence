import tempfile
import unittest
from pathlib import Path

from connectors import sqlmask


class SqlMaskTests(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self._orig_db_path = sqlmask.DB_PATH
        sqlmask.DB_PATH = Path(self._tmpdir.name) / "test_vault.db"

    def tearDown(self):
        sqlmask.DB_PATH = self._orig_db_path
        self._tmpdir.cleanup()

    def test_masking_is_deterministic(self):
        t1 = sqlmask.mask_value("EMPLID", "12345678")
        t2 = sqlmask.mask_value("EMPLID", "12345678")
        self.assertEqual(t1, t2)
        self.assertTrue(t1.startswith("EMP_"))

    def test_different_values_produce_different_tokens(self):
        t1 = sqlmask.mask_value("EMPLID", "11111111")
        t2 = sqlmask.mask_value("EMPLID", "22222222")
        self.assertNotEqual(t1, t2)

    def test_non_sensitive_column_passes_through(self):
        value = sqlmask.mask_value("LASTUPDDTTM", "2026-07-04T10:00:00")
        self.assertEqual(value, "2026-07-04T10:00:00")

    def test_none_passes_through(self):
        self.assertIsNone(sqlmask.mask_value("EMPLID", None))

    def test_reveal_round_trip(self):
        token = sqlmask.mask_value("EMPLID", "99999999")
        result = sqlmask.reveal(token)
        self.assertTrue(result["found"])
        self.assertEqual(result["real_value"], "99999999")
        self.assertEqual(result["category"], "EMP")

    def test_reveal_unknown_token(self):
        result = sqlmask.reveal("EMP_deadbeef")
        self.assertFalse(result["found"])

    def test_mask_result_masks_sensitive_columns_only(self):
        fake_result = {
            "columns": [
                {"name": "EMPLID", "type": "VARCHAR2"},
                {"name": "NAME", "type": "VARCHAR2"},
                {"name": "LASTUPDDTTM", "type": "DATE"},
            ],
            "rows": [
                {"EMPLID": "12345678", "NAME": "Bob Smith", "LASTUPDDTTM": "2026-01-01T00:00:00"},
                {"EMPLID": "12345678", "NAME": "Bob Smith", "LASTUPDDTTM": "2026-02-01T00:00:00"},
            ],
            "row_count": 2,
        }
        masked = sqlmask.mask_result(fake_result)

        # Same real EMPLID across rows must mask to the same token.
        self.assertEqual(masked["rows"][0]["EMPLID"], masked["rows"][1]["EMPLID"])
        self.assertTrue(masked["rows"][0]["EMPLID"].startswith("EMP_"))
        self.assertTrue(masked["rows"][0]["NAME"].startswith("PERSON_"))
        # Non-sensitive column passes through unchanged.
        self.assertEqual(masked["rows"][0]["LASTUPDDTTM"], "2026-01-01T00:00:00")
        # Original input must not be mutated.
        self.assertEqual(fake_result["rows"][0]["EMPLID"], "12345678")

    def test_category_for_column_handles_pattern_fallback(self):
        self.assertEqual(sqlmask.category_for_column("HOME_EMAIL_ADDR"), "EMAIL")
        self.assertIsNone(sqlmask.category_for_column("DESCR"))


if __name__ == "__main__":
    unittest.main()
