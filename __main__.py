from collections import defaultdict
import json
import random
import pygit2
import os
import pytest
from datetime import datetime
from pathlib import Path

from git_utils import get_all_commits, get_modified_lines, modifies_test_and_code
from test_utils import collect_tests

def process_repo(repo_name: str):

    repo_path = Path('Repos',repo_name, "code")
    if not os.path.exists(repo_path):
        raise ValueError(f"Directory {repo_path} does not exist")

    repo = pygit2.Repository(repo_path)

    data_path = Path('data', repo_name)

    test_file_path = Path('test_files.json')
    # point pytest to the repo
    pytest_args = ['--continue-on-collection-errors', '-p myplugin', '--rootdir', repo_path, repo_path]

    commit_walker = get_all_commits(repo)

    # first commit
    commit = next(commit_walker)

    repo.checkout_tree(commit.tree)
    repo.set_head(commit.id)

    test_files = set()

    # ensure test discovery is done at the start and at least every 10 commits, just in case
    remaining_before_test_discovery = 0
    max_test_discovery_interval = 10

    for next_commit in commit_walker:
        print(f"Processing commit {commit.id} (at {datetime.fromtimestamp(commit.commit_time)})")

        diff = repo.diff(commit, next_commit)
        new_files = [delta.new_file.path for delta in diff.deltas if delta.status == pygit2.GIT_DELTA_ADDED]
        if new_files or remaining_before_test_discovery <= 0:
            n_test_estimate = 0.9 * len(test_files) + 0.5 * len(new_files)
            print(f"Renewing test discovery as files {new_files} were added; expecting {n_test_estimate} tests")
            test_files = collect_tests(test_file_path, pytest_args, n_test_estimate)
            print(f"Discovered {len(test_files)} tests")
            remaining_before_test_discovery = max_test_discovery_interval

        # skip commits that don't look like bugfixes
        if not modifies_test_and_code(diff, test_files):
            print(f"Skipping commit {commit.id}")
            commit = next_commit
            continue

        # Get modified functions and test files
        modified_lines = get_modified_lines(diff)
        # save to the file for conftest.py to read
        tmp_to_track = Path("to_track.json")
        with open(tmp_to_track, 'w') as f:
            json.dump(modified_lines["old"], f)

        # Run pytest on parent commit
        # note we might have run on this commit already; but we have now new modified functions!
        print(f"Running tests on parent: {commit.id} ({datetime.fromtimestamp(commit.commit_time)})")
        pytest.main(pytest_args)

        data_path_commit = data_path.joinpath(commit.id)
        
        if Path('result.json').exists():
            data_path_commit.mkdir(parents=True, exist_ok=True)
            Path('result.json').rename(data_path_commit.joinpath('negative_example.json'))
        else:
            print("No result found for parent {commit.id}!")

        # ==========================================
        commit = next_commit

        # Run pytest on current commit
        repo.checkout_tree(commit.tree)
        repo.set_head(commit.id)

        with open('to_track.json', 'w') as f:
            json.dump(modified_lines["new"], f)

        print(f"Running tests on new commit {commit.id} ({datetime.fromtimestamp(commit.commit_time)})")
        pytest.main(pytest_args)

        if Path('result.json').exists():
            data_path_commit.mkdir(parents=True, exist_ok=True)
            Path('result.json').rename(data_path_commit.joinpath('positive_example.json'))
        else:
            print("No result found for {commit.id}!")


if __name__ == "__main__":
    process_repo('requests')
