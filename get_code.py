import json
from pathlib import Path
import string
import requests
import time
import diskcache

cache = diskcache.Cache('cache_directory')

def wait_until(reset_time, buffer = 2):
    sleep_time = reset_time - int(time.time()) + buffer  # Add a 5-second buffer
    if sleep_time > 0:
        print(f'Rate limit exceeded. Sleeping for {sleep_time} seconds.')
        time.sleep(sleep_time)

# Function to check and handle rate limits
@cache.memoize(expire=86400)
def call_with_rate_limit(url, headers, params):
    while True:
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            return response.json()
        if (response.status_code == 403
            and 'X-RateLimit-Remaining' in response.headers
            and response.headers['X-RateLimit-Remaining'] == '0'):
                wait_until(int(response.headers['X-RateLimit-Reset']))
                continue
        print('Unknown error:', response.json())
        return None

def get_repositories(language, sort, order, per_page, page, token):
    url = 'https://api.github.com/search/repositories'
    headers = {'Authorization': f'token {token}'}
    params = {
        'q': f'language:{language}',
        'sort': sort,
        'order': order,
        'per_page': per_page,
        'page': page,
    }
    repos_json = call_with_rate_limit(url, headers, params)
    if not repos_json or 'items' not in repos_json:
        print(f"Error fetching repository {page=}: {repos_json}")
        return None
    return repos_json["items"]


def get_repositories_from_X_to_Y(X, Y, language='Python', sort='stars', order='desc', token=None):
    repos = []
    per_page = 100
    start_page = (X - 1) // per_page + 1
    end_page = (Y - 1) // per_page + 1
    for page in range(start_page, end_page + 1):
        items_json = get_repositories(language, sort, order, per_page, page, token)
        if items_json:
            repos.extend(items_json)
    # Now slice the list to get the correct range
    start_index = (X - 1) % per_page
    end_index = start_index + (Y - X + 1)
    repos = repos[start_index:end_index]
    return repos


def get_default_branch(owner, repo, token):
    """
    Retrieves the default branch of a repository.
    """
    url = f'https://api.github.com/repos/{owner}/{repo}'
    headers = {'Authorization': f'token {token}'} if token else {}
    repo_data = call_with_rate_limit(url, headers, {})
    if not repo_data or 'default_branch' not in repo_data:
        print(f'Error fetching default branch for {owner}/{repo}: {repo_data}')
        return 'main' # default to 'main' if the API call fails
    return repo_data['default_branch']

def get_commits_from_branch(owner, repo, branch, token):
    """
    Fetches commits from a repository's branch.
    """
    per_page = 100
    url = f'https://api.github.com/repos/{owner}/{repo}/commits'
    headers = {'Authorization': f'token {token}'} if token else {}
    params = {
        'sha': branch,
        'per_page': per_page,
        'page': 0,
    }
    while True:
        commits_json = call_with_rate_limit(url, headers, params)
        params['page'] += 1
        if not commits_json:
            return
        else:
            for commit in commits_json:
                yield commit['sha']


def get_commit_files(owner, repo, sha, token):
    url = f'https://api.github.com/repos/{owner}/{repo}/commits/{sha}'
    headers = {'Authorization': f'token {token}'}
    commit_data = call_with_rate_limit(url, headers, {})
    if not commit_data or 'files' not in commit_data:
        print(f'Error fetching commit {sha}: {commit_data}')
        return None
    return commit_data["files"]

def is_ascii(s):
    return all(c in string.printable for c in s)

def main():
    token = "<token>"
    X = 10
    Y = 100
    repository_count = 0
    commit_count = 0
    file_count = 0
    print('Fetching repositories...')
    for repo in get_repositories_from_X_to_Y(X, Y, language='Python', sort='stars', order='desc', token=token):
        print(f"until now: {repository_count=}, {commit_count=}, {file_count=}")
        repository_count += 1
        owner = repo['owner']['login']
        repo_name = repo['name']
        print(f'\nProcessing repository #{repository_count}: {owner}/{repo_name}')
        for sha in get_commits_from_branch(owner, repo_name, get_default_branch(owner,repo_name,token), token):
            print(f"until now: {repository_count=}, {commit_count=}, {file_count=}")
            commit_count += 1
            print(f'Fetching commit #{commit_count}: {sha}...')
            files = get_commit_files(owner, repo_name, sha, token)
            if not files:
                continue
            for file in files:
                filename = file['filename']
                print(f'Checking file {filename}...')
                if not is_ascii(filename):
                    print(f'File {filename} is not ASCII. Skipping...')
                    continue
                if 'test' in filename.strip().lower():
                    file_count += 1
                    print(f'File #{file_count}: Commit {sha} changes file {filename}')
                    # Save the data to a file
                    path = Path('data') / owner / repo_name / f'commit_{sha}' / sha
                    path.mkdir(parents=True, exist_ok=True)
                    with open(path / "files.json", 'w') as f:
                        json.dump(files, f, indent=4)

if __name__ == '__main__':
    main()
