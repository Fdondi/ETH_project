from collections import defaultdict
import json
import pygit2
import os
import pytest
from datetime import datetime
from pathlib import Path

from git_utils import get_all_commits, get_modified_lines, modifies_test_and_code
from test_utils import collect_tests, get_test_files

def process_repo(repo_name: str, refresh_tests = True):

    repo_path = Path('Repos',repo_name)
    if not os.path.exists(repo_path):
        raise ValueError(f"Directory {repo_path} does not exist")

    repo = pygit2.Repository(repo_path)

    data_path = Path('data', repo_name)

    commit_walker = get_all_commits(repo)

    # first commit
    commit = next(commit_walker)

    repo.checkout_tree(commit.tree)
    repo.set_head(commit.id)

    for next_commit in commit_walker:
        print(f"Processing commit {commit.id}")

        test_file_path = Path('test_files.json')
        # point pytest to the repo
        pytest_args = ['--continue-on-collection-errors', '-p myplugin', repo_path]
        collect_tests(test_file_path, pytest_args)

        test_files = get_test_files(test_file_path)

        # skip commits that don't look like bugfixes
        if not modifies_test_and_code(repo.diff(commit, next_commit), test_files):
            print(f"Skipping commit {commit.id}")
            commit = next_commit
            continue

        # Get modified functions and test files
        modified_lines = get_modified_lines(repo.diff(commit, next_commit))
        # save to the file for conftest.py to read
        tmp_to_track = Path("to_track.json")
        with open(tmp_to_track, 'w') as f:
            json.dump(modified_lines["old"], f)

        # Run pytest on parent commit
        # note we might have run on this commit already; but we have now new modified functions!
        print(f"Running tests on parent: {commit.id} ({datetime.fromtimestamp(commit.commit_time)})")
        pytest.main(pytest_args)

        data_path_commit = data_path.joinpath(f'commit_{commit.id}')
        
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
    process_repo('gradio')
