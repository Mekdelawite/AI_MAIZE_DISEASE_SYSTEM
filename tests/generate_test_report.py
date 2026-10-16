import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORT_DIR = ROOT / "tests" / "reports"
REPORT_FILE = REPORT_DIR / "backend_test_report.txt"


def main():
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        errors="replace",
    )

    output = (result.stdout or "").strip()
    if result.stderr:
        output += "\n" + result.stderr.strip()

    if result.returncode == 0:
        status = "PASSED"
    elif result.returncode == 5:
        status = "NO TESTS COLLECTED"
    else:
        status = "FAILED OR TEST ERROR"

    report = f"""AI-BASED MAIZE DISEASE DETECTION SYSTEM
BACKEND AUTOMATED TEST REPORT
========================================
Generated: {datetime.now().astimezone().isoformat(timespec='seconds')}
Project: {ROOT}
Command: python -m pytest -q
Overall status: {status}
Pytest exit code: {result.returncode}

1. EXPLANATION OF TEST RESULTS
------------------------------
PASSED: Test assertions succeeded.
FAILED: Actual behavior did not match an expected result.
ERROR: A test could not complete because of a setup or execution problem.
SKIPPED: A test was intentionally not run.

2. PURPOSE OF BACKEND TESTING
-----------------------------
Automated tests check the backend behavior covered by the test suite.
Depending on the tests present, this may include authentication,
database operations, access control, image validation, security
limits, advisory behavior, and offline synchronization.

Passing tests provide evidence for the behaviors tested. They do
not prove the entire application is bug-free or production-ready.

3. ACTUAL PYTEST OUTPUT
----------------------
{output or '(No output captured.)'}

4. CONCLUSION
-------------
{status}. Review the actual pytest output above for the test counts
and any failures or errors.

This report records the results of this particular test run.
"""

    REPORT_FILE.write_text(report, encoding="utf-8")
    print(output)
    print("\nReport saved to:", REPORT_FILE)
    print("Pytest exit code:", result.returncode)
    raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
