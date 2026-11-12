import io
import json
import os
import tempfile
import unittest

from cli.main import main
from ingest import reports
from store.registry import Registry


class TestErrorRate(unittest.TestCase):
    def test_values(self):
        e = lambda s: {"status": s}
        self.assertEqual(reports.error_rate([]), 0.0)
        self.assertEqual(reports.error_rate([e(200), e(404), e(499)]), 0.0)
        self.assertEqual(reports.error_rate([e(500), e(200)]), 0.5)
        self.assertEqual(reports.error_rate([e(503), e(200), e(200)]), 0.3333)
        self.assertEqual(reports.error_rate([e(500), e(503), e(599), e(600), e(200), e(200), e(200)]), 0.5714)

    def test_cli(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "x.log")
            with open(path, "w") as f:
                f.write("2025-03-04T10:00:01Z GET /a 200 10 5ms\n2025-03-04T10:00:30Z GET /b 503 10 5ms\n"
                        "2025-03-04T10:00:31Z GET /b 200 10 5ms\n2025-03-04T10:00:32Z GET /b 500 10 5ms\n")
            out = io.StringIO()
            rc = main(["error-rate", path], registry=Registry(), out=out)
            self.assertEqual(rc, 0)
            self.assertEqual(json.loads(out.getvalue()), {"error_rate": 0.5})


if __name__ == "__main__":
    unittest.main()
