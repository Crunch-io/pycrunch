import json
import subprocess
import time


class TestCrunchLakeWorkflow:
    def test_ping(self):
        command = ["cr.core.launch", "ping", "crunch-lake-ping", '--kwargs={"pong": "test-ping"}']
        p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        start = time.time()
        stdout = p.stdout.readline()
        stderr = p.stderr.readline()

        while time.time() - start < 30:
            try:
                assert "Workflow launched with id" in stderr.decode("utf-8")
            except AssertionError as assertion_error:
                if not time.time() - start < 30:
                    raise assertion_error
            time.sleep(.01)
