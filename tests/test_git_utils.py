import pygit2
from ..git_utils import get_modified_functions

# Test the get_modified_functions function
def test_get_modified_functions():
    repo = pygit2.Repository("test_repo")

    head_commit = repo.head.peel(pygit2.Commit)
    
    modified_functions = get_modified_functions(repo, head_commit)
    assert modified_functions == {"f"}