from collections import defaultdict
from datetime import datetime
import pdb
from typing import Dict, Generator, List, Tuple, Set
import pygit2
from itertools import islice


def get_all_commits(repo: pygit2.Repository) -> pygit2.Walker:
    return repo.walk(repo.head.target, pygit2.GIT_SORT_TIME | pygit2.GIT_SORT_REVERSE)


def skip_first(iterable):
    return islice(iterable, 1, None)

def modifies_test_and_code(patches, test_files: Set[str]) -> bool:
    commit_modifies_test = False
    commit_modifies_code = False
    print('test_files:', test_files)
    for patch in patches:
        file = patch.delta.new_file.path
        if not file.endswith('.py'):
            continue
        if file in test_files:
            commit_modifies_test = True
            print(f'modifies test file {file}')
        else:
            commit_modifies_code = True
            print(f'modifies code file {file}')
        if commit_modifies_test and commit_modifies_code:
            print('FOUND!')
            return True
    return False

def get_commits_that_modify_test_and_code(repo: pygit2.Repository, test_files: List[str]) -> Generator:
    # skip first as wer're only interested in bugfixes
    print('test_files:', test_files)
    for commit in skip_first(get_all_commits(repo)):
        print(f'Commit {commit.id}')
        if modifies_test_and_code(repo.diff(commit.parents[0], commit), test_files):
                yield commit

# ========================================================================================================

def get_modified_lines(diff) -> Dict[str, Dict[str, List[int]]]:
    """
    Returns due ditionaries
    with the same keys, the functions
    values are the filename they find themselves in
    """
    modified_lines: Dict[str, Dict[str, List[int]]] = {"old": defaultdict(list), "new": defaultdict(list)}
   
    for patch in diff:
        new_file = patch.delta.new_file.path
        old_file = patch.delta.old_file.path
        if not new_file.endswith('.py'):
            continue

        # Go through the patch hunks (which contain the changes)
        for hunk in patch.hunks:
            for line in hunk.lines:
                # Collect both added and removed lines (lines that have either a new or old line number)
                if line.old_lineno != -1:
                    modified_lines["old"][old_file].append(line.old_lineno)
                if line.new_lineno != -1:
                    modified_lines["new"][new_file].append(line.new_lineno)

    return modified_lines