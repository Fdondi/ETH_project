from collections import defaultdict
from pathlib import Path
import subprocess
import os
from typing import Dict, List

def get_test_names(test_file_path: Path) -> Dict:
    tests = defaultdict(list)
    with open(test_file_path, 'r') as f:
        for line in f:
            if '::' not in line:
                continue
            file, test = line.split('::', 1)
            tests[file].append(test)
    return tests

def get_test_files(test_file_path: Path) -> List:
    tests = set()
    with open(test_file_path, 'r') as f:
        for line in f:
            if '::' not in line:
                continue
            file, _ = line.split('::', 1)
            tests.add(file)
    return list(tests)

def collect_tests(output_file, pytest_args):
    # Construct the pytest command
    pytest_command = ['python', '-m', 'pytest', '--collect-only', '--quiet'] + pytest_args

    # Open the output file and run pytest
    with open(output_file, 'w') as f:
        result = subprocess.run(
            pytest_command,
            stdout=f,  # Redirect stdout to the output file
            stderr=subprocess.PIPE  # Capture stderr separately
        )
        # Print stderr to actual stdout
        if result.stderr:
            print(result.stderr.decode())

    # Check if pytest ran successfully
    if result.returncode != 0:
        print(f"Pytest encountered errors. Check {output_file} for details.")
    else:
        print(f"Pytest collection completed successfully. Output saved to {output_file}.")



