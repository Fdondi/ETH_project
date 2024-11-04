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

def my_checkout(repo, commit):
    # Reset index and working directory to the target commit
    repo.reset(commit.id, pygit2.GIT_RESET_HARD)
    # Perform the forced checkout
    repo.checkout_tree(commit.tree, strategy=pygit2.GIT_CHECKOUT_FORCE)
    # Update HEAD to point to the new commit
    repo.set_head(commit.id)

def process_repo(repo_name: str, skip_existing = True, start_at = 0):

    repo_path = Path('Repos',repo_name, "code")
    if not os.path.exists(repo_path):
        raise ValueError(f"Directory {repo_path} does not exist")

    repo = pygit2.Repository(repo_path)
    main_branch = repo.branches['main']
    # Check out the latest commit on main and reset to it
    repo.checkout(main_branch.name)
    main_commit = main_branch.peel()
    my_checkout(repo, main_commit)

    data_path = Path('data', repo_name)

    # point pytest to the repo
    pytest_args = ['--continue-on-collection-errors', '--rootdir', str(repo_path), str(repo_path)]
    pytest_args_run = ['-p myplugin'] + pytest_args

    commit_walker = get_all_commits(repo)

    # first commit
    commit = next(commit_walker)

    print(f"Processing repo {repo_name} starting with {commit}  (at {datetime.fromtimestamp(commit.commit_time)})")
    my_checkout(repo, commit)

    test_files = set()

    # ensure test discovery is done at the start and at least every 10 commits, just in case
    remaining_before_test_discovery = 0
    max_test_discovery_interval = 10

    skipped_no_parent = []

    for next_commit in commit_walker:
        if commit.commit_time < start_at:
            commit = next_commit
            continue

        if not commit in next_commit.parents:
            print(f"{commit.id} (at {datetime.fromtimestamp(commit.commit_time)}), is not the parent of {next_commit.id} (at {datetime.fromtimestamp(next_commit.commit_time)}); skipping")
            skipped_no_parent.append((commit.id, next_commit.id))
            commit = next_commit
            continue

        print(f"Processing commit {commit.id} (at {datetime.fromtimestamp(commit.commit_time)})")

        # Note: Positive and negative examples are stored under the commit BEFORE the change
        # So the positive example is actually relative to the FOLLWING commit.  
        data_path_commit = data_path.joinpath(f'{commit.id}')

        if skip_existing and data_path_commit.exists():
            print(f"Data for commit {commit.id} already exists; skipping")
            commit = next_commit
            continue

        my_checkout(repo, commit)

        diff = repo.diff(commit, next_commit)
        new_py_files = [delta.new_file.path for delta in diff.deltas if delta.status == pygit2.GIT_DELTA_ADDED and delta.new_file.path.endswith('.py')]
        if new_py_files or remaining_before_test_discovery <= 0:
            n_test_estimate = 0.9 * len(test_files) + 0.5 * len(new_py_files)
            print(f"Renewing test discovery as files {new_py_files} were added; expecting {n_test_estimate} tests")
            test_files = collect_tests(pytest_args, n_test_estimate)
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
        pytest.main(pytest_args_run)
        
        if Path('result.json').exists():
            data_path_commit.mkdir(parents=True, exist_ok=True)
            Path('result.json').rename(data_path_commit.joinpath('negative_example.json'))
        else:
            print("No result found for parent {commit.id}!")

        # ==========================================
        commit = next_commit

        # Run pytest on current commit
        my_checkout(repo, commit)

        with open('to_track.json', 'w') as f:
            json.dump(modified_lines["new"], f)

        print(f"Running tests on new commit {commit.id} ({datetime.fromtimestamp(commit.commit_time)})")
        pytest.main(pytest_args_run)

        if Path('result.json').exists():
            data_path_commit.mkdir(parents=True, exist_ok=True)
            Path('result.json').rename(data_path_commit.joinpath('positive_example.json'))
        else:
            print("No result found for {commit.id}!")

    print(len(skipped_no_parent))
    print(skipped_no_parent[:100])

if __name__ == "__main__":
    process_repo('requests', start_at=datetime(2019, 1, 1).timestamp())
