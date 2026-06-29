import unittest
from unittest.mock import patch

from connectors import sqlws


class SqlwsTimeoutTests(unittest.TestCase):
    def test_normalize_timeout_secs_handles_common_inputs(self):
        self.assertEqual(sqlws._normalize_timeout_secs(None), 0)
        self.assertEqual(sqlws._normalize_timeout_secs(0), 0)
        self.assertEqual(sqlws._normalize_timeout_secs("30"), 30)
        self.assertEqual(sqlws._normalize_timeout_secs(-5), 0)
        self.assertEqual(sqlws._normalize_timeout_secs("abc"), 0)
        self.assertEqual(sqlws._normalize_timeout_secs(sqlws.MAX_TIMEOUT_SECS + 10), sqlws.MAX_TIMEOUT_SECS)

    def test_execute_query_returns_cancelled_when_cancel_check_is_true(self):
        class FakeCursor:
            def __init__(self):
                self.description = None

            def execute(self, *args, **kwargs):
                self.executed = True

            def fetchall(self):
                return []

        class FakeConn:
            def __init__(self):
                self.cursor_obj = FakeCursor()

            def cursor(self):
                return self.cursor_obj

            def close(self):
                return None

        fake_conn = FakeConn()

        def _fake_connect(_env):
            return fake_conn

        with patch.object(sqlws, "_connect", side_effect=_fake_connect):
            result = sqlws.execute_query("HCM", "SELECT 1 FROM dual", timeout_secs=5, cancel_check=lambda: True)

        self.assertFalse(result["blocked"])
        self.assertEqual(result["row_count"], 0)
        self.assertTrue(result["cancelled"])
        self.assertEqual(result["status"], "cancelled")
        self.assertIn("cancelled", " ".join(result["warnings"]).lower())

    def test_execute_query_handles_timeout_property_errors(self):
        class FakeCursor:
            def __init__(self):
                self._call_timeout = None
                self.description = None

            @property
            def callTimeout(self):
                return self._call_timeout

            @callTimeout.setter
            def callTimeout(self, value):
                raise RuntimeError("unsupported")

            def execute(self, *args, **kwargs):
                self.executed = True

            def fetchall(self):
                return []

        class FakeConn:
            def __init__(self):
                self.cursor_obj = FakeCursor()

            def cursor(self):
                return self.cursor_obj

            def close(self):
                return None

        fake_conn = FakeConn()

        def _fake_connect(_env):
            return fake_conn

        with patch.object(sqlws, "_connect", side_effect=_fake_connect):
            result = sqlws.execute_query("HCM", "SELECT 1 FROM dual", timeout_secs=5)

        self.assertFalse(result["blocked"])
        self.assertEqual(result["row_count"], 0)
        self.assertEqual(result["timed_out"], False)
        self.assertIn("Execution timeout is not supported", " ".join(result["warnings"]))


if __name__ == "__main__":
    unittest.main()
