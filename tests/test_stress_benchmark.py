import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class StressBenchmarkTest(unittest.TestCase):
    def test_stress_benchmark_script_runs_small_scale_and_writes_report(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "stress.json"
            completed = subprocess.run(
                [sys.executable, "scripts/stress_benchmark.py", "--scale", "small", "--output", str(output)],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(payload["status"], "passed")
            self.assertEqual({item["algorithm"] for item in payload["results"]}, {"pagerank", "sssp", "kmeans"})


if __name__ == "__main__":
    unittest.main()
