# conftest.py
import json
import linecache
import os
import sys
import threading
from collections import Counter, defaultdict
from pathlib import Path

import pytest

lock = threading.Lock()

src_root = os.path.join(os.getcwd(),"src")

interesting_lines_list = json.load(open("to_track.json"))
# convert to set for faster lookup
interesting_lines = {filename: set(lines) for filename, lines in interesting_lines_list.items()}

print("Conftest.py has interesting files: ", interesting_lines.keys())

# indexed by file first, then line number
file_info = defaultdict(lambda: defaultdict(dict))


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


def trace_function(frame, event, arg):
    if event not in ['line','call']:
        return trace_function
    
    # Only trace your application code
    code = frame.f_code
    filename = code.co_filename
    if not filename.startswith(src_root):
        return trace_function
    # also filter function=<module> which is the main function
    if code.co_name == "<module>":
        return trace_function
    if not filename in interesting_lines:
        return trace_function
    
    #function_name = code.co_name
    lineno = frame.f_lineno
    if lineno not in interesting_lines[filename]:
        return trace_function

    local_vars = frame.f_locals.copy()

    with lock:
        file_info[filename][lineno] = local_vars

    return trace_function

def pytest_sessionstart(session):
    sys.settrace(trace_function)
    threading.settrace(trace_function)
    print("Tracing started.")

def pytest_sessionfinish(session, exitstatus):
    sys.settrace(None)
    threading.settrace(None)
    print("Tracing stopped.")
    process_tracing_data()

def process_tracing_data(debug = False):
    # save result to a file
    with open('result.json', 'w') as f:
        json.dump(file_info, f)
    # debug print
    if debug:
        for file, file_data in file_info.items():
            print(f"File: {file}")
            for i, line in enumerate(file_data):
                print(f"Line {i+1}: {line['line']} executed {len(line['vars'])} times")
                for vars in line['vars']:
                    print(vars)
                print("")
