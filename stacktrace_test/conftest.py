# conftest.py
import os
import sys
import threading
from collections import Counter

lock = threading.Lock()

src_root = os.path.join(os.getcwd(),"src")

file_info = {}
# for each file with .py extesnion under the current directory
def collect_files(folder):
    for root, dirs, files in os.walk(folder):
        for file in files:
            if file.endswith(".py"):
                filename = os.path.join(root, file)
                file_info[filename] = [{"line": line, "vars":[], "function": None} for line in open(os.path.join(root, file))]
        for dir in dirs:
            collect_files(dir)

collect_files(src_root)

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
    
    #function_name = code.co_name
    lineno = frame.f_lineno
    local_vars = frame.f_locals.copy()

    with lock:
        file_info[filename][lineno-1]["vars"].append(local_vars)
        #line_info["function"] = function_name

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

def process_tracing_data():
    # print file_info in an organized manner
    for file, file_data in file_info.items():
        print(f"File: {file}")
        for i, line in enumerate(file_data):
            print(f"Line {i+1}: {line['line']} executed {len(line["vars"])} times")
            for vars in line['vars']:
                print(vars)
            print("")
