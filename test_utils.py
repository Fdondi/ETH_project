from contextlib import redirect_stderr
from io import StringIO
import sys
from typing import List, Set

import pytest

def extract_test_files(test_lines: List[str]) -> Set[str]:
    tests = set()
    for line in test_lines:
        if '::' not in line:
            continue
        file, _ = line.split('::', 1)
        tests.add(file)
    return tests

def collect_tests(pytest_args, test_estimate: int) -> Set[str]:
    collected_lines = []

    class CollectPlugin:
        def pytest_collection_modifyitems(self, session, config, items):
            for item in items:
                collected_lines.append(item.nodeid)

    # Run pytest in collection mode with the custom plugin
    pytest_local_args = ['--collect-only', '-q'] + pytest_args
    result = pytest.main(pytest_local_args, plugins=[CollectPlugin()])

    # Check if pytest ran successfully
    if result != 0:
        print(f"Pytest encountered errors, code: {result}")
    else:
        print("Pytest collection completed successfully.")

    return extract_test_files(collected_lines)



