# conftest.py
import json
import linecache
import os
import pickle
import sys
import threading
from collections import Counter, defaultdict
from pathlib import Path
from typing import List

import pytest

lock = threading.Lock()

interesting_lines_list = json.load(open("to_track.json"))
# convert to set for faster lookup
interesting_lines = {filename: set(lines) for filename, lines in interesting_lines_list.items()}

print("Conftest.py has interesting files: ", interesting_lines.keys())

# indexed by file first, then line number
file_info = defaultdict(lambda: defaultdict(list))

"""
def pytest_collection_modifyitems(items):
    for item in items:
        # Convert the item nodeid (which contains the full test path) to a Path object
        item_path = Path(item.nodeid.split("::")[0])  # Get the file part of nodeid, strip the '::' part
        
        was_test_modified = any(item_path.match(str(path)) for path in interesting_lines.keys())

        target_timeout = 600 if was_test_modified else 10

        current_timeout = item.get_closest_marker('timeout')

        # set timeout if not already set or if the current timeout is significantly different from the target timeout
        if current_timeout is None or abs(current_timeout.args[0] - target_timeout) / target_timeout > 0.5:
            item.add_marker(pytest.mark.timeout(target_timeout))
"""

def represent_variable(var_name, var_value, is_init: bool):
    # Special handling for 'self' to check if it's partially initialized
    if is_init and var_name == 'self':
        return "<partially initialized object>"
    try:
        return repr(var_value)
    except Exception as e:
        return "<unrepresentable object> (error: {e})"


def trace_function(frame, event, arg):
    if event not in ['line','call']:
        return trace_function
    
    # Only trace your application code
    code = frame.f_code
    # also filter function=<module> which is the main function
    if code.co_name == "<module>":
        return trace_function

    filename = code.co_filename
    file_path = Path(filename)
    lineno = frame.f_lineno

    is_init = event == 'call' and code.co_name == '__init__'

    for file, lines  in interesting_lines.items():
        if file_path.match(file) and lineno in lines:
            local_vars = { var_name: represent_variable(var_name, var_value, is_init) for var_name, var_value in frame.f_locals.items() }
            print(f"Found {filename}:{lineno} {code.co_name} {local_vars}")
            with lock:
                file_info[filename][lineno].append(local_vars)

    return trace_function

def pytest_sessionstart(session):
    sys.settrace(trace_function)
    threading.settrace(trace_function)
    print("Tracing started.")

def pytest_sessionfinish(session, exitstatus):
    sys.settrace(None)
    threading.settrace(None)
    print("Tracing stopped.")
    process_tracing_data(debug = True)

def process_tracing_data(debug = False):
    # save result to a file
    with open('result.json', 'w') as f:
        json.dump(file_info, f)
    # debug print
    if debug:
        print("Tracing result:")
        for file, file_data in file_info.items():
            print(f"File: {file}")
            for line_no, line_vars in enumerate(file_data):
                print(f"Line {line_no}: executed {len(line_vars)} times")
                for var in line_vars:
                    print(var)
                print("")
