import json
from pathlib import Path
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


def get_issues(owner, repo, labels, state, per_page, page, token):
    url = f'https://api.github.com/repos/{owner}/{repo}/issues'
    headers = {'Authorization': f'token {token}'}
    params = {
        'state': state,
        'labels': labels,
        'per_page': per_page,
        'page': page,
    }
    return call_with_rate_limit(url, headers, params)


def get_all_issues(owner, repo, labels, state, token):
    per_page = 100
    page = 1
    while True:
        issues_json = get_issues(owner, repo, labels, state, per_page, page, token)
        if not isinstance(issues_json, list):
            print('Error fetching issues:', issues_json)
            break
        if not issues_json:
            break
        for issue in issues_json:
            yield issue
        page += 1
    # Filter out pull requests


def get_issue_timeline(owner, repo, issue_number, token):
    url = f'https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}/timeline'
    headers = {
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.mockingbird-preview+json'
    }
    per_page = 100
    page = 1
    while True:
        params = {'per_page': per_page, 'page': page}
        events = call_with_rate_limit(url, headers, params)
        if not isinstance(events, list):
            print('Error fetching timeline:', events)
            break
        if not events:
            break
        for event in events:
            yield event
        page += 1


def get_commits_from_issue_timeline(owner, repo, issue_number, token):
    for event in get_issue_timeline(owner, repo, issue_number, token):
        if event.get('event') == 'closed' and 'commit_id' in event and event['commit_id'] is not None:
            yield event['commit_id']
        elif event.get('event') == 'cross-referenced':
            source = event.get('source', {})
            if source.get('type') == 'commit' and 'commit' in source:
                yield source['commit']['sha']


def get_commit_files(owner, repo, sha, token):
    url = f'https://api.github.com/repos/{owner}/{repo}/commits/{sha}'
    headers = {'Authorization': f'token {token}'}
    commit_data = call_with_rate_limit(url, headers, {})
    if not commit_data or 'files' not in commit_data:
        print(f'Error fetching commit {sha}: {commit_data}')
        return None
    return commit_data["files"]


def main():
    token = "<token>"
    X = 10
    Y = 100
    repository_count = 0
    issue_count = 0
    commit_count = 0
    file_count = 0
    print('Fetching repositories...')
    for repo in get_repositories_from_X_to_Y(X, Y, language='Python', sort='stars', order='desc', token=token):
        print(f"until now: {repository_count=}, {issue_count=}, {commit_count=}, {file_count=}")
        repository_count += 1
        owner = repo['owner']['login']
        repo_name = repo['name']
        print(f'\nProcessing repository #{repository_count}: {owner}/{repo_name}')
        for issue in get_all_issues(owner, repo_name, labels='bug', state='closed', token=token):
            issue_count += 1
            print(f'\nProcessing issue #{issue_count}: {issue["title"]}')
            for sha in get_commits_from_issue_timeline(owner, repo_name, issue['number'], token):
                commit_count += 1
                print(f'Fetching commit #{commit_count}: {sha}...')
                files = get_commit_files(owner, repo_name, sha, token)
                if not files:
                    continue
                for file in files:
                    filename = file['filename']
                    if 'test' in filename.lower():
                        file_count += 1
                        print(f'File #{file_count}: {filename}')
                        print(f'Commit {sha} in issue #{issue["number"]} changes file {filename}')
                        # Save the data to a file
                        path = Path('data') / owner / repo_name / f'issue_{issue["number"]}' / sha
                        path.mkdir(parents=True, exist_ok=True)
                        with open(path / "files.txt", 'w') as f:
                            f.write(str(files))

if __name__ == '__main__':
    main()
