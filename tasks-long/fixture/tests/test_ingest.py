import os
import unittest

from ingest import csvload, logparse, reports

LINE = "2025-03-04T10:22:31Z GET /v2/orders 503 1532 12ms"


class TestIngest(unittest.TestCase):
    def test_parse_line(self):
        e = logparse.parse_line(LINE)
        self.assertEqual((e["path"], e["status"], e["bytes"], e["ms"]), ("/v2/orders", 503, 1532, 12))
        self.assertIsNone(logparse.parse_line("garbage"))

    def test_reports_on_sample(self):
        entries = [logparse.parse_line(LINE), logparse.parse_line(LINE.replace("503", "200"))]
        self.assertEqual(reports.status_counts(entries), {200: 1, 503: 1})
        self.assertEqual(reports.bytes_by_path(entries), {"/v2/orders": 3064})
        self.assertEqual(reports.slow_requests(entries, 11), entries)
        self.assertEqual(reports.top_paths(entries, 1), [("/v2/orders", 2)])

    def test_sample_files_parse(self):
        entries = list(logparse.read_log(os.path.join("logs", "access.log")))
        self.assertGreater(len(entries), 1000)
        rows = list(csvload.read_shipments(os.path.join("data", "shipments.csv")))
        self.assertGreater(len(rows), 100)
        self.assertTrue(reports.cost_by_carrier(rows))


if __name__ == "__main__":
    unittest.main()
