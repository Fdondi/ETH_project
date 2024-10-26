from collections import defaultdict
from pathlib import Path
import subprocess
import os
from typing import Dict, List, Set

from tqdm import tqdm

def extract_test_files(test_lines: List[str]) -> Set[str]:
    tests = set()
    for line in test_lines:
        if '::' not in line:
            continue
        file, _ = line.split('::', 1)
        tests.add(file)
    return tests

def collect_tests(output_file, pytest_args, test_estimate: int) -> Set[str]:
    # Construct the pytest command
    pytest_command = ['python', '-m', 'pytest', '--collect-only', '--quiet'] + pytest_args

    test_lines = []

    # Open the output file and run pytest
    with subprocess.Popen(
        pytest_command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    ) as proc, tqdm(unit="test", desc="Collecting Tests", total = test_estimate) as progress:
        # Read each line of stdout in real-time
        for line in proc.stdout:
            test_lines.append(line)
            if "PASSED" in line or "FAILED" in line:
                progress.update(1)  # Update for each test result line

        # Capture and save any errors
        stderr_output = proc.stderr.read()
        if stderr_output:
            print("ERROR: " + stderr_output)

        # Check if pytest ran successfully
        proc_returncode = proc.wait()
        if proc_returncode != 0:
            print(f"Pytest encountered errors. See above for details.")
        else:
            print(f"Pytest collection completed successfully.")

    return extract_test_files(test_lines)



