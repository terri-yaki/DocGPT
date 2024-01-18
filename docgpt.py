import os
import getpass
import requests
from dotenv import load_dotenv
import time

# Load environment variables from .env file
load_dotenv()

def get_device_code():
    payload = {'client_id': os.getenv("GITHUB_CLIENT_ID"), 'scope': 'repo'}
    response = requests.post('https://github.com/login/device/code', data=payload)
    if response.status_code != 200:
        print(f"Error: {response.status_code}, {response.text}")
        return None
    return response.json()

def poll_for_access_token(device_code, interval):
    payload = {
        'client_id': os.getenv("GITHUB_CLIENT_ID"),
        'device_code': device_code,
        'grant_type': 'urn:ietf:params:oauth:grant-type:device_code'
    }
    while True:
        response = requests.post('https://github.com/login/oauth/access_token', data=payload)
        if response.status_code == 200:
            return response.json().get('access_token')
        time.sleep(interval)

def list_repositories(access_token):
    """
    List all repositories for the authenticated user.
    """
    headers = {'Authorization': f'token {access_token}'}
    response = requests.get('https://api.github.com/user/repos', headers=headers)
    repos = response.json()

    repos_without_readme = [repo for repo in repos if not has_readme(repo, access_token)]
    return repos_without_readme

def has_readme(repo, access_token):
    """
    Check if the specified repository has a README.md file.
    """
    headers = {'Authorization': f'token {access_token}'}
    url = f"{repo['contents_url'].replace('{+path}', 'README.md')}"

    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        # README exists
        return True
    return False


def main():
    device_code_response = get_device_code()

    if device_code_response is None:
        print("Failed to retrieve the device code.")
        return

    print("Please visit https://github.com/login/device and enter this code:", device_code_response['user_code'])
    access_token = poll_for_access_token(device_code_response['device_code'], device_code_response['interval'])
    
    if not access_token:
        print("Failed to authenticate with GitHub.")
        return

    print("Successfully authenticated with GitHub.")
    repositories = list_repositories(access_token)

    if not repositories:
        print("No repositories found without a README.md.")
        return

    for repo in repositories:
        print(f"Repository Name: {repo['name']} - URL: {repo['html_url']}")

if __name__ == "__main__":
    main()
