def pytest_runtest_logreport(report):
    """The gating commands use pytest -q, which hides prints on success.

    The checkpoint log has to show the device, the clear color, the submit
    counters, and the framebuffer comparison. Echo the test's own stdout
    after capture is finished.
    """
    if report.when != "call" or not report.capstdout:
        return
    print(report.capstdout, end="" if report.capstdout.endswith("\n") else "\n")
